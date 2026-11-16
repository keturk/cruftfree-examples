"""Per-entity field, column, index, foreign key and check diffing."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from cruftfree_common.errors.generation import GenerationError

from cruftfree_rdbms_schema._diff_details import (
    foreign_key_change_field,
    foreign_key_label,
    index_identity,
    index_label,
)
from cruftfree_rdbms_schema._diff_entity_tables import (
    TableSides,
    _Copy,
    _CopyMatch,
    _diff_entity_fields,
    _diff_entity_table,
    absent_table_sides,
)
from cruftfree_rdbms_schema._snapshot_models import (
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotTable,
)
from cruftfree_rdbms_schema.differ import (
    ChangeKind,
    SchemaChange,
    schema_change_builder,
)
from cruftfree_rdbms_schema.foreign_key_naming import foreign_key_identity


def _match_copies(
    previous: Sequence[_Copy], current: Sequence[_Copy], table_name: str, label: str
) -> _CopyMatch[_Copy]:
    """Pair the copies of one identity the two sides of a table hold.

    A table may hold one index or foreign key in several copies, each its own object.
    A copy pairs with the other side's copy of the same name. Of the copies left, one
    on each side pair (the same object under another name: a rename); otherwise they
    pair in order. A copy left over is removed or added. Which copy pairs and which is
    removed must not be a guess, so the copies left are refused when they are all named
    in any count but one each, or when the previous side keeps more copies than the
    current one and some of them carry a name.

    Raises:
        GenerationError: Which previous copy pairs and which is removed is undecided.
    """
    held = list(previous)
    pairs: list[tuple[_Copy, _Copy]] = []
    unpaired: list[_Copy] = []
    for item in current:
        position = next(
            (
                i
                for i, copy in enumerate(held)
                if item.name is not None and copy.name == item.name
            ),
            None,
        )
        if position is None:
            unpaired.append(item)
        else:
            pairs.append((held.pop(position), item))
    if not held or not unpaired:
        return _CopyMatch(tuple(pairs), tuple(held), tuple(unpaired))
    named = all(copy.name is not None for copy in (*held, *unpaired))
    surplus_named = len(held) > len(unpaired) and any(
        copy.name is not None for copy in held
    )
    if (named and (len(held), len(unpaired)) != (1, 1)) or (
        not named and surplus_named
    ):
        raise GenerationError(
            "Table '%s' holds %s in %d copies named %s on the previous side (the live catalog "
            "in a convergence), and the current side declares %d more, named %s. No previous "
            "copy carries a declared name, so which copy is kept and which removed is "
            "undecided. Fix: rename the copy the schema declares to its declared name in the "
            "database, then deploy again."
            % (
                table_name,
                label,
                len(held),
                [copy.name for copy in held],
                len(unpaired),
                [copy.name for copy in unpaired],
            )
        )
    count = min(len(held), len(unpaired))
    pairs.extend(zip(held[:count], unpaired[:count], strict=True))
    return _CopyMatch(tuple(pairs), tuple(held[count:]), tuple(unpaired[count:]))


def _renamed(previous: _Copy, current: _Copy) -> bool:
    """Whether a copy both sides hold carries a name on each side, and not the same one."""
    return (
        previous.name is not None
        and current.name is not None
        and previous.name != current.name
    )


def _indexes_by_identity(
    table: SnapshotTable,
) -> dict[tuple[object, ...], list[SnapshotIndex]]:
    """The indexes of *table* grouped by :func:`index_identity`, each group in table order."""
    grouped: dict[tuple[object, ...], list[SnapshotIndex]] = {}
    for index in table.indexes:
        grouped.setdefault(index_identity(index), []).append(index)
    return grouped


def _diff_entity_indexes(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """Diff the indexes of one entity, matched by :func:`index_identity` and then by name.

    A table holding two identical indexes holds two objects, so a copy one side holds
    beyond the other's (:func:`_match_copies`) is an index added or removed like any
    other. A copy both sides hold under different names is an ``INDEX_RENAMED`` of the
    previous side's index to the current side's name.
    """
    change = schema_change_builder(service_name, entity_name)
    changes: list[SchemaChange] = []
    prev_by_identity = _indexes_by_identity(prev.canonical)
    curr_by_identity = _indexes_by_identity(curr.canonical)
    for identity in sorted(prev_by_identity.keys() | curr_by_identity.keys(), key=repr):
        previous = prev_by_identity.get(identity, [])
        current = curr_by_identity.get(identity, [])
        sample = (previous or current)[0]
        match = _match_copies(
            previous,
            current,
            curr.raw.table_name,
            "index on columns %s" % list(sample.columns),
        )
        for removed in match.removed:
            changes.append(
                change(
                    ChangeKind.INDEX_REMOVED,
                    detail="Index %s removed" % index_label(removed),
                    subject=prev.index(removed),
                )
            )
        for added in match.added:
            changes.append(
                change(
                    ChangeKind.INDEX_ADDED,
                    detail="Index %s added" % index_label(added),
                    subject=curr.index(added),
                )
            )
        changes.extend(
            change(
                ChangeKind.INDEX_RENAMED,
                detail="Index %s renamed to '%s'" % (index_label(held), declared.name),
                old_value=held.name,
                new_value=declared.name,
                subject=prev.index(held),
            )
            for held, declared in match.pairs
            if _renamed(held, declared)
        )
    return changes


def diff_added_entity_members(
    service_name: str,
    entity_name: str,
    curr: TableSides,
) -> list[SchemaChange]:
    """Report the indexes, foreign keys, checks and triggers a table present ONLY in the current snapshot brings.

    ``ENTITY_ADDED`` names the table; it does not describe what is on it. Every
    ``ENTITY_ADDED`` rendering creates the table and its columns, and nothing else in
    the change list would mention the table's indexes or foreign keys -- so a table
    introduced later would get none of its indexes or constraints.

    Reported by diffing against an absent table, so an added table's members are
    produced by the very functions that report a changed table's -- identical
    ``ChangeKind`` and identical subjects, with no second implementation to drift.

    ``INDEX_REMOVED`` cannot arise here: the previous side is empty.

    Args:
        service_name: Owner recorded on every emitted change.
        entity_name: The added entity or CQRS view name.
        curr: Its table as the current snapshot records it.

    Returns:
        One ``INDEX_ADDED`` change per index, one ``RELATIONSHIP_ADDED`` change
        per foreign key, one ``CHECK_ADDED`` change per check and one
        ``TRIGGER_ADDED`` change per trigger the added table declares.
    """
    absent = absent_table_sides(curr.raw.table_name)
    return [
        *_diff_entity_indexes(service_name, entity_name, absent, curr),
        *_diff_entity_foreign_keys(service_name, entity_name, absent, curr),
        *_diff_entity_checks(service_name, entity_name, absent, curr),
        *_diff_entity_triggers(service_name, entity_name, absent, curr),
    ]


def diff_removed_entity_members(
    service_name: str,
    entity_name: str,
    prev: TableSides,
) -> list[SchemaChange]:
    """Report the triggers a table present ONLY in the previous snapshot takes with it.

    Dropping a table drops its triggers but not their functions, which are separate
    objects, so each trigger is reported removed: the drop of the trigger and of its
    function renders before the table's drop (a trigger removal ranks first). Indexes,
    foreign keys and checks go with the table and are not reported.

    Args:
        service_name: Owner recorded on every emitted change.
        entity_name: The removed entity or CQRS view name.
        prev: Its table as the previous snapshot records it.

    Returns:
        One ``TRIGGER_REMOVED`` change per trigger the removed table carried.
    """
    absent = absent_table_sides(prev.raw.table_name)
    return _diff_entity_triggers(service_name, entity_name, prev, absent)


def _diff_entity_triggers(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """Diff the triggers of one entity, by name.

    A trigger's name carries the digest of its definition, so two triggers are the same
    trigger exactly when their names are equal: one present on one side only is a
    ``TRIGGER_REMOVED`` / ``TRIGGER_ADDED`` carrying that side's trigger, and a changed
    definition is one of each.
    """
    change = schema_change_builder(service_name, entity_name)
    previous = {trigger.name: trigger for trigger in prev.raw.triggers}
    current = {trigger.name: trigger for trigger in curr.raw.triggers}
    return [
        *(
            change(ChangeKind.TRIGGER_REMOVED, detail=name, subject=previous[name])
            for name in sorted(previous.keys() - current.keys())
        ),
        *(
            change(ChangeKind.TRIGGER_ADDED, detail=name, subject=current[name])
            for name in sorted(current.keys() - previous.keys())
        ),
    ]


def _diff_entity_checks(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """Diff the check constraints of one entity, by name.

    A check's name carries the digest of its definition, so two checks are the same
    check exactly when their names are equal: one present on one side only is a
    ``CHECK_REMOVED`` / ``CHECK_ADDED`` carrying that side's check, and a changed
    definition is one of each. No tree or SQL is compared -- a check a live catalog
    reflected carries its name only, and is the declared check of that name.
    """
    change = schema_change_builder(service_name, entity_name)
    previous = {check.name: check for check in prev.raw.checks}
    current = {check.name: check for check in curr.raw.checks}
    return [
        *(
            change(ChangeKind.CHECK_REMOVED, detail=name, subject=previous[name])
            for name in sorted(previous.keys() - current.keys())
        ),
        *(
            change(ChangeKind.CHECK_ADDED, detail=name, subject=current[name])
            for name in sorted(current.keys() - previous.keys())
        ),
    ]


def _foreign_keys_by_identity(
    table: SnapshotTable,
) -> dict[tuple[tuple[str, ...], str, tuple[str, ...]], list[SnapshotForeignKey]]:
    """The foreign keys of *table* grouped by :func:`foreign_key_identity`, in table order."""
    grouped: dict[
        tuple[tuple[str, ...], str, tuple[str, ...]], list[SnapshotForeignKey]
    ] = {}
    for key in table.foreign_keys:
        grouped.setdefault(foreign_key_identity(key), []).append(key)
    return grouped


def _held_foreign_key_change(
    change: Callable[..., SchemaChange],
    held: SnapshotForeignKey,
    declared: SnapshotForeignKey,
) -> SchemaChange | None:
    """The change of a key both sides hold: replaced, renamed, or none.

    A key whose ``onDelete`` or ``onUpdate`` differs is a ``FOREIGN_KEY_REPLACED`` of
    the previous side's key by the current side's; one that differs only in its name is
    a ``FOREIGN_KEY_RENAMED`` of the previous side's key.
    """
    if (held.on_delete, held.on_update) != (declared.on_delete, declared.on_update):
        return change(
            ChangeKind.FOREIGN_KEY_REPLACED,
            field=foreign_key_change_field(declared),
            detail="Foreign key %s replaced by one with its declared actions"
            % foreign_key_label(held),
            old_value=held.name,
            new_value=declared.name,
            subject=declared,
        )
    if _renamed(held, declared):
        return change(
            ChangeKind.FOREIGN_KEY_RENAMED,
            field=foreign_key_change_field(held),
            detail="Foreign key %s renamed to '%s'"
            % (foreign_key_label(held), declared.name),
            old_value=held.name,
            new_value=declared.name,
            subject=held,
        )
    return None


def _diff_entity_foreign_keys(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """Diff the foreign keys (relationships) of one entity.

    A key is the same constraint across two snapshots when its columns, referred table
    and referred columns agree (:func:`~cruftfree_rdbms_schema.foreign_key_naming.foreign_key_identity`),
    copies matched as indexes are (:func:`_match_copies`). One present on one side only
    is a ``RELATIONSHIP_ADDED`` / ``RELATIONSHIP_REMOVED``; one present on both is
    replaced or renamed (:func:`_held_foreign_key_change`) -- an action is part of the
    constraint a database enforces, so a change to one must reach every existing
    database, not alter the schema hash and plan nothing.
    """
    change = schema_change_builder(service_name, entity_name)
    changes: list[SchemaChange] = []
    prev_by_identity = _foreign_keys_by_identity(prev.canonical)
    curr_by_identity = _foreign_keys_by_identity(curr.canonical)
    for identity in sorted(prev_by_identity.keys() | curr_by_identity.keys()):
        previous = prev_by_identity.get(identity, [])
        current = curr_by_identity.get(identity, [])
        sample = (previous or current)[0]
        label = "foreign key (%s) -> %s" % (
            ", ".join(sample.columns),
            sample.referred_table,
        )
        match = _match_copies(previous, current, curr.raw.table_name, label)
        for removed in match.removed:
            changes.append(
                change(
                    ChangeKind.RELATIONSHIP_REMOVED,
                    field=foreign_key_change_field(removed),
                    detail="Foreign key %s removed" % foreign_key_label(removed),
                    subject=removed,
                )
            )
        for added in match.added:
            changes.append(
                change(
                    ChangeKind.RELATIONSHIP_ADDED,
                    field=foreign_key_change_field(added),
                    detail="Foreign key %s added" % foreign_key_label(added),
                    subject=added,
                )
            )
        for held, declared in match.pairs:
            pair_change = _held_foreign_key_change(change, held, declared)
            if pair_change is not None:
                changes.append(pair_change)
    return changes


def diff_common_entity_members(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """The table, field, index, foreign key, check and trigger changes of a table both snapshots hold."""
    return [
        *_diff_entity_table(service_name, entity_name, prev, curr),
        *_diff_entity_fields(service_name, entity_name, prev, curr),
        *_diff_entity_indexes(service_name, entity_name, prev, curr),
        *_diff_entity_foreign_keys(service_name, entity_name, prev, curr),
        *_diff_entity_checks(service_name, entity_name, prev, curr),
        *_diff_entity_triggers(service_name, entity_name, prev, curr),
    ]


__all__ = [
    "diff_added_entity_members",
    "diff_common_entity_members",
    "diff_removed_entity_members",
]
