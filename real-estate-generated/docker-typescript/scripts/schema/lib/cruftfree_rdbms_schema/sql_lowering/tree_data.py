"""The lowered SQL tree as plain data, and back.

``tree_to_data`` writes a tree as nested dicts of JSON values and ``tree_from_data``
builds the same tree from them, so a schema snapshot can record the tree a default
lowered to. A node is a dict whose ``kind`` names its class, followed by its fields
in the fixed order :data:`TREE_DATA_FIELDS` gives; a field :data:`OMITTED_WHEN_EMPTY`
names is written only when it holds something, so a builtin call without operands is
``{"kind": "BuiltinCall", "key": ...}`` and every tree has one spelling. An operator is
its DSL spelling, a builtin key its name or ``[category, member]``, and a literal names
its type beside its value, a float written as its shortest round-trip text and an exact
decimal as its own text, so the value reads back exactly and ``true``, ``1``, ``1.0`` and
the decimal ``1.0`` stay distinct. Reading refuses an
unknown kind, a missing or extra key, an omitted-when-empty field written empty, and a
value of the wrong type, naming what it expects.

This module imports only the standard library and this subpackage, because a generated
script carries it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal, InvalidOperation
from enum import Enum
from types import MappingProxyType
from typing import Final, TypeVar

from cruftfree_rdbms_schema.sql_lowering.builtins_table import LoweringKey
from cruftfree_rdbms_schema.sql_lowering.lowered import (
    Aggregate,
    AggregateFunction,
    Arithmetic,
    ArithmeticOperator,
    BooleanOperation,
    BooleanOperator,
    BuiltinCall,
    Comparison,
    ComparisonOperator,
    Concatenation,
    Conditional,
    FieldReference,
    IntegerWidening,
    Literal,
    LiteralValue,
    Negation,
    Not,
    NullTest,
    SqlNode,
)

#: The key naming a node's kind; it comes first in every node's data.
KIND_KEY: Final[str] = "kind"

#: Every kind the data names, with the keys after ``kind``, in the order they are written.
TREE_DATA_FIELDS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "FieldReference": ("name",),
        "Literal": ("type", "value"),
        "Comparison": ("operator", "left", "right", "string_operands"),
        "BooleanOperation": ("operator", "operands"),
        "Not": ("operand",),
        "Arithmetic": ("operator", "left", "right"),
        "Negation": ("operand",),
        "IntegerWidening": ("operand",),
        "NullTest": ("operand", "negated"),
        "Concatenation": ("parts",),
        "BuiltinCall": ("key", "operands"),
        "Aggregate": ("function", "operand"),
        "Conditional": ("condition", "when_true", "when_false"),
    }
)

#: The fields of a kind written only when they hold something; an empty one is omitted,
#: and reading refuses it written empty, so a tree has one spelling. An aggregate without an
#: operand (``count``) omits it; an operand is a node, never an empty list.
OMITTED_WHEN_EMPTY: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
    {"BuiltinCall": frozenset({"operands"}), "Aggregate": frozenset({"operand"})}
)

#: The ``type`` a literal's data names for each kind of value.
_NULL: Final[str] = "null"
_BOOLEAN: Final[str] = "boolean"
_INTEGER: Final[str] = "integer"
_FLOAT: Final[str] = "float"
_DECIMAL: Final[str] = "decimal"
_TEXT: Final[str] = "text"
_LITERAL_TYPES: Final[tuple[str, ...]] = (_NULL, _BOOLEAN, _INTEGER, _FLOAT, _DECIMAL, _TEXT)

#: The length of a ``[category, member]`` builtin key.
_MEMBER_KEY_LENGTH: Final[int] = 2

_OperatorT = TypeVar("_OperatorT", bound=Enum)

#: A node's data as read: its keys checked, its values not yet.
_NodeData = Mapping[str, object]


def _literal_data(value: LiteralValue) -> dict[str, object]:
    if value is None:
        return {"type": _NULL, "value": None}
    if isinstance(value, bool):
        return {"type": _BOOLEAN, "value": value}
    if isinstance(value, int):
        return {"type": _INTEGER, "value": value}
    if isinstance(value, float):
        return {"type": _FLOAT, "value": repr(value)}
    if isinstance(value, Decimal):
        return {"type": _DECIMAL, "value": str(value)}
    return {"type": _TEXT, "value": value}


def tree_to_data(node: SqlNode) -> dict[str, object]:
    """*node* and its operands as nested dicts of JSON values, keys in :data:`TREE_DATA_FIELDS` order."""
    match node:
        case FieldReference():
            return {KIND_KEY: "FieldReference", "name": node.name}
        case Literal():
            return {KIND_KEY: "Literal", **_literal_data(node.value)}
        case Comparison():
            return {
                KIND_KEY: "Comparison",
                "operator": node.operator.value,
                "left": tree_to_data(node.left),
                "right": tree_to_data(node.right),
                "string_operands": node.string_operands,
            }
        case BooleanOperation():
            return {
                KIND_KEY: "BooleanOperation",
                "operator": node.operator.value,
                "operands": [tree_to_data(operand) for operand in node.operands],
            }
        case Not():
            return {KIND_KEY: "Not", "operand": tree_to_data(node.operand)}
        case Arithmetic():
            return {
                KIND_KEY: "Arithmetic",
                "operator": node.operator.value,
                "left": tree_to_data(node.left),
                "right": tree_to_data(node.right),
            }
        case Negation():
            return {KIND_KEY: "Negation", "operand": tree_to_data(node.operand)}
        case IntegerWidening():
            return {KIND_KEY: "IntegerWidening", "operand": tree_to_data(node.operand)}
        case NullTest():
            return {
                KIND_KEY: "NullTest",
                "operand": tree_to_data(node.operand),
                "negated": node.negated,
            }
        case Concatenation():
            return {
                KIND_KEY: "Concatenation",
                "parts": [tree_to_data(part) for part in node.parts],
            }
        case BuiltinCall():
            key = node.key if isinstance(node.key, str) else list(node.key)
            data: dict[str, object] = {KIND_KEY: "BuiltinCall", "key": key}
            if node.operands:
                data["operands"] = [tree_to_data(operand) for operand in node.operands]
            return data
        case Aggregate():
            aggregate: dict[str, object] = {KIND_KEY: "Aggregate", "function": node.function.value}
            if node.operand is not None:
                aggregate["operand"] = tree_to_data(node.operand)
            return aggregate
        case Conditional():
            return {
                KIND_KEY: "Conditional",
                "condition": tree_to_data(node.condition),
                "when_true": tree_to_data(node.when_true),
                "when_false": tree_to_data(node.when_false),
            }
    raise TypeError(
        f"Cannot write {node!r} of type {type(node).__name__} as lowered-tree data. "
        f"Expected: a node of one of the kinds {list(TREE_DATA_FIELDS)}. "
        "Fix: lower the expression to a tree before recording it."
    )


def _refused(kind: str, key: str, value: object, expected: str) -> ValueError:
    return ValueError(
        f"The lowered-tree data of a {kind} has {key}={value!r}. Expected: {expected}. "
        "Fix: record the tree with tree_to_data, never by hand."
    )


def _not_node_data(data: object) -> ValueError:
    # Malformed data is one error, a ValueError like the rest of a snapshot's reading.
    return ValueError(
        f"Lowered-tree data is {data!r} of type {type(data).__name__}. Expected: a dict "
        f"whose {KIND_KEY!r} is one of {list(TREE_DATA_FIELDS)}. "
        "Fix: record the tree with tree_to_data."
    )


def _text(data: _NodeData, kind: str, key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise _refused(kind, key, value, "a string")
    return value


def _flag(data: _NodeData, kind: str, key: str) -> bool:
    value = data[key]
    if not isinstance(value, bool):
        raise _refused(kind, key, value, "true or false")
    return value


def _operator(
    data: _NodeData, kind: str, operator_type: type[_OperatorT]
) -> _OperatorT:
    value = data["operator"]
    for member in operator_type:
        if isinstance(value, str) and member.value == value:
            return member
    raise _refused(
        kind,
        "operator",
        value,
        f"the DSL spelling of a {operator_type.__name__} ({[m.value for m in operator_type]})",
    )


def _child(data: _NodeData, key: str) -> SqlNode:
    return tree_from_data(data[key])


def _children(data: _NodeData, kind: str, key: str) -> tuple[SqlNode, ...]:
    value = data[key]
    if not isinstance(value, list):
        raise _refused(kind, key, value, "a list of node data")
    return tuple(tree_from_data(item) for item in value)


def _literal_value(data: _NodeData) -> LiteralValue:
    literal_type, value = data["type"], data["value"]
    if literal_type == _NULL and value is None:
        return None
    if literal_type == _BOOLEAN and isinstance(value, bool):
        return value
    if literal_type == _INTEGER and type(value) is int:
        return value
    if literal_type == _TEXT and isinstance(value, str):
        return value
    if literal_type == _FLOAT and isinstance(value, str):
        try:
            return float(value)
        except ValueError as error:
            raise _refused("Literal", "value", value, "the text of a float") from error
    if literal_type == _DECIMAL and isinstance(value, str):
        return _decimal_value(value)
    if literal_type not in _LITERAL_TYPES:
        raise _refused(
            "Literal", "type", literal_type, f"one of {list(_LITERAL_TYPES)}"
        )
    raise _refused(
        "Literal",
        "value",
        value,
        f"a value of the literal type {literal_type!r} (a float or a decimal as its text)",
    )


def _decimal_value(text: str) -> Decimal:
    """The finite decimal *text* spells, refusing any other text."""
    try:
        value = Decimal(text)
    except InvalidOperation as error:
        raise _refused("Literal", "value", text, "the text of a decimal") from error
    if not value.is_finite():
        raise _refused("Literal", "value", text, "the text of a finite decimal")
    return value


def _builtin_key(data: _NodeData) -> LoweringKey:
    value = data["key"]
    if isinstance(value, str):
        return value
    if (
        isinstance(value, list)
        and len(value) == _MEMBER_KEY_LENGTH
        and all(isinstance(part, str) for part in value)
    ):
        return (value[0], value[1])
    raise _refused(
        "BuiltinCall",
        "key",
        value,
        "a builtin name or a [category, member] pair of names",
    )


def _builtin_call(data: _NodeData) -> BuiltinCall:
    operands = (
        _children(data, "BuiltinCall", "operands") if "operands" in data else ()
    )
    return BuiltinCall(_builtin_key(data), operands)


def _aggregate(data: _NodeData) -> Aggregate:
    function = data["function"]
    for member in AggregateFunction:
        if isinstance(function, str) and member.value == function:
            operand = _child(data, "operand") if "operand" in data else None
            return Aggregate(member, operand)
    raise _refused(
        "Aggregate",
        "function",
        function,
        f"the DSL spelling of an AggregateFunction ({[m.value for m in AggregateFunction]})",
    )


#: How each kind's node is built from its checked data.
_READERS: Final[Mapping[str, Callable[[_NodeData], SqlNode]]] = MappingProxyType(
    {
        "FieldReference": lambda data: FieldReference(
            _text(data, "FieldReference", "name")
        ),
        "Literal": lambda data: Literal(_literal_value(data)),
        "Comparison": lambda data: Comparison(
            _operator(data, "Comparison", ComparisonOperator),
            _child(data, "left"),
            _child(data, "right"),
            _flag(data, "Comparison", "string_operands"),
        ),
        "BooleanOperation": lambda data: BooleanOperation(
            _operator(data, "BooleanOperation", BooleanOperator),
            _children(data, "BooleanOperation", "operands"),
        ),
        "Not": lambda data: Not(_child(data, "operand")),
        "Arithmetic": lambda data: Arithmetic(
            _operator(data, "Arithmetic", ArithmeticOperator),
            _child(data, "left"),
            _child(data, "right"),
        ),
        "Negation": lambda data: Negation(_child(data, "operand")),
        "IntegerWidening": lambda data: IntegerWidening(_child(data, "operand")),
        "NullTest": lambda data: NullTest(
            _child(data, "operand"), _flag(data, "NullTest", "negated")
        ),
        "Concatenation": lambda data: Concatenation(
            _children(data, "Concatenation", "parts")
        ),
        "BuiltinCall": _builtin_call,
        "Aggregate": _aggregate,
        "Conditional": lambda data: Conditional(
            _child(data, "condition"), _child(data, "when_true"), _child(data, "when_false")
        ),
    }
)


def tree_from_data(data: object) -> SqlNode:
    """The tree *data* records, as :func:`tree_to_data` wrote it.

    Raises:
        ValueError: *data* is not a node's dict, names a kind :data:`TREE_DATA_FIELDS`
            does not hold, misses or adds a key, writes an omitted-when-empty field
            empty, or holds a value of the wrong type.
    """
    if not isinstance(data, dict):
        raise _not_node_data(data)
    kind = data.get(KIND_KEY)
    if not isinstance(kind, str) or kind not in TREE_DATA_FIELDS:
        raise ValueError(
            f"Lowered-tree data names the kind {kind!r}. Expected: one of "
            f"{list(TREE_DATA_FIELDS)}. Fix: record the tree with tree_to_data."
        )
    allowed = {KIND_KEY, *TREE_DATA_FIELDS[kind]}
    optional = OMITTED_WHEN_EMPTY.get(kind, frozenset())
    required = allowed - optional
    missing = sorted(required - set(data))
    extra = sorted(set(data) - allowed)
    if missing or extra:
        raise ValueError(
            f"The lowered-tree data of a {kind} has the keys {sorted(data)}. Expected: "
            f"exactly {sorted(required)}, plus {sorted(optional)} when not empty (missing "
            f"{missing}, extra {extra}). Fix: record the tree with tree_to_data."
        )
    for key in sorted(optional & set(data)):
        if data[key] == []:
            raise _refused(kind, key, data[key], "a non-empty list; an empty one is omitted")
    return _READERS[kind](data)


__all__ = [
    "KIND_KEY",
    "OMITTED_WHEN_EMPTY",
    "TREE_DATA_FIELDS",
    "tree_from_data",
    "tree_to_data",
]
