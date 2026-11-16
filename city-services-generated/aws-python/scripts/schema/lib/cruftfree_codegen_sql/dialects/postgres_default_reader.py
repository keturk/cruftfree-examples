"""Read a column default PostgreSQL reports back into the lowered SQL tree it was written from.

A compound column default (``1 + 2``, ``"a" + "b"``, ``1 < 2``) is written from its lowered tree
by the one renderer (``cruftfree_rdbms_schema.sql_lowering.render``). The catalog does not keep
that text: ``pg_get_expr`` deparses the stored expression in PostgreSQL's own spelling, with a
cast on each constant (``'a'::text``), implicit coercions it inserted (``(2)::double
precision``), a negated number folded into one constant (``'-2'::integer``), a chain of ``||``
nested to the left and the code-point collation unquoted. :func:`read_postgres_default` is the
inverse of the renderer over that spelling: it parses the deparsed text and rebuilds the tree.

Nothing PostgreSQL spells the renderer's way is restated here. The SQL each builtin's row
writes (``char_length({0})``, ``({0} ~ {1})``, ``CURRENT_TIMESTAMP``), the concatenation
operator and the string-comparison collation are read by parsing what the dialect's own rows
render, so a change to a row is read back without a change here. Only PostgreSQL's deparse
grammar is this module's: casts, ``COLLATE``, the keyword constants and the type names a cast
gives a constant.

A default the reader cannot read back -- a function no row writes (``nextval(...)``), a form the
lowering has no node for, an escape string constant -- is ``None``: the caller records the
catalog's text as it is, so it compares unequal to any declared default and the difference shows.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from functools import cache

from cruftfree_common.config.datasource.ddl_dialect_names import POSTGRESQL_DDL_DIALECT
from cruftfree_rdbms_schema.sql_lowering.builtins_table import (
    LOWERING_BUILTINS,
    BuiltinOperand,
)
from cruftfree_rdbms_schema.sql_lowering.dialect_rows import dialect_rows
from cruftfree_rdbms_schema.sql_lowering.lowered import (
    Arithmetic,
    BooleanOperation,
    BuiltinCall,
    Comparison,
    Concatenation,
    IntegerWidening,
    Literal,
    Negation,
    Not,
    NullTest,
    SqlNode,
)

from cruftfree_codegen_sql.dialects._postgres_default_tokens import (
    _ADDITIVE_OPERATORS,
    _ARITHMETIC,
    _COMPARISON_OPERATORS,
    _COMPARISONS,
    _CONNECTIVES,
    _KEYWORDS,
    _MULTIPLICATIVE_OPERATORS,
    _NOT_EQUAL_ALIAS,
    _AtTimeZone,
    _Binary,
    _bind,
    _Call,
    _Cast,
    _Collate,
    _Connective,
    _Constant,
    _is_number_constant,
    _is_widening,
    _IsNull,
    _name,
    _Number,
    _number,
    _pattern,
    _Placeholder,
    _Prefix,
    _RowForm,
    _String,
    _Token,
    _tokens,
    _typed_constant,
    _uncast,
    _Unreadable,
    _Word,
)


class _Parser:
    """A recursive-descent parser of the expressions ``pg_get_expr`` deparses a default to."""

    def __init__(self, sql: str) -> None:
        self._tokens = _tokens(sql)
        self._index = 0

    def parse(self) -> object:
        node = self._or()
        if self._index != len(self._tokens):
            raise _Unreadable(self._tokens[self._index].text)
        return node

    def _peek(self) -> _Token | None:
        return self._tokens[self._index] if self._index < len(self._tokens) else None

    def _peek_word(self) -> str | None:
        token = self._peek()
        return (
            token.text.lower() if token is not None and token.kind == "word" else None
        )

    def _next(self) -> _Token:
        token = self._peek()
        if token is None:
            raise _Unreadable("end of text")
        self._index += 1
        return token

    def _expect(self, text: str) -> None:
        if self._next().text != text:
            raise _Unreadable(text)

    def _or(self) -> object:
        return self._connective("or", self._and)

    def _and(self) -> object:
        return self._connective("and", self._not)

    def _connective(self, word: str, operand: Callable[[], object]) -> object:
        operands = [operand()]
        while self._peek_word() == word:
            self._index += 1
            operands.append(operand())
        return operands[0] if len(operands) == 1 else _Connective(word, tuple(operands))

    def _not(self) -> object:
        if self._peek_word() == "not":
            self._index += 1
            return _Prefix("not", self._not())
        return self._is()

    def _is(self) -> object:
        operand = self._comparison()
        if self._peek_word() != "is":
            return operand
        self._index += 1
        negated = self._peek_word() == "not"
        if negated:
            self._index += 1
        if self._peek_word() != "null":
            raise _Unreadable("IS without NULL")
        self._index += 1
        return _IsNull(operand, negated)

    def _comparison(self) -> object:
        left = self._additive()
        token = self._peek()
        if (
            token is not None
            and token.kind == "operator"
            and token.text in _COMPARISON_OPERATORS
        ):
            self._index += 1
            return _Binary(token.text, left, self._additive())
        return left

    def _additive(self) -> object:
        return self._binary_level(_ADDITIVE_OPERATORS, self._multiplicative)

    def _multiplicative(self) -> object:
        return self._binary_level(_MULTIPLICATIVE_OPERATORS, self._prefix)

    def _binary_level(
        self, operators: frozenset[str], operand: Callable[[], object]
    ) -> object:
        node = operand()
        token = self._peek()
        while (
            token is not None and token.kind == "operator" and token.text in operators
        ):
            self._index += 1
            node = _Binary(token.text, node, operand())
            token = self._peek()
        return node

    def _prefix(self) -> object:
        token = self._peek()
        if token is not None and token.kind == "operator" and token.text == "-":
            self._index += 1
            return _Prefix("-", self._prefix())
        return self._postfix()

    def _postfix(self) -> object:
        node = self._primary()
        while True:
            token = self._peek()
            if token is not None and token.text == "::":
                self._index += 1
                node = _Cast(node, self._type_name())
            elif self._peek_word() == "collate":
                self._index += 1
                node = _Collate(node, self._qualified_name())
            elif self._peek_word() == "at":
                self._index += 1
                self._expect_word("time")
                self._expect_word("zone")
                node = _AtTimeZone(node, self._postfix())
            else:
                return node

    def _expect_word(self, word: str) -> None:
        if self._peek_word() != word:
            raise _Unreadable(word)
        self._index += 1

    def _qualified_name(self) -> str:
        parts = [self._identifier()]
        while (token := self._peek()) is not None and token.text == ".":
            self._index += 1
            parts.append(self._identifier())
        return ".".join(parts)

    def _identifier(self) -> str:
        token = self._next()
        if token.kind not in ("word", "quoted"):
            raise _Unreadable(token.text)
        return _name(token)

    def _type_name(self) -> str:
        words = [self._qualified_name()]
        while (word := self._peek_word()) is not None and word not in _KEYWORDS:
            words.append(self._qualified_name())
        token = self._peek()
        if token is not None and token.text == "(":
            self._skip_type_modifier()
        return " ".join(words)

    def _skip_type_modifier(self) -> None:
        self._expect("(")
        while self._next().text != ")":
            pass

    def _primary(self) -> object:
        token = self._next()
        if token.kind == "number":
            return _Number(token.text)
        if token.kind == "string":
            return _String(token.text[1:-1].replace("''", "'"))
        if token.kind == "placeholder":
            return _Placeholder(int(token.text[1:-1]))
        if token.text == "(":
            node = self._or()
            self._expect(")")
            return node
        if token.kind in ("word", "quoted"):
            return self._named(token)
        raise _Unreadable(token.text)

    def _named(self, token: _Token) -> object:
        name = _name(token)
        if token.kind == "word" and name in ("true", "false", "null"):
            return _Constant(name)
        if token.kind == "word" and name in _KEYWORDS:
            raise _Unreadable(token.text)
        following = self._peek()
        if following is None or following.text != "(":
            return _Word(name)
        self._index += 1
        arguments: list[object] = []
        if (closing := self._peek()) is not None and closing.text == ")":
            self._index += 1
            return _Call(name, ())
        arguments.append(self._or())
        while self._next().text == ",":
            arguments.append(self._or())
        if self._tokens[self._index - 1].text != ")":
            raise _Unreadable(name)
        return _Call(name, tuple(arguments))


def _parsed(sql: str) -> object:
    return _Parser(sql).parse()


@cache
def _row_forms() -> tuple[_RowForm, ...]:
    """Every ``LOWERING_BUILTINS`` row holding PostgreSQL SQL, its SQL parsed."""
    return tuple(
        _RowForm(key, row.operands, _template(row.sql[POSTGRESQL_DDL_DIALECT]))
        for key, row in LOWERING_BUILTINS.items()
        if POSTGRESQL_DDL_DIALECT in row.sql
    )


def _template(sql: str) -> object:
    """A row's SQL, parsed; a row this grammar cannot read is a defect of the reader, raised.

    Raises:
        TypeError: The deparse grammar cannot read *sql*, so a default written from it could
            never be read back. Fix: teach the grammar the row's form.
    """
    try:
        return _parsed(sql)
    except _Unreadable as unreadable:
        raise TypeError(
            f"The PostgreSQL default reader cannot read the dialect's own SQL {sql!r} "
            f"(at {unreadable}), so no default written with it reads back. Fix: add the form "
            "to the deparse grammar of postgres_default_reader."
        ) from unreadable


@cache
def _concatenation_operator() -> str:
    """The infix operator the dialect's concatenation row joins two parts with."""
    template = _template(
        dialect_rows(POSTGRESQL_DDL_DIALECT).concatenate(["{0}", "{1}"])
    )
    if not isinstance(template, _Binary):
        raise TypeError(
            f"PostgreSQL's concatenation row writes {template!r}, not an infix operator."
        )
    return template.operator


@cache
def _string_collation() -> str:
    """The collation the dialect's string-comparison row puts both operands under."""
    template = _template(
        dialect_rows(POSTGRESQL_DDL_DIALECT).compare_strings("=", "{0}", "{1}")
    )
    if not (isinstance(template, _Binary) and isinstance(template.left, _Collate)):
        raise TypeError(
            f"PostgreSQL's string comparison row writes {template!r}, not a collated operand."
        )
    return template.left.collation.lower()


def _builtin_call(node: object) -> BuiltinCall | None:
    """*node* as the call of the builtin whose row writes it, or ``None`` for none."""
    for form in _row_forms():
        bindings: dict[int, object] = {}
        written = node if isinstance(form.template, _Cast) else _uncast(node)
        if not _bind(form.template, written, bindings):
            continue
        if sorted(bindings) != list(range(len(form.operands))):
            continue
        operands = tuple(
            _pattern(bindings[index])
            if operand is BuiltinOperand.PATTERN
            else _tree(bindings[index])
            for index, operand in enumerate(form.operands)
        )
        return BuiltinCall(form.key, operands)
    return None


def _cast(node: _Cast) -> SqlNode:
    """A cast: a typed constant, a widening, or a coercion PostgreSQL inserted around an expression."""
    operand = node.operand
    if isinstance(operand, _String):
        return _typed_constant(operand.text, node.type_name)
    tree = _tree(operand)
    if _is_widening(node) and not _is_number_constant(tree):
        return IntegerWidening(tree)
    return tree


def _constant(node: _Constant) -> Literal:
    if node.word == "null":
        return Literal(None)
    return Literal(node.word == "true")


def _collated_operand(side: object, collation: str) -> object | None:
    """*side*'s operand when it is collated under *collation*, else ``None``."""
    if isinstance(side, _Collate) and side.collation.lower() == collation:
        return side.operand
    return None


def _comparison(node: _Binary) -> Comparison:
    operator = _COMPARISONS.get(
        "<>" if node.operator == _NOT_EQUAL_ALIAS else node.operator
    )
    if operator is None:
        raise _Unreadable(node.operator)
    collation = _string_collation()
    left = _collated_operand(node.left, collation)
    right = _collated_operand(node.right, collation)
    if (left is None) != (right is None):
        raise _Unreadable("a comparison collating one operand")
    if left is None or right is None:
        return Comparison(
            operator, _tree(node.left), _tree(node.right), string_operands=False
        )
    return Comparison(operator, _tree(left), _tree(right), string_operands=True)


def _parts(node: object, operator: str) -> Iterator[object]:
    """The operands of a chain of *operator*, PostgreSQL nesting it to the left."""
    if isinstance(node, _Binary) and node.operator == operator:
        yield from _parts(node.left, operator)
        yield from _parts(node.right, operator)
    else:
        yield node


def _binary(node: _Binary) -> SqlNode:
    if node.operator == _concatenation_operator():
        return Concatenation(tuple(_tree(part) for part in _parts(node, node.operator)))
    arithmetic = _ARITHMETIC.get(node.operator)
    if arithmetic is not None:
        return Arithmetic(arithmetic, _tree(node.left), _tree(node.right))
    return _comparison(node)


def _prefix(node: _Prefix) -> SqlNode:
    if node.operator == "not":
        return Not(_tree(node.operand))
    return Negation(_tree(node.operand))


def _connective(node: _Connective) -> BooleanOperation:
    if node.operator not in _CONNECTIVES:
        raise _Unreadable(node.operator)
    return BooleanOperation(
        _CONNECTIVES[node.operator], tuple(_tree(item) for item in node.operands)
    )


def _tree(node: object) -> SqlNode:
    """*node*, a parsed deparse, as the lowered tree the renderer wrote it from."""
    builtin = None if _is_widening(node) else _builtin_call(node)
    if builtin is not None:
        return builtin
    match node:
        case _Cast():
            return _cast(node)
        case _String(text=text):
            return Literal(text)
        case _Number(text=text):
            return _number(text)
        case _Constant():
            return _constant(node)
        case _Binary():
            return _binary(node)
        case _Prefix():
            return _prefix(node)
        case _Connective():
            return _connective(node)
        case _IsNull(operand=operand, negated=negated):
            return NullTest(_tree(operand), negated)
    raise _Unreadable(repr(node))


# @canonical(sql/postgres-default-read-back): Read a PostgreSQL-reported column default back into its lowered tree
# @rule: Every builtin, the concatenation operator and the string collation are read from what the dialect's rows render
# @rule: A default no row or node can have written reads as None, never as a guess
def read_postgres_default(sql: str) -> SqlNode | None:
    """The lowered tree PostgreSQL's spelling *sql* of a column default was written from.

    *sql* is ``pg_get_expr`` of the column's default. ``None`` when the text is no default
    the renderer writes (a sequence's ``nextval``, a function no builtin row writes, an
    escape string constant, a form the lowered tree has no node for).
    """
    try:
        return _tree(_parsed(sql))
    except _Unreadable:
        return None
    except ValueError:
        # A lowered node refuses what the text holds (a one-part concatenation): the
        # renderer writes no such tree, so no default it wrote reads as this text.
        return None


__all__ = ["read_postgres_default"]
