"""Entity and field comment diffing."""

from __future__ import annotations

from cruftfree_rdbms_schema._diff_entity_members import diff_common_entity_members
from cruftfree_rdbms_schema._diff_entity_tables import TableSides, _ColumnPairing
from cruftfree_rdbms_schema.differ import (
    ChangeKind,
    SchemaChange,
    schema_change_builder,
)


def _diff_entity_comments(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """Diff the table comment and every common column's comment."""
    change = schema_change_builder(service_name, entity_name)
    changes: list[SchemaChange] = []

    if prev.canonical.comment != curr.canonical.comment:
        changes.append(
            change(
                ChangeKind.ENTITY_COMMENT_CHANGED,
                detail="Entity %s comment changed" % entity_name,
                old_value=prev.canonical.comment,
                new_value=curr.canonical.comment,
                subject=curr.raw,
            )
        )

    for field_name, prev_col, curr_col in _ColumnPairing(prev.canonical, curr.canonical).common:
        prev_comment = prev_col.comment
        curr_comment = curr_col.comment
        if prev_comment != curr_comment:
            changes.append(
                change(
                    ChangeKind.FIELD_COMMENT_CHANGED,
                    field=field_name,
                    detail="Field %s comment changed" % field_name,
                    old_value=prev_comment,
                    new_value=curr_comment,
                    subject=curr.column(field_name),
                )
            )
    return changes


def _diff_common_entity(
    service_name: str,
    entity_name: str,
    prev: TableSides,
    curr: TableSides,
) -> list[SchemaChange]:
    """Diff a single entity present in both snapshots (table, fields, indexes, FKs, checks, comments)."""
    return [
        *diff_common_entity_members(service_name, entity_name, prev, curr),
        *_diff_entity_comments(service_name, entity_name, prev, curr),
    ]
