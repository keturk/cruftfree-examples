"""Shared FIELD_DEFAULT_CHANGED / FIELD_UNIQUE_CHANGED statement builders.

A column's DEFAULT and its single-column UNIQUE constraint are column facts the
database holds, so a change to either is migrated by every adapter with the same
statements: ``ALTER COLUMN ... SET DEFAULT`` / ``DROP DEFAULT``, and a unique
constraint added under the shared ``uq_`` name or dropped under whatever name the
catalog holds. The statements are the dialect's
(:class:`~cruftfree_codegen_kernel.sql_facts.dialects.base.SQLDialect`); the only
per-language leaf is the default's SQL expression, which each adapter renders with
the same renderer its ``CREATE TABLE`` and ``ADD COLUMN`` use, so a default set on
an existing column and one created with the table are the same text.

Each builder states what one column records: the convergence passes the change's
subject, the column as the declared schema holds it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cruftfree_rdbms_schema.index_naming import unique_constraint_name

from cruftfree_codegen_kernel.sql_facts.dialects.dialect_table import sql_dialect

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import (
        SnapshotColumn,
        SnapshotTable,
    )

#: Renders a column's snapshot default as the SQL expression after ``DEFAULT`` --
#: ``(table, column) -> SQL``; called only for a column that carries a default.
RenderColumnDefault = Callable[["SnapshotTable", "SnapshotColumn"], str]


def _default_statement(
    table: "SnapshotTable",
    column: "SnapshotColumn",
    ddl_dialect: str,
    schema: str | None,
    render_default: RenderColumnDefault,
) -> str:
    """The statement that gives *column* the default it records."""
    dialect = sql_dialect(ddl_dialect)
    if column.default is None:
        return dialect.render_drop_column_default(
            table.table_name, column.column_name, schema=schema
        )
    return dialect.render_set_column_default(
        table.table_name,
        column.column_name,
        render_default(table, column),
        schema=schema,
    )


def _unique_statements(
    table: "SnapshotTable",
    column: "SnapshotColumn",
    ddl_dialect: str,
    schema: str | None,
) -> tuple[str, ...]:
    """The statements that bring *column*'s unique constraint to what *table* records.

    A unique column gets the constraint under the shared name
    (:func:`~cruftfree_rdbms_schema.index_naming.unique_constraint_name`); a column that
    is not unique loses every single-column unique constraint the catalog holds on
    it, whatever its creator named it.
    """
    dialect = sql_dialect(ddl_dialect)
    if column.unique:
        return (
            dialect.render_add_unique_constraint(
                unique_constraint_name(table.table_name, [column.column_name]),
                table.table_name,
                (column.column_name,),
                schema=schema,
            ),
        )
    return dialect.render_drop_column_unique_constraints(
        table.table_name, column.column_name, schema=schema
    )


def column_default_statements(
    table: "SnapshotTable",
    column: "SnapshotColumn",
    ddl_dialect: str,
    *,
    schema: str | None,
    render_default: RenderColumnDefault,
) -> tuple[str, ...]:
    """The statements of a ``FIELD_DEFAULT_CHANGED``, stating *column*'s default.

    ``SET DEFAULT`` when *column* records one, ``DROP DEFAULT`` otherwise. The
    convergence passes the change's subject, the column as the declared schema holds it.

    Args:
        table: The table holding *column*.
        column: The column whose default the database is brought to.
        ddl_dialect: The block's DDL dialect name.
        schema: The schema the adapter qualifies tables with, or ``None``.
        render_default: This language's default renderer -- the one its
            ``CREATE TABLE`` and ``ADD COLUMN`` state defaults with.

    Raises:
        GenerationError: The column's default cannot be a database default.
        DialectNotFoundError: *ddl_dialect* is not a registered DDL dialect.
    """
    return (_default_statement(table, column, ddl_dialect, schema, render_default),)


def column_unique_statements(
    table: "SnapshotTable",
    column: "SnapshotColumn",
    ddl_dialect: str,
    *,
    schema: str | None,
) -> tuple[str, ...]:
    """The statements of a ``FIELD_UNIQUE_CHANGED``, stating *column*'s unique flag.

    A unique column gains its constraint (a row duplicating another fails the
    revision, naming the constraint; no row is deleted); a column that is not
    unique loses every single-column unique constraint it holds, whatever it is
    named. The convergence passes the change's subject.

    Raises:
        DialectNotFoundError: *ddl_dialect* is not a registered DDL dialect.
    """
    return _unique_statements(table, column, ddl_dialect, schema)


@dataclass(frozen=True)
class AddedColumnStatements:
    """What follows an ``ADD COLUMN``: the default statement and the unique constraint.

    ``set_default`` is ``None`` when the add itself states the default (or there is
    none); ``unique`` is empty for a column that is not unique.
    """

    set_default: str | None
    unique: tuple[str, ...]


def added_column_parts(
    table: "SnapshotTable",
    column: "SnapshotColumn",
    ddl_dialect: str,
    *,
    schema: str | None,
    render_default: RenderColumnDefault,
) -> AddedColumnStatements:
    """The statements that follow an ``ADD COLUMN`` so the column matches a created one.

    A column added to an existing table must end up as the same column a
    ``CREATE TABLE`` would have made. Two of its facts are stated after the add:

    * a NULLABLE column's default -- the add leaves the rows already in the table
      NULL (an ``ADD COLUMN ... DEFAULT`` would backfill them), and the default
      then applies to the rows inserted afterwards; a NOT NULL column's default is
      part of the add itself, which needs it to fill the existing rows;
    * a ``: unique`` column's constraint, under the shared ``uq_`` name.
    """
    set_default = None
    if column.nullable and column.default is not None:
        set_default = _default_statement(
            table, column, ddl_dialect, schema, render_default
        )
    unique: tuple[str, ...] = ()
    if column.unique and not column.primary_key:
        unique = _unique_statements(table, column, ddl_dialect, schema)
    return AddedColumnStatements(set_default=set_default, unique=unique)


def added_column_statements(
    table: "SnapshotTable",
    column: "SnapshotColumn",
    ddl_dialect: str,
    *,
    schema: str | None,
    render_default: RenderColumnDefault,
) -> tuple[str, ...]:
    """The statements of :func:`added_column_parts`, in order: the default, then the constraint.

    Returns:
        The statements; empty when the add itself says everything.
    """
    parts = added_column_parts(
        table, column, ddl_dialect, schema=schema, render_default=render_default
    )
    leading = () if parts.set_default is None else (parts.set_default,)
    return (*leading, *parts.unique)


__all__ = [
    "AddedColumnStatements",
    "RenderColumnDefault",
    "added_column_parts",
    "added_column_statements",
    "column_default_statements",
    "column_unique_statements",
]
