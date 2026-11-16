"""What it takes to bring a live catalog to the declared schema, one outcome per change.

``L`` is a block's live catalog read into a snapshot, ``D`` the schema the DSL declares. The
changes that bring ``L`` to ``D`` are the diff of the two
(:func:`~cruftfree_rdbms_schema.snapshot_diff.compute_snapshot_diff`), which holds every comparison
of ``L`` with ``D``: each removal carries the undeclared object the database holds
(:mod:`cruftfree_rdbms_schema.undeclared_objects`), and each change lands in exactly one convergence
outcome (:func:`~cruftfree_rdbms_schema.change_policy.convergence_outcome`). An empty database is an
``L`` holding nothing, and its changes create all of ``D``.

Approval is one boolean, ``approved``, true exactly when the deploy's command line carried
``--approved``: it moves every change that needs approval into the applied ones, and nothing
else does. A change no forward DDL realizes stays refused whatever it says.

Approval names no object, so no change says that two objects are one. A column renamed in
the DSL is the old column's removal and the new column's addition; a changed enum label is
the old label's removal (never applied) and the member's addition; a block that changes its
schema is read, and created, in the new one, the old one being outside its scope. No
``ENUM_VALUE_RELABELED`` or ``SCHEMA_RELOCATED`` is planned: an operator who wants the data
kept renames in the database before the deploy, and the next read then matches ``D``.

Only a name is renamed: an index or a foreign key ``L`` holds once with ``D``'s definition
under another name is one object, and it takes ``D``'s name (``INDEX_RENAMED``,
``FOREIGN_KEY_RENAMED``, applied as safe), never removed and added again. A foreign key whose
action changed is replaced: dropped under the name ``L`` holds and added under ``D``'s
(``FOREIGN_KEY_REPLACED``).

Whether a database holds ``D`` is answered once, by :func:`require_same_schema`, which fails
closed: a difference the change differ does not classify is still a refusal.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cruftfree_rdbms_schema._policy_rename_detection import _entities_with_kind
from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot
from cruftfree_rdbms_schema.canonicalize import canonicalize_snapshot, prepare_live_for_comparison
from cruftfree_rdbms_schema._canonicalize_rules import LiveCatalogFacts
from cruftfree_rdbms_schema.change_policy import (
    ConvergenceOutcome,
    ConvergenceOutcomeKind,
    convergence_outcome,
)
from cruftfree_rdbms_schema.differ import (
    ChangeKind,
    SchemaChange,
    schema_change_order,
)
from cruftfree_rdbms_schema.errors import SchemaMismatchError
from cruftfree_rdbms_schema.schema_snapshot import snapshots_describe_the_same_schema
from cruftfree_rdbms_schema.snapshot_diff import compute_snapshot_diff
from cruftfree_rdbms_schema.undeclared_objects import (
    is_undeclared_removal,
    undeclared_removal,
)

__all__ = ["ConvergenceChanges", "convergence_changes", "require_same_schema"]

logger = logging.getLogger(__name__)

#: The difference ``require_same_schema`` names when the differ reports none but the
#: snapshots are not equal: the differ, not the database, is what is wrong.
UNCLASSIFIED_DIFFERENCE = (
    "the schemas differ in a way the change differ does not classify: "
    "compute_snapshot_diff reported no change while snapshots_describe_the_same_schema "
    "is false, so the differ is missing a comparison for a schema-bearing field"
)


@dataclass(frozen=True)
class ConvergenceChanges:
    """The changes that bring ``L`` to ``D``, each in exactly one of three groups.

    Attributes:
        live: ``L`` prepared for comparison and not canonicalized, so its index and
            foreign key names are the ones the database holds.
        desired: ``D`` as given, with the names generation recorded.
        approved: Whether the deploy ran with ``--approved``.
        applied: The changes that run, in render order: each one applied safe or applied
            risky (marked by its kind), and with *approved* each one that needs approval
            (kind ``NEEDS_APPROVAL``).
        refused: With *approved* false, the changes that need approval, each diagnostic
            naming the change and the fix (run the deploy again with ``--approved``, or
            change the DSL); empty with *approved* true.
        never_applied: The changes no forward DDL realizes, each diagnostic giving the
            reason and the fix, whatever *approved* says.
    """

    live: RdbmsSchemaSnapshot
    desired: RdbmsSchemaSnapshot
    approved: bool
    applied: tuple[ConvergenceOutcome, ...]
    refused: tuple[ConvergenceOutcome, ...]
    never_applied: tuple[ConvergenceOutcome, ...]

    @property
    def applied_changes(self) -> tuple[SchemaChange, ...]:
        """The schema changes that run, in render order."""
        return tuple(outcome.change for outcome in self.applied)

    @property
    def risky(self) -> tuple[ConvergenceOutcome, ...]:
        """The applied changes rows the generator cannot see may fail, naming the constraint."""
        return tuple(
            outcome
            for outcome in self.applied
            if outcome.kind is ConvergenceOutcomeKind.APPLIED_RISKY
        )


def _diff_changes(
    live: RdbmsSchemaSnapshot, desired: RdbmsSchemaSnapshot
) -> tuple[SchemaChange, ...]:
    """The changes of ``L`` against ``D``, each removal the undeclared object ``L`` holds.

    One diff (:func:`compute_snapshot_diff`) answers every comparison: additions carry
    ``D``'s objects, removals and renames ``L``'s, under the names the database holds. A
    live-only uniqueness is the removal of its unique index (:func:`undeclared_removal`).
    """
    diff = compute_snapshot_diff(live, desired)
    return tuple(
        sorted(
            (
                undeclared_removal(live, change) if is_undeclared_removal(change) else change
                for change in diff.changes
            ),
            key=schema_change_order,
        )
    )


def _placement(schema_name: str | None) -> str:
    """A block's schema as a message names it."""
    return "the default schema" if schema_name is None else f"schema '{schema_name}'"


def _require_read_at_declared_placement(
    live: RdbmsSchemaSnapshot, desired: RdbmsSchemaSnapshot
) -> None:
    """Refuse an ``L`` read anywhere but the schema ``D`` places the block in.

    The deploy reads the block's catalog at its declared schema, and the plan's guards
    read the same place again. An ``L`` read elsewhere describes another catalog, and
    diffing it would plan a relocation of the block, which approval cannot name.
    """
    if live.schema_name == desired.schema_name:
        return
    declared = _placement(desired.schema_name)
    raise ValueError(
        f"The live catalog of block '{desired.block.name}' was read in "
        f"{_placement(live.schema_name)}, but the block is declared in {declared}. "
        "A block that changes its schema reaches the new schema, and the old one is left "
        f"as it was. Fix: read the catalog in {declared}."
    )


# @canonical(rdbms-schema/convergence-changes): The changes that bring a live catalog L
#   to the declared schema D, each in exactly one outcome: applied, refused until approved,
#   never applied
# @rule: One comparison: prepare_live_for_comparison, then compute_snapshot_diff -- never a
#   second differ, and no comparison of names, actions or enum types beside it
# @rule: A removal carries the undeclared object L holds; a removal is never planned twice
# @rule: Only `approved` moves a needs-approval change into the applied ones; a never-applied
#   change stays refused
# @rule: No plan holds ENUM_VALUE_RELABELED or SCHEMA_RELOCATED: L is read at D's schema, and a
#   live label no member is stored as never reads as a declared member
# @see: rdbms-schema/change-policy
# @see: rdbms-schema/live-catalog-preparation
def convergence_changes(
    live: RdbmsSchemaSnapshot,
    desired: RdbmsSchemaSnapshot,
    approved: bool,
    facts: LiveCatalogFacts,
) -> ConvergenceChanges:
    """The changes that bring *live* to *desired*, each in exactly one outcome.

    Args:
        live: ``L``, the block's catalog as its reader parsed it (no table and no enum
            for an empty database).
        desired: ``D``, the block's schema as generation wrote it.
        approved: True exactly when the deploy was run with ``--approved``.
        facts: The target's and engine's facts about the live catalog.

    Returns:
        The applied, refused and never-applied changes, with the prepared ``L`` and the
        ``D`` the renderer reads.

    Raises:
        GenerationError: A removed index or foreign key is unnamed in *live*, or *live*
            holds an index or foreign key in several copies, none under the name *desired*
            gives it.
        ValueError: *live* was read in another schema than *desired* places the block in, a
            change carries a malformed value pair, or a kind classified blocked has no
            outcome.
    """
    _require_read_at_declared_placement(live, desired)
    prepared = prepare_live_for_comparison(desired, live, facts)
    changes = _diff_changes(prepared, desired)
    added_entities = _entities_with_kind(changes, ChangeKind.ENTITY_ADDED)
    applied: list[ConvergenceOutcome] = []
    refused: list[ConvergenceOutcome] = []
    never_applied: list[ConvergenceOutcome] = []
    for change in changes:
        outcome = convergence_outcome(change, added_entities)
        if outcome.kind is ConvergenceOutcomeKind.NEVER_APPLIED:
            never_applied.append(outcome)
        elif outcome.kind is ConvergenceOutcomeKind.NEEDS_APPROVAL and not approved:
            refused.append(outcome)
        else:
            applied.append(outcome)
    logger.debug(
        "convergence_changes block=%s applied=%d refused=%d never_applied=%d approved=%s",
        desired.block.name,
        len(applied),
        len(refused),
        len(never_applied),
        approved,
    )
    return ConvergenceChanges(
        live=prepared,
        desired=desired,
        approved=approved,
        applied=tuple(applied),
        refused=tuple(refused),
        never_applied=tuple(never_applied),
    )


def _difference_line(change: SchemaChange) -> str:
    """One change, named by its kind, the object it touches and its detail."""
    names = tuple(
        name for name in (change.enum, change.entity, change.field) if name is not None
    )
    if not names:
        return f"{change.kind.value}: {change.detail}"
    return f"{change.kind.value} {'.'.join(names)}: {change.detail}"


# @canonical(rdbms-schema/require-same-schema): Whether a database holds D, answered
#   once and failing closed
# @rule: compute_snapshot_diff names each difference, names and actions included; an empty
#   diff with snapshots_describe_the_same_schema false is still a refusal (the differ missed it)
# @rule: The left side is L as convergence_changes prepares it, whole: never filtered by
#   name, prefix or kind
# @see: rdbms-schema/convergence-changes
# @see: rdbms-schema/snapshot-diff
def require_same_schema(left: RdbmsSchemaSnapshot, right: RdbmsSchemaSnapshot) -> None:
    """Refuse unless *left* and *right* describe the same schema.

    Args:
        left: ``L`` as :func:`convergence_changes` prepares it (``ConvergenceChanges.live``),
            whole: an object it holds that *right* does not declare is a difference.
        right: ``D``, the block's declared schema.

    Raises:
        SchemaMismatchError: The change differ reports changes from *left* to *right*
            (each named), or reports none while the two are not equal (named as a
            difference the differ does not classify).
        ValueError: A column of either side lists members its type does not declare
            (:func:`~cruftfree_rdbms_schema.schema_snapshot.require_column_members_declared`).
    """
    diff = compute_snapshot_diff(left, right)
    if diff.changes:
        raise SchemaMismatchError(
            right.block.name, tuple(_difference_line(change) for change in diff.changes)
        )
    if not snapshots_describe_the_same_schema(
        canonicalize_snapshot(left), canonicalize_snapshot(right)
    ):
        raise SchemaMismatchError(right.block.name, (UNCLASSIFIED_DIFFERENCE,))
    logger.debug("require_same_schema block=%s same=True", right.block.name)
