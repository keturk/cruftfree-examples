"""The SQL of a lowered expression tree, written for one DDL dialect.

:func:`render_sql` writes every node of a tree from ``lowered.py``. What differs
between engines comes from the dialect's rows (``dialect_rows.py``): field
references, string, boolean, float and exact-decimal literals, an integer operand of
arithmetic (a constant of the DSL's 64-bit ``Integer`` width), an integer widening,
concatenation and string comparison. What the SQL standard spells one way on every engine is written here:
``NULL``, any other integer, ``IS [NOT] NULL``, ``AND``/``OR``/``NOT``, the comparison operators
``=``/``<>``/``<``/``<=``/``>``/``>=``, ``+``/``-``/``*``, unary ``-``, the aggregates
``SUM``/``COUNT``/``MIN``/``MAX`` and ``CASE WHEN ... THEN ... ELSE ... END``. A builtin
call is written from its ``LOWERING_BUILTINS`` row's SQL for the dialect; a row that
takes operands is a template, filled with each operand as the row declares it (a value
rendered as any expression, a pattern through the dialect's ``regex_pattern`` row).

Every compound node is parenthesized, so the SQL means the tree whatever the
engine's operator precedence, and a negative integer is parenthesized too, so a
unary minus never meets it as ``--``, which opens a comment.

:func:`column_default_sql` writes a tree as a column ``DEFAULT``, wrapped by the
dialect's ``expression_default`` row; :func:`builtin_call_for_sql` reads a
builtin call's SQL back to its row, the inverse of :func:`builtin_call_sql`.

This module imports only the standard library, this subpackage, and the quoting
modules of ``cruftfree_common.utils``, because a generated script carries it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from decimal import Decimal
from types import MappingProxyType
from typing import Final

from cruftfree_common.utils.hidden_text import hidden_in_source

from cruftfree_rdbms_schema.sql_lowering.builtins_table import (
    LOWERING_BUILTINS,
    BuiltinOperand,
    LoweringBuiltin,
    LoweringKey,
)
from cruftfree_rdbms_schema.sql_lowering.dialect_rows import DialectRows, dialect_rows
from cruftfree_rdbms_schema.sql_lowering.lowered import (
    NODE_TYPES,
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

#: The SQL of each comparison operator.
COMPARISON_SQL: Final[Mapping[ComparisonOperator, str]] = MappingProxyType(
    {
        ComparisonOperator.EQUAL: "=",
        ComparisonOperator.NOT_EQUAL: "<>",
        ComparisonOperator.LESS: "<",
        ComparisonOperator.LESS_OR_EQUAL: "<=",
        ComparisonOperator.GREATER: ">",
        ComparisonOperator.GREATER_OR_EQUAL: ">=",
    }
)

#: The SQL of each boolean connective.
BOOLEAN_SQL: Final[Mapping[BooleanOperator, str]] = MappingProxyType(
    {BooleanOperator.AND: "AND", BooleanOperator.OR: "OR"}
)

#: The SQL of each binary arithmetic operator.
ARITHMETIC_SQL: Final[Mapping[ArithmeticOperator, str]] = MappingProxyType(
    {
        ArithmeticOperator.ADD: "+",
        ArithmeticOperator.SUBTRACT: "-",
        ArithmeticOperator.MULTIPLY: "*",
    }
)

#: The SQL of each aggregate function.
AGGREGATE_SQL: Final[Mapping[AggregateFunction, str]] = MappingProxyType(
    {
        AggregateFunction.SUM: "SUM",
        AggregateFunction.COUNT: "COUNT",
        AggregateFunction.MIN: "MIN",
        AggregateFunction.MAX: "MAX",
    }
)

_NULL: Final[str] = "NULL"
_MINUS: Final[str] = "-"

#: How a node is written: its tree, the dialect's rows and the dialect's name to its SQL.
_Renderer = Callable[[SqlNode, DialectRows, str], str]


def builtin_call_sql(
    builtins: Mapping[LoweringKey, LoweringBuiltin], key: LoweringKey, ddl_dialect: str
) -> str:
    """The SQL *builtins* gives the builtin *key* on *ddl_dialect*.

    Raises:
        LookupError: *builtins* holds no row for *key*, or the row holds no SQL
            for *ddl_dialect*; the message names what the table does hold.
    """
    if key not in builtins:
        raise LookupError(
            f"No lowering row for the builtin {key!r}. Rows: {sorted(map(str, builtins))}. "
            "Fix: refuse the builtin in the lowering, or add its row (with its DSL "
            "definition) to LOWERING_BUILTINS."
        )
    row = builtins[key]
    if ddl_dialect not in row.sql:
        raise LookupError(
            f"The lowering row of the builtin {key!r} holds no SQL for the DDL dialect "
            f"{ddl_dialect!r}; it holds SQL for {sorted(row.sql)}. Fix: add the "
            f"{ddl_dialect!r} SQL that gives {row.definition!r} to the row."
        )
    return row.sql[ddl_dialect]


def _integer(value: int) -> str:
    """*value* as an integer constant, parenthesized when negative."""
    text = str(value)
    return f"({text})" if text.startswith(_MINUS) else text


def _literal(value: LiteralValue, rows: DialectRows) -> str:
    """The constant *value*; ``bool`` is matched before ``int``, which it subclasses."""
    match value:
        case None:
            return _NULL
        case bool():
            return rows.boolean_literal(value)
        case int():
            return _integer(value)
        case float():
            return rows.float_literal(value)
        case Decimal():
            return rows.decimal_literal(value)
        case str():
            return rows.quote_string(value)
    raise TypeError(
        f"A literal holds {value!r} of type {type(value).__name__}, which no SQL constant "
        "spells. Expected: str, int, float, Decimal, bool or None."
    )


def _conditional(
    node: Conditional, rows: DialectRows, ddl_dialect: str, branch: _Renderer
) -> str:
    """``CASE WHEN ... THEN ... ELSE ... END``, each branch written by *branch*."""
    return (
        f"(CASE WHEN {_render(node.condition, rows, ddl_dialect)} "
        f"THEN {branch(node.when_true, rows, ddl_dialect)} "
        f"ELSE {branch(node.when_false, rows, ddl_dialect)} END)"
    )


def _arithmetic_operand(node: SqlNode, rows: DialectRows, ddl_dialect: str) -> str:
    """An operand of ``+ - *``, each integer constant in it in the DSL's integer width.

    An engine types an unadorned integer constant by its spelling (``7`` is 32-bit on
    PostgreSQL), and arithmetic over two such operands computes in that width, so
    ``2147483647 + 1`` would overflow where the DSL's 64-bit ``Integer`` does not. The
    dialect's ``integer_literal`` row writes the 64-bit constant; a constant under a
    negation or in a conditional's branch is the operand's value too, so it is widened
    there as well. Outside arithmetic an integer stays unadorned: a comparison or a
    column default never computes in the constant's width.
    """
    match node:
        case Literal(value=int() as value) if not isinstance(value, bool):
            return rows.integer_literal(value)
        case Negation(operand=operand):
            return f"({_MINUS}{_arithmetic_operand(operand, rows, ddl_dialect)})"
        case Conditional():
            return _conditional(node, rows, ddl_dialect, _arithmetic_operand)
    return _render(node, rows, ddl_dialect)


def _pattern_operand(operand: SqlNode, rows: DialectRows, key: LoweringKey) -> str:
    """The text literal *operand* as the dialect's whole-value regex constant."""
    if isinstance(operand, Literal) and isinstance(operand.value, str):
        return rows.regex_pattern(operand.value)
    raise ValueError(
        f"The pattern operand of a call of the builtin {key!r} is {operand!r}. Expected: a "
        "text literal, the only pattern the regex pattern language reads before the "
        "query runs. Fix: lower the call only when its pattern is a string literal."
    )


def _builtin_call(node: BuiltinCall, rows: DialectRows, ddl_dialect: str) -> str:
    """*node* as its row's SQL, the template filled with each operand as the row declares it."""
    sql = builtin_call_sql(LOWERING_BUILTINS, node.key, ddl_dialect)
    forms = LOWERING_BUILTINS[node.key].operands
    if len(node.operands) != len(forms):
        raise ValueError(
            f"The call of the builtin {node.key!r} carries {len(node.operands)} operand(s); "
            f"its LOWERING_BUILTINS row declares {len(forms)} "
            f"({[form.value for form in forms]}). Fix: lower the call with exactly the "
            "operands its row declares."
        )
    if not forms:
        return sql
    rendered = [
        _pattern_operand(operand, rows, node.key)
        if form is BuiltinOperand.PATTERN
        else _render(operand, rows, ddl_dialect)
        for form, operand in zip(forms, node.operands, strict=True)
    ]
    return sql.format(*rendered)


def _comparison(node: Comparison, rows: DialectRows, ddl_dialect: str) -> str:
    operator_sql = COMPARISON_SQL[node.operator]
    left = _render(node.left, rows, ddl_dialect)
    right = _render(node.right, rows, ddl_dialect)
    if node.string_operands:
        return rows.compare_strings(operator_sql, left, right)
    return f"({left} {operator_sql} {right})"


def _render(node: SqlNode, rows: DialectRows, ddl_dialect: str) -> str:
    match node:
        case FieldReference(name=name):
            return rows.quote_identifier(name)
        case Literal(value=value):
            return _literal(value, rows)
        case Comparison():
            return _comparison(node, rows, ddl_dialect)
        case BooleanOperation(operator=operator, operands=operands):
            joined = f" {BOOLEAN_SQL[operator]} ".join(
                _render(operand, rows, ddl_dialect) for operand in operands
            )
            return f"({joined})"
        case Not(operand=operand):
            return f"(NOT {_render(operand, rows, ddl_dialect)})"
        case Arithmetic(operator=operator, left=left, right=right):
            return (
                f"({_arithmetic_operand(left, rows, ddl_dialect)} {ARITHMETIC_SQL[operator]} "
                f"{_arithmetic_operand(right, rows, ddl_dialect)})"
            )
        case Negation(operand=operand):
            return f"({_MINUS}{_render(operand, rows, ddl_dialect)})"
        case IntegerWidening(operand=operand):
            return rows.integer_widening(_render(operand, rows, ddl_dialect))
        case NullTest(operand=operand, negated=negated):
            test = "IS NOT NULL" if negated else "IS NULL"
            return f"({_render(operand, rows, ddl_dialect)} {test})"
        case Concatenation(parts=parts):
            return rows.concatenate(
                [_render(part, rows, ddl_dialect) for part in parts]
            )
        case BuiltinCall():
            return _builtin_call(node, rows, ddl_dialect)
        case Aggregate(function=function, operand=operand):
            counted = "*" if operand is None else _render(operand, rows, ddl_dialect)
            return f"{AGGREGATE_SQL[function]}({counted})"
        case Conditional():
            return _conditional(node, rows, ddl_dialect, _render)
    raise TypeError(
        f"Cannot render {node!r} of type {type(node).__name__} as SQL. Expected: a node of "
        f"the lowered SQL tree, one of {[form.__name__ for form in NODE_TYPES]}."
    )


def _refuse_hidden_code_points(sql: str) -> None:
    """Raise when *sql* holds a code point a reviewer cannot see, which a literal would have escaped."""
    for index, char in enumerate(sql):
        if hidden_in_source(char):
            raise ValueError(
                f"The rendered SQL {sql!r} holds the hidden code point U+{ord(char):04X} at "
                f"index {index}, outside any string constant (a field name or a builtin's "
                "SQL), where no escape can make it visible. Fix: remove it from the name "
                "or the builtin's row."
            )


# @canonical(sql/lowered-expression-render): Write a lowered expression tree as one dialect's SQL
# @rule: Every token comes from the tree, the dialect's rows or a builtin row; author text only through the rows' quoting
# @rule: Every compound node is parenthesized, so precedence never changes what the SQL means
# @anti-pattern: Formatting a DSL expression as SQL text at a call site instead of lowering it to the tree
def render_sql(tree: SqlNode, ddl_dialect: str) -> str:
    """*tree* as SQL for the DDL dialect *ddl_dialect*.

    Raises:
        LookupError: No dialect supplies rows under *ddl_dialect*, or a builtin
            call names a builtin with no lowering row or a row with no SQL for
            the dialect.
        TypeError: *tree* or one of its operands is not a node of the tree.
        ValueError: A dialect row refuses a value (a NUL or a lone surrogate in a
            string, a double quote or NUL in a field name, a pattern outside the regex
            pattern language), a builtin call carries other operands than its row
            declares or a pattern operand that is no text literal, or the SQL would
            hold a hidden code point outside a string constant.
    """
    rows = dialect_rows(ddl_dialect)
    sql = _render(tree, rows, ddl_dialect)
    _refuse_hidden_code_points(sql)
    return sql


def column_default_sql(tree: SqlNode, ddl_dialect: str) -> str:
    """*tree* as the expression of a column ``DEFAULT`` on *ddl_dialect*.

    The tree's SQL from :func:`render_sql`, wrapped by the dialect's
    ``expression_default`` row, so ``CREATE TABLE`` and ``ADD COLUMN`` write one
    default the same way.

    Raises:
        LookupError, TypeError, ValueError: As :func:`render_sql`, or the dialect's
            row refuses the rendered expression.
    """
    return dialect_rows(ddl_dialect).expression_default(render_sql(tree, ddl_dialect))


def _normalized_call_sql(sql: str) -> str:
    """*sql* as a builtin call's SQL is compared: stripped and lower-cased."""
    return sql.strip().lower()


def builtin_call_for_sql(
    sql: str,
    ddl_dialect: str,
    *,
    builtins: Mapping[LoweringKey, LoweringBuiltin] = LOWERING_BUILTINS,
) -> LoweringKey | None:
    """The builtin whose row in *builtins* gives *sql* on *ddl_dialect*, or ``None`` for none.

    The inverse of :func:`builtin_call_sql`: an engine reports a column default as
    it spells it, and this reads that SQL back to the call it was written from.
    The SQL is compared stripped and lower-cased, because engines report keywords
    such as ``CURRENT_TIMESTAMP`` in either case. ``None`` means *sql* is no
    builtin's SQL on the dialect (a constant, or an expression). Only rows that take
    no operand are read back: a reported default is a constant spelling, and a row
    with operands holds a template, never one.

    Raises:
        LookupError: No dialect supplies rows under *ddl_dialect*.
        ValueError: Two rows of *builtins* give the same SQL on *ddl_dialect*, so
            the SQL cannot say which builtin it was written from; the message
            names both.
    """
    # Refuses a dialect without rows, which no row could match.
    dialect_rows(ddl_dialect)
    inverse: dict[str, LoweringKey] = {}
    for key, row in builtins.items():
        if row.operands or ddl_dialect not in row.sql:
            continue
        written = _normalized_call_sql(row.sql[ddl_dialect])
        if written in inverse:
            raise ValueError(
                f"The lowering rows of the builtins {inverse[written]!r} and {key!r} both give "
                f"{written!r} on the DDL dialect {ddl_dialect!r}, so a column default reported "
                "as that SQL cannot be read back as the call it was written from. Fix: give "
                "each builtin SQL of its own on every dialect in LOWERING_BUILTINS."
            )
        inverse[written] = key
    return inverse.get(_normalized_call_sql(sql))


__all__ = [
    "AGGREGATE_SQL",
    "ARITHMETIC_SQL",
    "BOOLEAN_SQL",
    "COMPARISON_SQL",
    "builtin_call_for_sql",
    "builtin_call_sql",
    "column_default_sql",
    "render_sql",
]
