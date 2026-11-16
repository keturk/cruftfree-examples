"""The change policy: one convergence outcome per schema change.

Each change kind has a classifier (:func:`_classify_change`) that calls a change ``safe``,
``risky`` or ``blocked``:

- **Safe:** additive changes that never cause data loss (nullable field add, index add, new
  table, enum value append, nullability relaxation, check removal, etc.).
- **Risky:** changes the database verifies against existing rows, or that existing rows may
  fail (type widening, unique constraint add, check add, foreign-key replacement).
- **Blocked:** changes no plan applies on its own (field removal, table removal, type
  narrowing, FK to an existing table, enum value removal or reorder, a primary-key,
  ownership, table-name or table-option change, etc.).

A convergence plan, which brings a live catalog to the declared schema, puts each change in
one outcome (:func:`convergence_outcome`): applied safe, applied risky, needs approval
(applied when the deploy runs with ``--approved``), or never applied. Each applied outcome
has one phase (:data:`CONVERGENCE_PHASE`): expand, before the new release starts, or
contract, after it is healthy.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal

from cruftfree_rdbms_schema._policy_constraints import _constraint_narrowings
from cruftfree_rdbms_schema._policy_field_classifiers import (
    _classify_entity_added,
    _classify_entity_removed,
    _classify_field_added,
    _classify_field_removed,
    _classify_field_type_changed,
    _classify_nullable_changed,
    _classify_primary_key_changed,
    _classify_table_options_changed,
    _classify_table_renamed,
)
from cruftfree_rdbms_schema._policy_structure_classifiers import (
    _classify_check_added,
    _classify_check_removed,
    _classify_entity_comment_changed,
    _classify_enum_type_added,
    _classify_enum_type_removed,
    _classify_enum_type_renamed,
    _classify_enum_value_added,
    _classify_enum_value_relabeled,
    _classify_enum_value_removed,
    _classify_enum_values_reordered,
    _classify_field_comment_changed,
    _classify_field_default_changed,
    _classify_field_unique_changed,
    _classify_foreign_key_renamed,
    _classify_foreign_key_replaced,
    _classify_index_added,
    _classify_index_removed,
    _classify_index_renamed,
    _classify_relationship_added,
    _classify_relationship_removed,
    _classify_schema_relocated,
    _classify_trigger_added,
    _classify_trigger_removed,
)
from cruftfree_rdbms_schema._snapshot_models import SnapshotColumn
from cruftfree_rdbms_schema.differ import ChangeKind, SchemaChange
from cruftfree_rdbms_schema.undeclared_objects import (
    UNDECLARED_REMOVAL_KINDS,
    refusal_text,
    removal_outcomes,
)

_ChangeClassification = tuple[Literal["safe", "risky", "blocked"], str]

#: Change kinds whose classification depends only on the change itself.
_CHANGE_CLASSIFIERS: Final[Mapping[ChangeKind, Callable[[SchemaChange], _ChangeClassification]]] = {
    ChangeKind.ENTITY_ADDED: _classify_entity_added,
    ChangeKind.ENTITY_REMOVED: _classify_entity_removed,
    ChangeKind.FIELD_REMOVED: _classify_field_removed,
    ChangeKind.FIELD_TYPE_CHANGED: _classify_field_type_changed,
    ChangeKind.FIELD_NULLABLE_CHANGED: _classify_nullable_changed,
    ChangeKind.FIELD_DEFAULT_CHANGED: _classify_field_default_changed,
    ChangeKind.FIELD_UNIQUE_CHANGED: _classify_field_unique_changed,
    ChangeKind.FIELD_PRIMARY_KEY_CHANGED: _classify_primary_key_changed,
    ChangeKind.ENTITY_TABLE_RENAMED: _classify_table_renamed,
    ChangeKind.ENTITY_OPTIONS_CHANGED: _classify_table_options_changed,
    ChangeKind.INDEX_ADDED: _classify_index_added,
    ChangeKind.INDEX_REMOVED: _classify_index_removed,
    ChangeKind.INDEX_RENAMED: _classify_index_renamed,
    ChangeKind.RELATIONSHIP_REMOVED: _classify_relationship_removed,
    ChangeKind.FOREIGN_KEY_REPLACED: _classify_foreign_key_replaced,
    ChangeKind.FOREIGN_KEY_RENAMED: _classify_foreign_key_renamed,
    ChangeKind.SCHEMA_RELOCATED: _classify_schema_relocated,
    ChangeKind.ENUM_VALUE_ADDED: _classify_enum_value_added,
    ChangeKind.ENUM_VALUE_RELABELED: _classify_enum_value_relabeled,
    ChangeKind.ENUM_TYPE_REMOVED: _classify_enum_type_removed,
    ChangeKind.ENUM_TYPE_ADDED: _classify_enum_type_added,
    ChangeKind.ENUM_TYPE_RENAMED: _classify_enum_type_renamed,
    ChangeKind.ENUM_VALUE_REMOVED: _classify_enum_value_removed,
    ChangeKind.ENUM_VALUES_REORDERED: _classify_enum_values_reordered,
    ChangeKind.ENTITY_COMMENT_CHANGED: _classify_entity_comment_changed,
    ChangeKind.FIELD_COMMENT_CHANGED: _classify_field_comment_changed,
    ChangeKind.CHECK_ADDED: _classify_check_added,
    ChangeKind.CHECK_REMOVED: _classify_check_removed,
    ChangeKind.TRIGGER_ADDED: _classify_trigger_added,
    ChangeKind.TRIGGER_REMOVED: _classify_trigger_removed,
}

#: Change kinds whose classification also depends on which entities this diff adds.
_ENTITY_AWARE_CHANGE_CLASSIFIERS: Final[
    Mapping[ChangeKind, Callable[[SchemaChange, set[str]], _ChangeClassification]]
] = {
    ChangeKind.FIELD_ADDED: _classify_field_added,
    ChangeKind.RELATIONSHIP_ADDED: _classify_relationship_added,
}


def _classify_change(
    change: SchemaChange,
    added_entities: set[str],
) -> tuple[Literal["safe", "risky", "blocked"], str]:
    """Classify a single schema change by dispatching on its kind.

    Args:
        change: The schema change to classify.
        added_entities: Set of entity names that are newly added in this diff.

    Returns:
        Tuple of (classification, diagnostic message).

    Raises:
        ValueError: If the change carries an unknown ChangeKind.
    """
    entity_aware = _ENTITY_AWARE_CHANGE_CLASSIFIERS.get(change.kind)
    if entity_aware is not None:
        return entity_aware(change, added_entities)
    classifier = _CHANGE_CLASSIFIERS.get(change.kind)
    if classifier is not None:
        return classifier(change)
    raise ValueError(
        "Unknown ChangeKind '%s'. "
        "Expected one of: %s."
        % (change.kind, sorted(ck.value for ck in ChangeKind))
    )


class ConvergenceOutcomeKind(Enum):
    """What a convergence plan does with one change."""

    #: Applied: the change loses no row and no write it accepts fails.
    APPLIED_SAFE = "applied_safe"
    #: Applied and marked: rows the generator cannot see may fail the apply, naming the
    #: constraint; no row is deleted to make it pass.
    APPLIED_RISKY = "applied_risky"
    #: Refused until the deploy runs with ``--approved``; applied when it does.
    NEEDS_APPROVAL = "needs_approval"
    #: Refused whatever the deploy's switches: no forward DDL realizes it.
    NEVER_APPLIED = "never_applied"


@dataclass(frozen=True)
class ConvergenceOutcome:
    """One change of a convergence plan and what the plan does with it.

    Attributes:
        change: The schema change.
        kind: The one outcome the change lands in.
        diagnostic: Why the change lands there; for a refused change also the fix.
    """

    change: SchemaChange
    kind: ConvergenceOutcomeKind
    diagnostic: str


class ConvergencePhase(Enum):
    """When a convergence plan applies a change, relative to the release that serves.

    The previous release keeps serving while the new one starts, so a change runs either
    before the new release starts, while the previous one still writes, or once the new
    release is healthy.
    """

    #: Before the new release starts: no write the previous release makes is refused.
    EXPAND = "expand"
    #: After the new release is healthy: the previous release may still write a dropped
    #: column or a value a narrowing forbids, and the new release needs none of it.
    CONTRACT = "contract"


#: The phase of every outcome a convergence plan applies, stated once. ``NEVER_APPLIED`` has
#: none: no forward DDL realizes it. A ``NEEDS_APPROVAL`` change is applied only when the
#: deploy runs with ``--approved``, and then after the new release is healthy.
CONVERGENCE_PHASE: Final[Mapping[ConvergenceOutcomeKind, ConvergencePhase]] = {
    ConvergenceOutcomeKind.APPLIED_SAFE: ConvergencePhase.EXPAND,
    ConvergenceOutcomeKind.APPLIED_RISKY: ConvergencePhase.EXPAND,
    ConvergenceOutcomeKind.NEEDS_APPROVAL: ConvergencePhase.CONTRACT,
}


def convergence_phase(kind: ConvergenceOutcomeKind) -> ConvergencePhase:
    """Return the phase a change of outcome *kind* is applied in (:data:`CONVERGENCE_PHASE`).

    Args:
        kind: The outcome of an applied change.

    Returns:
        The one phase the change runs in.

    Raises:
        ValueError: If *kind* is an outcome no plan applies.
    """
    phase = CONVERGENCE_PHASE.get(kind)
    if phase is None:
        expected = sorted(outcome.value for outcome in CONVERGENCE_PHASE)
        raise ValueError(
            f"Convergence outcome '{kind.value}' has no phase: a convergence plan never "
            f"applies it. Outcomes with a phase: {expected}."
        )
    return phase


#: The change kinds whose ``old_value`` / ``new_value`` are a ``"True"`` / ``"False"`` pair.
_BOOLEAN_CHANGE_KINDS: Final[frozenset[ChangeKind]] = frozenset(
    {
        ChangeKind.FIELD_UNIQUE_CHANGED,
        ChangeKind.FIELD_NULLABLE_CHANGED,
        ChangeKind.FIELD_PRIMARY_KEY_CHANGED,
    }
)

#: The two moves a boolean change makes.
_BOOLEAN_TRANSITIONS: Final[frozenset[tuple[str | None, str | None]]] = frozenset(
    {("True", "False"), ("False", "True")}
)

#: Added to the reason of a needs-approval change that is not a removal.
_APPROVAL_FIX: Final[str] = (
    " Applying it needs approval. Fix: run the deploy again with --approved to apply it, "
    "or change the DSL so the column stays as the database holds it."
)


def _require_boolean_transition(change: SchemaChange) -> None:
    """Refuse a boolean column change (``_BOOLEAN_CHANGE_KINDS``) not between True and False."""
    if change.kind not in _BOOLEAN_CHANGE_KINDS:
        return
    if (change.old_value, change.new_value) in _BOOLEAN_TRANSITIONS:
        return
    raise ValueError(
        "%s change on column '%s.%s' moves from %r to %r. Expected: 'True' -> 'False' or "
        "'False' -> 'True'. Fix: regenerate so the diff is recomputed."
        % (change.kind.value, change.entity, change.field, change.old_value, change.new_value)
    )


def _foreign_key_on_existing_table(change: SchemaChange, _diagnostic: str) -> ConvergenceOutcome:
    """A foreign key added to a table that already exists: applied, validated over its rows."""
    return ConvergenceOutcome(
        change=change,
        kind=ConvergenceOutcomeKind.APPLIED_RISKY,
        diagnostic=(
            "Foreign key '%s' added to existing table '%s' -- risky (the constraint is "
            "validated against existing rows; an orphan row fails the apply, naming the "
            "constraint, and is never deleted)"
            % (change.field or "<unknown>", change.entity or "<unknown>")
        ),
    )


def _narrowing_needs_approval(change: SchemaChange, _diagnostic: str) -> ConvergenceOutcome:
    """A column type change that narrows what the column holds: applied only when approved."""
    narrowings = _constraint_narrowings(
        dict(change.old_constraints), dict(change.new_constraints)
    )
    detail = " (%s)" % "; ".join(narrowings) if narrowings else ""
    reason = (
        "Column '%s' of table '%s' changes type from '%s' to '%s'%s: a value the column "
        "holds may not fit the new type."
        % (change.field, change.entity, change.old_value, change.new_value, detail)
    )
    return ConvergenceOutcome(
        change=change,
        kind=ConvergenceOutcomeKind.NEEDS_APPROVAL,
        diagnostic=reason + _APPROVAL_FIX,
    )


def _tightening_outcome(change: SchemaChange, _diagnostic: str) -> ConvergenceOutcome:
    """A nullable column becoming NOT NULL: applied only when approved, and only with a default.

    The forward DDL backfills every row holding NULL with the column's database default, then
    sets NOT NULL, so a column that declares no default has no forward DDL: like a NOT NULL
    column added without one, it is never applied, and the reason names the fix.

    Raises:
        ValueError: The change carries no SnapshotColumn as its subject.
    """
    column = change.subject
    if not isinstance(column, SnapshotColumn):
        raise ValueError(
            "A FIELD_NULLABLE_CHANGED change of '%s.%s' carries %s as its subject. Expected: "
            "the declared SnapshotColumn. Fix: build the change through the snapshot differ."
            % (change.entity, change.field, type(column).__name__)
        )
    if column.default is None:
        return ConvergenceOutcome(
            change=change,
            kind=ConvergenceOutcomeKind.NEVER_APPLIED,
            diagnostic=(
                "Column '%s' of table '%s' becomes NOT NULL and declares no default, so no "
                "forward DDL can fill the rows that hold NULL in it -- never applied, with or "
                "without approval. Fix: declare a default for the field, or leave it nullable."
                % (change.field, change.entity)
            ),
        )
    reason = (
        "Column '%s' of table '%s' becomes NOT NULL: every row holding NULL in it is set to "
        "its default." % (change.field, change.entity)
    )
    return ConvergenceOutcome(
        change=change,
        kind=ConvergenceOutcomeKind.NEEDS_APPROVAL,
        diagnostic=reason + _APPROVAL_FIX,
    )


def _never_applied(change: SchemaChange, diagnostic: str) -> ConvergenceOutcome:
    """A change no forward DDL realizes: refused with the classifier's reason and fix."""
    return ConvergenceOutcome(
        change=change, kind=ConvergenceOutcomeKind.NEVER_APPLIED, diagnostic=diagnostic
    )


#: What each change kind the classifiers call ``blocked`` becomes in a convergence plan.
#: The removals of undeclared objects are decided before, by ``removal_outcomes``.
_BLOCKED_OUTCOMES: Final[
    Mapping[ChangeKind, Callable[[SchemaChange, str], ConvergenceOutcome]]
] = {
    ChangeKind.RELATIONSHIP_ADDED: _foreign_key_on_existing_table,
    ChangeKind.FIELD_TYPE_CHANGED: _narrowing_needs_approval,
    ChangeKind.FIELD_NULLABLE_CHANGED: _tightening_outcome,
    ChangeKind.FIELD_ADDED: _never_applied,
    ChangeKind.ENUM_VALUE_REMOVED: _never_applied,
    ChangeKind.ENUM_VALUES_REORDERED: _never_applied,
    ChangeKind.FIELD_PRIMARY_KEY_CHANGED: _never_applied,
    ChangeKind.ENTITY_TABLE_RENAMED: _never_applied,
    ChangeKind.ENTITY_OPTIONS_CHANGED: _never_applied,
    ChangeKind.ENUM_TYPE_ADDED: _never_applied,
    ChangeKind.ENUM_TYPE_RENAMED: _never_applied,
}


# @canonical(rdbms-schema/change-policy): One convergence outcome per schema change: applied safe or risky, needs approval, never applied
# @rule: Policy is renderer-independent -- runs before rendering
# @rule: Every change lands in exactly one outcome; a kind classified blocked with no
#   outcome is refused, never guessed
# @rule: Nothing but `approved` (the deploy's --approved switch) converts a refused change
#   into an applied one: no config document, environment variable, DSL element or file does
# @rule: A foreign key added to an existing table is applied as risky: the constraint is
#   validated over the rows and an orphan row fails the apply, naming the constraint
# @rule: Every removal of an undeclared object is decided by removal_outcomes, never here
# @see: rdbms-schema/schema-differ
def convergence_outcome(
    change: SchemaChange,
    added_entities: set[str],
) -> ConvergenceOutcome:
    """Put *change* in exactly one convergence outcome.

    The per-kind classifiers (:func:`_classify_change`) decide: ``safe`` and ``risky``
    changes are applied, a ``risky`` one marked. A removal of an undeclared object needs
    approval unless :func:`~cruftfree_rdbms_schema.undeclared_objects.removal_outcomes` applies it
    without (a check named by its definition). Of the other ``blocked`` changes a foreign key
    added to an existing table is applied as risky, a narrowing type change and a tightening
    nullability change need approval, and an enum member removal or reorder, a primary-key
    or ownership change of a column, a table's rename or options change, an enum type no
    column uses added or a type's database name changed, and a NOT NULL
    column without a database default added to an existing table are never applied.

    Args:
        change: The schema change.
        added_entities: The entities the same plan creates
            (``_entities_with_kind(changes, ChangeKind.ENTITY_ADDED)``): a field or foreign
            key on one of them is safe.

    Returns:
        The change's outcome with its diagnostic; a refused change's names the fix.

    Raises:
        ValueError: A uniqueness, nullability, primary-key or ownership change is not a
            move between ``"True"`` and ``"False"``, or a kind classified ``blocked`` has no
            outcome.
    """
    if (
        change.kind in UNDECLARED_REMOVAL_KINDS
        and removal_outcomes((change,), approved=False).needs_approval
    ):
        return ConvergenceOutcome(
            change=change,
            kind=ConvergenceOutcomeKind.NEEDS_APPROVAL,
            diagnostic=refusal_text(change),
        )
    _require_boolean_transition(change)
    classification, diagnostic = _classify_change(change, added_entities)
    if classification == "safe":
        return ConvergenceOutcome(change, ConvergenceOutcomeKind.APPLIED_SAFE, diagnostic)
    if classification == "risky":
        return ConvergenceOutcome(change, ConvergenceOutcomeKind.APPLIED_RISKY, diagnostic)
    blocked_outcome = _BLOCKED_OUTCOMES.get(change.kind)
    if blocked_outcome is None:
        raise ValueError(
            "Change kind '%s' is classified blocked and has no convergence outcome. "
            "Expected one of: %s. Fix: give the kind its outcome in _BLOCKED_OUTCOMES."
            % (change.kind.value, sorted(kind.value for kind in _BLOCKED_OUTCOMES))
        )
    return blocked_outcome(change, diagnostic)
