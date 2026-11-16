"""The SQL each DDL dialect writes for the constructs of a lowered expression.

A dialect's rows are its quoting and spelling of the constructs whose SQL differs
between engines: identifier quoting, string-literal quoting, boolean literals,
the typed integer, float and exact-decimal constants, concatenation, the wrapping
of an expression used as a column default, string comparison, and the regex pattern
a whole-value match reads. Everything the SQL standard spells one way on every
engine (``NULL``, an integer outside arithmetic, ``AND``/``OR``/``NOT``, the
comparison and arithmetic operators) is written
by the renderer, and a builtin call is written from its ``LOWERING_BUILTINS`` row,
so a new dialect adds one :class:`DialectRows` here and changes nothing else.

Rows are keyed by the DDL dialect names the registered RDBMS engines declare
(``RdbmsEngine.ddl_dialect``).

This module imports only the standard library, the quoting modules of
``cruftfree_common.utils`` and the regex pattern reader
(``cruftfree_common.builtins.regex_pattern``, which imports only the standard library
and its own stdlib-only modules), because a generated script carries it.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Final

from cruftfree_common.builtins.regex_pattern import read_regex_pattern
from cruftfree_common.builtins.regex_rendering import (
    RegexSpelling,
    hex_code_point_escape,
    render_regex_pattern,
)
from cruftfree_common.utils.hidden_text import (
    EscapeForm,
    escape_hidden,
    hidden_in_source,
)
from cruftfree_common.utils.sql_text import sql_quoted_identifier, sql_string_literal


@dataclass(frozen=True)
class DialectRows:
    """One DDL dialect's SQL for the constructs whose spelling differs between engines.

    Attributes:
        quote_identifier: A field, table or collation name as a quoted identifier.
        quote_string: A text value as a string constant that the engine reads back unchanged.
        boolean_literal: ``True`` or ``False`` as a boolean constant.
        integer_literal: An integer as a constant of the engine's 64-bit integer type, the
            width of the DSL's ``Integer``, so arithmetic over it computes in that width,
            never in the narrower type an engine gives an unadorned constant by its
            spelling. Raises ``ValueError`` for a value outside the 64-bit range.
        integer_widening: A rendered integer expression in the engine's 64-bit integer type,
            so arithmetic over a value the engine holds narrower computes in the DSL's width.
        float_literal: A finite float as a constant of the engine's IEEE 754 double type, so
            arithmetic and comparisons over it compute in binary floating point, as every
            language does, never in exact decimal.
        decimal_literal: A finite exact decimal as a constant of the engine's exact numeric
            type, every digit kept, never passing through a binary floating-point type.
        concatenate: The text concatenation of two or more already-rendered operands.
        expression_default: A rendered expression wrapped so a column ``DEFAULT`` accepts it.
        compare_strings: ``(operator, left, right)``: a comparison of two rendered text
            operands by code point, with no padding and no case or accent folding,
            whatever the operands' collation. *operator* is one of ``=``, ``<>``,
            ``<``, ``<=``, ``>``, ``>=``.
        regex_pattern: A literal pattern of the regex pattern language
            (``read_regex_pattern``) as the string constant the engine's regex match
            operator reads as the whole-value match of the pattern: the read tree in
            explicit forms, never the pattern text. Raises ``RegexPatternError`` for a
            pattern outside the language.
    """

    quote_identifier: Callable[[str], str]
    quote_string: Callable[[str], str]
    boolean_literal: Callable[[bool], str]
    integer_literal: Callable[[int], str]
    integer_widening: Callable[[str], str]
    float_literal: Callable[[float], str]
    decimal_literal: Callable[[Decimal], str]
    concatenate: Callable[[Sequence[str]], str]
    expression_default: Callable[[str], str]
    compare_strings: Callable[[str, str, str], str]
    regex_pattern: Callable[[str], str]


#: The SQL comparison operators a string comparison may apply.
COMPARISON_OPERATORS: Final[frozenset[str]] = frozenset(
    {"=", "<>", "<", "<=", ">", ">="}
)

#: The fewest operands a concatenation joins.
_MIN_CONCATENATION_PARTS: Final[int] = 2


def _refuse_blank(sql: str, construct: str) -> None:
    if not sql.strip():
        raise ValueError(
            f"A {construct} was given blank SQL {sql!r}. Expected: a rendered SQL expression. "
            "Fix: render the operand before passing it to the dialect row."
        )


def _require_comparison_operator(operator_sql: str) -> None:
    if operator_sql not in COMPARISON_OPERATORS:
        raise ValueError(
            f"String comparison operator {operator_sql!r} is not a SQL comparison operator. "
            f"Expected one of {sorted(COMPARISON_OPERATORS)}. Fix: map the DSL operator to "
            "its SQL spelling before rendering the comparison."
        )


def _boolean_constant(true_sql: str, false_sql: str) -> Callable[[bool], str]:
    """A boolean-literal row writing *true_sql* and *false_sql*, refusing a non-``bool``."""

    def boolean_literal(value: bool) -> str:
        if value is True:
            return true_sql
        if value is False:
            return false_sql
        raise TypeError(
            f"A boolean literal was given {value!r} of type {type(value).__name__}. "
            "Expected: True or False. Fix: lower the value to a bool before rendering it."
        )

    return boolean_literal


def _require_finite_float(value: float) -> None:
    """Raise unless *value* is a finite ``float`` (not a ``bool`` or an ``int``)."""
    if type(value) is not float:
        raise TypeError(
            f"A float literal was given {value!r} of type {type(value).__name__}. Expected: a "
            "float. Fix: render an integer or a boolean through its own constant."
        )
    if not math.isfinite(value):
        raise ValueError(
            f"A float literal was given the non-finite float {value!r}, which the languages "
            "and SQL spell differently. Expected: a finite float. Fix: refuse the expression "
            "in the lowering."
        )


#: The range of a 64-bit two's-complement integer, the DSL's ``Integer``.
_INTEGER_64_MIN: Final[int] = -(2**63)
_INTEGER_64_MAX: Final[int] = 2**63 - 1


def _require_integer_64(value: int) -> None:
    """Raise unless *value* is an ``int`` (not a ``bool``) within the 64-bit range."""
    if type(value) is not int:
        raise TypeError(
            f"An integer literal was given {value!r} of type {type(value).__name__}. Expected: "
            "an int. Fix: render a boolean or a float through its own constant."
        )
    if not _INTEGER_64_MIN <= value <= _INTEGER_64_MAX:
        raise ValueError(
            f"An integer literal was given {value}, outside the 64-bit range "
            f"[{_INTEGER_64_MIN}, {_INTEGER_64_MAX}] of the DSL's Integer, so no 64-bit "
            "constant holds it. Expected: a value of that range. Fix: write a value the "
            "field's type holds."
        )


def _require_finite_decimal(value: Decimal) -> None:
    """Raise unless *value* is a finite ``Decimal``."""
    if not isinstance(value, Decimal):
        raise TypeError(
            f"A decimal literal was given {value!r} of type {type(value).__name__}. Expected: "
            "a Decimal. Fix: render a float or an integer through its own constant."
        )
    if not value.is_finite():
        raise ValueError(
            f"A decimal literal was given the non-finite decimal {value!r}, which no exact "
            "numeric constant spells. Expected: a finite Decimal. Fix: refuse the expression "
            "in the lowering."
        )


def _infix_concatenation(operator_sql: str) -> Callable[[Sequence[str]], str]:
    """A concatenation row joining its operands with the infix *operator_sql*, parenthesized."""

    def concatenate(parts: Sequence[str]) -> str:
        if len(parts) < _MIN_CONCATENATION_PARTS:
            raise ValueError(
                f"A concatenation was given {len(parts)} operand(s): {list(parts)!r}. Expected: "
                f"at least {_MIN_CONCATENATION_PARTS}. Fix: render a single operand on its own."
            )
        for part in parts:
            _refuse_blank(part, "concatenation operand")
        return f"({f' {operator_sql} '.join(parts)})"

    return concatenate


def _parenthesized_default(sql: str) -> str:
    """*sql* in parentheses, which every column ``DEFAULT`` grammar accepts as one operand."""
    _refuse_blank(sql, "column default expression")
    return f"({sql})"


# --- PostgreSQL -------------------------------------------------------------------

#: The prefix of a string constant with Unicode escapes (PostgreSQL manual 4.1.2.3).
_UNICODE_ESCAPE_PREFIX: Final[str] = "U&"
_FIRST_SURROGATE: Final[int] = 0xD800
_LAST_SURROGATE: Final[int] = 0xDFFF

#: The collation that orders text by Unicode code point (PostgreSQL manual, "Collation Support").
_CODE_POINT_COLLATION: Final[str] = "ucs_basic"

_POSTGRESQL_CONCATENATION: Final[str] = "||"


def _refuse_surrogates(value: str) -> None:
    """Raise when *value* holds a lone UTF-16 surrogate, which no PostgreSQL text value can carry."""
    for index, char in enumerate(value):
        if _FIRST_SURROGATE <= ord(char) <= _LAST_SURROGATE:
            raise ValueError(
                f"SQL string literal holds the surrogate code point U+{ord(char):04X} at index "
                f"{index}, which PostgreSQL cannot store in a text value (UTF-8 has no encoding "
                "for it, and the engine refuses its escape). Expected: text of whole code points. "
                "Fix: remove the surrogate from the source text before it reaches the emitter."
            )


def _postgresql_string(value: str) -> str:
    """*value* as a standard string constant, or as ``U&'…'`` when it holds a hidden code point.

    Text holding no code point ``hidden_in_source`` flags is a standard-conforming
    string constant: ``'`` doubled, ``\\`` an ordinary character
    (``standard_conforming_strings = on``, the default since PostgreSQL 9.1).
    Otherwise the constant is a string constant with Unicode escapes (PostgreSQL
    manual 4.1.2.3): ``'`` and ``\\`` (the constant's escape character) are
    doubled, then each hidden code point is written ``\\hhhh``, or ``\\+hhhhhh``
    above U+FFFF. The engine stores the decoded value, so the SQL a reviewer reads
    holds every character the database stores, visibly. ``U&`` also needs
    ``standard_conforming_strings = on``.

    Raises:
        ValueError: *value* holds a NUL (the canonical quoter's refusal) or a
            lone surrogate, neither of which a PostgreSQL text value can carry.
    """
    _refuse_surrogates(value)
    if not any(hidden_in_source(char) for char in value):
        return sql_string_literal(value)
    quoted = sql_string_literal(value, escape_backslashes=True)
    return (
        f"{_UNICODE_ESCAPE_PREFIX}{escape_hidden(quoted, EscapeForm.FOUR_OR_PLUS_SIX)}"
    )


def _postgresql_double(value: float) -> str:
    """*value* as a ``DOUBLE PRECISION`` constant, read from its shortest round-trip text.

    A bare ``2.5`` is a ``numeric`` constant on PostgreSQL, which computes in exact
    decimal (``0.1 + 0.2`` is ``0.3``); the languages compute in IEEE 754 double
    (``0.30000000000000004``). The text form is cast straight to ``float8``, so it keeps
    the sign of ``-0.0``, which a ``numeric`` operand would drop.
    """
    _require_finite_float(value)
    return f"CAST({sql_string_literal(repr(value))} AS DOUBLE PRECISION)"


def _postgresql_bigint(value: int) -> str:
    """*value* as a ``BIGINT`` constant.

    PostgreSQL types an unadorned integer constant by its spelling: ``7`` is ``integer``
    (32-bit), so ``2147483647 + 1`` raises "integer out of range" where the DSL's 64-bit
    ``Integer`` gives ``2147483648``. A ``BIGINT`` operand makes the arithmetic 64-bit.
    """
    _require_integer_64(value)
    return f"CAST({value} AS BIGINT)"


def _postgresql_bigint_widening(sql: str) -> str:
    """The rendered integer *sql* as a ``BIGINT``.

    ``smallint * smallint`` computes in ``smallint`` and ``integer * integer`` in
    ``integer``, each raising "out of range" where the DSL's 64-bit ``Integer`` does not.
    """
    _refuse_blank(sql, "integer widening")
    return f"CAST({sql} AS BIGINT)"


def _postgresql_numeric(value: Decimal) -> str:
    """*value* as a ``NUMERIC`` constant, read from its plain decimal text.

    The text is cast straight to ``numeric``, which keeps every digit; a
    ``DOUBLE PRECISION`` constant converted to ``numeric`` keeps only 15 significant
    digits (``DBL_DIG``).
    """
    _require_finite_decimal(value)
    return f"CAST({sql_string_literal(format(value, 'f'))} AS NUMERIC)"


def _postgresql_string_comparison(operator_sql: str, left: str, right: str) -> str:
    """Both operands under the code-point collation, so the answer ignores the columns' collations.

    ``ucs_basic`` exists only in a ``UTF8`` database; on any other encoding the
    engine refuses the statement rather than compare by another order.
    """
    _require_comparison_operator(operator_sql)
    _refuse_blank(left, "string comparison operand")
    _refuse_blank(right, "string comparison operand")
    collation = sql_quoted_identifier(_CODE_POINT_COLLATION)
    return f"({left} COLLATE {collation} {operator_sql} {right} COLLATE {collation})"


def _are_named_group_head(_name: str) -> str:
    """An ARE has no named group: a named group is a plain capturing ``(``, numbered
    by its opening parenthesis like every other."""
    return "("


#: PostgreSQL's advanced regular expression (manual 9.7.3): outside a bracket
#: expression ``^ $ \\ . * + ? ( ) [ ] { } |`` are syntax (9.7.3.2); inside one a
#: backslash starts an escape, so ``\\ ] [ ^ -`` are escaped; every code point outside
#: printable ASCII is the character-entry escape ``\\uHHHH`` / ``\\UHHHHHHHH``
#: (9.7.3.3); ``\\A``/``\\Z`` are the constraint escapes for the edges of the whole
#: string, which no matching flag moves.
_ARE_SPELLING: Final[RegexSpelling] = RegexSpelling(
    syntax=frozenset("^$\\.*+?()[]{}|"),
    set_syntax=frozenset("\\][^-"),
    code_point_escape=hex_code_point_escape,
    start_anchor="\\A",
    end_anchor="\\Z",
    named_group_head=_are_named_group_head,
)


def _postgresql_regex_pattern(pattern: str) -> str:
    """*pattern* read in the regex pattern language and written as a whole-value ARE constant.

    The read tree is rendered with explicit forms only (``cruftfree-builtins.md`` § Regex
    patterns › Rendering): every set a bracket expression of its ranges (no shorthand
    class, no ``.``), a single code point an atom, syntax escaped, every code point
    outside printable ASCII a character-entry escape, ``^``/``$`` the string edges
    ``\\A``/``\\Z``. The whole is wrapped as ``\\A(?:...)\\Z``, so ``~`` (case-sensitive,
    no flag) is the whole-value match, and quoted as a standard string constant: the
    source is printable ASCII, so ``\\`` stays an ordinary character of the constant.

    Raises:
        RegexPatternError: *pattern* is outside the regex pattern language.
    """
    return _postgresql_string(
        render_regex_pattern(
            read_regex_pattern(pattern), _ARE_SPELLING, whole_value=True
        )
    )


POSTGRESQL_ROWS: Final[DialectRows] = DialectRows(
    quote_identifier=sql_quoted_identifier,
    quote_string=_postgresql_string,
    boolean_literal=_boolean_constant("TRUE", "FALSE"),
    integer_literal=_postgresql_bigint,
    integer_widening=_postgresql_bigint_widening,
    float_literal=_postgresql_double,
    decimal_literal=_postgresql_numeric,
    concatenate=_infix_concatenation(_POSTGRESQL_CONCATENATION),
    expression_default=_parenthesized_default,
    compare_strings=_postgresql_string_comparison,
    regex_pattern=_postgresql_regex_pattern,
)


#: Every DDL dialect's rows, keyed by the dialect name its RDBMS engines declare.
DIALECT_ROWS: Final[Mapping[str, DialectRows]] = MappingProxyType(
    {"postgresql": POSTGRESQL_ROWS}
)


def dialect_rows(ddl_dialect: str) -> DialectRows:
    """The rows of *ddl_dialect*.

    Raises:
        LookupError: No dialect supplies rows under *ddl_dialect*; the message names
            the dialects that do.
    """
    if ddl_dialect not in DIALECT_ROWS:
        raise LookupError(
            f"No SQL dialect rows for the DDL dialect {ddl_dialect!r}. Registered: "
            f"{sorted(DIALECT_ROWS)}. Fix: name the DDL dialect a registered RDBMS engine "
            "declares, or add that dialect's DialectRows to DIALECT_ROWS."
        )
    return DIALECT_ROWS[ddl_dialect]


__all__ = [
    "COMPARISON_OPERATORS",
    "DIALECT_ROWS",
    "POSTGRESQL_ROWS",
    "DialectRows",
    "dialect_rows",
]
