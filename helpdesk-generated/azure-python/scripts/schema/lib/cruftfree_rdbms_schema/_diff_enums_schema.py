"""Schema placement and enum diffing."""

from __future__ import annotations

from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot, SnapshotEnum
from cruftfree_rdbms_schema.differ import ChangeKind, SchemaChange
from cruftfree_rdbms_schema.enum_relabel import relabeled_members
from cruftfree_rdbms_schema.schema_snapshot import enum_names_in_use


def _diff_schema_placement(
    service_name: str,
    previous: RdbmsSchemaSnapshot,
    current: RdbmsSchemaSnapshot,
) -> list[SchemaChange]:
    """Emit a SCHEMA_RELOCATED change when the block's schema placement changed.

    The block's PostgreSQL schema is recorded on every snapshot, so placement is
    compared on every call.

    ``old_value``/``new_value`` carry the previous and current schema (``None``
    meaning the default schema). The change is about the whole block, so it carries
    no subject.
    """
    if previous.schema_name == current.schema_name:
        return []
    return [
        SchemaChange(
            kind=ChangeKind.SCHEMA_RELOCATED,
            service=service_name,
            old_value=previous.schema_name,
            new_value=current.schema_name,
            detail="Block schema relocated from %s to %s"
            % (
                previous.schema_name or "<default>",
                current.schema_name or "<default>",
            ),
        )
    ]


def _diff_one_enum(
    service_name: str,
    previous: SnapshotEnum,
    current: SnapshotEnum,
) -> list[SchemaChange]:
    """Diff the member list and stored labels of one enum present in both snapshots.

    Every change carries *current*, the enum as the current snapshot holds it.

    Args:
        service_name: Owner recorded on every emitted change.
        previous: The enum as the previous snapshot holds it.
        current: The enum as the current snapshot holds it.

    Raises:
        ValueError: Either enum records fewer declared member values than members
            (:func:`~cruftfree_rdbms_schema.enum_relabel.relabeled_members`).
    """
    changes: list[SchemaChange] = []
    relabels = relabeled_members(previous, current)
    if relabels:
        changes.append(
            SchemaChange(
                kind=ChangeKind.ENUM_VALUE_RELABELED,
                service=service_name,
                enum=current.name,
                detail="Members %s of enum %s relabeled"
                % (", ".join(name for name, _, _ in relabels), current.name),
                old_value=",".join(old for _, old, _ in relabels),
                new_value=",".join(new for _, _, new in relabels),
                subject=current,
            )
        )
    if previous.values == current.values:
        return changes

    previous_members = set(previous.values)
    current_members = set(current.values)

    for removed in sorted(previous_members - current_members):
        changes.append(
            SchemaChange(
                kind=ChangeKind.ENUM_VALUE_REMOVED,
                service=service_name,
                enum=current.name,
                detail="Member %s removed from enum %s" % (removed, current.name),
                old_value=removed,
                subject=current,
            )
        )
    for added in sorted(current_members - previous_members):
        changes.append(
            SchemaChange(
                kind=ChangeKind.ENUM_VALUE_ADDED,
                service=service_name,
                enum=current.name,
                detail="Member %s added to enum %s" % (added, current.name),
                new_value=added,
                subject=current,
            )
        )

    # Reordering is only meaningful for the members BOTH sides have: an added
    # member is placed beside its declared neighbour, and a removed one leaves a
    # gap, so comparing the raw tuples would report a reorder for every addition.
    # Compare the shared members' relative order instead, which is exactly what an
    # existing database can no longer be made to match.
    shared = previous_members & current_members
    previous_order = tuple(v for v in previous.values if v in shared)
    current_order = tuple(v for v in current.values if v in shared)
    if previous_order != current_order:
        changes.append(
            SchemaChange(
                kind=ChangeKind.ENUM_VALUES_REORDERED,
                service=service_name,
                enum=current.name,
                detail="Members of enum %s reordered" % current.name,
                old_value=",".join(previous_order),
                new_value=",".join(current_order),
                subject=current,
            )
        )
    return changes


def _type_change(
    service_name: str, kind: ChangeKind, enum: SnapshotEnum
) -> SchemaChange:
    """An ``ENUM_TYPE_REMOVED`` / ``ENUM_TYPE_ADDED`` of *enum*, the type one side holds."""
    return SchemaChange(
        kind=kind,
        service=service_name,
        enum=enum.name,
        detail=enum.database_name,
        subject=enum,
    )


def _diff_enum_types(
    service_name: str,
    previous: RdbmsSchemaSnapshot,
    current: RdbmsSchemaSnapshot,
) -> list[SchemaChange]:
    """Emit the enum type changes no column change implies.

    ``ENUM_TYPE_REMOVED`` for each type *previous* holds under a database name *current*
    declares no type under, and so no column of *current* uses: one no column of either
    side uses, and one only a column or table *current* removes used -- dropping the
    column or table leaves the type in the database. A type *current* holds under the
    same name and another database name is an ``ENUM_TYPE_RENAMED`` instead, carrying
    both database names.

    ``ENUM_TYPE_ADDED`` for each type only *current* holds and no column of *current*
    uses. A used type needs none: the column change that introduces its first use
    creates it.
    """
    previous_by_name = {e.name: e for e in previous.enums}
    current_by_name = {e.name: e for e in current.enums}
    renamed = sorted(
        name
        for name in previous_by_name.keys() & current_by_name.keys()
        if previous_by_name[name].database_name != current_by_name[name].database_name
    )
    declared = {e.database_name for e in current.enums}
    changes = [
        _type_change(service_name, ChangeKind.ENUM_TYPE_REMOVED, enum)
        for enum in sorted(previous.enums, key=lambda e: (e.name, e.database_name))
        if enum.database_name not in declared and enum.name not in renamed
    ]
    current_in_use = enum_names_in_use(current)
    changes.extend(
        _type_change(service_name, ChangeKind.ENUM_TYPE_ADDED, current_by_name[name])
        for name in sorted(current_by_name.keys() - previous_by_name.keys())
        if name not in current_in_use
    )
    changes.extend(
        SchemaChange(
            kind=ChangeKind.ENUM_TYPE_RENAMED,
            service=service_name,
            enum=name,
            detail="Enum %s renamed from %s to %s"
            % (
                name,
                previous_by_name[name].database_name,
                current_by_name[name].database_name,
            ),
            old_value=previous_by_name[name].database_name,
            new_value=current_by_name[name].database_name,
            subject=current_by_name[name],
        )
        for name in renamed
    )
    return changes


def _diff_enums(
    service_name: str,
    previous: RdbmsSchemaSnapshot,
    current: RdbmsSchemaSnapshot,
) -> list[SchemaChange]:
    """Emit the enum type changes and the member-list changes of enums in BOTH snapshots.

    ``enums`` is part of the hashed snapshot payload, so a change confined to
    ``enums[].values`` is compared here: otherwise it would read as *no schema
    change*, and a destructive edit (removal, rename, reorder) would never
    reach the convergence gate that exists to refuse it. A
    column's own ``SnapshotType.values`` does not cover it either:
    :func:`_diff_entity_fields` compares ``type.name``, which an enum member
    change leaves untouched. The types themselves are compared by
    :func:`_diff_enum_types`.

    Args:
        service_name: Owner recorded on every emitted change.
        previous: The previous snapshot (the live catalog ``L`` in a convergence).
        current: The current snapshot (the declared schema ``D``).

    Returns:
        Ordered enum changes: the type changes, then the member changes grouped by
        enum name.
    """
    previous_by_name = {e.name: e for e in previous.enums}
    changes = _diff_enum_types(service_name, previous, current)
    for current_enum in sorted(current.enums, key=lambda e: e.name):
        previous_enum = previous_by_name.get(current_enum.name)
        if previous_enum is None:
            continue
        changes.extend(_diff_one_enum(service_name, previous_enum, current_enum))
    return changes
