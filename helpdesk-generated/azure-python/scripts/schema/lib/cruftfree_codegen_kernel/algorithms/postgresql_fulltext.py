"""PostgreSQL full-text-search SQL expression building.

Both helpers here build plain PostgreSQL ``to_tsvector(...)`` expression
text from a list of already-resolved wire column names -- no ORM object, no
target-language syntax, nothing but the one SQL dialect every RDBMS-target
language package that supports the ``fulltext`` index kind must emit
identically, since it is the exact SQL PostgreSQL itself requires.
"""

from __future__ import annotations

#: PostgreSQL text-search configuration used for every generated
#: ``to_tsvector(...)`` expression -- the DSL exposes no per-field language
#: override yet, so every fulltext index shares this one configuration.
DEFAULT_TEXT_SEARCH_CONFIG = "english"

#: PostgreSQL index method a ``to_tsvector(...)`` expression index is built
#: with. It lives beside the expression builders because it is the same one
#: fact: an expression index over a ``tsvector`` is only useful under GIN, so
#: every target that emits the expression emits this method with it. Kept here
#: rather than once per language package so the ORM/entity declaration and the
#: migration DDL of a given target can never name different methods.
FULLTEXT_INDEX_METHOD = "gin"


def build_fulltext_text_concat_expression(column_names: list[str]) -> str:
    """Build an immutable, nullable-safe text expression from *column_names*.

    Each column is wrapped in ``coalesce(col, '')`` so a NULL column does not
    collapse the whole concatenation to NULL, then joined with a single space
    -- the same immutability requirement PostgreSQL's functional/expression
    index machinery imposes on any expression used inside ``to_tsvector``.

    Args:
        column_names: Wire (snake_case) column names participating in the
            fulltext index, in declared order.

    Returns:
        A ``coalesce(a, '') || ' ' || coalesce(b, '')``-shaped SQL fragment.
    """
    return " || ' ' || ".join(f"coalesce({col}, '')" for col in column_names)


def build_fulltext_migration_expression(wire_names: list[str]) -> str:
    """Build the ``to_tsvector(...)`` expression for migration DDL.

    Args:
        wire_names: Wire (snake_case) column names participating in the
            fulltext index, in declared order.

    Returns:
        SQL expression string for the migration index, e.g.
        ``to_tsvector('english', coalesce(title, '') || ' ' || coalesce(body, ''))``.
    """
    col_expr = build_fulltext_text_concat_expression(wire_names)
    return f"to_tsvector('{DEFAULT_TEXT_SEARCH_CONFIG}', {col_expr})"


__all__ = [
    "DEFAULT_TEXT_SEARCH_CONFIG",
    "FULLTEXT_INDEX_METHOD",
    "build_fulltext_migration_expression",
    "build_fulltext_text_concat_expression",
]
