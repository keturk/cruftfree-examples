"""Table sides and copy matching for the entity differ."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from cruftfree_common.errors.generation import GenerationError

from cruftfree_rdbms_schema._canonicalize_rules import canonical_index_identity
from cruftfree_rdbms_schema._diff_details import index_label
from cruftfree_rdbms_schema._snapshot_models import (
    SnapshotColumn,
    SnapshotDefault,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotTable,
)
from cruftfree_rdbms_schema.differ import (
    ChangeKind,
    SchemaChange,
    constraint_pairs,
    schema_change_builder,
)


@dataclass(frozen=True)
class TableSides:
    """One table of one snapshot: as the differ compares it, and as a change carries it.

    The differ compares the canonical form
    (:func:`~cruftfree_rdbms_schema.canonicalize.canonicalize_snapshot`), and every change
    carries the object as the snapshot holds it, so a reader gets the table, column or
    index exactly as the database holds it or the schema declares it, never its
    canonical spelling.

    Attributes:
        canonical: The table in canonical form, which the differ compares.
        raw: The table as the snapshot holds it, which supplies every subject.
    """

    canonical: SnapshotTable
    raw: SnapshotTable

    def column(self, field_name: str) -> SnapshotColumn:
        """The column of field *field_name* as the snapshot holds it."""
        return self.raw.fields[field_name]

    def index(self, index: SnapshotIndex) -> SnapshotIndex:
        """The index *index*, one of the canonical table's, as the snapshot holds it.

        Raises:
            GenerationError: The table holds no index of that identity and name, so
                the canonical form is not this table's.
        """
        wanted = canonical_index_identity(index)
        for candidate in self.raw.indexes:
            if (
                canonical_index_identity(candidate) == wanted
                and candidate.name == index.name
            ):
                return candidate
        raise GenerationError(
            "Table '%s' holds no index %s, which its canonical form holds (its indexes: %s). "
            "Expected: the canonical form is the canonicalization of this table. Fix: compare "
            "the snapshot through compute_snapshot_diff, which canonicalizes it itself."
            % (
                self.raw.table_name,
                index_label(index),
                [index_label(i) for i in self.raw.indexes],
            )
        )


def absent_table_sides(table_name: str) -> TableSides:
    """Both forms of the empty stand-in for a table one snapshot never had.

    Used as the other side when diffing a table that exists in one snapshot only.
    Reusing the real per-member diff functions against it is what keeps an added
    table's members reported in exactly the shape a changed table's are -- a second,
    hand-written producer would be free to drift from it, which is how the members
    went missing in the first place.
    """
    absent = SnapshotTable(
        table_name=table_name,
        fields={},
        indexes=(),
        foreign_keys=(),
        table_options={},
    )
    return TableSides(canonical=absent, raw=absent)


class _ColumnPairing:
    """The columns of one table in two snapshots, matched by physical column name.

    A field's identity in the database is its column, not its DSL name: a field
    renamed only in its DSL spelling (``heightAGL`` to ``heightAgl``) keeps the
    column ``height_agl`` and is the same column on both sides. Matching by DSL name
    instead read that rename as one column dropped and another added -- a
    destructive change the policy refuses, for a schema that did not change.

    Every change still names a field by its DSL name: a removed column by the name
    the previous snapshot records, an added or common one by the current name, the
    name the current snapshot (which revisions render against) is keyed by.

    Attributes:
        removed: ``(previous field name, column)`` for each column only *previous* holds.
        added: ``(current field name, column)`` for each column only *current* holds.
        common: ``(current field name, previous column, current column)`` for each
            column both hold.
    """

    def __init__(self, prev_table: SnapshotTable, curr_table: SnapshotTable) -> None:
        prev_by_column = _fields_by_column(prev_table)
        curr_by_column = _fields_by_column(curr_table)
        self.removed: list[tuple[str, SnapshotColumn]] = sorted(
            prev_by_column[column]
            for column in prev_by_column.keys() - curr_by_column.keys()
        )
        self.added: list[tuple[str, SnapshotColumn]] = sorted(
            curr_by_column[column]
            for column in curr_by_column.keys() - prev_by_column.keys()
        )
        self.common: list[tuple[str, SnapshotColumn, SnapshotColumn]] = sorted(
            (
                curr_by_column[column][0],
                prev_by_column[column][1],
                curr_by_column[column][1],
            )
            for column in prev_by_column.keys() & curr_by_column.keys()
        )


def _fields_by_column(table: SnapshotTable) -> dict[str, tuple[str, SnapshotColumn]]:
    """Map each column name of *table* to its ``(field name, column)``."""
    return {column.column_name: (name, column) for name, column in table.fields.items()}


def _diff_entity_fields(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """Diff the columns of one entity present in both snapshots, matched by column name."""
    change = schema_change_builder(service_name, entity_name)
    changes: list[SchemaChange] = []
    pairing = _ColumnPairing(prev.canonical, curr.canonical)

    for removed_field, _removed_col in pairing.removed:
        changes.append(
            change(
                ChangeKind.FIELD_REMOVED,
                field=removed_field,
                detail="Field %s removed" % removed_field,
                subject=prev.column(removed_field),
            )
        )

    for added_field, _added_col in pairing.added:
        changes.append(
            change(
                ChangeKind.FIELD_ADDED,
                field=added_field,
                detail="Field %s added" % added_field,
                subject=curr.column(added_field),
            )
        )

    for field_name, prev_col, curr_col in pairing.common:
        subject = curr.column(field_name)
        if _column_type_changed(prev_col, curr_col):
            changes.append(
                change(
                    ChangeKind.FIELD_TYPE_CHANGED,
                    field=field_name,
                    detail="Field %s type changed" % field_name,
                    old_value=prev_col.type.name,
                    new_value=curr_col.type.name,
                    old_constraints=constraint_pairs(prev_col.type.constraints),
                    new_constraints=constraint_pairs(curr_col.type.constraints),
                    subject=subject,
                )
            )

        if prev_col.nullable != curr_col.nullable:
            changes.append(
                change(
                    ChangeKind.FIELD_NULLABLE_CHANGED,
                    field=field_name,
                    detail="Field %s nullable changed" % field_name,
                    old_value=str(prev_col.nullable),
                    new_value=str(curr_col.nullable),
                    subject=subject,
                )
            )
        changes.extend(
            _diff_column_constraints(change, field_name, prev_col, curr_col, subject)
        )

    return changes


def _column_type_changed(prev_col: SnapshotColumn, curr_col: SnapshotColumn) -> bool:
    """Whether a column both snapshots hold changed its type, a ``FIELD_TYPE_CHANGED``.

    The type is its kind, name and constraints, and the storage the constraints
    give it. Its member list is not read: a column restates the members of the enum
    it is typed with (:func:`~cruftfree_rdbms_schema.schema_snapshot.require_column_members_declared`),
    so a member change is the enum's own change, reported once by the enum diff.
    """
    return (
        prev_col.type.kind != curr_col.type.kind
        or prev_col.type.name != curr_col.type.name
        or constraint_pairs(prev_col.type.constraints)
        != constraint_pairs(curr_col.type.constraints)
        or prev_col.storage != curr_col.storage
    )


def default_change_value(default: SnapshotDefault | None) -> str | None:
    """A column default as a ``FIELD_DEFAULT_CHANGED`` change carries it.

    ``None`` for no default; otherwise the default's kind, value and name as sorted
    JSON, so two defaults compare equal exactly when the snapshot would hash them
    equal.
    """
    if default is None:
        return None
    return json.dumps(
        {"kind": default.kind, "name": default.name, "value": default.value},
        sort_keys=True,
    )


def _diff_column_constraints(
    change: Callable[..., SchemaChange],
    field_name: str,
    prev_col: SnapshotColumn,
    curr_col: SnapshotColumn,
    subject: SnapshotColumn,
) -> list[SchemaChange]:
    """The DEFAULT, primary-key and single-column UNIQUE changes of one column both snapshots hold.

    A default is compared by kind, value and name. A column joining or leaving its
    table's primary key is a ``FIELD_PRIMARY_KEY_CHANGED``. A unique flag is compared only
    on a column that is not a primary key on either side: a primary key is unique by its
    key, and canonicalization marks it so. Every change carries *subject*, the column
    as the current snapshot holds it.
    """
    changes: list[SchemaChange] = []
    previous_default = default_change_value(prev_col.default)
    current_default = default_change_value(curr_col.default)
    if previous_default != current_default:
        changes.append(
            change(
                ChangeKind.FIELD_DEFAULT_CHANGED,
                field=field_name,
                detail="Field %s default changed" % field_name,
                old_value=previous_default,
                new_value=current_default,
                subject=subject,
            )
        )
    if prev_col.primary_key != curr_col.primary_key:
        changes.append(
            change(
                ChangeKind.FIELD_PRIMARY_KEY_CHANGED,
                field=field_name,
                detail="Field %s primary key changed" % field_name,
                old_value=str(prev_col.primary_key),
                new_value=str(curr_col.primary_key),
                subject=subject,
            )
        )
    keyed = prev_col.primary_key or curr_col.primary_key
    if not keyed and prev_col.unique != curr_col.unique:
        changes.append(
            change(
                ChangeKind.FIELD_UNIQUE_CHANGED,
                field=field_name,
                detail="Field %s unique changed" % field_name,
                old_value=str(prev_col.unique),
                new_value=str(curr_col.unique),
                subject=subject,
            )
        )
    return changes


def _table_options_value(table: SnapshotTable) -> str:
    """A table's options as an ``ENTITY_OPTIONS_CHANGED`` change carries them: sorted JSON."""
    return json.dumps(table.table_options, sort_keys=True)


def _diff_entity_table(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """The table-level changes of one entity both snapshots hold under the same key.

    A changed physical name is an ``ENTITY_TABLE_RENAMED`` naming the old and new
    table; changed table options an ``ENTITY_OPTIONS_CHANGED``. Both carry the current
    table.
    """
    change = schema_change_builder(service_name, entity_name)
    changes: list[SchemaChange] = []
    if prev.canonical.table_name != curr.canonical.table_name:
        changes.append(
            change(
                ChangeKind.ENTITY_TABLE_RENAMED,
                detail="Entity %s table renamed" % entity_name,
                old_value=prev.canonical.table_name,
                new_value=curr.canonical.table_name,
                subject=curr.raw,
            )
        )
    previous_options = _table_options_value(prev.canonical)
    current_options = _table_options_value(curr.canonical)
    if previous_options != current_options:
        changes.append(
            change(
                ChangeKind.ENTITY_OPTIONS_CHANGED,
                detail="Entity %s table options changed" % entity_name,
                old_value=previous_options,
                new_value=current_options,
                subject=curr.raw,
            )
        )
    return changes


_Copy = TypeVar("_Copy", SnapshotIndex, SnapshotForeignKey)


@dataclass(frozen=True)
class _CopyMatch(Generic[_Copy]):
    """The copies of one identity on both sides of a table, matched one to one.

    Attributes:
        pairs: ``(previous copy, current copy)`` for each copy both sides hold.
        removed: The copies only the previous side holds.
        added: The copies only the current side holds.
    """

    pairs: tuple[tuple[_Copy, _Copy], ...]
    removed: tuple[_Copy, ...]
    added: tuple[_Copy, ...]
