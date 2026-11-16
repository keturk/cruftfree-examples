"""The objects a live catalog holds and the declared schema does not, and what removing them takes.

``L`` is a block's live catalog read into a snapshot, ``D`` the schema the DSL declares. An
object of ``L`` that ``D`` does not state is *undeclared*, and one rule removes it: a table, a
column, an index (a unique one included), a foreign key, a check or a named enum type goes, and
it goes only when the operator approves. The one exception is a check whose name has the
definition-name form (:mod:`cruftfree_rdbms_schema.definition_naming`): CruftFree created it from a rule
the DSL no longer states, and dropping a check refuses no write.

Which objects are undeclared is the differ's answer
(:func:`~cruftfree_rdbms_schema.snapshot_diff.compute_snapshot_diff`): each removal it reports
carries the object ``L`` holds, under the name the database holds it by.

Approval is one boolean, ``approved``, true exactly when the deploy's command line carried
``--approved``. It is a parameter and nothing reads it from anywhere else: no environment
variable, configuration value, DSL element or file approves a removal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from cruftfree_common.errors.generation import GenerationError

from cruftfree_rdbms_schema._diff_details import foreign_key_label, index_label
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotCheck,
    SnapshotEnum,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotTable,
    SnapshotTrigger,
)
from cruftfree_rdbms_schema.definition_naming import CHECK_KIND, DEFINITION_DIGEST_LENGTH
from cruftfree_rdbms_schema.differ import ChangeKind, SchemaChange, schema_change_order
from cruftfree_rdbms_schema.snapshot_diff import compute_snapshot_diff

__all__ = [
    "UNDECLARED_REMOVAL_KINDS",
    "RemovalOutcomes",
    "is_undeclared_removal",
    "refusal_text",
    "removal_outcomes",
    "undeclared_object_changes",
    "undeclared_removal",
]

#: The change kinds that remove an object ``D`` does not declare.
UNDECLARED_REMOVAL_KINDS: Final[frozenset[ChangeKind]] = frozenset(
    {
        ChangeKind.ENTITY_REMOVED,
        ChangeKind.FIELD_REMOVED,
        ChangeKind.INDEX_REMOVED,
        ChangeKind.RELATIONSHIP_REMOVED,
        ChangeKind.CHECK_REMOVED,
        ChangeKind.TRIGGER_REMOVED,
        ChangeKind.ENUM_TYPE_REMOVED,
    }
)

#: The name of a check CruftFree derived from a definition: ``chk_<table>_<subject>_<digest>``.
#: The digest's hex digits are spelled out one class each: this module is copied into the
#: schema tool's runtime, which refuses a template delimiter such as a brace quantifier.
_DEFINITION_NAMED_CHECK: Final[re.Pattern[str]] = re.compile(
    "^%s_.+_%s$" % (re.escape(CHECK_KIND), "[0-9a-f]" * DEFINITION_DIGEST_LENGTH)
)

#: Added to the refusal of a table or column: its data goes with it.
_DATA_LOSS_NOTE: Final[str] = (
    " Removing %s loses its data; an operator who wants the data kept renames it in the "
    "database before the deploy."
)


@dataclass(frozen=True)
class RemovalOutcomes:
    """Each undeclared-object removal in exactly one outcome.

    Attributes:
        applied: The removals that run: every one that needs no approval, and every
            one when the operator approved.
        needs_approval: The removals refused until the operator approves.
    """

    applied: tuple[SchemaChange, ...]
    needs_approval: tuple[SchemaChange, ...]


def _live_table(live: RdbmsSchemaSnapshot, change: SchemaChange) -> SnapshotTable:
    """The table of *live* that *change* is about.

    Raises:
        GenerationError: *live* holds no table under the change's entity.
    """
    tables = live.declared_tables()
    if change.entity is None or change.entity not in tables:
        raise GenerationError(
            "A %s change names table '%s', which the live snapshot it was computed from "
            "does not hold (its tables: %s). Fix: read the catalog again so the diff is "
            "recomputed." % (change.kind.value, change.entity, sorted(tables))
        )
    return tables[change.entity]


def _require_held_name(change: SchemaChange, label: str, name: str | None) -> None:
    """Refuse a removal of an object the live snapshot records with no name.

    Raises:
        GenerationError: *name* is None, so no statement can name what it drops.
    """
    if name is None:
        raise GenerationError(
            "The live catalog holds %s on table '%s' with no name, so its removal cannot "
            "name it. Expected: a catalog reader records every index's and foreign key's "
            "name. Fix: pass the live snapshot as its reader parsed it, prepared for "
            "comparison." % (label, change.entity)
        )


def _drops_a_live_unique(change: SchemaChange) -> bool:
    """Whether *change* is a live column's uniqueness the declared column does not state."""
    return (
        change.kind is ChangeKind.FIELD_UNIQUE_CHANGED
        and change.old_value == str(True)
        and change.new_value == str(False)
    )


def _unique_constraint_removal(live: RdbmsSchemaSnapshot, change: SchemaChange) -> SchemaChange:
    """The ``INDEX_REMOVED`` of the single-column unique index behind a live-only uniqueness.

    A catalog reports a one-column unique constraint as its column's uniqueness, and
    canonicalization drops the index it implies, so the diff calls an undeclared unique
    constraint on a declared column a uniqueness change. It is an index the declared
    schema does not state, removed as one under the name the database holds.

    Raises:
        GenerationError: *live*'s table holds no single named unique index over the column.
    """
    table = _live_table(live, change)
    column = table.fields.get(change.field or "")
    if column is None:
        raise GenerationError(
            "A FIELD_UNIQUE_CHANGED change names column '%s', which table '%s' of the live "
            "snapshot does not hold. Fix: read the catalog again so the diff is recomputed."
            % (change.field, table.table_name)
        )
    key = (column.column_name.lower(),)
    held = [
        index
        for index in table.indexes
        if index.unique
        and not index.fulltext
        and not index.spatial
        and tuple(name.lower() for name in index.columns) == key
    ]
    if len(held) != 1:
        raise GenerationError(
            "Column '%s' of table '%s' is unique in the live catalog, which the declared "
            "schema does not state, but the live snapshot holds %d unique indexes over it "
            "(expected exactly one, the constraint's). Fix: read the catalog with the "
            "engine's reader, which reports a unique constraint's index."
            % (column.column_name, table.table_name, len(held))
        )
    _require_held_name(
        change, "a unique constraint on column '%s'" % column.column_name, held[0].name
    )
    return SchemaChange(
        kind=ChangeKind.INDEX_REMOVED,
        service=change.service,
        entity=change.entity,
        detail="Index %s removed" % index_label(held[0]),
        subject=held[0],
    )


def is_undeclared_removal(change: SchemaChange) -> bool:
    """Whether *change*, a change of the diff of ``L`` against ``D``, removes an undeclared object.

    True for every removal kind and for a live column's uniqueness the declared column does
    not state (the removal of its unique index). :func:`undeclared_removal` gives the
    removal each such change stands for.
    """
    return _drops_a_live_unique(change) or change.kind in UNDECLARED_REMOVAL_KINDS


def undeclared_removal(live: RdbmsSchemaSnapshot, change: SchemaChange) -> SchemaChange:
    """The removal *change*, a change of the diff of ``L`` against ``D``, stands for.

    A live-only uniqueness is the removal of its unique index; every other removal is
    *change* itself, its subject the object ``L`` holds.

    Args:
        live: ``L``, prepared for comparison, the diff's previous side.
        change: A change :func:`is_undeclared_removal` holds true for.

    Raises:
        GenerationError: The removed index or foreign key is unnamed in *live*, so no
            statement can name it, or a live-only uniqueness has no single unique index.
        ValueError: *change* removes no undeclared object.
    """
    if not is_undeclared_removal(change):
        raise ValueError(
            "A %s change removes no undeclared object. Expected one of: %s, or a uniqueness "
            "the declared column does not state."
            % (change.kind.value, sorted(kind.value for kind in UNDECLARED_REMOVAL_KINDS))
        )
    if _drops_a_live_unique(change):
        return _unique_constraint_removal(live, change)
    subject = change.subject
    if isinstance(subject, SnapshotIndex):
        _require_held_name(change, "an index %s" % index_label(subject), subject.name)
    if isinstance(subject, SnapshotForeignKey):
        _require_held_name(change, "a foreign key %s" % foreign_key_label(subject), subject.name)
    return change


def undeclared_object_changes(
    live: RdbmsSchemaSnapshot, desired: RdbmsSchemaSnapshot
) -> tuple[SchemaChange, ...]:
    """The removals of every object of *live* that *desired* does not declare.

    The removals of the diff of *live* against *desired*, each the object *live* holds,
    under the name the database holds (:func:`undeclared_removal`).

    Args:
        live: ``L``, prepared for comparison (``prepare_live_for_comparison``) and not
            canonicalized, so its names are the ones the database holds. Render the
            removals against this same snapshot.
        desired: ``D``.

    Returns:
        The removals, each object once, in render order.

    Raises:
        GenerationError: A removed index or foreign key is unnamed in *live*, or the
            differ cannot decide which copy of an index or key is surplus.
    """
    diff = compute_snapshot_diff(live, desired).changes
    return tuple(
        sorted(
            (undeclared_removal(live, change) for change in diff if is_undeclared_removal(change)),
            key=schema_change_order,
        )
    )


def _needs_approval(change: SchemaChange) -> bool:
    """Whether removing the object *change* names needs the operator's approval."""
    if change.kind not in UNDECLARED_REMOVAL_KINDS:
        raise ValueError(
            "Change kind '%s' is not the removal of an undeclared object. Expected one of: %s."
            % (
                change.kind.value,
                sorted(kind.value for kind in UNDECLARED_REMOVAL_KINDS),
            )
        )
    subject = change.subject
    if isinstance(subject, SnapshotCheck):
        return _DEFINITION_NAMED_CHECK.fullmatch(subject.name) is None
    if isinstance(subject, SnapshotTrigger):
        # A catalog reader reports a trigger only when its name is a definition-derived
        # one, so a live trigger here is a CruftFree trigger whose declaration was removed.
        return False
    return True


def removal_outcomes(
    changes: tuple[SchemaChange, ...], approved: bool
) -> RemovalOutcomes:
    """Put each removal in exactly one outcome.

    Args:
        changes: Removals of undeclared objects (:func:`undeclared_object_changes`).
        approved: True exactly when the deploy was run with ``--approved``.

    Returns:
        The removals that run and the ones refused until approved. Nothing but *approved*
        moves a removal out of ``needs_approval``.

    Raises:
        ValueError: A change is not the removal of an undeclared object.
    """
    applied: list[SchemaChange] = []
    refused: list[SchemaChange] = []
    for change in changes:
        (refused if _needs_approval(change) and not approved else applied).append(
            change
        )
    return RemovalOutcomes(applied=tuple(applied), needs_approval=tuple(refused))


def _object_label(change: SchemaChange) -> str:
    """The undeclared object *change* removes, by kind, table and name, read from its subject."""
    subject = change.subject
    if isinstance(subject, SnapshotTable):
        return "table '%s'" % change.entity
    if change.kind is ChangeKind.FIELD_REMOVED:
        return "column '%s' of table '%s'" % (change.field, change.entity)
    if isinstance(subject, SnapshotIndex):
        return "index %s of table '%s'" % (index_label(subject), change.entity)
    if isinstance(subject, SnapshotForeignKey):
        return "foreign key %s of table '%s'" % (foreign_key_label(subject), change.entity)
    if isinstance(subject, SnapshotCheck):
        return "check '%s' of table '%s'" % (subject.name, change.entity)
    if isinstance(subject, SnapshotTrigger):
        return "trigger '%s' of table '%s'" % (subject.name, change.entity)
    if isinstance(subject, SnapshotEnum):
        return "enum type '%s'" % subject.database_name
    raise ValueError(
        "A %s change is not the removal of an undeclared object. Expected one of: %s."
        % (change.kind.value, sorted(kind.value for kind in UNDECLARED_REMOVAL_KINDS))
    )


def refusal_text(change: SchemaChange) -> str:
    """The refusal of one removal: the object and the two ways to settle it.

    Args:
        change: A removal that needs approval.

    Returns:
        A message naming the object, the deploy's ``--approved`` switch and the
        declaration to add to the DSL; a removed table or column adds that its data is lost.
    """
    label = _object_label(change)
    text = (
        "The database holds %s, which the declared schema does not state, and removing it "
        "needs approval. Fix: run the deploy again with --approved to drop it, or declare it "
        "in the DSL to keep it." % label
    )
    if change.kind in {ChangeKind.ENTITY_REMOVED, ChangeKind.FIELD_REMOVED}:
        text += _DATA_LOSS_NOTE % label
    return text
