"""The entities a set of schema changes names under one change kind."""

from __future__ import annotations

from cruftfree_rdbms_schema.differ import ChangeKind, SchemaChange


def _entities_with_kind(
    changes: tuple[SchemaChange, ...],
    kind: ChangeKind,
) -> set[str]:
    """Collect the named entities of every change of a given kind.

    Args:
        changes: The full set of schema changes.
        kind: The change kind to select.

    Returns:
        Set of entity names carried by matching changes.
    """
    return {
        change.entity
        for change in changes
        if change.kind == kind and change.entity is not None
    }
