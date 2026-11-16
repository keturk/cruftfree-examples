"""Enum value and comment change rendering."""

from __future__ import annotations

from collections.abc import Mapping

from cruftfree_common.cruftfree_model.enum_literal_text import (
    stored_enum_literal_from_parts,
)
from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotEnum,
    SnapshotTable,
)
from cruftfree_rdbms_schema.differ import SchemaChange
from cruftfree_rdbms_schema.enum_relabel import ordered_relabel_steps

from cruftfree_codegen_kernel.sql_facts._revision_columns import (
    _column_definition,
    _definition_text,
    _statements,
)
from cruftfree_codegen_kernel.sql_facts._revision_model import (
    SqlObjectKind,
    SqlStatement,
    SqlStatementKind,
)
from cruftfree_codegen_kernel.sql_facts._revision_statements import (
    _changed_column,
    _column_restatements,
    _enum_default_of,
    _RevisionContext,
)
from cruftfree_codegen_kernel.sql_facts.constants import FEATURE_NAMED_ENUM_TYPES
from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    enum_label_neighbour,
)
from cruftfree_codegen_kernel.sql_facts.enum_member_change import (
    enum_added_member,
    enum_columns,
    enum_relabels,
    inline_enum_add_statements,
    inline_enum_relabel_phases,
    member_stored_label,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_change_lookup import (
    change_subject,
)


def _named_enum(snapshot: RdbmsSchemaSnapshot, enum_name: str) -> SnapshotEnum:
    """*snapshot*'s enum *enum_name*.

    Raises:
        GenerationError: *snapshot* declares no enum *enum_name*.
    """
    for snap_enum in snapshot.enums:
        if snap_enum.name == enum_name:
            return snap_enum
    raise GenerationError(
        "Enum '%s' is not declared by the snapshot (it declares %s), so the labels its "
        "type holds cannot be told. Expected: a label addition to an enum both snapshots "
        "declare." % (enum_name, sorted(snap_enum.name for snap_enum in snapshot.enums))
    )


def _previous_member_labels(
    previous_enum: SnapshotEnum, current: Mapping[str, str]
) -> dict[str, str]:
    """``{member name: stored label}`` the type holds before the revision runs.

    A snapshot that records its members' declared values says each label. One
    written before they were recorded cannot, and then the differ plans no relabel
    either, so each member the revision keeps is held under its current label.
    """
    if len(previous_enum.member_values) == len(previous_enum.values):
        return {
            member: stored_enum_literal_from_parts(member, declared)
            for member, declared in zip(
                previous_enum.values, previous_enum.member_values, strict=True
            )
        }
    return {
        member: current[member] for member in previous_enum.values if member in current
    }


def _declared_labels(enum: SnapshotEnum) -> tuple[str, ...]:
    """The stored label of every member of *enum*, in member order."""
    return tuple(member_stored_label(enum, member) for member in enum.values)


def _enum_labels_held_as(
    ctx: _RevisionContext, change: SchemaChange, current_enum: SnapshotEnum
) -> list[str | None]:
    """Per member of the declared enum, the label the type holds it under now.

    A member the live catalog holds is held under its live label (a relabel in the
    same revision renames it in place, after the additions); a member this revision
    has already added is held under its label; any other member is not held yet
    (``None``).
    """
    enum_name = current_enum.name
    current = dict(
        zip(current_enum.values, _declared_labels(current_enum), strict=True)
    )
    previous = _previous_member_labels(
        _named_enum(ctx.previous_snapshot(change), enum_name), current
    )
    added = ctx.added_enum_labels.get(enum_name, set())
    held_as: list[str | None] = []
    for member, label in current.items():
        if member in previous:
            held_as.append(previous[member])
        elif label in added:
            held_as.append(label)
        else:
            held_as.append(None)
    return held_as


def _render_enum_value_added(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The label added to the named type beside its declared neighbour, or every column
    of an inline enum restated.

    The neighbour is a member the type holds when the statement runs
    (:func:`_enum_labels_held_as`), so the additions place correctly in whatever
    order the revision renders them.
    """
    dialect = ctx.dialect
    database_name, label = enum_added_member(change)
    enum = change_subject(change, SnapshotEnum)
    labels = _declared_labels(enum)
    if dialect.supports_feature(FEATURE_NAMED_ENUM_TYPES):
        held_as = _enum_labels_held_as(ctx, change, enum)
        neighbour = enum_label_neighbour(held_as, labels.index(label))
        ctx.added_enum_labels.setdefault(enum.name, set()).add(label)
        return _statements(
            SqlStatementKind.ADD_ENUM_VALUE,
            SqlObjectKind.ENUM_TYPE,
            database_name,
            None,
            dialect.render_add_enum_value(
                database_name, label, (), neighbour=neighbour
            ),
        )
    columns = enum_columns(ctx.current, enum.name)
    sqls = inline_enum_add_statements(dialect, columns, labels, _enum_default_of(ctx))
    return _column_restatements(SqlStatementKind.ALTER_COLUMN_TYPE, columns, sqls)


def _render_enum_value_relabeled(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The labels renamed in the named type, or an inline enum widened, moved and narrowed.

    The rows are the live catalog's enum against the change's subject
    (:func:`~cruftfree_codegen_kernel.sql_facts.enum_member_change.enum_relabels`).
    """
    dialect = ctx.dialect
    enum = change_subject(change, SnapshotEnum)
    previous = _named_enum(ctx.previous_snapshot(change), enum.name)
    database_name, relabels = enum_relabels(change, previous)
    labels = _declared_labels(enum)
    if dialect.supports_feature(FEATURE_NAMED_ENUM_TYPES):
        reserved = set(labels) | set(relabels)
        return _statements(
            SqlStatementKind.RENAME_ENUM_VALUE,
            SqlObjectKind.ENUM_TYPE,
            database_name,
            None,
            [
                dialect.render_rename_enum_value(database_name, old, new)
                for old, new in ordered_relabel_steps(relabels, reserved=reserved)
            ],
        )
    columns = enum_columns(ctx.current, enum.name)
    phases = inline_enum_relabel_phases(
        dialect, columns, labels, relabels, _enum_default_of(ctx)
    )
    return [
        *_column_restatements(
            SqlStatementKind.ALTER_COLUMN_TYPE, columns, phases.widen
        ),
        *_column_restatements(SqlStatementKind.RAW_BACKFILL, columns, phases.move),
        *_column_restatements(
            SqlStatementKind.ALTER_COLUMN_TYPE, columns, phases.narrow
        ),
    ]


def _render_enum_type_removed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The drop of the named enum type the live catalog holds, the change's subject."""
    database_name = change_subject(change, SnapshotEnum).database_name
    return _statements(
        SqlStatementKind.DROP_ENUM_TYPE,
        SqlObjectKind.ENUM_TYPE,
        database_name,
        None,
        [ctx.dialect.render_drop_enum_type(database_name)],
    )


def _render_entity_comment_changed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The table comment the subject records (cleared when it records none)."""
    table = change_subject(change, SnapshotTable)
    return _statements(
        SqlStatementKind.SET_COMMENT,
        SqlObjectKind.TABLE,
        table.table_name,
        table.table_name,
        [ctx.dialect.render_table_comment(table.table_name, table.comment)],
    )


def _render_field_comment_changed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The column comment the current snapshot records, restating the whole column where needed.

    An engine that keeps the comment in the column definition restates it, so the
    definition passed carries the type, the numbering, the nullability and the default.
    """
    dialect = ctx.dialect
    table, column = _changed_column(ctx.current, change)
    definition = _column_definition(dialect, ctx.current, table, column, created=False)
    return _statements(
        SqlStatementKind.SET_COMMENT,
        SqlObjectKind.COLUMN,
        column.column_name,
        table.table_name,
        [
            dialect.render_column_comment(
                table.table_name,
                column.column_name,
                _definition_text(definition),
                column.comment,
            )
        ],
    )
