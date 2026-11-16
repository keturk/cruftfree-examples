"""The tree of a DSL expression lowered to SQL, before any dialect spells it.

Each node is a frozen dataclass naming one construct: a field reference, a
literal, a comparison, a boolean operation, a negation, arithmetic, an integer
widening, a ``null`` test, a concatenation, a call of a builtin that names a ``LOWERING_BUILTINS``
row, an aggregate over the rows of a group, or a conditional. The tree holds no SQL text; a renderer writes it for one DDL dialect.
Operators carry the DSL's spelling, so the lowering maps an analyzed operator to
its member by value. A node refuses a malformed shape when it is built, so a tree
that exists is one a renderer can write.

This module imports only the standard library and this subpackage, because a
generated script carries it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Final

from cruftfree_rdbms_schema.sql_lowering.builtins_table import LoweringKey


class ComparisonOperator(Enum):
    """A comparison, by its DSL spelling."""

    EQUAL = "=="
    NOT_EQUAL = "!="
    LESS = "<"
    LESS_OR_EQUAL = "<="
    GREATER = ">"
    GREATER_OR_EQUAL = ">="


class BooleanOperator(Enum):
    """A boolean connective, by its DSL spelling."""

    AND = "&&"
    OR = "||"


class ArithmeticOperator(Enum):
    """A binary arithmetic operator, by its DSL spelling."""

    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"


#: The value types a literal holds; ``None`` is the null literal. A ``Decimal`` is an
#: exact decimal constant: a fractional literal stored in an exact-decimal column.
LiteralValue = str | int | float | Decimal | bool | None

#: The fewest operands a concatenation or a boolean operation joins.
_MIN_JOINED_OPERANDS: Final[int] = 2

#: The length of a ``(category, member)`` builtin key.
_MEMBER_KEY_LENGTH: Final[int] = 2


def _require_node(value: object, role: str) -> None:
    if not isinstance(value, NODE_TYPES):
        raise TypeError(
            f"The {role} of a lowered SQL node is {value!r} of type {type(value).__name__}. "
            f"Expected: one of {[node.__name__ for node in NODE_TYPES]}. "
            "Fix: lower the operand to a node before building its parent."
        )


def _require_operator(value: object, operator_type: type[Enum], node: str) -> None:
    if not isinstance(value, operator_type):
        raise TypeError(
            f"A {node} was given the operator {value!r}. Expected: a member of "
            f"{operator_type.__name__} ({[member.value for member in operator_type]}). "
            f"Fix: map the DSL operator to {operator_type.__name__} by its spelling."
        )


def _require_joined_operands(operands: object, node: str) -> None:
    if not isinstance(operands, tuple):
        raise TypeError(
            f"A {node} was given operands of type {type(operands).__name__}. Expected: a "
            "tuple, so the node stays immutable and hashable. Fix: pass tuple(operands)."
        )
    if len(operands) < _MIN_JOINED_OPERANDS:
        raise ValueError(
            f"A {node} was given {len(operands)} operand(s): {operands!r}. Expected: at "
            f"least {_MIN_JOINED_OPERANDS}. Fix: lower a single operand on its own."
        )
    for operand in operands:
        _require_node(operand, f"operand of a {node}")


@dataclass(frozen=True)
class FieldReference:
    """A reference to the column of the field *name*, which a renderer quotes."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(
                f"A field reference was given the name {self.name!r}. Expected: a non-blank "
                "field name. Fix: lower the reference from the analyzed field's name."
            )


@dataclass(frozen=True, eq=False)
class Literal:
    """A constant: text, an integer, a finite float, a finite exact decimal, a boolean, or
    ``None`` for null.

    Two literals are equal only when their values have the same type and spelling, so
    ``True``, ``1`` and ``1.0``, which Python counts equal but SQL spells differently,
    stay distinct nodes, as do the decimals ``1.0`` and ``1.00``.
    """

    value: LiteralValue

    def _identity(self) -> tuple[type, object]:
        spelled = str(self.value) if isinstance(self.value, Decimal) else self.value
        return type(self.value), spelled

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Literal):
            return NotImplemented
        return self._identity() == other._identity()

    def __hash__(self) -> int:
        return hash(self._identity())

    def __post_init__(self) -> None:
        if self.value is not None and not isinstance(self.value, str | int | float | Decimal):
            raise TypeError(
                f"A literal was given {self.value!r} of type {type(self.value).__name__}. "
                "Expected: str, int, float, Decimal, bool or None. Fix: lower the value to "
                "one of those types."
            )
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError(
                f"A literal was given the non-finite float {self.value!r}, which no SQL "
                "numeric constant spells. Expected: a finite float. Fix: refuse the "
                "expression in the lowering."
            )
        if isinstance(self.value, Decimal) and not self.value.is_finite():
            raise ValueError(
                f"A literal was given the non-finite decimal {self.value!r}, which no SQL "
                "numeric constant spells. Expected: a finite Decimal. Fix: refuse the "
                "expression in the lowering."
            )


@dataclass(frozen=True)
class Comparison:
    """``left operator right``; *string_operands* marks a comparison of two ``String`` operands."""

    operator: ComparisonOperator
    left: SqlNode
    right: SqlNode
    string_operands: bool

    def __post_init__(self) -> None:
        _require_operator(self.operator, ComparisonOperator, "comparison")
        _require_node(self.left, "left operand of a comparison")
        _require_node(self.right, "right operand of a comparison")
        if not isinstance(self.string_operands, bool):
            raise TypeError(
                f"A comparison was given string_operands={self.string_operands!r}. "
                "Expected: a bool. Fix: set it from the analyzed operand types."
            )


@dataclass(frozen=True)
class BooleanOperation:
    """Two or more operands joined by one boolean connective."""

    operator: BooleanOperator
    operands: tuple[SqlNode, ...]

    def __post_init__(self) -> None:
        _require_operator(self.operator, BooleanOperator, "boolean operation")
        _require_joined_operands(self.operands, "boolean operation")


@dataclass(frozen=True)
class Not:
    """The boolean negation of *operand*."""

    operand: SqlNode

    def __post_init__(self) -> None:
        _require_node(self.operand, "operand of a boolean negation")


@dataclass(frozen=True)
class Arithmetic:
    """``left operator right`` over numbers."""

    operator: ArithmeticOperator
    left: SqlNode
    right: SqlNode

    def __post_init__(self) -> None:
        _require_operator(self.operator, ArithmeticOperator, "arithmetic operation")
        _require_node(self.left, "left operand of an arithmetic operation")
        _require_node(self.right, "right operand of an arithmetic operation")


@dataclass(frozen=True)
class Negation:
    """The arithmetic negation of *operand*."""

    operand: SqlNode

    def __post_init__(self) -> None:
        _require_node(self.operand, "operand of an arithmetic negation")


@dataclass(frozen=True)
class IntegerWidening:
    """*operand*, an integer narrower than the DSL's ``Integer``, in that 64-bit width."""

    operand: SqlNode

    def __post_init__(self) -> None:
        _require_node(self.operand, "operand of an integer widening")


@dataclass(frozen=True)
class NullTest:
    """Whether *operand* is null, or with *negated* whether it is not."""

    operand: SqlNode
    negated: bool

    def __post_init__(self) -> None:
        _require_node(self.operand, "operand of a null test")
        if not isinstance(self.negated, bool):
            raise TypeError(
                f"A null test was given negated={self.negated!r}. Expected: a bool. "
                "Fix: set it from the DSL operator (== null or != null)."
            )


@dataclass(frozen=True)
class Concatenation:
    """The text concatenation of two or more operands, in order."""

    parts: tuple[SqlNode, ...]

    def __post_init__(self) -> None:
        _require_joined_operands(self.parts, "concatenation")


@dataclass(frozen=True)
class BuiltinCall:
    """A call of the builtin whose ``LOWERING_BUILTINS`` row is keyed *key*.

    *operands* are the call's operands in the order the row declares them: the
    receiver of a call on a value first, then the arguments; empty for a builtin
    that takes none.
    """

    key: LoweringKey
    operands: tuple[SqlNode, ...] = ()

    def __post_init__(self) -> None:
        bare = isinstance(self.key, str) and bool(self.key.strip())
        member = (
            isinstance(self.key, tuple)
            and len(self.key) == _MEMBER_KEY_LENGTH
            and all(isinstance(part, str) and part.strip() for part in self.key)
        )
        if not (bare or member):
            raise ValueError(
                f"A builtin call was given the key {self.key!r}. Expected: a non-blank "
                "builtin name, or a (category, member) pair of non-blank names. Fix: key "
                "the call by the identity analysis resolved the builtin to."
            )
        if not isinstance(self.operands, tuple):
            raise TypeError(
                f"A builtin call was given operands of type {type(self.operands).__name__}. "
                "Expected: a tuple, so the node stays immutable and hashable. Fix: pass "
                "tuple(operands)."
            )
        for operand in self.operands:
            _require_node(operand, "operand of a builtin call")


class AggregateFunction(Enum):
    """An aggregate over the rows of a group, by its DSL spelling."""

    SUM = "sum"
    COUNT = "count"
    MIN = "min"
    MAX = "max"


@dataclass(frozen=True)
class Aggregate:
    """The *function* of *operand* over the rows of a group; ``COUNT`` with no operand counts the rows."""

    function: AggregateFunction
    operand: SqlNode | None = None

    def __post_init__(self) -> None:
        _require_operator(self.function, AggregateFunction, "aggregate")
        if self.operand is None:
            if self.function is not AggregateFunction.COUNT:
                raise ValueError(
                    f"An aggregate {self.function.value} was given no operand. Expected: an "
                    "operand; only count counts rows without one. Fix: lower the operand of "
                    "the aggregate before building it."
                )
            return
        _require_node(self.operand, "operand of an aggregate")


@dataclass(frozen=True)
class Conditional:
    """*when_true* where *condition* holds, else *when_false*."""

    condition: SqlNode
    when_true: SqlNode
    when_false: SqlNode

    def __post_init__(self) -> None:
        _require_node(self.condition, "condition of a conditional")
        _require_node(self.when_true, "true branch of a conditional")
        _require_node(self.when_false, "false branch of a conditional")


#: A node of the lowered SQL tree.
SqlNode = (
    FieldReference
    | Literal
    | Comparison
    | BooleanOperation
    | Not
    | Arithmetic
    | Negation
    | IntegerWidening
    | NullTest
    | Concatenation
    | BuiltinCall
    | Aggregate
    | Conditional
)

#: Every node class, in the order :data:`SqlNode` names them.
NODE_TYPES: Final[tuple[type, ...]] = (
    FieldReference,
    Literal,
    Comparison,
    BooleanOperation,
    Not,
    Arithmetic,
    Negation,
    IntegerWidening,
    NullTest,
    Concatenation,
    BuiltinCall,
    Aggregate,
    Conditional,
)


@dataclass(frozen=True)
class SqlExpression:
    """A lowered expression: its tree and the SQL a renderer wrote for it."""

    tree: SqlNode
    sql: str

    def __post_init__(self) -> None:
        _require_node(self.tree, "tree of a lowered expression")
        if not isinstance(self.sql, str) or not self.sql.strip():
            raise ValueError(
                f"A lowered expression was given the SQL {self.sql!r}. Expected: the "
                "non-blank SQL rendered from its tree. Fix: render the tree before pairing it."
            )


__all__ = [
    "NODE_TYPES",
    "Aggregate",
    "AggregateFunction",
    "Arithmetic",
    "ArithmeticOperator",
    "BooleanOperation",
    "BooleanOperator",
    "BuiltinCall",
    "Comparison",
    "ComparisonOperator",
    "Concatenation",
    "Conditional",
    "FieldReference",
    "IntegerWidening",
    "Literal",
    "LiteralValue",
    "Negation",
    "Not",
    "NullTest",
    "SqlExpression",
    "SqlNode",
]
