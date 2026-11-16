"""Canonical SQL string-literal quoting.

One home for "turn this Python string into a SQL string literal", because
every caller of it is an injection surface: the values reaching it are DSL
author text (a ``COMMENT ON`` body), constraint messages, and seed data --
none of which the emitter controls.

Engine differences that actually change the escaping are parameters, never
separate functions:

- **Single quotes** are doubled everywhere. This is the SQL standard and is
  correct on every engine CruftFree emits for.
- **Backslashes** are ordinary characters in a standard-conforming string
  literal (PostgreSQL with ``standard_conforming_strings = on``, the default
  since 9.1). An engine whose literals treat a backslash as an ESCAPE
  character would let an unescaped trailing ``\\`` swallow the closing quote,
  so a dialect that declares it passes ``escape_backslashes=True``.
- **NUL** cannot appear in a SQL text value on any engine; it is rejected
  loudly rather than silently stripped, because silently dropping a byte from
  text on its way into a database is a corruption nobody would see.
"""

from __future__ import annotations

from cruftfree_common.utils.comment_text import comment_physical_lines

_SINGLE_QUOTE = "'"
_DOUBLE_QUOTE = '"'
_BACKSLASH = "\\"
_NUL = "\x00"


# @canonical(sql/string-literal): Quote a Python string as a SQL string literal
# @rule: Single quotes are always doubled; backslashes only where the dialect escapes them
# @rule: A dialect whose literals treat a backslash as an escape MUST pass escape_backslashes=True
# @anti-pattern: Hand-rolling "'" + value.replace("'", "''") + "'" at a call site
def sql_string_literal(value: str, *, escape_backslashes: bool = False) -> str:
    """Render *value* as a quoted SQL string literal.

    Args:
        value: The text to quote. Author-supplied text is expected here --
            that is the whole reason this function exists.
        escape_backslashes: Double every backslash as well. Required for a
            literal whose grammar treats ``\\`` as an escape character (a
            PostgreSQL ``U&'…'`` constant, written by the dialect's string row
            in ``cruftfree_rdbms_schema.sql_lowering.dialect_rows``); wrong for a
            standard-conforming PostgreSQL literal, where it would emit a
            doubled backslash as data.

    Returns:
        The literal including its surrounding single quotes.

    Raises:
        ValueError: *value* contains a NUL byte, which no SQL text value can
            carry on any supported engine.
    """
    if _NUL in value:
        raise ValueError(
            "SQL string literal contains a NUL (U+0000) character, which no "
            "supported database engine can store in a text value. Expected: "
            "NUL-free text. Fix: remove the NUL from the source text (for a "
            "DSL comment, the '///' body) before it reaches the emitter."
        )
    escaped = value
    if escape_backslashes:
        escaped = escaped.replace(_BACKSLASH, _BACKSLASH * 2)
    escaped = escaped.replace(_SINGLE_QUOTE, _SINGLE_QUOTE * 2)
    return f"{_SINGLE_QUOTE}{escaped}{_SINGLE_QUOTE}"


# @canonical(sql/quoted-identifier): Quote a Python string as a SQL double-quoted identifier
# @rule: An embedded double quote or a NUL raises -- this function never escapes and continues
# @rule: This is for IDENTIFIERS (type/column/table names); SQL text VALUES use sql_string_literal
# @anti-pattern: Concatenating '"' + value + '"' at a call site instead of calling this function
# @anti-pattern: Reusing sql_string_literal for an identifier -- it quotes with single quotes and doubles the wrong character
def sql_quoted_identifier(value: str) -> str:
    """Render *value* as a double-quoted SQL identifier.

    Unlike :func:`sql_string_literal`, this function does not repair its
    input: an identifier that cannot be encoded safely raises rather than
    being escaped and emitted, because a quoted identifier is emitted once
    into a migration that ships with every generated project and runs with
    schema-modifying privileges. A single quote is not special here -- it
    is ordinary data inside a double-quoted identifier, and doubling it
    would be `sql_string_literal`'s job, not this one.

    Args:
        value: The identifier text to quote. DSL-authored text (a type
            name, a column name) is expected here.

    Returns:
        The identifier including its surrounding double quotes.

    Raises:
        ValueError: *value* contains a double quote, which this function
            does not escape, or a NUL byte, which no SQL identifier can
            carry on any supported engine.
    """
    if _NUL in value:
        raise ValueError(
            f"SQL identifier {value!r} contains a NUL (U+0000) character, "
            "which no supported database engine can store in an "
            "identifier. Expected: NUL-free text for the identifier name. "
            "Fix: remove the NUL from the DSL-authored name before it "
            "reaches the emitter."
        )
    if _DOUBLE_QUOTE in value:
        raise ValueError(
            f"SQL identifier {value!r} contains a double quote (\"), which "
            "this function does not escape -- a quoted identifier is "
            "emitted once into a migration that runs with schema-modifying "
            "privileges, so an identifier that cannot be encoded safely "
            "must stop generation rather than be repaired silently. "
            "Expected: an identifier with no embedded double quote. Fix: "
            "rename the DSL-authored identifier to remove the '\"' "
            "character."
        )
    return f"{_DOUBLE_QUOTE}{value}{_DOUBLE_QUOTE}"


def sql_line_comment_lines(text: str | None) -> tuple[str, ...]:
    """Render *text* as ``--``-prefixed SQL line comments, one per physical line.

    The lines are :func:`~cruftfree_common.utils.comment_text.comment_physical_lines`
    of *text*: they break at CRLF, CR, LF, U+2028 and U+2029, so no line break
    stands raw inside one ``--`` comment (an engine whose scanner ends the
    comment at a lone CR would otherwise read the rest of the note as SQL), and
    every other hidden code point is written as the visible text ``[U+HHHH]``.
    Every physical line carries its own marker -- the same per-line rule every
    language's comment emitter follows. A ``--`` comment runs to end-of-line
    and has no terminator to escape, which is why this needs no counterpart to
    :func:`sql_string_literal`'s quoting.

    Args:
        text: The note body, or ``None`` for a construct with no note.

    Returns:
        One ``"-- ..."`` line per physical line of *text*; empty for ``None``
        or for text that is entirely whitespace, so an undocumented construct
        emits nothing at all.
    """
    if text is None or not text.strip():
        return ()
    return tuple(f"-- {line}".rstrip() for line in comment_physical_lines(text))


# @canonical(sql/dollar-quoted): Wrap a PostgreSQL ``DO`` body in a dollar-quote tag it cannot contain
# @rule: A body that embeds author text (an enum label) can contain ``$$``; the tag is chosen
#   so it never appears in the body, because a body that holds its own closing tag ends the
#   block early and runs the remainder as top-level SQL
# @anti-pattern: A fixed ``$$`` around a body that interpolates author text
def dollar_quote_tag(*embedded: str) -> str:
    """The first PostgreSQL dollar-quote tag that none of *embedded* contains.

    For a caller that formats a block from a template: pass the author text that will
    be embedded in it (the template's own text never contains a ``$``), then use the
    returned tag for both the opening and closing delimiter.

    Args:
        embedded: The already-quoted text the block will carry.

    Returns:
        ``$$``, else ``$cruftfree1$``, ``$cruftfree2$``, ... -- the first absent from every string.
    """
    tag = "$$"
    ordinal = 0
    while any(tag in text for text in embedded):
        ordinal += 1
        tag = f"$cruftfree{ordinal}$"
    return tag


def dollar_quoted(body: str) -> str:
    """Wrap *body* in a PostgreSQL dollar-quote whose tag does not occur inside it.

    Args:
        body: The block body, with any author text already quoted as SQL literals.

    Returns:
        ``$tag$ body $tag$`` for the first tag (``$$``, then ``$cruftfree1$``, ``$cruftfree2$``, ...)
        that *body* does not contain.
    """
    tag = dollar_quote_tag(body)
    return f"{tag} {body} {tag}"


__all__ = [
    "dollar_quote_tag",
    "dollar_quoted",
    "sql_line_comment_lines",
    "sql_quoted_identifier",
    "sql_string_literal",
]
