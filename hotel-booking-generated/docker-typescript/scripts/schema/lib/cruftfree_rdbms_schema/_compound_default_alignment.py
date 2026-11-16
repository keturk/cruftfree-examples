"""A live compound column default read as the declared one when both are the same expression.

A compound default (``1 + 2``, ``"a" + "b"``, ``"abc".length()``) is recorded by the declared
snapshot as its DSL source beside its lowered tree. A catalog reader reads the engine's spelling
of it back into a tree (the inverse of the renderer); the two spellings never compare equal, the
trees do. Two trees the renderer writes as the same expression are one default:

- a negated number constant is the negative constant (the engine folds ``-(2)`` into ``-2``);
- a concatenation or a boolean connective inside one of its own kind is one chain (the engine
  nests ``a || b || c`` and flattens ``a AND (b AND c)``);
- a regex pattern operand is compared as the constant the dialect writes it as (a reader reads
  the written pattern, the declaration holds the pattern-language source).

When the live tree is the declared tree under these rules, the live column takes the declared
default; otherwise it keeps what the catalog reported, so a real difference still shows.
"""

from __future__ import annotations

from dataclasses import fields, replace
from decimal import Decimal

from cruftfree_rdbms_schema._snapshot_models import SnapshotDefault
from cruftfree_rdbms_schema.sql_lowering.builtins_table import (
    LOWERING_BUILTINS,
    BuiltinOperand,
)
from cruftfree_rdbms_schema.sql_lowering.dialect_rows import DialectRows, dialect_rows
from cruftfree_rdbms_schema.sql_lowering.lowered import (
    NODE_TYPES,
    BooleanOperation,
    BuiltinCall,
    Concatenation,
    Literal,
    Negation,
    SqlNode,
)


def is_scalar_tree(tree: SqlNode) -> bool:
    """Whether *tree* is a default the per-type canonical forms cover.

    A constant, a negated number constant and a call of a builtin taking no operand
    each have spellings a catalog reports differently; any other tree, a builtin call
    with operands included, is a compound expression.
    """
    if isinstance(tree, Negation):
        return isinstance(tree.operand, Literal)
    if isinstance(tree, BuiltinCall):
        return not tree.operands
    return isinstance(tree, Literal)


def _negated_constant(node: Negation) -> SqlNode:
    """``-(n)`` of a number constant as the constant ``-n``; any other negation as it is."""
    operand = node.operand
    if isinstance(operand, Literal) and isinstance(
        operand.value, int | float | Decimal
    ) and not isinstance(operand.value, bool):
        return Literal(-operand.value)
    return node


def _chained(node: SqlNode) -> SqlNode:
    """A concatenation or connective with each operand of its own kind spliced into it."""
    if isinstance(node, Concatenation):
        return Concatenation(
            tuple(
                part
                for operand in node.parts
                for part in (operand.parts if isinstance(operand, Concatenation) else (operand,))
            )
        )
    if isinstance(node, BooleanOperation):
        return BooleanOperation(
            node.operator,
            tuple(
                item
                for operand in node.operands
                for item in (
                    operand.operands
                    if isinstance(operand, BooleanOperation) and operand.operator is node.operator
                    else (operand,)
                )
            ),
        )
    return node


def _written_patterns(node: BuiltinCall, rows: DialectRows, *, declared: bool) -> BuiltinCall:
    """*node* with each pattern operand as the SQL constant the dialect writes it as.

    A declared operand holds the pattern-language source, written through the dialect's
    ``regex_pattern`` row; a live one holds the constant's text, quoted as any string.
    """
    row = LOWERING_BUILTINS.get(node.key)
    if row is None or len(row.operands) != len(node.operands):
        return node
    operands = tuple(
        Literal(rows.regex_pattern(operand.value) if declared else rows.quote_string(operand.value))
        if form is BuiltinOperand.PATTERN
        and isinstance(operand, Literal)
        and isinstance(operand.value, str)
        else operand
        for form, operand in zip(row.operands, node.operands, strict=True)
    )
    return replace(node, operands=operands)


def _normal(node: SqlNode, rows: DialectRows, *, declared: bool) -> SqlNode:
    """*node* in the one form every spelling of its expression reads back as."""
    changes: dict[str, object] = {}
    for field in fields(node):
        value = getattr(node, field.name)
        if isinstance(value, NODE_TYPES):
            changes[field.name] = _normal(value, rows, declared=declared)
        elif isinstance(value, tuple) and value and all(isinstance(item, NODE_TYPES) for item in value):
            changes[field.name] = tuple(_normal(item, rows, declared=declared) for item in value)
    normal = replace(node, **changes) if changes else node
    if isinstance(normal, Negation):
        return _negated_constant(normal)
    if isinstance(normal, BuiltinCall):
        return _written_patterns(normal, rows, declared=declared)
    return _chained(normal)


# @rule: A live compound default the reader read back takes the declared default when the two trees are one expression
def aligned_compound_default(
    declared: SnapshotDefault | None,
    live: SnapshotDefault | None,
    ddl_dialect: str,
) -> SnapshotDefault | None:
    """*live* as *declared* when both are one compound default on *ddl_dialect*, else *live*.

    Scalar defaults are left to the per-type canonical forms; a live default with no tree
    (one its reader could not read back) is left as reported.

    Raises:
        LookupError: No dialect supplies rows under *ddl_dialect*.
    """
    if declared is None or live is None or declared.tree is None or live.tree is None:
        return live
    if is_scalar_tree(declared.tree):
        return live
    rows = dialect_rows(ddl_dialect)
    if _normal(live.tree, rows, declared=False) == _normal(declared.tree, rows, declared=True):
        return declared
    return live


__all__ = ["aligned_compound_default", "is_scalar_tree"]
