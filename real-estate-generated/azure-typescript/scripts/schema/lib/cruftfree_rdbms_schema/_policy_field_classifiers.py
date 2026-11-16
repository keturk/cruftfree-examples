"""Classifiers for entity and field level schema changes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, Literal

from cruftfree_rdbms_schema._policy_constraints import (
    _constraint_narrowings,
    _constraint_widening_note,
    _is_type_widening,
)
from cruftfree_rdbms_schema._snapshot_models import SnapshotColumn
from cruftfree_rdbms_schema.differ import SchemaChange

#: The default kinds a database evaluates for every row an ``ADD COLUMN`` fills.
_ROW_FILLING_DEFAULT_KINDS: Final[frozenset[str]] = frozenset(
    {"literal", "server_function", "generated"}
)


def _classify_field_added(
    change: SchemaChange,
    added_entities: set[str],
) -> tuple[Literal["safe", "blocked"], str]:
    """Classify a FIELD_ADDED change.

    A nullable field or a field on a newly created table is safe.
    A non-nullable field is only safe if it's on a new table (all fields
    are populated at creation time).

    For existing tables, the field must be nullable to be safe.  Non-nullable
    fields without a database default that fills the existing rows are blocked.

    Args:
        change: The FIELD_ADDED schema change.
        added_entities: Set of entity names that are newly added in this diff.

    Returns:
        Tuple of (classification, diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    field_name = change.field or "<unknown>"

    # Fields on newly created tables are always safe
    if entity_name in added_entities:
        return (
            "safe",
            "Field '%s' added to new table '%s' -- safe (new table)"
            % (field_name, entity_name),
        )

    column = change.subject
    if not isinstance(column, SnapshotColumn):
        raise ValueError(
            "A FIELD_ADDED change of '%s.%s' carries %s as its subject. Expected: the "
            "added SnapshotColumn. Fix: build the change through the snapshot differ."
            % (entity_name, field_name, type(column).__name__)
        )
    if column.nullable:
        return (
            "safe",
            "Nullable field '%s' added to existing table '%s' -- safe"
            % (field_name, entity_name),
        )
    if column.default is not None and column.default.kind in _ROW_FILLING_DEFAULT_KINDS:
        return (
            "safe",
            "Non-nullable field '%s' added to existing table '%s' with "
            "a database default that fills the existing rows -- safe"
            % (field_name, entity_name),
        )

    return (
        "blocked",
        "Non-nullable field '%s' added to existing table '%s' without "
        "a database default that fills the existing rows -- blocked. "
        "Make the field nullable or provide a database default."
        % (field_name, entity_name),
    )


def _classify_field_removed(change: SchemaChange) -> tuple[Literal["blocked"], str]:
    """Classify a FIELD_REMOVED change -- always blocked.

    Args:
        change: The FIELD_REMOVED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    field_name = change.field or "<unknown>"
    return (
        "blocked",
        "Field '%s' removed from table '%s' -- blocked. "
        "Field removal is a destructive operation that causes data loss."
        % (field_name, entity_name),
    )


def _classify_primary_key_changed(change: SchemaChange) -> tuple[Literal["blocked"], str]:
    """Classify a FIELD_PRIMARY_KEY_CHANGED change -- always blocked.

    A column joining or leaving its table's primary key re-keys every row and every
    foreign key that references the table, and no engine's forward DDL is rendered for
    it, so the change is refused in every direction: a convergence plan never applies
    it, whatever the deploy's switches.

    Args:
        change: The FIELD_PRIMARY_KEY_CHANGED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message naming the fix).
    """
    entity_name = change.entity or "<unknown>"
    field_name = change.field or "<unknown>"
    joins = change.new_value == str(True)
    return (
        "blocked",
        "Column '%s' of table '%s' %s the table's primary key -- blocked. Convergence "
        "never changes a primary key in place: it re-keys every row and every foreign key that "
        "references the table. Fix: keep the column's key as the database holds it, or "
        "move the rows to a new table declared with the new key."
        % (field_name, entity_name, "joins" if joins else "leaves"),
    )


def _classify_table_renamed(change: SchemaChange) -> tuple[Literal["blocked"], str]:
    """Classify an ENTITY_TABLE_RENAMED change -- always blocked.

    No engine's forward DDL is rendered for a table rename, while the generated code
    already reads and writes the new name, so the change is refused in every direction.

    Args:
        change: The ENTITY_TABLE_RENAMED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message naming both tables and the fix).
    """
    return (
        "blocked",
        "Entity '%s' moves from table '%s' to table '%s' -- blocked. Convergence never renames "
        "a table in place. Fix: keep the table name the database holds, or move the rows "
        "to a new entity declared with the new table."
        % (change.entity or "<unknown>", change.old_value, change.new_value),
    )


def _classify_table_options_changed(change: SchemaChange) -> tuple[Literal["blocked"], str]:
    """Classify an ENTITY_OPTIONS_CHANGED change -- always blocked.

    No engine's forward DDL is rendered for a table option, so the change is refused in
    every direction.

    Args:
        change: The ENTITY_OPTIONS_CHANGED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message naming both option sets and the fix).
    """
    return (
        "blocked",
        "Table '%s' changes its options from %s to %s -- blocked. Convergence never changes a "
        "table's options in place. Fix: keep the options the recorded schema holds."
        % (change.entity or "<unknown>", change.old_value, change.new_value),
    )


def _classify_entity_added(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify an ENTITY_ADDED change -- always safe.

    Args:
        change: The ENTITY_ADDED schema change.

    Returns:
        Tuple of ("safe", diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    return (
        "safe",
        "Table '%s' added -- safe (new table)" % entity_name,
    )


def _classify_entity_removed(change: SchemaChange) -> tuple[Literal["blocked"], str]:
    """Classify an ENTITY_REMOVED change -- always blocked.

    Args:
        change: The ENTITY_REMOVED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    return (
        "blocked",
        "Table '%s' removed -- blocked. "
        "Table removal is a destructive operation that causes data loss."
        % entity_name,
    )


def _type_widening_diagnostic(
    field_name: str,
    entity_name: str,
    old_type: str | None,
    new_type: str | None,
    old_constraints: Mapping[str, int],
    new_constraints: Mapping[str, int],
) -> str:
    """Diagnostic for a FIELD_TYPE_CHANGED classified risky (widening, no narrowing)."""
    constraint_note = _constraint_widening_note(old_constraints, new_constraints)
    suffix = " (%s)" % constraint_note if constraint_note else ""
    if old_type == new_type:
        return (
            "Field '%s' in table '%s' type widened%s "
            "-- risky (requires adapter verification)"
            % (field_name, entity_name, suffix)
        )
    return (
        "Field '%s' in table '%s' type widened from '%s' to '%s'%s "
        "-- risky (requires adapter verification)"
        % (field_name, entity_name, old_type, new_type, suffix)
    )


def _type_narrowing_diagnostic(
    field_name: str,
    entity_name: str,
    old_type: str | None,
    new_type: str | None,
    narrowings: list[str],
) -> str:
    """Diagnostic for a FIELD_TYPE_CHANGED classified blocked."""
    if narrowings:
        return (
            "Field '%s' in table '%s' type changed from '%s' to '%s' "
            "-- blocked (%s). Resolve manually, or widen the constraint instead."
            % (field_name, entity_name, old_type, new_type, "; ".join(narrowings))
        )
    return (
        "Field '%s' in table '%s' type changed from '%s' to '%s' "
        "-- blocked. Type narrowing or incompatible type change is not allowed. "
        "Resolve manually."
        % (field_name, entity_name, old_type, new_type)
    )


def _classify_field_type_changed(
    change: SchemaChange,
) -> tuple[Literal["risky", "blocked"], str]:
    """Classify a FIELD_TYPE_CHANGED change.

    Risky (adapter-verified widening) when the name change is a
    recognized widening pair or the name is unchanged, AND no constraint
    narrows (:func:`_constraint_narrowings`). Blocked otherwise -- naming the
    field, table, both type names, both constraint sets, and each narrowing.

    Args:
        change: The FIELD_TYPE_CHANGED schema change.

    Returns:
        Tuple of (classification, diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    field_name = change.field or "<unknown>"
    old_type = change.old_value
    new_type = change.new_value
    old_constraints = dict(change.old_constraints)
    new_constraints = dict(change.new_constraints)
    narrowings = _constraint_narrowings(old_constraints, new_constraints)
    name_change_is_safe = old_type == new_type or _is_type_widening(old_type, new_type)

    if name_change_is_safe and not narrowings:
        return (
            "risky",
            _type_widening_diagnostic(
                field_name, entity_name, old_type, new_type, old_constraints, new_constraints
            ),
        )

    return (
        "blocked",
        _type_narrowing_diagnostic(field_name, entity_name, old_type, new_type, narrowings),
    )


def _classify_nullable_changed(
    change: SchemaChange,
) -> tuple[Literal["safe", "blocked"], str]:
    """Classify a FIELD_NULLABLE_CHANGED change.

    Relaxing nullability (NOT NULL -> nullable) is safe.
    Tightening nullability (nullable -> NOT NULL) is blocked.

    Args:
        change: The FIELD_NULLABLE_CHANGED schema change.

    Returns:
        Tuple of (classification, diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    field_name = change.field or "<unknown>"

    # old_value/new_value are string representations of booleans from the differ
    old_nullable = change.old_value
    new_nullable = change.new_value

    # Relaxation: was NOT NULL (False), now nullable (True)
    if old_nullable == "False" and new_nullable == "True":
        return (
            "safe",
            "Field '%s' in table '%s' nullability relaxed (NOT NULL -> nullable) "
            "-- safe" % (field_name, entity_name),
        )

    # Tightening: was nullable (True), now NOT NULL (False)
    if old_nullable == "True" and new_nullable == "False":
        return (
            "blocked",
            "Field '%s' in table '%s' nullability tightened (nullable -> NOT NULL) "
            "-- blocked. Existing NULL values would violate the new constraint."
            % (field_name, entity_name),
        )

    # Unexpected values -- blocked for safety
    return (
        "blocked",
        "Field '%s' in table '%s' nullable changed from '%s' to '%s' "
        "-- blocked (unexpected nullable values)"
        % (field_name, entity_name, old_nullable, new_nullable),
    )
