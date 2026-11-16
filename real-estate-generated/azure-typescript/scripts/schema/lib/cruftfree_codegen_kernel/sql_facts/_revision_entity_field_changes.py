"""Entity and field change rendering.

Every renderer reads the table or column it acts on from the change's subject; the
table a column belongs to is read from the snapshot that holds it, for its name and
its enum types.
"""

from __future__ import annotations

import dataclasses

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import SnapshotTable
from cruftfree_rdbms_schema.differ import SchemaChange
from cruftfree_rdbms_schema.index_naming import unique_constraint_name

from cruftfree_codegen_kernel.sql_facts._revision_columns import (
    _column_definition,
    _statements,
)
from cruftfree_codegen_kernel.sql_facts._revision_literals import (
    _default_renderer,
    _default_sql,
)
from cruftfree_codegen_kernel.sql_facts._revision_model import (
    SqlObjectKind,
    SqlStatement,
    SqlStatementKind,
)
from cruftfree_codegen_kernel.sql_facts._revision_statements import (
    _changed_column,
    _column_unique_statements,
    _create_table_statements,
    _enum_type_statements,
    _RevisionContext,
    _standalone_comment_statements,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.column_constraint_change import (
    added_column_parts,
    column_default_statements,
    column_unique_statements,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_change_lookup import (
    change_subject,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_default_literal import (
    require_nullable_changed_default,
)


def _render_entity_added(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The table, its enum types, its column uniques and its standalone comments."""
    table = change_subject(change, SnapshotTable)
    return [
        *_enum_type_statements(ctx, [(table.table_name, c) for c in table.fields.values()]),
        *_create_table_statements(ctx, table),
        *_column_unique_statements(ctx, table),
        *_standalone_comment_statements(ctx, table),
    ]


def _render_entity_removed(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The drop of the table the live catalog holds."""
    table = change_subject(change, SnapshotTable)
    return _statements(
        SqlStatementKind.DROP_TABLE,
        SqlObjectKind.TABLE,
        table.table_name,
        table.table_name,
        ctx.dialect.render_drop_table(table.table_name),
    )


def _render_field_added(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """``ADD COLUMN``, then the column's default, unique constraint and comment.

    A NOT NULL column carries its default in the add, which fills the rows the table
    holds; a nullable one gets it from the statement after, so existing rows stay NULL.

    Raises:
        GenerationError: A NOT NULL column carries no default to fill existing rows.
    """
    dialect = ctx.dialect
    table, column = _changed_column(ctx.current, change)
    table_name = table.table_name
    definition = _column_definition(dialect, ctx.current, table, column, created=True)
    if not column.nullable and definition.default is None and not definition.auto_increment:
        raise GenerationError(
            "Non-nullable column '%s' is added to existing table '%s' without a database "
            "default, so ADD COLUMN ... NOT NULL cannot fill the rows the table holds and "
            "the revision would fail on apply. Fix: make the field optional, or give it a "
            "default the database can evaluate." % (column.column_name, table_name)
        )
    if column.nullable:
        definition = dataclasses.replace(definition, default=None)
    parts = added_column_parts(
        table, column, dialect.name, schema=None, render_default=_default_renderer(dialect)
    )
    name = column.column_name
    statements = [
        *_enum_type_statements(ctx, [(table_name, column)]),
        *_statements(
            SqlStatementKind.ADD_COLUMN,
            SqlObjectKind.COLUMN,
            name,
            table_name,
            [dialect.render_add_column(table_name, definition)],
        ),
        *_statements(
            SqlStatementKind.SET_DEFAULT,
            SqlObjectKind.COLUMN,
            name,
            table_name,
            [] if parts.set_default is None else [parts.set_default],
        ),
        *_statements(
            SqlStatementKind.ADD_UNIQUE_CONSTRAINT,
            SqlObjectKind.CONSTRAINT,
            unique_constraint_name(table_name, [name]),
            table_name,
            parts.unique,
        ),
    ]
    if column.comment is not None and dialect.inline_column_comment(column.comment) == "":
        statements.extend(
            _statements(
                SqlStatementKind.SET_COMMENT,
                SqlObjectKind.COLUMN,
                name,
                table_name,
                [dialect.render_column_comment(table_name, name, "", column.comment)],
            )
        )
    return statements


def _render_field_removed(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The drop of the column the live catalog holds."""
    table, column = _changed_column(ctx.previous_snapshot(change), change)
    return _statements(
        SqlStatementKind.DROP_COLUMN,
        SqlObjectKind.COLUMN,
        column.column_name,
        table.table_name,
        [ctx.dialect.render_drop_column(table.table_name, column.column_name)],
    )


def _render_field_type_changed(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The column's new type, read from the subject (with its enum type, if new)."""
    table, column = _changed_column(ctx.current, change)
    definition = _column_definition(ctx.dialect, ctx.current, table, column, created=False)
    return [
        *_enum_type_statements(ctx, [(table.table_name, column)]),
        *_statements(
            SqlStatementKind.ALTER_COLUMN_TYPE,
            SqlObjectKind.COLUMN,
            column.column_name,
            table.table_name,
            [ctx.dialect.render_alter_column_type(table.table_name, definition)],
        ),
    ]


def _render_field_nullable_changed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The column's nullability; a column becoming NOT NULL first fills its NULL rows.

    Raises:
        GenerationError: The change and its subject disagree on the nullability, or a
            column becoming NOT NULL has no default to fill with.
    """
    dialect = ctx.dialect
    table, column = _changed_column(ctx.current, change)
    table_name = table.table_name
    if change.new_value != str(column.nullable):
        raise GenerationError(
            "FIELD_NULLABLE_CHANGED on '%s.%s' moves nullability to %r, but its column "
            "records nullable=%s. Expected: the change and the column it carries agree. "
            "Fix: build the change through the snapshot differ."
            % (table_name, column.column_name, change.new_value, column.nullable)
        )
    statements: list[SqlStatement] = []
    if not column.nullable:
        require_nullable_changed_default(
            column.default, entity_name=change.entity or "", field_name=column.column_name
        )
        quoted = dialect.quote_identifier(column.column_name)
        backfill = "UPDATE %s SET %s = %s WHERE %s IS NULL;" % (
            dialect.quote_identifier(table_name),
            quoted,
            _default_sql(table_name, column, dialect),
            quoted,
        )
        statements.extend(
            _statements(
                SqlStatementKind.RAW_BACKFILL, SqlObjectKind.COLUMN, column.column_name, table_name, [backfill]
            )
        )
    definition = _column_definition(dialect, ctx.current, table, column, created=False)
    statements.extend(
        _statements(
            SqlStatementKind.ALTER_NULLABILITY,
            SqlObjectKind.COLUMN,
            column.column_name,
            table_name,
            [dialect.render_alter_nullability(table_name, definition)],
        )
    )
    return statements


def _render_field_default_changed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """``SET DEFAULT`` to the subject's default, or ``DROP DEFAULT`` when it has none."""
    table, column = _changed_column(ctx.current, change)
    kind = SqlStatementKind.SET_DEFAULT if column.default is not None else SqlStatementKind.DROP_DEFAULT
    return _statements(
        kind,
        SqlObjectKind.COLUMN,
        column.column_name,
        table.table_name,
        column_default_statements(
            table,
            column,
            ctx.dialect.name,
            schema=None,
            render_default=_default_renderer(ctx.dialect),
        ),
    )


def _render_field_unique_changed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The ``uq_`` constraint of a column now unique, or the drop of every one it held."""
    table, column = _changed_column(ctx.current, change)
    sqls = column_unique_statements(table, column, ctx.dialect.name, schema=None)
    if column.unique:
        return _statements(
            SqlStatementKind.ADD_UNIQUE_CONSTRAINT,
            SqlObjectKind.CONSTRAINT,
            unique_constraint_name(table.table_name, [column.column_name]),
            table.table_name,
            sqls,
        )
    return _statements(
        SqlStatementKind.DROP_UNIQUE_CONSTRAINT,
        SqlObjectKind.COLUMN,
        column.column_name,
        table.table_name,
        sqls,
    )
