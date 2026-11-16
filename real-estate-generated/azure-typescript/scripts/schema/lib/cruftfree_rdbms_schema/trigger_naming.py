"""The one rule that names a table trigger by its definition.

A trigger carries a rule over a table's rows (a table whose rows may only be appended,
a group of rows whose aggregate must hold at commit). Whether a live trigger is the
declared one cannot be decided by reading its function back, so the name decides it,
the way :mod:`cruftfree_rdbms_schema.definition_naming` decides it for a check: the name
ends in the digest of the trigger's definition, and a changed definition is a new
name -- the old trigger is dropped and the new one created, never compared or parsed.

The definition is a text of the rule alone (:func:`trigger_definition`), so the
snapshot builder that derives the name and the renderer that proves it write the
same text. A trigger's function is named exactly as the trigger is.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from cruftfree_rdbms_schema.definition_naming import definition_name

__all__ = [
    "TRIGGER_AGGREGATE_INVARIANT",
    "TRIGGER_APPEND_ONLY",
    "TRIGGER_KIND",
    "TRIGGER_KINDS",
    "trigger_definition",
    "trigger_name",
]

#: Kind marker of a trigger name.
TRIGGER_KIND: Final[str] = "trg"

#: A table whose rows are never deleted and whose updates change only the listed columns.
TRIGGER_APPEND_ONLY: Final[str] = "append_only"

#: A group of rows (rows sharing the listed columns' values) whose aggregate must hold
#: whenever a transaction commits.
TRIGGER_AGGREGATE_INVARIANT: Final[str] = "aggregate_invariant"

#: Every kind of trigger the snapshot records.
TRIGGER_KINDS: Final[frozenset[str]] = frozenset({TRIGGER_APPEND_ONLY, TRIGGER_AGGREGATE_INVARIANT})


def trigger_definition(kind: str, columns: Iterable[str], predicate_sql: str | None) -> str:
    """The text a trigger's name digests: its kind, its columns and its predicate.

    Args:
        kind: One of :data:`TRIGGER_KINDS`.
        columns: The columns the rule is stated over; their order is not part of the rule.
        predicate_sql: For an aggregate invariant, the group condition as the block's
            dialect renders it; ``None`` for an append-only rule.

    Raises:
        ValueError: *kind* is not a trigger kind, or *predicate_sql* is present exactly
            when the kind takes none (or absent when it takes one).
    """
    if kind not in TRIGGER_KINDS:
        raise ValueError(
            "A trigger was given the kind %r. Expected: one of %s. Fix: build the trigger "
            "from an append-only or aggregate-invariant declaration." % (kind, sorted(TRIGGER_KINDS))
        )
    if (kind == TRIGGER_AGGREGATE_INVARIANT) != (predicate_sql is not None):
        raise ValueError(
            "A %s trigger was given the predicate %r. Expected: a predicate for an "
            "aggregate invariant and none for an append-only rule. Fix: lower the "
            "invariant's condition before naming it." % (kind, predicate_sql)
        )
    listed = ",".join(sorted(columns))
    if predicate_sql is None:
        return "%s(%s)" % (kind, listed)
    return "%s(%s):%s" % (kind, listed, predicate_sql)


def trigger_name(table: str, subject: str, definition: str) -> str:
    """Name a trigger by its table, its subject and its definition.

    Args:
        table: Physical name of the table holding the trigger.
        subject: What the trigger governs: the rule's kind for an append-only table, the
            invariant's name for an aggregate invariant.
        definition: The text :func:`trigger_definition` returned.

    Returns:
        ``trg_<table>_<subject>_<digest>``, capped at the identifier limit and always
        ending in the digest of *definition*.
    """
    return definition_name(TRIGGER_KIND, table, subject, definition)
