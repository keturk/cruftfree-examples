"""Canonical RDBMS schema snapshot format.

Defines the language-neutral contract (schema.json) for a block's schema. All
dataclasses are frozen (immutable). The snapshot must NOT include resolved
database engine, database name, host, port, provider, profile, or platform.
Target-language metadata (SQLAlchemy types, MikroORM decorators) must NOT
appear in snapshots.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import replace

from cruftfree_common.cruftfree_model.enum_literal_text import (
    stored_enum_literal_from_parts,
)

from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot, SnapshotTable
from cruftfree_rdbms_schema._snapshot_serialization import (
    _dict_to_snapshot,
    _snapshot_to_dict,
)
from cruftfree_rdbms_schema._snapshot_versions import UTF8


def snapshots_describe_the_same_schema(
    previous: RdbmsSchemaSnapshot,
    current: RdbmsSchemaSnapshot,
) -> bool:
    """True when two snapshots describe the same database schema.

    Compares only the SCHEMA-bearing fields -- tables, CQRS view tables,
    audit-log, junction and framework tables, native enum types and the block's schema placement.  A
    table's columns are compared by column name, the identity the change differ
    pairs them by (:func:`~cruftfree_rdbms_schema.snapshot_diff.compute_snapshot_diff`):
    the key a table's ``fields`` carries is a DSL field name, not a schema fact,
    so a field renamed only in its DSL spelling (``skuID`` -> ``skuId``, both
    ``sku_id``) describes the same schema.  :func:`compute_schema_hash` is not a
    substitute: it also covers snapshot ``version``, ``service.version``,
    container and block names and ``rdbms_id``, so a service version bump
    changes the hash without changing one column.

    This exists for callers that must fail closed on a schema difference the
    change differ did NOT describe.  ``compute_snapshot_diff`` reports a
    structured change per difference it knows how to compare; a difference it
    does not compare yields an empty diff, which reads as "nothing changed".
    Asking this function instead turns "the differ had nothing to say" into
    "the differ had nothing to say AND the schemas really are identical".

    Args:
        previous: The previous snapshot.
        current: The current snapshot.

    Returns:
        True when every schema-bearing field is equal.
    """
    return (
        _column_keyed_tables(previous.entities)
        == _column_keyed_tables(current.entities)
        and _column_keyed_tables(previous.cqrs_views)
        == _column_keyed_tables(current.cqrs_views)
        and _column_keyed_tables(previous.audit_log_tables)
        == _column_keyed_tables(current.audit_log_tables)
        and _column_keyed_tables(previous.junction_tables)
        == _column_keyed_tables(current.junction_tables)
        and _column_keyed_tables(previous.framework_tables)
        == _column_keyed_tables(current.framework_tables)
        and previous.enums == current.enums
        and previous.schema_name == current.schema_name
    )


def _column_keyed_tables(
    tables: Mapping[str, SnapshotTable],
) -> dict[str, SnapshotTable]:
    """*tables* with each table's columns keyed by column name instead of DSL field name."""
    return {
        name: replace(
            table,
            fields={column.column_name: column for column in table.fields.values()},
        )
        for name, table in tables.items()
    }


# @canonical(rdbms-schema/snapshot-enum-stored-labels): The labels a snapshot's enums
#   are stored as, per enum name, in member order
# @rule: Every emitter that spells an enum member in DDL, an ORM type or a
#   hand-written statement reads its labels here -- never from SnapshotEnum.values
#   (member NAMES) and never by re-deriving a case rule
# @anti-pattern: Rendering a member NAME as a label, or defaulting an unrecorded
#   member_values to "no member declares a value"
# @see: enum/stored-literal
def stored_enum_labels(snapshot: RdbmsSchemaSnapshot) -> dict[str, tuple[str, ...]]:
    """The stored label of every member of every enum *snapshot* declares.

    Each label is :func:`~cruftfree_common.cruftfree_model.enum_literal_text.stored_enum_literal_from_parts`
    over the member's name and its recorded ``value(...)``.

    Args:
        snapshot: A snapshot built from the model (it records member values).

    Returns:
        ``{enum name: labels in member order}``.

    Raises:
        ValueError: An enum records fewer member values than members, or a column
            lists members its type does not declare
            (:func:`require_column_members_declared`). A snapshot written before
            member values were recorded, or reflected from a live database, cannot
            say which label each member is stored as -- the caller must refuse
            rather than guess.
    """
    labels: dict[str, tuple[str, ...]] = {}
    for snap_enum in snapshot.enums:
        if len(snap_enum.member_values) != len(snap_enum.values):
            raise ValueError(
                "Enum '%s' records %d declared member values for %d members, so the "
                "label each member is stored as cannot be told. A snapshot written "
                "before enum member values were recorded, or reflected from a live "
                "database, carries none of them -- and a database's labels do not say "
                "which came from a DSL value('...'). Re-generate the snapshot from the "
                ".cfree sources."
                % (snap_enum.name, len(snap_enum.member_values), len(snap_enum.values))
            )
        labels[snap_enum.name] = tuple(
            stored_enum_literal_from_parts(name, declared)
            for name, declared in zip(
                snap_enum.values, snap_enum.member_values, strict=True
            )
        )
    require_column_members_declared(snapshot)
    return labels


def require_column_members_declared(snapshot: RdbmsSchemaSnapshot) -> None:
    """Refuse a column whose type or ``type.values`` are not what its snapshot declares.

    A column's member list is a restatement, never a fact of its own: an enum-typed
    column lists exactly the members of the block-level enum it is typed with, and a
    scalar column lists none. Every producer copies them so (the source builder from
    the enum node, a reflector from the catalog's enum), so a column that disagrees
    describes no database: the type would be created with one member list and the
    column hold another. For the same reason the block declares each enum once, and an
    enum-typed column is typed with an enum the block declares: a type held twice, or
    a column typed with a type the block does not hold, is no schema a database has.

    Args:
        snapshot: The snapshot whose enums and declared tables are checked.

    Raises:
        ValueError: Two enums share a name or a database name; or a column is typed with an enum the
            snapshot does not declare, or lists members its type does not declare,
            naming the table, the column, both member lists and the type.
    """
    members_by_enum = {snap_enum.name: snap_enum.values for snap_enum in snapshot.enums}
    if len(members_by_enum) != len(snapshot.enums):
        raise ValueError(
            "The snapshot declares enums %s, naming one more than once; a block holds each "
            "enum type once. Re-generate the snapshot from the .cfree sources."
            % sorted(snap_enum.name for snap_enum in snapshot.enums)
        )
    database_names = [snap_enum.database_name for snap_enum in snapshot.enums]
    if len(set(database_names)) != len(database_names):
        raise ValueError(
            "The snapshot declares enums %s under the database names %s, one database name "
            "more than once; a database holds one type under each name. Re-generate the "
            "snapshot from the .cfree sources."
            % (
                [snap_enum.name for snap_enum in snapshot.enums],
                database_names,
            )
        )
    for table_name, table in snapshot.declared_tables().items():
        for column in table.fields.values():
            if column.type.kind != "enum":
                if column.type.values:
                    raise ValueError(
                        "Column '%s.%s' is typed with scalar '%s' but lists enum members "
                        "%s; only an enum-typed column lists members. Re-generate the "
                        "snapshot from the .cfree sources."
                        % (
                            table_name,
                            column.column_name,
                            column.type.name,
                            list(column.type.values),
                        )
                    )
                continue
            declared_members = members_by_enum.get(column.type.name)
            if declared_members is None:
                raise ValueError(
                    "Column '%s.%s' is typed with enum '%s', which the snapshot does not "
                    "declare (it declares %s), so no type would be created for it. "
                    "Re-generate the snapshot from the .cfree sources."
                    % (
                        table_name,
                        column.column_name,
                        column.type.name,
                        sorted(members_by_enum),
                    )
                )
            if column.type.values != declared_members:
                raise ValueError(
                    "Column '%s.%s' is typed with enum '%s' listing members %s, but the "
                    "block-level enum declares %s. The type would be created with one "
                    "member list and the column hold another; re-generate the snapshot "
                    "from the .cfree sources."
                    % (
                        table_name,
                        column.column_name,
                        column.type.name,
                        list(column.type.values),
                        list(declared_members),
                    )
                )


def enum_names_in_use(snapshot: RdbmsSchemaSnapshot) -> frozenset[str]:
    """The names of the enums some column of *snapshot*'s declared tables is typed with."""
    return frozenset(
        column.type.name
        for table in snapshot.declared_tables().values()
        for column in table.fields.values()
        if column.type.kind == "enum"
    )


def _canonical_json(data: object) -> str:
    """The one canonical JSON form: sorted keys, 2-space indent, non-ASCII kept."""
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)


# @canonical(rdbms-schema/schema-snapshot): Frozen RDBMS schema snapshot format and serialize/hash/compare functions
# @rule: Snapshot must not include engine, database, host, port, provider, profile, or platform
# @rule: Target-language metadata must not appear in snapshots
# @rule: Empty maps/arrays serialized as {} and [] -- omitted optional collections are invalid
# @see: rdbms-schema/schema-snapshot-builder
# @see: rdbms-schema/schema-differ
def compute_schema_hash(snapshot: RdbmsSchemaSnapshot) -> str:
    """SHA-256 over the snapshot's canonical JSON, computed on demand and never stored.

    The differ's equal-schema short cut: two snapshots with one hash describe one
    schema.
    Args:
        snapshot: The snapshot to hash.

    Returns:
        Lowercase hexadecimal SHA-256 string.
    """
    hashable = _snapshot_to_dict(snapshot)
    return hashlib.sha256(_canonical_json(hashable).encode(UTF8)).hexdigest()


def serialize_snapshot(snapshot: RdbmsSchemaSnapshot) -> str:
    """Serialize snapshot to JSON string.

    Args:
        snapshot: The snapshot to serialize.

    Returns:
        JSON string with sorted keys and 2-space indent.
    """
    return _canonical_json(_snapshot_to_dict(snapshot))


def deserialize_snapshot(data: str) -> RdbmsSchemaSnapshot:
    """Load snapshot from JSON string.

    Validates structure and format: every object must carry exactly the keys
    its encoder writes -- an unknown key, or a missing required one, is refused
    with the key, the object kind and its place in the snapshot named.  A
    snapshot of another format or version is refused, naming both and the fix.

    Args:
        data: JSON string to parse.

    Returns:
        RdbmsSchemaSnapshot.

    Raises:
        ValueError: If the JSON is invalid, has another format or version, or is
            structurally malformed (a wrong value type, an unknown key, a missing
            required key).
    """
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Invalid JSON in snapshot: {e}. Expected a valid schema.json file."
        ) from e
    if not isinstance(parsed, dict):
        raise ValueError(
            f"Expected JSON object at top level, got {type(parsed).__name__}. "
            "Snapshot must be a JSON object."
        )
    return _dict_to_snapshot(parsed)
