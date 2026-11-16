"""Shared facts of a change to an enum type that already exists in a database.

PostgreSQL keeps an enum as a named type and changes its member list with
``ALTER TYPE`` (the dialect's
:meth:`~cruftfree_codegen_kernel.sql_facts.dialects.base.SQLDialect.render_add_enum_value`
and ``render_rename_enum_value``). An engine without named enum types keeps the
labels inline in every column's type, so a change restates each column typed
with the enum.

Which columns that is, which label a member is stored as, and the statements that
restate them are facts of the snapshot and of the engine, never of the host
language, so every migration adapter reads them here and only wraps the statements
in its own migration file.

Restating a column is ``ALTER TABLE ... MODIFY COLUMN`` with the column's WHOLE
definition: such an engine replaces the definition rather than editing it, so a restatement
that omitted the default or the comment would silently drop it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cruftfree_common.cruftfree_model.enum_literal_text import (
    stored_enum_literal_from_parts,
)
from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotColumn,
    SnapshotEnum,
)
from cruftfree_rdbms_schema.differ import SchemaChange
from cruftfree_rdbms_schema.enum_relabel import relabeled_members

from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_change_lookup import (
    change_subject,
)

__all__ = [
    "DefaultSqlOf",
    "EnumColumn",
    "InlineEnumRelabelPhases",
    "enum_added_member",
    "enum_columns",
    "enum_relabels",
    "inline_enum_add_statements",
    "inline_enum_relabel_phases",
    "inline_enum_relabel_statements",
    "inline_enum_type_sql",
    "member_stored_label",
    "widened_labels",
]

#: The SQL expression after ``DEFAULT`` that a column keeps through a restatement, or
#: ``None`` when it has none. The caller renders it: a default's spelling is the
#: adapter's own (its server-function table, its literal quoting).
DefaultSqlOf = Callable[["EnumColumn"], str | None]


@dataclass(frozen=True)
class EnumColumn:
    """One column typed with an enum, with the physical table that holds it."""

    table_name: str
    column: SnapshotColumn


def member_stored_label(enum: SnapshotEnum, member: str) -> str:
    """The stored label of one member of *enum*.

    Raises:
        GenerationError: *enum* does not declare the member, or records no member
            values (so no label can be told).
    """
    if member not in enum.values:
        raise GenerationError(
            "Enum member '%s' of '%s' is not among the members it declares (%s), so its "
            "stored label cannot be told." % (member, enum.name, list(enum.values))
        )
    if len(enum.member_values) != len(enum.values):
        raise GenerationError(
            "Enum '%s' records %d declared member values for %d members, so the label "
            "member '%s' is stored as cannot be told. Fix: regenerate the snapshot."
            % (enum.name, len(enum.member_values), len(enum.values), member)
        )
    position = enum.values.index(member)
    return stored_enum_literal_from_parts(member, enum.member_values[position])


def enum_added_member(change: SchemaChange) -> tuple[str, str]:
    """``(database type name, stored label)`` of the member an ``ENUM_VALUE_ADDED`` change appends.

    Both are read from the change's subject, the enum as the declared schema holds it,
    and its ``new_value``, the member added.

    Raises:
        GenerationError: The change names no member, or its enum does not declare it.
    """
    enum = change_subject(change, SnapshotEnum)
    if change.new_value is None:
        raise GenerationError(
            "ENUM_VALUE_ADDED change for enum '%s' names no member. Expected: the member "
            "added, in new_value. Fix: build the change through the snapshot differ."
            % enum.name
        )
    return enum.database_name, member_stored_label(enum, change.new_value)


def enum_relabels(
    change: SchemaChange, previous: SnapshotEnum
) -> tuple[str, dict[str, str]]:
    """``(database type name, {old label: new label})`` of an ``ENUM_VALUE_RELABELED`` change.

    The rows are :func:`~cruftfree_rdbms_schema.enum_relabel.relabeled_members` of *previous*,
    the enum the live catalog holds, and the change's subject, the enum the declared
    schema holds: the one rule the differ decided the change with.

    Raises:
        GenerationError: The two enums relabel no member, or either records no member values.
    """
    enum = change_subject(change, SnapshotEnum)
    try:
        rows = relabeled_members(previous, enum)
    except ValueError as exc:
        raise GenerationError(str(exc)) from exc
    if not rows:
        raise GenerationError(
            "ENUM_VALUE_RELABELED change for enum '%s' relabels no member: the live catalog "
            "and the declared schema store every member under one label. Fix: build the "
            "change through the snapshot differ against the catalog it is rendered with."
            % enum.name
        )
    return enum.database_name, {old: new for _, old, new in rows}


def enum_columns(
    snapshot: RdbmsSchemaSnapshot, enum_name: str
) -> tuple[EnumColumn, ...]:
    """Every column of every table in *snapshot* typed with the enum *enum_name*.

    Tables are walked in the snapshot's own order, so a revision's bytes do not
    depend on anything else.

    Raises:
        GenerationError: No column is typed with the enum. A change to an enum no
            column uses has nothing to restate, so it is a defect in the diff.
    """
    found = tuple(
        EnumColumn(table.table_name, column)
        for table in snapshot.declared_tables().values()
        for column in table.fields.values()
        if column.type.kind == "enum" and column.type.name == enum_name
    )
    if not found:
        raise GenerationError(
            "Enum '%s' changed but no column of the current snapshot is typed with "
            "it, so there is no column to restate. Check that an entity field of "
            "this rdbms block uses the enum." % enum_name
        )
    return found


def widened_labels(final: Sequence[str], also: Sequence[str]) -> tuple[str, ...]:
    """The labels in *final*, then those of *also* that *final* lacks.

    The inline enum a column holds while a relabel moves its rows: it accepts both
    the labels the rows hold now and the ones they move to.
    """
    held = set(final)
    return (*final, *(label for label in also if label not in held))


def inline_enum_type_sql(dialect: SQLDialect, labels: Sequence[str]) -> str:
    """The column type of an inline-enum engine holding *labels*: ``ENUM('a', 'b')``."""
    return "ENUM(%s)" % ", ".join(dialect.quote_literal(label) for label in labels)


def _modify_column_sql(
    dialect: SQLDialect,
    ref: EnumColumn,
    labels: Sequence[str],
    default_sql: str | None,
) -> str:
    """``ALTER TABLE ... MODIFY COLUMN`` restating *ref* as an inline enum of *labels*."""
    column = ref.column
    parts = [
        dialect.quote_identifier(column.column_name),
        inline_enum_type_sql(dialect, labels),
    ]
    if not column.nullable:
        parts.append("NOT NULL")
    if default_sql is not None:
        parts.append("DEFAULT %s" % default_sql)
    definition = " ".join(parts) + dialect.inline_column_comment(column.comment)
    return "ALTER TABLE %s MODIFY COLUMN %s;" % (
        dialect.quote_identifier(ref.table_name),
        definition,
    )


def _relabel_update_sql(
    dialect: SQLDialect, ref: EnumColumn, relabels: Mapping[str, str]
) -> str:
    """One ``UPDATE`` moving a column's rows from their old labels to their new ones.

    A single ``CASE`` reads every row's label as it was before the statement, so a
    chain (``a -> b``, ``b -> c``) and a swap (``a -> b``, ``b -> a``) are correct
    without the ordering a one-label-at-a-time rename needs.
    """
    column = dialect.quote_identifier(ref.column.column_name)
    whens = " ".join(
        "WHEN %s THEN %s" % (dialect.quote_literal(old), dialect.quote_literal(new))
        for old, new in relabels.items()
    )
    return "UPDATE %s SET %s = CASE %s %s ELSE %s END WHERE %s IN (%s);" % (
        dialect.quote_identifier(ref.table_name),
        column,
        column,
        whens,
        column,
        column,
        ", ".join(dialect.quote_literal(old) for old in relabels),
    )


def inline_enum_add_statements(
    dialect: SQLDialect,
    columns: Sequence[EnumColumn],
    final_labels: Sequence[str],
    default_sql_of: DefaultSqlOf,
) -> list[str]:
    """Statements that give every column of an inline-enum engine the member list *final_labels*."""
    return [
        _modify_column_sql(dialect, ref, final_labels, default_sql_of(ref))
        for ref in columns
    ]


@dataclass(frozen=True)
class InlineEnumRelabelPhases:
    """The three phases of an inline-enum relabel, each one statement per column.

    ``widen`` restates every column to a list accepting both the old and the new
    labels, ``move`` updates the rows, ``narrow`` restates to the final list.
    """

    widen: tuple[str, ...]
    move: tuple[str, ...]
    narrow: tuple[str, ...]


def inline_enum_relabel_phases(
    dialect: SQLDialect,
    columns: Sequence[EnumColumn],
    final_labels: Sequence[str],
    relabels: Mapping[str, str],
    default_sql_of: DefaultSqlOf,
) -> InlineEnumRelabelPhases:
    """The widen, move and narrow statements of a relabel on an inline-enum engine.

    A column never holds a row its type cannot represent between the phases, so
    the revision applies under a strict SQL mode.

    Raises:
        GenerationError: *relabels* is empty.
    """
    if not relabels:
        raise GenerationError(
            "An enum relabel needs at least one {old label: new label} pair; the "
            "differ never emits an empty relabel."
        )
    widened = widened_labels(final_labels, tuple(relabels))
    return InlineEnumRelabelPhases(
        widen=tuple(
            _modify_column_sql(dialect, ref, widened, default_sql_of(ref))
            for ref in columns
        ),
        move=tuple(_relabel_update_sql(dialect, ref, relabels) for ref in columns),
        narrow=tuple(
            _modify_column_sql(dialect, ref, final_labels, default_sql_of(ref))
            for ref in columns
        ),
    )


def inline_enum_relabel_statements(
    dialect: SQLDialect,
    columns: Sequence[EnumColumn],
    final_labels: Sequence[str],
    relabels: Mapping[str, str],
    default_sql_of: DefaultSqlOf,
) -> list[str]:
    """Statements that move every column's rows to their new labels, ending on *final_labels*.

    The phases of :func:`inline_enum_relabel_phases`, in order.

    Raises:
        GenerationError: *relabels* is empty.
    """
    phases = inline_enum_relabel_phases(
        dialect, columns, final_labels, relabels, default_sql_of
    )
    return [*phases.widen, *phases.move, *phases.narrow]
