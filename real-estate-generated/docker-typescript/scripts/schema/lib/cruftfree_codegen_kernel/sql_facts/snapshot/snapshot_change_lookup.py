"""Shared lookups for what a schema change is about: its subject and its table.

A migration renderer turns a ``SchemaChange`` into DDL. It reads the object the
change is about from the change's subject (:func:`change_subject`), and the table
that object belongs to by resolving the change's declared entity name against the
snapshot that holds it (:func:`snapshot_table_for`), with one fail-loud message,
down to the sorted ``Available:`` hint.

Every caller raises the same shared ``GenerationError``, so no per-package
exception class is declared here -- unlike
:func:`~cruftfree_codegen_common.algorithms.declared_table_lookup.lookup_declared_entry`,
whose callers genuinely raise different classes.

The table lookup resolves against every table the block's migrations own --
entity tables and CQRS read-model backing tables alike
(:meth:`RdbmsSchemaSnapshot.declared_tables`). Looking in ``entities`` alone
would raise "not found" for a change the differ legitimately emits about a read
model, which is a generation failure rather than the missing DDL it replaced,
but still the wrong answer.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

from cruftfree_common.errors.generation import GenerationError

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import (
        RdbmsSchemaSnapshot,
        SnapshotTable,
    )
    from cruftfree_rdbms_schema.differ import SchemaChange

logger = logging.getLogger(__name__)

_Subject = TypeVar("_Subject")


def change_subject(change: "SchemaChange", expected: type[_Subject]) -> _Subject:
    """The snapshot object *change* is about, which a renderer reads instead of looking it up.

    Args:
        change: The change being rendered.
        expected: The subject type the renderer reads for the change's kind.

    Returns:
        The change's subject.

    Raises:
        GenerationError: The subject is not of *expected* type -- the renderer and
            ``CHANGE_SUBJECT_TYPES`` disagree about the kind.
    """
    subject = change.subject
    if not isinstance(subject, expected):
        raise GenerationError(
            "The %s renderer reads a %s subject, but the change carries %s. Expected: "
            "the renderer reads the type CHANGE_SUBJECT_TYPES gives the kind. Fix: align "
            "the renderer with CHANGE_SUBJECT_TYPES."
            % (change.kind.value, expected.__name__, type(subject).__name__)
        )
    return subject


def snapshot_table_for(
    snapshot: "RdbmsSchemaSnapshot", entity_name: str | None, operation: str
) -> "SnapshotTable":
    """Resolve a change's declared name to its table in *snapshot*, or raise.

    Args:
        snapshot: The current snapshot the revision renders against.
        entity_name: The change's declared entity/view name. ``None`` is a
            differ-side defect rather than an author error, and says so.
        operation: The change kind's wire string, for the error message
            (``ChangeKind.value`` at the call site).

    Returns:
        The named table.

    Raises:
        GenerationError: If the name is absent, or names nothing in the
            snapshot's migration tables.
    """
    if entity_name is None:
        raise GenerationError(
            f"{operation} change is missing entity name. "
            "This is an internal error in the schema differ."
        )
    tables = snapshot.declared_tables()
    table = tables.get(entity_name)
    if table is None:
        raise GenerationError(
            f"Entity '{entity_name}' not found in current snapshot for {operation}. "
            f"Available: {sorted(tables)}."
        )
    return table


__all__ = ["change_subject", "snapshot_table_for"]
