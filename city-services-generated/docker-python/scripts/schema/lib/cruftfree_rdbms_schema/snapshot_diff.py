"""Canonical structural diff between two RDBMS schema snapshots.

A :class:`~cruftfree_rdbms_schema._snapshot_models.RdbmsSchemaSnapshot` is a
single-block structure (one service, one RDBMS block).  This module compares two
such snapshots field-by-field and emits the ordered
:class:`~cruftfree_rdbms_schema.differ.SchemaChange` records the convergence
gate consumes.  It is the SINGLE source of truth for snapshot → snapshot
diffing and holds every comparison of a live catalog ``L`` with the declared
schema ``D``: the convergence calls :func:`compute_snapshot_diff`, and so does
every other comparison.
"""

from __future__ import annotations

from cruftfree_rdbms_schema._diff_entity_comments import _diff_common_entity
from cruftfree_rdbms_schema._diff_entity_members import (
    diff_added_entity_members,
    diff_removed_entity_members,
)
from cruftfree_rdbms_schema._diff_entity_tables import TableSides
from cruftfree_rdbms_schema._diff_enums_schema import (
    _diff_enums,
    _diff_schema_placement,
)
from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot
from cruftfree_rdbms_schema.canonicalize import canonicalize_snapshot
from cruftfree_rdbms_schema.differ import (
    ChangeKind,
    SchemaChange,
    SchemaDiff,
    schema_change_order,
)
from cruftfree_rdbms_schema.schema_snapshot import (
    compute_schema_hash,
    require_column_members_declared,
)


def _table_sides(
    snapshot: RdbmsSchemaSnapshot, canonical: RdbmsSchemaSnapshot
) -> dict[str, TableSides]:
    """Every declared table of *snapshot*, in canonical form and as it holds it."""
    canonical_tables = canonical.declared_tables()
    return {
        name: TableSides(canonical=canonical_tables[name], raw=table)
        for name, table in snapshot.declared_tables().items()
    }


def _table_changes(
    service_name: str, previous: dict[str, TableSides], current: dict[str, TableSides]
) -> list[SchemaChange]:
    """The table, column, index, key, check, trigger and comment changes of two snapshots."""
    changes: list[SchemaChange] = []
    for removed_name in sorted(previous.keys() - current.keys()):
        changes.append(
            SchemaChange(
                kind=ChangeKind.ENTITY_REMOVED,
                service=service_name,
                entity=removed_name,
                detail="Entity %s removed" % removed_name,
                subject=previous[removed_name].raw,
            )
        )
        changes.extend(
            diff_removed_entity_members(
                service_name, removed_name, previous[removed_name]
            )
        )

    for added_name in sorted(current.keys() - previous.keys()):
        changes.append(
            SchemaChange(
                kind=ChangeKind.ENTITY_ADDED,
                service=service_name,
                entity=added_name,
                detail="Entity %s added" % added_name,
                subject=current[added_name].raw,
            )
        )
        # ENTITY_ADDED names the table; the indexes on it are separate changes,
        # exactly as they are for an entity that gained one.
        changes.extend(
            diff_added_entity_members(service_name, added_name, current[added_name])
        )

    for common_name in sorted(previous.keys() & current.keys()):
        changes.extend(
            _diff_common_entity(
                service_name, common_name, previous[common_name], current[common_name]
            )
        )
    return changes


# @canonical(rdbms-schema/snapshot-diff): Single source of truth for diffing two
# RDBMS schema snapshots, and the one home of every comparison of L with D
# @rule: Every comparison of two snapshots (a convergence's L vs D included) MUST call
# compute_snapshot_diff so no two diffs diverge; it canonicalizes both operands itself.
# @rule: A name-only difference of an index or foreign key is a rename it reports, an
# action change of a foreign key a replacement, and a type no current column uses a
# removal -- no caller compares names, actions or enum types a second time.
# @rule: Every change carries its subject as the snapshot holds it, never canonicalized.
# @rule: Equal schema hashes short-circuit to an empty diff.
# @see: rdbms-schema/schema-differ
# @see: rdbms-schema/snapshot-canonicalization
def compute_snapshot_diff(
    previous: RdbmsSchemaSnapshot,
    current: RdbmsSchemaSnapshot,
) -> SchemaDiff:
    """Compute a schema diff between two single-block RDBMS snapshots.

    Both operands are canonicalized (:func:`~cruftfree_rdbms_schema.canonicalize.canonicalize_snapshot`)
    and compared in that form; every change carries its subject as the operand holds it,
    so a removal names the object the previous side holds and an addition the object
    the current side declares. Equal canonical hashes return an empty diff. Otherwise
    the full ordered set of :class:`SchemaChange` records is built from
    table/field/index/foreign-key, check, trigger, table/column comment, enum and block
    schema-placement diffs. "Table" here means every table the block's schema declares
    -- entity tables, CQRS read-model backing tables, audit-log, junction and
    framework tables alike (:meth:`RdbmsSchemaSnapshot.declared_tables`).

    The ``service`` field on every emitted change is taken from
    ``current.service.name`` so changes carry a stable owner.

    Args:
        previous: The previous snapshot (the live catalog ``L`` in a convergence,
            prepared and not canonicalized, so its names are the ones the database holds).
        current: The current snapshot (the declared schema ``D``).

    Returns:
        :class:`SchemaDiff` with all detected changes and both canonical schema hashes.

    Raises:
        ValueError: A column of either snapshot lists members its type does not
            declare (:func:`require_column_members_declared`): its member list is
            a restatement the differ does not compare, so a malformed one is refused
            rather than read as no change.
        GenerationError: A table holds several copies of an index or foreign key under
            names no copy of the other side carries, other than one each, so which copy
            is renamed and which removed is undecided.
    """
    require_column_members_declared(previous)
    require_column_members_declared(current)
    canonical_previous = canonicalize_snapshot(previous)
    canonical_current = canonicalize_snapshot(current)
    previous_hash = compute_schema_hash(canonical_previous)
    current_hash = compute_schema_hash(canonical_current)

    if previous_hash == current_hash:
        return SchemaDiff(
            changes=(),
            previous_hash=previous_hash,
            current_hash=current_hash,
        )

    service_name = current.service.name
    changes = _table_changes(
        service_name,
        _table_sides(previous, canonical_previous),
        _table_sides(current, canonical_current),
    )
    changes.extend(_diff_enums(service_name, previous, current))
    changes.extend(_diff_schema_placement(service_name, previous, current))

    changes.sort(key=schema_change_order)

    return SchemaDiff(
        changes=tuple(changes),
        previous_hash=previous_hash,
        current_hash=current_hash,
    )


__all__ = [
    "compute_snapshot_diff",
]
