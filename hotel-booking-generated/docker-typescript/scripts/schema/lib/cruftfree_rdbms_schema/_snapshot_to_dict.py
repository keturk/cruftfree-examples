"""Serialization of snapshot types to dictionaries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotBlockIdentity,
    SnapshotCheck,
    SnapshotColumn,
    SnapshotContainerIdentity,
    SnapshotDefault,
    SnapshotEnum,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotServiceIdentity,
    SnapshotStorage,
    SnapshotTable,
    SnapshotTrigger,
    SnapshotType,
)
from cruftfree_rdbms_schema.sql_lowering.lowered import SqlNode
from cruftfree_rdbms_schema.sql_lowering.tree_data import tree_to_data

_T = TypeVar("_T")


@dataclass(frozen=True)
class _ObjectKeys(Generic[_T]):
    """The keys one snapshot object is written with, and so the only keys it is read with.

    A ``required`` key is always written and must be present on read. An
    ``optional`` key is written only when its reader returns something other
    than ``None``, and may be absent on read: the encoder omits it, or the
    snapshot was written before the key existed.
    """

    label: str
    required: Mapping[str, Callable[[_T], object]]
    optional: Mapping[str, Callable[[_T], object]]

    def encode(self, obj: _T) -> dict[str, object]:
        """Write *obj* as a JSON-safe dict of exactly this table's keys."""
        result = {key: read(obj) for key, read in self.required.items()}
        for key, read in self.optional.items():
            value = read(obj)
            if value is not None:
                result[key] = value
        return result

    def read(self, value: object, where: str) -> dict[str, object]:
        """Return *value* as a dict holding only this table's keys and all its required ones.

        Raises:
            ValueError: If *value* is not an object, carries a key this table
                does not write, or lacks a required key. The message names the
                key, the object kind and where in the snapshot it sits.
        """
        if not isinstance(value, dict):
            raise ValueError(
                f"Expected an object for {self.label} at {where}, got "
                f"{type(value).__name__}. Snapshot data may be corrupted."
            )
        known = set(self.required) | set(self.optional)
        unknown = sorted(str(key) for key in value if key not in known)
        if unknown:
            raise ValueError(
                f"Unknown key(s) {unknown} in {self.label} at {where}. A "
                f"{self.label} is written with the keys {sorted(known)} only. The "
                "snapshot was edited by hand, corrupted, or written by a different "
                "CruftFree version; re-generate it."
            )
        missing = sorted(key for key in self.required if key not in value)
        if missing:
            raise ValueError(
                f"Missing required key(s) {missing} in {self.label} at {where}. "
                f"Every {self.label} is written with {sorted(self.required)}. The "
                "snapshot was edited by hand or corrupted; re-generate it."
            )
        return value


def _tree_or_none(tree: SqlNode | None) -> object:
    """The JSON form of a lowered tree, or ``None`` when there is none (key omitted)."""
    return None if tree is None else tree_to_data(tree)


def _tables_or_none(tables: Mapping[str, SnapshotTable]) -> object:
    """A name-to-table map's JSON form, or ``None`` when it is empty (key omitted)."""
    if not tables:
        return None
    return {name: _snapshot_table_to_dict(table) for name, table in tables.items()}


# ── Key tables ──
#
# An optional key is omitted when unset, so a snapshot not using it serializes
# without it.

_TYPE_KEYS: _ObjectKeys[SnapshotType] = _ObjectKeys(
    label="column type",
    required={
        "kind": lambda t: t.kind,
        "name": lambda t: t.name,
        "constraints": lambda t: dict(t.constraints),
        "values": lambda t: list(t.values),
    },
    optional={},
)

_STORAGE_KEYS: _ObjectKeys[SnapshotStorage] = _ObjectKeys(
    label="column storage",
    required={
        "max_length": lambda s: s.max_length,
        "precision": lambda s: s.precision,
        "scale": lambda s: s.scale,
    },
    optional={},
)

_DEFAULT_KEYS: _ObjectKeys[SnapshotDefault] = _ObjectKeys(
    label="column default",
    required={
        "kind": lambda d: d.kind,
        "value": lambda d: d.value,
        "name": lambda d: d.name,
    },
    # Only a lowered default carries "tree"; a collection literal or a reflected
    # default has none.
    optional={"tree": lambda d: _tree_or_none(d.tree)},
)

_COLUMN_KEYS: _ObjectKeys[SnapshotColumn] = _ObjectKeys(
    label="column",
    required={
        "column_name": lambda c: c.column_name,
        "type": lambda c: _TYPE_KEYS.encode(c.type),
        "storage": lambda c: _STORAGE_KEYS.encode(c.storage),
        "nullable": lambda c: c.nullable,
        "primary_key": lambda c: c.primary_key,
        "default": lambda c: _snapshot_default_to_dict(c.default),
    },
    optional={
        "unique": lambda c: True if c.unique else None,
        "comment": lambda c: c.comment,
    },
)

_INDEX_KEYS: _ObjectKeys[SnapshotIndex] = _ObjectKeys(
    label="index",
    required={
        "columns": lambda i: list(i.columns),
        "unique": lambda i: i.unique,
        "fulltext": lambda i: i.fulltext,
    },
    optional={
        "spatial": lambda i: True if i.spatial else None,
        "name": lambda i: i.name,
        # Written only for a unique index no constraint owns, so every declared
        # snapshot's bytes are unchanged.
        "constraint_backed": lambda i: None if i.constraint_backed else False,
    },
)

_FOREIGN_KEY_KEYS: _ObjectKeys[SnapshotForeignKey] = _ObjectKeys(
    label="foreign key",
    required={
        "columns": lambda f: list(f.columns),
        "referred_table": lambda f: f.referred_table,
        "referred_columns": lambda f: list(f.referred_columns),
        "on_delete": lambda f: f.on_delete,
        "on_update": lambda f: f.on_update,
    },
    # A key built by hand, outside the snapshot builder and a catalog reader, may carry no name.
    optional={"name": lambda f: f.name},
)

_CHECK_KEYS: _ObjectKeys[SnapshotCheck] = _ObjectKeys(
    label="check",
    required={"name": lambda c: c.name},
    # A reflected check carries its name only.
    optional={"tree": lambda c: _tree_or_none(c.tree)},
)

_TRIGGER_KEYS: _ObjectKeys[SnapshotTrigger] = _ObjectKeys(
    label="trigger",
    required={
        "name": lambda t: t.name,
        "columns": lambda t: list(t.columns),
    },
    # A reflected trigger carries its name and kind; only an aggregate invariant has a predicate.
    optional={
        "kind": lambda t: t.kind,
        "predicate": lambda t: _tree_or_none(t.predicate),
    },
)

_TABLE_KEYS: _ObjectKeys[SnapshotTable] = _ObjectKeys(
    label="table",
    required={
        "table_name": lambda t: t.table_name,
        "fields": lambda t: {name: _COLUMN_KEYS.encode(col) for name, col in t.fields.items()},
        "indexes": lambda t: [_INDEX_KEYS.encode(idx) for idx in t.indexes],
        "foreign_keys": lambda t: [_FOREIGN_KEY_KEYS.encode(fk) for fk in t.foreign_keys],
        "table_options": lambda t: dict(t.table_options),
    },
    optional={
        "comment": lambda t: t.comment,
        "checks": lambda t: [_CHECK_KEYS.encode(check) for check in t.checks] if t.checks else None,
        # Written only when the table has triggers, so every other table's bytes are unchanged.
        "triggers": lambda t: (
            [_TRIGGER_KEYS.encode(trigger) for trigger in t.triggers] if t.triggers else None
        ),
    },
)

_ENUM_KEYS: _ObjectKeys[SnapshotEnum] = _ObjectKeys(
    label="enum",
    required={
        "name": lambda e: e.name,
        "database_name": lambda e: e.database_name,
        "values": lambda e: list(e.values),
    },
    # Omitted when UNRECORDED (an empty tuple); written whenever recorded --
    # including when every entry is None, the positive statement "these members
    # were read and none declares a value", distinct from silence.
    optional={"member_values": lambda e: list(e.member_values) if e.member_values else None},
)

_SERVICE_KEYS: _ObjectKeys[SnapshotServiceIdentity] = _ObjectKeys(
    label="service",
    required={"name": lambda s: s.name, "version": lambda s: s.version},
    optional={},
)

_CONTAINER_KEYS: _ObjectKeys[SnapshotContainerIdentity] = _ObjectKeys(
    label="container",
    required={"name": lambda c: c.name, "kind": lambda c: c.kind},
    optional={},
)

_BLOCK_KEYS: _ObjectKeys[SnapshotBlockIdentity] = _ObjectKeys(
    label="block",
    required={"name": lambda b: b.name},
    optional={},
)

_SNAPSHOT_KEYS: _ObjectKeys[RdbmsSchemaSnapshot] = _ObjectKeys(
    label="snapshot",
    required={
        "format": lambda s: s.format,
        "version": lambda s: s.version,
        "rdbms_id": lambda s: s.rdbms_id,
        "service": lambda s: _SERVICE_KEYS.encode(s.service),
        "container": lambda s: _CONTAINER_KEYS.encode(s.container),
        "block": lambda s: _BLOCK_KEYS.encode(s.block),
        "entities": lambda s: {name: _TABLE_KEYS.encode(t) for name, t in s.entities.items()},
        "cqrs_views": lambda s: {name: _TABLE_KEYS.encode(v) for name, v in s.cqrs_views.items()},
        "enums": lambda s: [_ENUM_KEYS.encode(e) for e in s.enums],
    },
    optional={
        # Absent for a schemaless block.
        "schema_name": lambda s: s.schema_name,
        "audit_log_tables": lambda s: _tables_or_none(s.audit_log_tables),
        "junction_tables": lambda s: _tables_or_none(s.junction_tables),
        "framework_tables": lambda s: _tables_or_none(s.framework_tables),
    },
)


# ── Serialization helpers ──


def _snapshot_type_to_dict(t: SnapshotType) -> dict[str, object]:
    """Serialize a SnapshotType to a JSON-safe dict."""
    return _TYPE_KEYS.encode(t)


def _snapshot_storage_to_dict(s: SnapshotStorage) -> dict[str, object]:
    """Serialize a SnapshotStorage to a JSON-safe dict."""
    return _STORAGE_KEYS.encode(s)


def _snapshot_default_to_dict(d: SnapshotDefault | None) -> object:
    """Serialize a SnapshotDefault to a JSON-safe dict or None."""
    if d is None:
        return None
    return _DEFAULT_KEYS.encode(d)


def _snapshot_column_to_dict(col: SnapshotColumn) -> dict[str, object]:
    """Serialize a SnapshotColumn to a JSON-safe dict."""
    return _COLUMN_KEYS.encode(col)


def _snapshot_index_to_dict(idx: SnapshotIndex) -> dict[str, object]:
    """Serialize a SnapshotIndex to a JSON-safe dict."""
    return _INDEX_KEYS.encode(idx)


def _snapshot_fk_to_dict(fk: SnapshotForeignKey) -> dict[str, object]:
    """Serialize a SnapshotForeignKey to a JSON-safe dict."""
    return _FOREIGN_KEY_KEYS.encode(fk)


def _snapshot_check_to_dict(check: SnapshotCheck) -> dict[str, object]:
    """Serialize a SnapshotCheck to a JSON-safe dict."""
    return _CHECK_KEYS.encode(check)


def _snapshot_table_to_dict(table: SnapshotTable) -> dict[str, object]:
    """Serialize a SnapshotTable to a JSON-safe dict."""
    return _TABLE_KEYS.encode(table)
