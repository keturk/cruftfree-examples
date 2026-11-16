"""Classifiers for index, relationship, comment, default, unique, check and enum schema changes."""

from __future__ import annotations

from typing import Literal

from cruftfree_rdbms_schema._snapshot_models import (
    SnapshotCheck,
    SnapshotEnum,
    SnapshotTrigger,
)
from cruftfree_rdbms_schema.differ import SchemaChange


def _subject_name(change: SchemaChange) -> str:
    """The name the database holds a check, trigger or enum type change's subject under.

    Raises:
        ValueError: The change's subject is not a check, a trigger or an enum type.
    """
    subject = change.subject
    if isinstance(subject, SnapshotCheck | SnapshotTrigger):
        return subject.name
    if isinstance(subject, SnapshotEnum):
        return subject.database_name
    raise ValueError(
        "A %s change carries %s as its subject. Expected: a check, a trigger or an enum "
        "type (CHANGE_SUBJECT_TYPES). Fix: build the change through the snapshot differ."
        % (change.kind.value, type(subject).__name__)
    )


def _classify_index_added(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify an INDEX_ADDED change -- always safe.

    Args:
        change: The INDEX_ADDED schema change.

    Returns:
        Tuple of ("safe", diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    return (
        "safe",
        "Index added to table '%s' -- safe" % entity_name,
    )


def _classify_index_renamed(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify an INDEX_RENAMED change -- always safe.

    A rename gives an object the name the shared naming rule derives; it moves no row,
    drops no object and changes no query's semantics.

    Args:
        change: The INDEX_RENAMED schema change.

    Returns:
        Tuple of ("safe", diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    return (
        "safe",
        "Index on table '%s' renamed to '%s' -- safe" % (entity_name, change.new_value),
    )


def _classify_index_removed(change: SchemaChange) -> tuple[Literal["blocked"], str]:
    """Classify an INDEX_REMOVED change -- always blocked.

    Args:
        change: The INDEX_REMOVED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    return (
        "blocked",
        "Index removed from table '%s' -- blocked. "
        "Index removal can impact query performance and application behavior."
        % entity_name,
    )


def _classify_relationship_added(
    change: SchemaChange,
    added_entities: set[str],
) -> tuple[Literal["safe", "blocked"], str]:
    """Classify a RELATIONSHIP_ADDED change.

    FK additions are only allowed for newly created tables in the same
    revision.  FK additions to existing tables are blocked.

    Args:
        change: The RELATIONSHIP_ADDED schema change.
        added_entities: Set of entity names that are newly added in this diff.

    Returns:
        Tuple of (classification, diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    field_name = change.field or "<unknown>"

    if entity_name in added_entities:
        return (
            "safe",
            "Relationship '%s' added to new table '%s' -- safe (new table)"
            % (field_name, entity_name),
        )

    return (
        "blocked",
        "Foreign key relationship '%s' added to existing table '%s' -- blocked. "
        "FK additions to existing tables are not allowed. "
        "Create the relationship in a new table instead."
        % (field_name, entity_name),
    )


def _classify_foreign_key_replaced(
    change: SchemaChange,
) -> tuple[Literal["risky"], str]:
    """Classify a FOREIGN_KEY_REPLACED change -- risky, never blocked.

    The constraint is dropped under the name the database holds and added again under
    its declared name with the DSL's actions. No row is moved or lost, so the change is
    never blocked; but the new constraint is validated against the rows already in the
    table, and a table holding an orphan row fails the apply (naming the constraint)
    rather than silently dropping the row. That is an apply that can fail on data the
    generator cannot see, which is what ``risky`` states.

    Args:
        change: The FOREIGN_KEY_REPLACED schema change.

    Returns:
        Tuple of ("risky", diagnostic message).
    """
    return (
        "risky",
        "Foreign key '%s' on table '%s' replaced from '%s' to '%s' with its declared actions "
        "-- risky (the constraint is validated against existing rows; an orphan row fails "
        "the apply and is never deleted)"
        % (
            change.field or "<unknown>",
            change.entity or "<unknown>",
            change.old_value,
            change.new_value,
        ),
    )


def _classify_foreign_key_renamed(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify a FOREIGN_KEY_RENAMED change -- always safe.

    The constraint keeps its columns, referred table, referred columns and actions and
    takes the name the schema declares; it moves no row and is never absent.

    Args:
        change: The FOREIGN_KEY_RENAMED schema change.

    Returns:
        Tuple of ("safe", diagnostic message).
    """
    return (
        "safe",
        "Foreign key '%s' on table '%s' renamed from '%s' to '%s' -- safe"
        % (
            change.field or "<unknown>",
            change.entity or "<unknown>",
            change.old_value,
            change.new_value,
        ),
    )


def _classify_schema_relocated(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify a SCHEMA_RELOCATED change -- safe (non-destructive).

    Moving every table and native enum type to a new PostgreSQL schema via
    ``ALTER ... SET SCHEMA`` preserves all data; it changes only object
    placement.  It is therefore additive/non-destructive and rendered as a
    forward revision, never blocked.

    Args:
        change: The SCHEMA_RELOCATED schema change.

    Returns:
        Tuple of ("safe", diagnostic message).
    """
    return (
        "safe",
        "Block schema relocated from %s to %s -- safe (ALTER ... SET SCHEMA "
        "preserves data)"
        % (change.old_value or "<default>", change.new_value or "<default>"),
    )


def _comment_change_diagnostic(subject: str, change: SchemaChange) -> str:
    """One diagnostic line for a table/column comment change.

    Names the transition rather than echoing the text: comment bodies are
    multi-line author prose, and pasting one into a policy diagnostic makes
    the operator's log unreadable for no added decision value.
    """
    if change.old_value is None:
        return "%s comment set -- safe (COMMENT ON writes no row data)" % subject
    if change.new_value is None:
        return (
            "%s comment cleared -- safe (COMMENT ON ... IS NULL drops only the "
            "text the DSL no longer declares)" % subject
        )
    return "%s comment updated -- safe (COMMENT ON writes no row data)" % subject


def _classify_entity_comment_changed(
    change: SchemaChange,
) -> tuple[Literal["safe"], str]:
    """Classify an ENTITY_COMMENT_CHANGED change -- safe (non-destructive).

    ``COMMENT ON TABLE`` replaces catalog text and touches no row, no
    column type, and no constraint, so it can never lose data. It is still
    a schema change (an existing database keeps the old text until the
    forward revision runs), which is why it is diffed and rendered at all
    rather than treated as metadata.
    """
    return ("safe", _comment_change_diagnostic(
        "Table '%s'" % (change.entity or "<unknown>"), change,
    ))


def _classify_field_comment_changed(
    change: SchemaChange,
) -> tuple[Literal["safe"], str]:
    """Classify a FIELD_COMMENT_CHANGED change -- safe (non-destructive).

    The column analogue of :func:`_classify_entity_comment_changed`.
    """
    return ("safe", _comment_change_diagnostic(
        "Column '%s.%s'" % (change.entity or "<unknown>", change.field or "<unknown>"),
        change,
    ))


def _classify_field_default_changed(
    change: SchemaChange,
) -> tuple[Literal["safe"], str]:
    """Classify a FIELD_DEFAULT_CHANGED change -- safe (non-destructive).

    ``ALTER COLUMN ... SET DEFAULT`` / ``DROP DEFAULT`` changes what a row
    inserted afterwards receives when it omits the column; it rewrites no row
    already stored and cannot fail on existing data.
    """
    column = "Column '%s.%s'" % (change.entity or "<unknown>", change.field or "<unknown>")
    if change.new_value is None:
        return ("safe", "%s default dropped -- safe (existing rows keep their values)" % column)
    return ("safe", "%s default set -- safe (applies to rows inserted afterwards)" % column)


def _classify_field_unique_changed(
    change: SchemaChange,
) -> tuple[Literal["safe", "risky", "blocked"], str]:
    """Classify a FIELD_UNIQUE_CHANGED change.

    Dropping a column's unique constraint loses no row: safe. Adding one is
    risky -- a table already holding two rows with the same value fails the
    revision, naming the constraint; no row is deleted to make it pass.
    """
    column = "Column '%s.%s'" % (change.entity or "<unknown>", change.field or "<unknown>")
    if change.old_value == "True" and change.new_value == "False":
        return ("safe", "%s unique constraint dropped -- safe" % column)
    if change.old_value == "False" and change.new_value == "True":
        return (
            "risky",
            "%s unique constraint added -- risky: the revision fails if existing "
            "rows hold duplicate values; remove the duplicates before applying it" % column,
        )
    return (
        "blocked",
        "%s unique changed from '%s' to '%s' -- blocked (unexpected unique values)"
        % (column, change.old_value, change.new_value),
    )


def _classify_check_added(change: SchemaChange) -> tuple[Literal["risky"], str]:
    """Classify a CHECK_ADDED change -- risky, never blocked.

    The new check is validated against the rows already in the table: a table holding
    a row that violates it fails the revision, naming the check, and no row is deleted
    to make it pass. That is a revision that can fail on data the generator cannot
    see, which is what ``risky`` states.
    """
    return (
        "risky",
        "Check '%s' added to table '%s' -- risky: the revision fails if existing rows "
        "violate it; correct those rows before applying it"
        % (_subject_name(change), change.entity or "<unknown>"),
    )


def _classify_check_removed(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify a CHECK_REMOVED change -- safe: dropping a check loses no row."""
    return (
        "safe",
        "Check '%s' removed from table '%s' -- safe (no row is lost)"
        % (_subject_name(change), change.entity or "<unknown>"),
    )


def _classify_trigger_added(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify a TRIGGER_ADDED change -- safe: a trigger answers later writes, not existing rows."""
    return (
        "safe",
        "Trigger '%s' added to table '%s' -- safe (it judges only writes made after it exists)"
        % (_subject_name(change), change.entity or "<unknown>"),
    )


def _classify_trigger_removed(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify a TRIGGER_REMOVED change -- safe: dropping a trigger loses no row."""
    return (
        "safe",
        "Trigger '%s' removed from table '%s' -- safe (no row is lost)"
        % (_subject_name(change), change.entity or "<unknown>"),
    )


def _classify_enum_value_added(change: SchemaChange) -> tuple[Literal["safe"], str]:
    """Classify an ENUM_VALUE_ADDED change -- always safe.

    Appending a member to a native enum type is non-destructive: no existing
    row holds the new label, no column changes, and PostgreSQL has forward DDL
    for exactly this (``ALTER TYPE ... ADD VALUE IF NOT EXISTS``). This is the
    one enum edit a convergence applies in place.

    Args:
        change: The ENUM_VALUE_ADDED schema change.

    Returns:
        Tuple of ("safe", diagnostic message).
    """
    return (
        "safe",
        "Member '%s' added to enum '%s' -- safe (ALTER TYPE ... ADD VALUE "
        "appends without touching existing rows)"
        % (change.new_value or "<unknown>", change.enum or "<unknown>"),
    )


def _classify_enum_value_relabeled(
    change: SchemaChange,
) -> tuple[Literal["safe"], str]:
    """Classify an ENUM_VALUE_RELABELED change -- always safe.

    Every member keeps its place in the type; only the label it is stored under
    changes. Renaming a label in place (``ALTER TYPE ... RENAME VALUE``, or an
    ``UPDATE`` on a column holding its labels as data) preserves every row, and a
    set of relabels whose new labels collide with each other's old labels is
    ordered by the renderer, not refused.

    Args:
        change: The ENUM_VALUE_RELABELED schema change.

    Returns:
        Tuple of ("safe", diagnostic message).
    """
    return (
        "safe",
        "Members of enum '%s' relabeled -- safe (a label is renamed in place; "
        "no row is lost)" % (change.enum or "<unknown>"),
    )


def _classify_enum_value_removed(
    change: SchemaChange,
) -> tuple[Literal["blocked"], str]:
    """Classify an ENUM_VALUE_REMOVED change -- always blocked.

    PostgreSQL has no ``ALTER TYPE ... DROP VALUE``. A member dropped from the
    DSL therefore stays in a deployed type forever while a fresh database
    creates the type without it, so the two diverge permanently -- and any row
    still holding the removed label fails to decode against the generated enum
    the moment it is read. A rename arrives here as a removal plus an addition
    and is blocked by this same rule.

    Args:
        change: The ENUM_VALUE_REMOVED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message).
    """
    return (
        "blocked",
        "Member '%s' removed from enum '%s' -- blocked. PostgreSQL has no "
        "ALTER TYPE ... DROP VALUE: an already-deployed database keeps the "
        "member while a fresh one is created without it, and any row still "
        "holding '%s' stops decoding. Keep the member, or move the data off it "
        "and drop the type manually."
        % (
            change.old_value or "<unknown>",
            change.enum or "<unknown>",
            change.old_value or "<unknown>",
        ),
    )


def _classify_enum_type_removed(
    change: SchemaChange,
) -> tuple[Literal["blocked"], str]:
    """Classify an ENUM_TYPE_REMOVED change -- always blocked.

    The type is one the live catalog holds and the declared schema never uses, so
    dropping it is the removal of an undeclared object: it needs the operator's
    approval (:mod:`cruftfree_rdbms_schema.undeclared_objects`).

    Args:
        change: The ENUM_TYPE_REMOVED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message).
    """
    return (
        "blocked",
        "Enum type '%s' is held by the database and used by no declared column -- "
        "blocked. Dropping it needs approval. Declare the type in the DSL, or drop it "
        "through an approved deploy." % (change.enum or "<unknown>"),
    )


def _classify_enum_type_added(
    change: SchemaChange,
) -> tuple[Literal["blocked"], str]:
    """Classify an ENUM_TYPE_ADDED change -- always blocked.

    The type is one the current schema holds and no column of it uses, so no column's
    creation creates it, and no engine's forward DDL is rendered for it alone.

    Args:
        change: The ENUM_TYPE_ADDED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message naming the type and the fix).
    """
    return (
        "blocked",
        "Enum type '%s' (database name '%s') is added and used by no column -- blocked. "
        "Convergence never creates a type no column uses. Fix: type a column with it, or "
        "remove it from the schema." % (change.enum or "<unknown>", _subject_name(change)),
    )


def _classify_enum_type_renamed(
    change: SchemaChange,
) -> tuple[Literal["blocked"], str]:
    """Classify an ENUM_TYPE_RENAMED change -- always blocked.

    No engine's forward DDL is rendered for a type rename, so the change is refused in
    every direction.

    Args:
        change: The ENUM_TYPE_RENAMED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message naming both database names and the fix).
    """
    return (
        "blocked",
        "Enum type '%s' moves from database name '%s' to '%s' -- blocked. Convergence never "
        "renames a type in place. Fix: keep the database name the recorded schema holds."
        % (change.enum or "<unknown>", change.old_value, change.new_value),
    )


def _classify_enum_values_reordered(
    change: SchemaChange,
) -> tuple[Literal["blocked"], str]:
    """Classify an ENUM_VALUES_REORDERED change -- always blocked.

    A native enum's member order is its ``enumsortorder``, and it is what
    ``ORDER BY <enum column>`` sorts on. ``ADD VALUE`` cannot reposition an
    existing member, so a reorder in the DSL is silently invisible to a
    deployed database: fresh environments sort one way and existing ones
    another, from the same source.

    Args:
        change: The ENUM_VALUES_REORDERED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message).
    """
    return (
        "blocked",
        "Members of enum '%s' reordered ('%s' -> '%s') -- blocked. A native "
        "enum's declaration order is its sort order, and no forward DDL "
        "repositions an existing member: an already-deployed database would "
        "keep sorting by the old order while a fresh one uses the new. Restore "
        "the previous order, or reorder the type manually in every environment."
        % (
            change.enum or "<unknown>",
            change.old_value or "",
            change.new_value or "",
        ),
    )


def _classify_relationship_removed(
    change: SchemaChange,
) -> tuple[Literal["blocked"], str]:
    """Classify a RELATIONSHIP_REMOVED change -- always blocked.

    Args:
        change: The RELATIONSHIP_REMOVED schema change.

    Returns:
        Tuple of ("blocked", diagnostic message).
    """
    entity_name = change.entity or "<unknown>"
    field_name = change.field or "<unknown>"
    return (
        "blocked",
        "Relationship '%s' removed from table '%s' -- blocked. "
        "Relationship removal is a destructive operation."
        % (field_name, entity_name),
    )
