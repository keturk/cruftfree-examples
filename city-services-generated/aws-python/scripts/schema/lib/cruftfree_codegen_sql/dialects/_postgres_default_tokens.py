"""Tokens and tree nodes of the PostgreSQL default reader."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType
from typing import Final

from cruftfree_rdbms_schema.sql_lowering.builtins_table import (
    BuiltinOperand,
    LoweringKey,
)
from cruftfree_rdbms_schema.sql_lowering.lowered import (
    ArithmeticOperator,
    BooleanOperator,
    ComparisonOperator,
    Literal,
    Negation,
    SqlNode,
)
from cruftfree_rdbms_schema.sql_lowering.render import (
    ARITHMETIC_SQL,
    BOOLEAN_SQL,
    COMPARISON_SQL,
)

# ── Tokens ──

_TOKEN_RE: Final[re.Pattern[str]] = re.compile(
    r"""
    (?P<space>\s+)
    | (?P<placeholder>\{\d+\})
    | (?P<escape_string>[EeUu]&?')
    | (?P<string>'(?:[^']|'')*')
    | (?P<number>\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)
    | (?P<quoted>"(?:[^"]|"")*")
    | (?P<word>[A-Za-z_][A-Za-z0-9_$]*)
    | (?P<operator>::|\|\||<=|>=|<>|!=|[(),.+\-*/%<>=~\[\]])
    """,
    re.VERBOSE,
)

#: The words PostgreSQL's expression grammar reads as keywords, never as a name.
_KEYWORDS: Final[frozenset[str]] = frozenset(
    {"and", "or", "not", "is", "null", "true", "false", "collate", "at"}
)

#: The cast types whose quoted constant is an integer, a float, an exact decimal, a boolean.
_INTEGER_TYPES: Final[frozenset[str]] = frozenset(
    {"integer", "bigint", "smallint", "int", "int2", "int4", "int8"}
)
_INTEGER_64_TYPES: Final[frozenset[str]] = frozenset({"bigint", "int8"})
_FLOAT_TYPES: Final[frozenset[str]] = frozenset(
    {"double precision", "real", "float4", "float8"}
)
_DECIMAL_TYPES: Final[frozenset[str]] = frozenset({"numeric", "decimal"})
_BOOLEAN_TYPE: Final[str] = "boolean"
_BOOLEAN_TRUE_SPELLINGS: Final[frozenset[str]] = frozenset({"true", "t"})
_BOOLEAN_FALSE_SPELLINGS: Final[frozenset[str]] = frozenset({"false", "f"})

_NOT_EQUAL_ALIAS: Final[str] = "!="


class _Unreadable(Exception):
    """The text is no default the renderer writes; :func:`read_postgres_default` answers ``None``."""


@dataclass(frozen=True)
class _Token:
    kind: str
    text: str


def _tokens(sql: str) -> list[_Token]:
    """*sql* as tokens; an escape string constant or an unknown character is unreadable."""
    tokens: list[_Token] = []
    position = 0
    while position < len(sql):
        match = _TOKEN_RE.match(sql, position)
        if match is None or match.lastgroup == "escape_string":
            raise _Unreadable(sql[position:])
        position = match.end()
        if match.lastgroup != "space":
            tokens.append(_Token(str(match.lastgroup), match.group()))
    return tokens


# ── The deparse grammar, parsed into its own small tree ──


@dataclass(frozen=True)
class _Number:
    text: str


@dataclass(frozen=True)
class _String:
    text: str


@dataclass(frozen=True)
class _Constant:
    """``TRUE``, ``FALSE`` or ``NULL``."""

    word: str


@dataclass(frozen=True)
class _Word:
    """A bare name: a keyword constant such as ``CURRENT_TIMESTAMP``."""

    name: str


@dataclass(frozen=True)
class _Placeholder:
    index: int


@dataclass(frozen=True)
class _Call:
    name: str
    arguments: tuple[object, ...]


@dataclass(frozen=True)
class _Cast:
    operand: object
    type_name: str


@dataclass(frozen=True)
class _Collate:
    operand: object
    collation: str


@dataclass(frozen=True)
class _Binary:
    operator: str
    left: object
    right: object


@dataclass(frozen=True)
class _Connective:
    """``AND`` / ``OR`` over two or more operands."""

    operator: str
    operands: tuple[object, ...]


@dataclass(frozen=True)
class _Prefix:
    """``NOT x`` or ``- x``."""

    operator: str
    operand: object


@dataclass(frozen=True)
class _AtTimeZone:
    """``operand AT TIME ZONE zone``, which only a builtin's row writes."""

    operand: object
    zone: object


@dataclass(frozen=True)
class _IsNull:
    operand: object
    negated: bool


_COMPARISON_OPERATORS: Final[frozenset[str]] = frozenset(
    {*COMPARISON_SQL.values(), _NOT_EQUAL_ALIAS, "~"}
)
_ADDITIVE_OPERATORS: Final[frozenset[str]] = frozenset({"+", "-", "||"})
_MULTIPLICATIVE_OPERATORS: Final[frozenset[str]] = frozenset({"*", "/", "%"})


def _name(token: _Token) -> str:
    """A word or quoted identifier as a name: a word folded to lower case, as PostgreSQL folds it."""
    if token.kind == "quoted":
        return token.text[1:-1].replace('""', '"')
    return token.text.lower()


# ── What the dialect's own rows render, read with the same grammar ──


@dataclass(frozen=True)
class _RowForm:
    """One builtin's SQL on PostgreSQL, parsed: its key, its operand forms and its template."""

    key: LoweringKey
    operands: tuple[BuiltinOperand, ...]
    template: object


_COMPARISONS: Final[Mapping[str, ComparisonOperator]] = MappingProxyType(
    {sql: operator for operator, sql in COMPARISON_SQL.items()}
)
_ARITHMETIC: Final[Mapping[str, ArithmeticOperator]] = MappingProxyType(
    {sql: operator for operator, sql in ARITHMETIC_SQL.items()}
)
_CONNECTIVES: Final[Mapping[str, BooleanOperator]] = MappingProxyType(
    {sql.lower(): operator for operator, sql in BOOLEAN_SQL.items()}
)


def _bind_all(
    templates: tuple[object, ...],
    nodes: tuple[object, ...],
    bindings: dict[int, object],
) -> bool:
    return len(templates) == len(nodes) and all(
        _bind(template, node, bindings)
        for template, node in zip(templates, nodes, strict=True)
    )


def _bind(template: object, node: object, bindings: dict[int, object]) -> bool:
    """Whether *node* is *template* with each placeholder bound to a subtree (into *bindings*)."""
    if isinstance(template, _Placeholder):
        bindings[template.index] = node
        return True
    if isinstance(template, _Call) and isinstance(node, _Call):
        return template.name == node.name and _bind_all(
            template.arguments, node.arguments, bindings
        )
    if isinstance(template, _Binary) and isinstance(node, _Binary):
        return template.operator == node.operator and _bind_all(
            (template.left, template.right), (node.left, node.right), bindings
        )
    return template == node


def _uncast(node: object) -> object:
    """*node* without the casts PostgreSQL wrapped around it."""
    while isinstance(node, _Cast):
        node = node.operand
    return node


def _pattern(node: object) -> Literal:
    """A pattern operand: the text constant the dialect's ``regex_pattern`` row wrote."""
    constant = _uncast(node)
    if not isinstance(constant, _String):
        raise _Unreadable(repr(node))
    return Literal(constant.text)


def _float(text: str) -> Literal:
    value = float(text)
    if not math.isfinite(value):
        raise _Unreadable(text)
    return Literal(value)


def _decimal(text: str) -> Literal:
    try:
        value = Decimal(text)
    except InvalidOperation as error:
        raise _Unreadable(text) from error
    if not value.is_finite():
        raise _Unreadable(text)
    return Literal(value)


def _number(text: str) -> Literal:
    """A bare number: an integer, or an exact decimal when it has a fraction or an exponent.

    PostgreSQL prints an ``integer`` constant bare and a ``numeric`` one bare when it has a
    fraction; a ``double precision`` constant always carries its cast.
    """
    if "." in text or "e" in text.lower():
        return _decimal(text)
    return Literal(int(text))


def _typed_constant(text: str, type_name: str) -> Literal:
    """The quoted constant *text* of a cast to *type_name*: a number, a boolean or a text."""
    if type_name in _INTEGER_TYPES:
        return Literal(int(text.strip()))
    if type_name in _FLOAT_TYPES:
        return _float(text.strip())
    if type_name in _DECIMAL_TYPES:
        return _decimal(text.strip())
    if type_name == _BOOLEAN_TYPE:
        spelled = text.strip().lower()
        if spelled in _BOOLEAN_TRUE_SPELLINGS:
            return Literal(True)
        if spelled in _BOOLEAN_FALSE_SPELLINGS:
            return Literal(False)
        raise _Unreadable(text)
    return Literal(text)


def _is_number_constant(tree: SqlNode) -> bool:
    """Whether *tree* is a constant or its negation, whose cast the renderer writes itself."""
    return isinstance(tree.operand if isinstance(tree, Negation) else tree, Literal)


def _is_widening(node: object) -> bool:
    """Whether *node* is a cast of an expression to the 64-bit integer, which only the renderer writes."""
    return (
        isinstance(node, _Cast)
        and node.type_name in _INTEGER_64_TYPES
        and not isinstance(node.operand, _String)
    )
