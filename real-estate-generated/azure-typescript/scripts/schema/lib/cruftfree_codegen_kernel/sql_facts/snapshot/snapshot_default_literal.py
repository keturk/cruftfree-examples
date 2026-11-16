"""Shared rendering of a snapshot column default for a migration statement.

A snapshot records every column default but a collection literal beside the tree
the SQL lowering gives it (``SnapshotDefault.tree``). A migration statement
(``ADD COLUMN``, ``SET DEFAULT``, the backfill of a nullable-to-non-nullable
``ALTER``) renders that tree through the dialect's column-default writer
(``column_default_sql``) -- the writer ``CREATE TABLE`` renders the same default
with, so a column created and a column added later state one default. A default
with no tree is an internal error: the extraction records a tree for every default
analysis accepted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema.sql_lowering.render import column_default_sql

from cruftfree_codegen_kernel.sql_facts.collection_default import (
    collection_default_sql,
    is_collection_default_source,
)
from cruftfree_codegen_kernel.sql_facts.type_mappings import supported_ddl_dialect

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import SnapshotColumn, SnapshotDefault

#: The ``SnapshotDefault.kind`` of a value the column stores.
_LITERAL_KIND: str = "literal"


def require_nullable_changed_default(
    default: object,
    *,
    entity_name: str,
    field_name: str,
) -> object:
    """Return *default* once proven present for a nullable-to-non-nullable ALTER.

    A column moving from nullable to non-nullable on an EXISTING (and
    possibly populated) table needs a DATABASE-side default to backfill the
    rows that already hold NULL there -- the same invariant every registered
    adapter's ``add_column`` op already enforces for a non-nullable column
    added fresh. Its absence here would emit an ``ALTER`` that fails at apply
    time against any row already NULL in that column.

    Args:
        default: The column's snapshot default, or None.
        entity_name: The owning entity's name, for the error message.
        field_name: The field's name, for the error message.

    Returns:
        *default*, unchanged, when present.

    Raises:
        GenerationError: *default* is None.
    """
    if default is None:
        raise GenerationError(
            f"Field '{field_name}' on entity '{entity_name}' is changing from nullable to "
            f"non-nullable, but declares no default. A NOT NULL constraint added to an existing "
            f"column cannot backfill the rows that already hold NULL there, so the migration "
            f"would fail on apply. Make the field's default explicit, or leave it nullable."
        )
    return default


def _no_tree(col: SnapshotColumn, default: SnapshotDefault, table_name: str) -> GenerationError:
    """The refusal of *default*, which no extraction of an analyzed application recorded."""
    return GenerationError(
        f"Column '{col.column_name}' (type '{col.type.name}') on table '{table_name}' "
        f"carries the {default.kind} default {default.value!r} with no lowered tree, so no "
        "database DEFAULT can be rendered for it. A snapshot records the tree of every "
        "default analysis accepts; this is an internal error in schema snapshot "
        "extraction or a hand-edited snapshot."
    )


# @canonical(migration/snapshot-default-sql): Render a snapshot column default for a
# migration statement from its lowered tree
# @rule: ADD COLUMN, SET DEFAULT and a backfill write a default through column_default_sql, as CREATE TABLE does
# @anti-pattern: Spelling a default from its recorded source text, or a builtin call from a per-adapter table
def render_snapshot_default_sql(
    col: SnapshotColumn,
    default: SnapshotDefault,
    table_name: str,
    dialect: str,
) -> str:
    """Render *col*'s snapshot default as the SQL expression after ``DEFAULT``.

    A collection literal is the JSON column's document, written by
    :func:`~cruftfree_codegen_kernel.sql_facts.collection_default.collection_default_sql`.
    Every other default is rendered from its lowered tree by the dialect's
    column-default writer, the one ``CREATE TABLE`` uses.

    Args:
        col: The column carrying the default.
        default: The column's snapshot default.
        table_name: Physical table name, for the error messages.
        dialect: The DDL dialect name this RDBMS block's engine speaks.

    Returns:
        The raw SQL expression to place after ``DEFAULT``/``SET column =``.

    Raises:
        GenerationError: The default carries no tree it can be rendered from, or
            *dialect* is not a supported DDL dialect name.
    """
    ddl_dialect = supported_ddl_dialect(dialect)
    if default.tree is not None:
        return column_default_sql(default.tree, ddl_dialect)
    if default.kind == _LITERAL_KIND and is_collection_default_source(default.value):
        return collection_default_sql(default.value, ddl_dialect, column=col.column_name)
    raise _no_tree(col, default, table_name)
