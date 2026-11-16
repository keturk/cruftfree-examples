"""Order a set of enum label renames so each one applies cleanly in sequence.

A relabel set is a mapping ``old label -> new label`` over ONE enum type. PostgreSQL
renames a label in place (``ALTER TYPE ... RENAME VALUE``) and refuses a rename whose
target label already exists, so the set cannot be applied in an arbitrary order:

* a chain (``a -> b``, ``b -> c``) must run from its END backward (``b -> c`` first),
  or the first rename lands on a label that is still held;
* a cycle (``a -> b``, ``b -> a``, the swap of two ``value(...)`` declarations) has no
  safe starting rename at all, so one label of the cycle is parked under a fresh
  temporary label first.

The set is always injective (semantic analysis rejects two members storing one label),
so its functional graph is only paths and cycles and this ordering is total.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping

from cruftfree_common.cruftfree_model.enum_literal_text import (
    stored_enum_literal_from_parts,
)

from cruftfree_rdbms_schema._snapshot_models import SnapshotEnum

__all__ = ["ordered_relabel_steps", "relabeled_members"]


# @canonical(rdbms-schema/enum-relabel-rows): Which members of one enum change the
#   label they are stored as
# @rule: The differ decides an ENUM_VALUE_RELABELED with this function and the renderer
#   reads its rows from it, over the same two enums -- never a second comparison
def relabeled_members(
    previous: SnapshotEnum, current: SnapshotEnum
) -> tuple[tuple[str, str, str], ...]:
    """The members both enums hold whose STORED label differs, in declaration order.

    A member's stored label is its declared ``value(...)`` else its snake_case
    name (:func:`~cruftfree_common.cruftfree_model.enum_literal_text.stored_enum_literal_from_parts`),
    so a ``value(...)`` added, changed or removed on a member that stays is a
    relabel even though the member list is unchanged.

    Args:
        previous: The enum as the previous snapshot holds it.
        current: The enum as the current snapshot holds it.

    Returns:
        ``(member name, old label, new label)`` for each relabeled member.

    Raises:
        ValueError: Either enum records fewer declared member values than members,
            so the label a member is stored as cannot be told.
    """
    for enum in (previous, current):
        if len(enum.member_values) != len(enum.values):
            raise ValueError(
                "Enum '%s' records %d declared member values for %d members, so the "
                "label each member is stored as cannot be told. Fix: regenerate the "
                "snapshot with this CruftFree."
                % (enum.name, len(enum.member_values), len(enum.values))
            )
    previous_declared = dict(zip(previous.values, previous.member_values, strict=True))
    rows: list[tuple[str, str, str]] = []
    for name, declared in zip(current.values, current.member_values, strict=True):
        if name not in previous_declared:
            continue
        old = stored_enum_literal_from_parts(name, previous_declared[name])
        new = stored_enum_literal_from_parts(name, declared)
        if old != new:
            rows.append((name, old, new))
    return tuple(rows)


_TEMPORARY_PREFIX = "__relabel_"


def ordered_relabel_steps(
    relabels: Mapping[str, str],
    *,
    reserved: Collection[str],
) -> tuple[tuple[str, str], ...]:
    """Return ``(old, new)`` renames in an order each of which succeeds in turn.

    Args:
        relabels: ``{old label: new label}`` for one enum type. Old labels are
            distinct (dict keys) and new labels must be distinct.
        reserved: Every label the type holds before or after the relabel, so a
            temporary label never collides with a real one.

    Returns:
        The renames, each applying to a database in which every earlier one has run.
        A cycle contributes one extra pair of steps through a temporary label.

    Raises:
        ValueError: Two old labels map to one new label, or a label maps to itself --
            both mean the set was not built by the differ and cannot be ordered.
    """
    new_labels = list(relabels.values())
    if len(set(new_labels)) != len(new_labels):
        raise ValueError(
            "A relabel set must map distinct old labels to distinct new labels; got "
            "%r. Two members cannot be stored under one label." % dict(relabels)
        )
    for old, new in relabels.items():
        if old == new:
            raise ValueError(
                "Label %r relabels to itself; the differ never emits a no-op relabel."
                % old
            )
    taken = set(reserved) | set(relabels) | set(new_labels)
    pending = dict(relabels)
    steps: list[tuple[str, str]] = []
    temporaries = 0
    while pending:
        ready = [old for old, new in pending.items() if new not in pending]
        if ready:
            for old in ready:
                steps.append((old, pending.pop(old)))
            continue
        # Only cycles remain: park the first label under a temporary one, which
        # frees its old name for the rename that was blocked on it.
        old = next(iter(pending))
        temporary = _fresh_temporary(taken, temporaries)
        temporaries += 1
        taken.add(temporary)
        steps.append((old, temporary))
        pending[temporary] = pending.pop(old)
    return tuple(steps)


def _fresh_temporary(taken: Collection[str], start: int) -> str:
    """The first ``__relabel_<n>`` label, from *start*, that is not in *taken*."""
    ordinal = start
    while f"{_TEMPORARY_PREFIX}{ordinal}" in taken:
        ordinal += 1
    return f"{_TEMPORARY_PREFIX}{ordinal}"
