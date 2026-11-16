"""How author text is written into a generated comment.

A comment has no escape grammar. A line break in author text would end a line
comment early and leave the rest of the text in the file as source, so every
writer splits the text at :data:`COMMENT_LINE_BREAKS` and writes each physical
line as a comment line of its own (a block-comment renderer, a line-comment
emitter, or the SQL ``--`` writer ``sql_text.sql_line_comment_lines``), or folds
the lines into one (:func:`comment_line_text`, for a comment a template writes
on one line). Every other code point ``hidden_in_source`` flags is written by
``visible_text`` as the visible text ``[U+HHHH]``. The rule names no grammar: a
writer adds only its own comment terminator's split.
"""

from __future__ import annotations

import re
from typing import Final

from cruftfree_common.utils.hidden_text import visible_text

__all__ = ["COMMENT_LINE_BREAKS", "comment_line_text", "comment_physical_lines"]

#: U+2028 LINE SEPARATOR and U+2029 PARAGRAPH SEPARATOR, which a JavaScript scanner
#: reads as line terminators.
_LINE_SEPARATOR: Final[str] = chr(0x2028)
_PARAGRAPH_SEPARATOR: Final[str] = chr(0x2029)

#: Everything that ends a line comment in some language a generator emits: the line
#: terminators every C-style, Python and SQL scanner recognizes, plus the two Unicode
#: separators. No other code point breaks a comment line.
COMMENT_LINE_BREAKS: Final[re.Pattern[str]] = re.compile(
    "|".join(("\r\n", f"[\r\n{_LINE_SEPARATOR}{_PARAGRAPH_SEPARATOR}]"))
)

#: What a line break becomes in a comment written on one line.
_FOLDED_LINE_BREAK: Final[str] = " "


# @canonical(text/comment-lines): Split author text into the physical lines of a comment
# @rule: Lines break at CRLF, CR, LF, U+2028 and U+2029 (COMMENT_LINE_BREAKS), so
#   none survives raw into a single comment line where some scanner would read it
#   as ending the comment early.
# @rule: A comment has no escape grammar: every other hidden code point stays on its
#   line written by visible_text as [U+HHHH], never with a string literal's escape.
# @anti-pattern: A private line-break set in one target's comment writer
def comment_physical_lines(text: str) -> tuple[str, ...]:
    """Split *text* into physical lines safe to embed one per comment line.

    Lines break at :data:`COMMENT_LINE_BREAKS`; a final break ends the last
    line rather than opening an empty one, as :meth:`str.splitlines` does. Every
    other code point ``hidden_in_source`` flags (tab, backspace, the other C0
    and C1 codes, bidi controls, zero-width characters) stays on its line,
    written by :func:`~cruftfree_common.utils.hidden_text.visible_text` as the
    visible text ``[U+HHHH]`` -- no code point a reader cannot see reaches
    emitted source. An empty *text* yields one empty line so callers always
    emit at least one comment line.

    Args:
        text: Author text bound for a comment.
    """
    physical_lines = COMMENT_LINE_BREAKS.split(text)
    if len(physical_lines) > 1 and physical_lines[-1] == "":
        physical_lines.pop()
    return tuple(visible_text(line) for line in physical_lines)


# @canonical(text/comment-line): Author text as the body of a comment written on one line
# @rule: Every line break becomes a space and every other hidden code point [U+HHHH];
#   a grammar with a block terminator splits it after this, never before
# @see: text/comment-lines, text/visible-spelling
def comment_line_text(text: str) -> str:
    """*text* as one comment line: its :func:`comment_physical_lines` joined by a space.

    The output holds no code point ``hidden_in_source`` flags, LF included, so a
    template can place it after a line-comment marker (``#``, ``//``, ``--``) or
    inside a one-line block comment and the rest of the line stays the comment.

    Args:
        text: Author text bound for a comment.
    """
    return _FOLDED_LINE_BREAK.join(comment_physical_lines(text))
