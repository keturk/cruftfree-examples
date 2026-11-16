"""The SQL of each DSL builtin, per DDL dialect.

A row implements the DSL's definition of its builtin, never the engine's native
function of the same name: the DSL defines each builtin once and every target
realizes that definition, so a row's SQL is whatever construction gives the
definition's value on that dialect. ``definition`` states the definition the SQL
realizes and ``defined_at`` names the DSL declaration it belongs to. A builtin
with no single definition has no row.

A row is keyed by the identity analysis resolves a use to: the bare name for a
bare call (``uuid``) and ``(category, member)`` for a member of a builtin object,
a call on a value included (``("DateTime", "now")``). Its SQL is keyed by the
DDL dialect names the registered RDBMS engines declare.

A row that takes operands declares them in ``operands``, in order: the receiver
of a call on a value first, then the arguments. Its SQL is then a template whose
placeholders ``{0}``, ``{1}``... name the operands by index. A row without
operands holds the SQL itself, the spelling an engine reports for a column
default.

This module imports only the standard library, because a generated script
carries it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import Enum
from string import Formatter
from types import MappingProxyType
from typing import Final

#: A row's key: a bare builtin name, or ``(category, member)``.
LoweringKey = str | tuple[str, str]


class BuiltinOperand(Enum):
    """How a row writes one of its operands."""

    #: A value: the operand's lowered tree, rendered as any expression is.
    VALUE = "value"
    #: A literal pattern of the regex pattern language: the operand is a text
    #: literal, written by the dialect's ``regex_pattern`` row from its text.
    PATTERN = "pattern"


@dataclass(frozen=True)
class LoweringBuiltin:
    """One builtin's SQL on every DDL dialect.

    Attributes:
        key: The identity analysis resolves a use to.
        sql: The SQL that gives the builtin's defined value, keyed by DDL dialect name;
            for a row with operands, a template naming each operand ``{index}``.
        deterministic: Whether every evaluation of the SQL gives the same value.
        definition: The DSL's definition of the builtin's value, which the SQL realizes.
        defined_at: The dotted import path of the builtin's DSL declaration.
        operands: How each operand is written, in order; empty for a builtin taking none.
        narrow_integer: Whether the SQL answers an integer narrower than the DSL's 64-bit
            ``Integer`` on some dialect, so arithmetic over the call widens it first.
    """

    key: LoweringKey
    sql: Mapping[str, str]
    deterministic: bool
    definition: str
    defined_at: str
    operands: tuple[BuiltinOperand, ...] = ()
    narrow_integer: bool = False


def sql_template_indices(sql: str) -> tuple[int, ...]:
    """The operand index each placeholder of the template *sql* names, in order of appearance.

    ``{{`` and ``}}`` are literal braces and name no operand.

    Raises:
        ValueError: A brace is unbalanced, or a placeholder is anything but a bare
            operand index (``{0}``): a name, an empty ``{}``, a conversion or a format spec.
    """
    indices: list[int] = []
    for _text, field, spec, conversion in Formatter().parse(sql):
        if field is None:
            continue
        if not (field.isascii() and field.isdigit()) or spec or conversion:
            raise ValueError(
                f"The builtin SQL template {sql!r} holds a placeholder naming {field!r} "
                f"(conversion {conversion!r}, format spec {spec!r}). Expected: a bare "
                "operand index such as {0}. Fix: name each operand by its index in the "
                "row's operands, and double a literal brace."
            )
        indices.append(int(field))
    return tuple(indices)


def _keyed_by_builtin(
    rows: Iterable[LoweringBuiltin],
) -> Mapping[LoweringKey, LoweringBuiltin]:
    """*rows* keyed by their builtin, read-only.

    Raises:
        ValueError: Two rows name the same builtin.
    """
    table: dict[LoweringKey, LoweringBuiltin] = {}
    for row in rows:
        if row.key in table:
            raise ValueError(
                f"Two lowering rows name the builtin {row.key!r}. A builtin has one definition and "
                "so one row: merge them."
            )
        table[row.key] = row
    return MappingProxyType(table)


LOWERING_BUILTINS: Final[Mapping[LoweringKey, LoweringBuiltin]] = _keyed_by_builtin(
    (
        LoweringBuiltin(
            key="uuid",
            sql=MappingProxyType({"postgresql": "gen_random_uuid()"}),
            deterministic=False,
            definition="a random version-4 UUID in its dashed lowercase text form",
            defined_at="cruftfree_common.builtins.functions.DslBuiltinFunction.UUID",
        ),
        LoweringBuiltin(
            key=("DateTime", "now"),
            sql=MappingProxyType({"postgresql": "CURRENT_TIMESTAMP"}),
            deterministic=False,
            definition="the current instant",
            defined_at="cruftfree_common.builtins.objects.datetime.DateTime.now",
        ),
        # The UTC day, never CURRENT_DATE (the session's TimeZone day). Spelled exactly as
        # PostgreSQL deparses the default, so a reported default reads back to this row.
        LoweringBuiltin(
            key=("Date", "now"),
            sql=MappingProxyType(
                {"postgresql": "((CURRENT_TIMESTAMP AT TIME ZONE 'UTC'::text))::date"}
            ),
            deterministic=False,
            definition="the calendar day of the current instant at UTC",
            defined_at="cruftfree_common.builtins.objects.date.Date.now",
        ),
        # char_length counts characters: one per code point in a UTF-8 database. It answers
        # a 32-bit integer, where the DSL's length is an Integer.
        LoweringBuiltin(
            key=("String", "length"),
            sql=MappingProxyType({"postgresql": "char_length({0})"}),
            deterministic=True,
            definition="the number of code points",
            defined_at="cruftfree_common.builtins.objects.string.String.length",
            operands=(BuiltinOperand.VALUE,),
            narrow_integer=True,
        ),
        # ~ is case-sensitive and takes no flag; the pattern is the whole-value
        # constant the dialect's regex_pattern row writes from the read pattern tree.
        LoweringBuiltin(
            key=("String", "matches"),
            sql=MappingProxyType({"postgresql": "({0} ~ {1})"}),
            deterministic=True,
            definition="a full match of the literal pattern in the pattern language",
            defined_at="cruftfree_common.builtins.objects.string.String.matches",
            operands=(BuiltinOperand.VALUE, BuiltinOperand.PATTERN),
        ),
    )
)

__all__ = [
    "LOWERING_BUILTINS",
    "BuiltinOperand",
    "LoweringBuiltin",
    "LoweringKey",
    "sql_template_indices",
]
