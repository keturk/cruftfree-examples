"""Type widening and constraint narrowing rules of the schema change policy."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from cruftfree_common.types.geo_column import GEO_SRID_CONSTRAINT

# ── Constants ──

# Type widening pairs: (old_type, new_type) that are considered safe widening.
# These are adapter-dependent so they are classified as "risky" -- the adapter
# must verify compatibility.
_TYPE_WIDENING_PAIRS: frozenset[tuple[str, str]] = frozenset({
    ("Integer", "Long"),
    ("Int", "Long"),
    ("Short", "Integer"),
    ("Short", "Int"),
    ("Short", "Long"),
    ("Float", "Double"),
    ("String", "Text"),
})

#: Constraints that size a column's TYPE (``VARCHAR(n)``, ``NUMERIC(p, s)``).
#: Raising one keeps every stored value representable; lowering one can
#: truncate or overflow an existing row.
_WIDENABLE_TYPE_CONSTRAINTS: Final[frozenset[str]] = frozenset({"max_length", "precision", "scale"})
#: A sized string's length floor (``String(3, 40)``). It sizes no stored type: the
#: database holds it as a check of its own (``length_bound_predicates``), named from its
#: definition, so a changed floor is that check's ``CHECK_REMOVED`` and ``CHECK_ADDED``,
#: classified as checks are (the added one validated over the rows). A live catalog's
#: type therefore never states it, and a type change never reads it: comparing it would
#: count every widening of a floored string as a floor change.
_MIN_LENGTH_KEY: Final[str] = "min_length"
_PRECISION_KEY: Final[str] = "precision"
_SCALE_KEY: Final[str] = "scale"
#: Every constraint key the differ can emit (:func:`SnapshotType.constraints`
#: keys, per ``_constraints_from_type``). A key outside this set cannot be
#: proven safe by any rule below, so it is fail-closed treated as a narrowing.
#: A geographic column's SRID, part of its type (``geometry(Geometry,4326)``).
#: Dropping it widens the column; adding or changing it makes the database
#: refuse a stored value in another SRID -- see :func:`_srid_narrowing`.
_SRID_KEY: Final[str] = GEO_SRID_CONSTRAINT
_RECOGNIZED_CONSTRAINT_KEYS: Final[frozenset[str]] = _WIDENABLE_TYPE_CONSTRAINTS | {
    _MIN_LENGTH_KEY,
    _SRID_KEY,
}


def _srid_narrowing(old: Mapping[str, int], new: Mapping[str, int]) -> str | None:
    """The narrowing reason of a geographic column's SRID, or ``None`` when *new* states none or the same one.

    A column whose SRID is set or moved stamps that SRID on a value carrying none
    and refuses a value in any other SRID, so neither direction is provably safe.
    A column whose SRID is dropped widens.
    """
    if _SRID_KEY not in new or old.get(_SRID_KEY) == new[_SRID_KEY]:
        return None
    before = "unconstrained" if _SRID_KEY not in old else str(old[_SRID_KEY])
    return "srid %s -> %d (a stored value in another SRID no longer fits)" % (
        before,
        new[_SRID_KEY],
    )


def _widenable_constraint_narrowing(
    key: str, old: Mapping[str, int], new: Mapping[str, int]
) -> str | None:
    """One widenable constraint's narrowing reason, or ``None`` if it widens or is unchanged.

    A bound present before and lower now, or absent before (unbounded) and
    present now, narrows. A bound present before and absent now widens (the
    column becomes unbounded in that dimension).
    """
    old_has, new_has = key in old, key in new
    if old_has and new_has and new[key] < old[key]:
        return "%s %d -> %d" % (key, old[key], new[key])
    if not old_has and new_has:
        return "%s introduced at %d (previously unbounded)" % (key, new[key])
    return None


def _integer_digit_loss(old: Mapping[str, int], new: Mapping[str, int]) -> str | None:
    """``precision - scale`` integer-digit capacity, when both sides declare both.

    ``NUMERIC(10, 2)`` -> ``NUMERIC(10, 4)`` raises ``scale`` but loses two
    integer digits: capacity drops from 8 to 6, and an existing value like
    12345678.90 no longer fits even though every individual constraint moved
    in a widening direction.
    """
    if _PRECISION_KEY not in old or _SCALE_KEY not in old:
        return None
    if _PRECISION_KEY not in new or _SCALE_KEY not in new:
        return None
    old_capacity = old[_PRECISION_KEY] - old[_SCALE_KEY]
    new_capacity = new[_PRECISION_KEY] - new[_SCALE_KEY]
    if new_capacity >= old_capacity:
        return None
    return (
        "integer-digit capacity %d -> %d (precision/scale %d,%d -> %d,%d)"
        % (
            old_capacity,
            new_capacity,
            old[_PRECISION_KEY],
            old[_SCALE_KEY],
            new[_PRECISION_KEY],
            new[_SCALE_KEY],
        )
    )


def _unrecognized_constraint_narrowings(
    old: Mapping[str, int], new: Mapping[str, int]
) -> list[str]:
    """Fail closed on any constraint key this policy does not know how to size."""
    unrecognized = sorted((set(old) | set(new)) - _RECOGNIZED_CONSTRAINT_KEYS)
    return [
        "unrecognized constraint '%s' cannot be proven safe" % key
        for key in unrecognized
    ]


def _constraint_narrowings(
    old: Mapping[str, int], new: Mapping[str, int]
) -> list[str]:
    """Every way *new* refuses a value *old* holds.

    Returns human-readable reasons, empty when *new* widens or equals *old*:

    - a widenable constraint present before and lower now (``max_length``
      200 -> 50, ``precision`` 12 -> 10, ``scale`` 4 -> 2);
    - a widenable constraint absent before (unbounded) and present now;
    - the integer-digit capacity ``precision - scale`` decreased when both
      sides declare both (``NUMERIC(10,2)`` -> ``NUMERIC(10,4)`` raises scale but
      loses two integer digits);
    - a geographic column's ``srid`` set or moved (:func:`_srid_narrowing`).

    A widenable constraint present before and absent now is a widening (the
    column becomes unbounded in that dimension). ``min_length`` is never read: its
    check carries it (:data:`_MIN_LENGTH_KEY`).
    """
    narrowings: list[str] = []

    for key in sorted(_WIDENABLE_TYPE_CONSTRAINTS):
        reason = _widenable_constraint_narrowing(key, old, new)
        if reason is not None:
            narrowings.append(reason)

    digit_loss_reason = _integer_digit_loss(old, new)
    if digit_loss_reason is not None:
        narrowings.append(digit_loss_reason)

    srid_reason = _srid_narrowing(old, new)
    if srid_reason is not None:
        narrowings.append(srid_reason)

    narrowings.extend(_unrecognized_constraint_narrowings(old, new))
    return narrowings


def _constraint_widening_note(old: Mapping[str, int], new: Mapping[str, int]) -> str:
    """Describe every widenable constraint that moved, for a risky diagnostic.

    Only called once :func:`_constraint_narrowings` has already found nothing
    to block, so every difference here is a widening.
    """
    notes: list[str] = []
    for key in sorted(_WIDENABLE_TYPE_CONSTRAINTS):
        old_has, new_has = key in old, key in new
        if old_has and new_has and new[key] != old[key]:
            notes.append("%s %d -> %d" % (key, old[key], new[key]))
        elif old_has and not new_has:
            notes.append("%s %d -> unbounded" % (key, old[key]))
        elif not old_has and new_has:
            notes.append("%s unbounded -> %d" % (key, new[key]))
    if _SRID_KEY in old and _SRID_KEY not in new:
        notes.append("srid %d -> unconstrained" % old[_SRID_KEY])
    return ", ".join(notes)


# ── Classification helpers ──


def _is_type_widening(old_type: str | None, new_type: str | None) -> bool:
    """Check if a type change is a widening (safe direction).

    Args:
        old_type: The previous type name.
        new_type: The new type name.

    Returns:
        True if the change is a recognized type widening.
    """
    if old_type is None or new_type is None:
        return False
    return (old_type, new_type) in _TYPE_WIDENING_PAIRS
