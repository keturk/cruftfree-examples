"""Recover a ``fulltext(...)`` index's columns from the expression PostgreSQL holds.

The dialect creates a ``fulltext(...)`` declaration as a GIN index over one
expression key, the shared coalesce ``to_tsvector`` expression
(:func:`~cruftfree_codegen_kernel.algorithms.postgresql_fulltext.build_fulltext_migration_expression`).
PostgreSQL records ``0`` in ``pg_index.indkey`` for an expression key, so the
column list and its declared order exist only inside the expression the catalog
deparses -- and the deparse is not the text the dialect wrote: PostgreSQL adds a
cast to every constant and operand (``'english'::regconfig``,
``''::character varying``, ``(...)::text``), wraps sub-expressions in
parentheses, upper-cases ``COALESCE`` and drops the identifier quoting a
lower-case name does not need.

Those are the only differences, and none of them changes what the expression
computes for the text columns a fulltext index covers. So the deparse is lexed
into tokens, casts and grouping parentheses are set aside on both sides, and the
result must equal -- token for token -- the expression the dialect renders for
the columns the deparse names. Anything else (another configuration, another
function, a missing ``coalesce``, an extra operand, a token this lexer does not
know) is not the shape the dialect emits, and the caller refuses it.
"""

from __future__ import annotations

from dataclasses import dataclass

from cruftfree_codegen_kernel.algorithms.postgresql_fulltext import (
    build_fulltext_migration_expression,
)

# ── Token kinds ──

_NAME = "name"
_STRING = "string"
_NUMBER = "number"
_SYMBOL = "symbol"

#: The function every column of the shared expression is wrapped in.
_COALESCE = "coalesce"

#: The cast operator PostgreSQL attaches to constants and operands.
_CAST = "::"

#: Grouping punctuation PostgreSQL adds around sub-expressions.
_GROUPING = frozenset({"(", ")"})

#: Punctuation and operators the shared expression can contain.
_SYMBOLS = ("::", "||", "(", ")", ",", ".", "[", "]")

#: Words that continue a multi-word type name after its first word
#: (``character varying``, ``double precision``,
#: ``timestamp without time zone``). Only these are consumed as part of a cast,
#: so a keyword after a cast (``COLLATE``) stays a token and fails the match.
_TYPE_NAME_CONTINUATIONS = frozenset(
    {"varying", "precision", "with", "without", "time", "zone"}
)

_SINGLE_QUOTE = "'"
_DOUBLE_QUOTE = '"'


@dataclass(frozen=True)
class _Token:
    """One lexed token: its kind and its normalized text."""

    kind: str
    text: str


def _read_quoted(source: str, start: int, quote: str) -> tuple[str, int] | None:
    """The quoted text opening at *start* (doubled quotes unescaped), and its end.

    Returns ``None`` when the quote never closes.
    """
    chars: list[str] = []
    position = start + 1
    while position < len(source):
        char = source[position]
        if char != quote:
            chars.append(char)
            position += 1
            continue
        if position + 1 < len(source) and source[position + 1] == quote:
            chars.append(quote)
            position += 2
            continue
        return "".join(chars), position + 1
    return None


def _read_while(source: str, start: int, accept: str) -> int:
    """The index of the first character at or after *start* that is neither
    alphanumeric nor one of *accept*."""
    position = start
    while position < len(source) and (
        source[position].isalnum() or source[position] in accept
    ):
        position += 1
    return position


def _lex_one(source: str, position: int) -> tuple[_Token, int] | None:
    """The token starting at *position*, and where it ends; ``None`` if unknown."""
    char = source[position]
    if char == _SINGLE_QUOTE:
        quoted = _read_quoted(source, position, _SINGLE_QUOTE)
        return None if quoted is None else (_Token(_STRING, quoted[0]), quoted[1])
    if char == _DOUBLE_QUOTE:
        quoted = _read_quoted(source, position, _DOUBLE_QUOTE)
        # A quoted identifier keeps its exact spelling.
        return None if quoted is None else (_Token(_NAME, quoted[0]), quoted[1])
    if char.isalpha() or char == "_":
        end = _read_while(source, position, "_$")
        # PostgreSQL folds an unquoted identifier or keyword to lower case.
        return _Token(_NAME, source[position:end].lower()), end
    if char.isdigit():
        end = _read_while(source, position, ".")
        return _Token(_NUMBER, source[position:end]), end
    for symbol in _SYMBOLS:
        if source.startswith(symbol, position):
            return _Token(_SYMBOL, symbol), position + len(symbol)
    return None


def _lex(source: str) -> list[_Token] | None:
    """Every token of *source*, whitespace dropped; ``None`` on an unknown character."""
    tokens: list[_Token] = []
    position = 0
    while position < len(source):
        if source[position].isspace():
            position += 1
            continue
        lexed = _lex_one(source, position)
        if lexed is None:
            return None
        token, position = lexed
        tokens.append(token)
    return tokens


def _skip_type_modifier(tokens: list[_Token], position: int) -> int:
    """Past a ``(n)`` / ``(p, s)`` type modifier at *position*, if one is there."""
    shape = [_SYMBOL, _NUMBER]
    if [t.kind for t in tokens[position : position + 2]] != shape:
        return position
    if tokens[position].text != "(":
        return position
    cursor = position + 2
    if (
        cursor + 1 < len(tokens)
        and tokens[cursor].text == ","
        and tokens[cursor + 1].kind == _NUMBER
    ):
        cursor += 2
    if cursor < len(tokens) and tokens[cursor].text == ")":
        return cursor + 1
    return position


def _skip_cast_type(tokens: list[_Token], position: int) -> int:
    """Past the type name a ``::`` cast at *position* - 1 names; *position* if none.

    A type name is a (possibly schema-qualified) name, the words that continue a
    multi-word type name, an optional size modifier and optional array brackets.
    """
    if position >= len(tokens) or tokens[position].kind != _NAME:
        return position
    cursor = position + 1
    while (
        cursor + 1 < len(tokens)
        and tokens[cursor].text == "."
        and tokens[cursor + 1].kind == _NAME
    ):
        cursor += 2
    while (
        cursor < len(tokens)
        and tokens[cursor].kind == _NAME
        and tokens[cursor].text in _TYPE_NAME_CONTINUATIONS
    ):
        cursor += 1
    cursor = _skip_type_modifier(tokens, cursor)
    while (
        cursor + 1 < len(tokens)
        and tokens[cursor].text == "["
        and tokens[cursor + 1].text == "]"
    ):
        cursor += 2
    return cursor


def _comparable_tokens(source: str) -> tuple[_Token, ...] | None:
    """*source*'s tokens with casts and grouping parentheses set aside.

    Returns ``None`` when *source* holds a character this lexer does not know or
    a cast naming no type -- neither is the shape the dialect emits.
    """
    tokens = _lex(source)
    if tokens is None:
        return None
    kept: list[_Token] = []
    position = 0
    while position < len(tokens):
        token = tokens[position]
        if token.kind == _SYMBOL and token.text == _CAST:
            after = _skip_cast_type(tokens, position + 1)
            if after == position + 1:
                return None
            position = after
            continue
        if not (token.kind == _SYMBOL and token.text in _GROUPING):
            kept.append(token)
        position += 1
    return tuple(kept)


def _coalesced_columns(tokens: tuple[_Token, ...]) -> tuple[str, ...]:
    """The column named right after each ``coalesce`` in *tokens*, in order."""
    return tuple(
        tokens[index + 1].text
        for index, token in enumerate(tokens[:-1])
        if token.kind == _NAME
        and token.text == _COALESCE
        and tokens[index + 1].kind == _NAME
    )


def _quoted_identifier(name: str) -> str:
    """*name* as a PostgreSQL quoted identifier, so its spelling is kept exactly."""
    return (
        _DOUBLE_QUOTE + name.replace(_DOUBLE_QUOTE, _DOUBLE_QUOTE * 2) + _DOUBLE_QUOTE
    )


def fulltext_index_columns(deparsed_expression: str) -> tuple[str, ...] | None:
    """The columns, in declared order, of the fulltext expression PostgreSQL deparsed.

    Args:
        deparsed_expression: The index's one key expression as the catalog
            deparses it (``pg_get_indexdef(indexrelid, 1, false)``).

    Returns:
        The column names, in the order the declaration listed them, when the
        expression is exactly the one the dialect renders for those columns;
        ``None`` for any other expression.
    """
    deparsed = _comparable_tokens(deparsed_expression)
    if deparsed is None:
        return None
    columns = _coalesced_columns(deparsed)
    if not columns:
        return None
    rendered = build_fulltext_migration_expression(
        [_quoted_identifier(column) for column in columns]
    )
    if _comparable_tokens(rendered) != deparsed:
        return None
    return columns


__all__ = ["fulltext_index_columns"]
