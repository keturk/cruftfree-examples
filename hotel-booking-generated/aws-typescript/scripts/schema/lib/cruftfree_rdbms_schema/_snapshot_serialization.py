"""Snapshot to and from dictionaries.

Each snapshot object is written through its key table (:class:`_ObjectKeys`),
and the same table is the only set of keys the object is read with: a key the
encoder never writes is refused on read, as is a required key that is missing.
The two sides cannot drift because there is one list.
"""

from __future__ import annotations

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
from cruftfree_rdbms_schema._snapshot_to_dict import (
    _BLOCK_KEYS,
    _CHECK_KEYS,
    _COLUMN_KEYS,
    _CONTAINER_KEYS,
    _DEFAULT_KEYS,
    _ENUM_KEYS,
    _FOREIGN_KEY_KEYS,
    _INDEX_KEYS,
    _SERVICE_KEYS,
    _SNAPSHOT_KEYS,
    _STORAGE_KEYS,
    _TABLE_KEYS,
    _TRIGGER_KEYS,
    _TYPE_KEYS,
)
from cruftfree_rdbms_schema._snapshot_versions import SCHEMA_FORMAT, SCHEMA_VERSION
from cruftfree_rdbms_schema.sql_lowering.tree_data import tree_from_data


def _snapshot_enum_to_dict(e: SnapshotEnum) -> dict[str, object]:
    """Serialize a SnapshotEnum to a JSON-safe dict."""
    return _ENUM_KEYS.encode(e)


def _snapshot_to_dict(snapshot: RdbmsSchemaSnapshot) -> dict[str, object]:
    """Convert a snapshot to a JSON-serializable dict (full representation)."""
    return _SNAPSHOT_KEYS.encode(snapshot)


# ── Deserialization helpers ──


def _dict_to_snapshot_type(value: object, where: str) -> SnapshotType:
    """Deserialize a dict to a SnapshotType."""
    d = _TYPE_KEYS.read(value, where)
    constraints = _expect_dict(d["constraints"], f"{where}.constraints")
    return SnapshotType(
        kind=str(d["kind"]),
        name=str(d["name"]),
        constraints={
            str(k): _expect_int(v, f"{where}.constraints[{k!r}]") for k, v in constraints.items()
        },
        values=tuple(str(v) for v in _expect_list(d["values"], f"{where}.values")),
    )


def _dict_to_snapshot_storage(value: object, where: str) -> SnapshotStorage:
    """Deserialize a dict to a SnapshotStorage."""
    d = _STORAGE_KEYS.read(value, where)
    return SnapshotStorage(
        max_length=_optional_int(d["max_length"], f"{where}.max_length"),
        precision=_optional_int(d["precision"], f"{where}.precision"),
        scale=_optional_int(d["scale"], f"{where}.scale"),
    )


def _corrupted(expected: str, label: str, value: object) -> ValueError:
    """The error for a value of the wrong JSON type at *label*."""
    return ValueError(
        f"Expected {expected} for {label}, got {type(value).__name__}. "
        "Snapshot data may be corrupted."
    )


def _expect_dict(value: object, label: str) -> dict[str, object]:
    """Return *value* as a JSON object, raising ValueError if it is not one."""
    if not isinstance(value, dict):
        raise _corrupted("dict", label, value)
    return value


def _expect_list(value: object, label: str) -> list[object]:
    """Return *value* as a JSON array, raising ValueError if it is not one."""
    if not isinstance(value, list):
        raise _corrupted("list", label, value)
    return value


def _expect_str(value: object, label: str) -> str:
    """Return *value* as a JSON string, raising ValueError if it is not one."""
    if not isinstance(value, str):
        raise _corrupted("str", label, value)
    return value


def _expect_int(value: object, label: str) -> int:
    """Return *value* as a JSON integer, raising ValueError if it is not one."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise _corrupted("int", label, value)
    return value


def _optional_int(value: object, label: str) -> int | None:
    """Return *value* as a JSON integer or ``None``, raising ValueError otherwise."""
    return None if value is None else _expect_int(value, label)


def _dict_to_snapshot_default(value: object, where: str) -> SnapshotDefault | None:
    """Deserialize a dict to a SnapshotDefault or None."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(
            f"Expected dict or None for default at {where}, got {type(value).__name__}. "
            "Snapshot data may be corrupted."
        )
    d = _DEFAULT_KEYS.read(value, where)
    return SnapshotDefault(
        kind=str(d["kind"]),
        value=str(d["value"]),
        name=str(d["name"]),
        tree=tree_from_data(d["tree"]) if "tree" in d else None,
    )


def _dict_to_snapshot_column(value: object, where: str = "column") -> SnapshotColumn:
    """Deserialize a dict to a SnapshotColumn."""
    d = _COLUMN_KEYS.read(value, where)
    return SnapshotColumn(
        column_name=str(d["column_name"]),
        type=_dict_to_snapshot_type(d["type"], f"{where}.type"),
        storage=_dict_to_snapshot_storage(d["storage"], f"{where}.storage"),
        nullable=bool(d["nullable"]),
        primary_key=bool(d["primary_key"]),
        unique=bool(d.get("unique", False)),
        default=_dict_to_snapshot_default(d["default"], f"{where}.default"),
        comment=_optional_comment(d),
    )


def _optional_comment(d: dict[str, object]) -> str | None:
    """Read the optional ``comment`` key from a serialized table/column.

    The key is written only when set (:data:`_COLUMN_KEYS`, :data:`_TABLE_KEYS`),
    so its absence reads as no comment.
    """
    value = d.get("comment")
    if value is None:
        return None
    return str(value)


def _dict_to_snapshot_index(value: object, where: str = "index") -> SnapshotIndex:
    """Deserialize a dict to a SnapshotIndex."""
    d = _INDEX_KEYS.read(value, where)
    return SnapshotIndex(
        columns=tuple(str(c) for c in _expect_list(d["columns"], f"{where}.columns")),
        unique=bool(d["unique"]),
        name=str(d["name"]) if d.get("name") is not None else None,
        fulltext=bool(d["fulltext"]),
        spatial=bool(d.get("spatial", False)),
        constraint_backed=bool(d.get("constraint_backed", True)),
    )


def _dict_to_snapshot_fk(value: object, where: str = "foreign key") -> SnapshotForeignKey:
    """Deserialize a dict to a SnapshotForeignKey."""
    d = _FOREIGN_KEY_KEYS.read(value, where)
    referred_columns = _expect_list(d["referred_columns"], f"{where}.referred_columns")
    return SnapshotForeignKey(
        columns=tuple(str(c) for c in _expect_list(d["columns"], f"{where}.columns")),
        referred_table=str(d["referred_table"]),
        referred_columns=tuple(str(c) for c in referred_columns),
        on_delete=str(d["on_delete"]),
        on_update=str(d["on_update"]),
        name=str(d["name"]) if d.get("name") is not None else None,
    )


def _dict_to_snapshot_check(value: object, where: str = "check") -> SnapshotCheck:
    """Deserialize a dict to a SnapshotCheck."""
    d = _CHECK_KEYS.read(value, where)
    return SnapshotCheck(
        name=_expect_str(d["name"], "check name"),
        tree=tree_from_data(d["tree"]) if "tree" in d else None,
    )


def _optional_checks(d: dict[str, object], where: str) -> tuple[SnapshotCheck, ...]:
    """Read the optional ``checks`` key from a serialized table.

    The key is written only when the table has checks (:data:`_TABLE_KEYS`), so
    its absence reads as no checks.
    """
    if "checks" not in d:
        return ()
    return tuple(
        _dict_to_snapshot_check(check, f"{where}.checks[{position}]")
        for position, check in enumerate(_expect_list(d["checks"], "table checks"))
    )


def _dict_to_snapshot_trigger(value: object, where: str = "trigger") -> SnapshotTrigger:
    """Deserialize a dict to a SnapshotTrigger."""
    d = _TRIGGER_KEYS.read(value, where)
    return SnapshotTrigger(
        name=_expect_str(d["name"], "trigger name"),
        kind=_expect_str(d["kind"], "trigger kind") if "kind" in d else None,
        columns=tuple(str(c) for c in _expect_list(d["columns"], f"{where}.columns")),
        predicate=tree_from_data(d["predicate"]) if "predicate" in d else None,
    )


def _optional_triggers(d: dict[str, object], where: str) -> tuple[SnapshotTrigger, ...]:
    """Read the optional ``triggers`` key from a serialized table (absent: no triggers)."""
    if "triggers" not in d:
        return ()
    return tuple(
        _dict_to_snapshot_trigger(trigger, f"{where}.triggers[{position}]")
        for position, trigger in enumerate(_expect_list(d["triggers"], "table triggers"))
    )


def _dict_to_snapshot_table(value: object, where: str = "table") -> SnapshotTable:
    """Deserialize a dict to a SnapshotTable."""
    d = _TABLE_KEYS.read(value, where)
    fields_raw = _expect_dict(d["fields"], f"{where}.fields")
    indexes_raw = _expect_list(d["indexes"], f"{where}.indexes")
    fks_raw = _expect_list(d["foreign_keys"], f"{where}.foreign_keys")
    return SnapshotTable(
        table_name=str(d["table_name"]),
        fields={
            str(name): _dict_to_snapshot_column(col, f"{where}.fields[{name!r}]")
            for name, col in fields_raw.items()
        },
        indexes=tuple(
            _dict_to_snapshot_index(idx, f"{where}.indexes[{position}]")
            for position, idx in enumerate(indexes_raw)
        ),
        foreign_keys=tuple(
            _dict_to_snapshot_fk(fk, f"{where}.foreign_keys[{position}]")
            for position, fk in enumerate(fks_raw)
        ),
        table_options=dict(_expect_dict(d["table_options"], f"{where}.table_options")),
        comment=_optional_comment(d),
        checks=_optional_checks(d, where),
        triggers=_optional_triggers(d, where),
    )


def _dict_to_snapshot_enum(value: object, where: str = "enum") -> SnapshotEnum:
    """Deserialize a dict to a SnapshotEnum.

    A missing ``member_values`` key loads as the empty tuple, which
    :class:`SnapshotEnum` documents as UNRECORDED -- an enum a catalog reader
    read, whose database stores labels only.

    Raises:
        ValueError: If ``member_values`` is present but does not have one entry
            per member.  The two lists are positionally parallel, so a length
            mismatch would silently pair a member with another member's label.
    """
    d = _ENUM_KEYS.read(value, where)
    values = tuple(str(v) for v in _expect_list(d["values"], "enum values"))
    member_values: tuple[str | None, ...] = ()
    if "member_values" in d:
        member_values_raw = _expect_list(d["member_values"], "enum member_values")
        if len(member_values_raw) != len(values):
            raise ValueError(
                "Enum '%s' records %d member_values for %d values. They are "
                "positionally parallel, so every member needs exactly one entry "
                "(null where the member declares no value('...')). Re-generate "
                "the snapshot to rewrite it."
                % (d["name"], len(member_values_raw), len(values))
            )
        member_values = tuple(None if v is None else str(v) for v in member_values_raw)
    return SnapshotEnum(
        name=str(d["name"]),
        database_name=str(d["database_name"]),
        values=values,
        member_values=member_values,
    )


def _dict_to_tables(value: object, where: str) -> dict[str, SnapshotTable]:
    """Deserialize a name-to-table map."""
    return {
        str(name): _dict_to_snapshot_table(table, f"{where}[{name!r}]")
        for name, table in _expect_dict(value, where).items()
    }


def _dict_to_snapshot(value: dict[str, object]) -> RdbmsSchemaSnapshot:
    """Deserialize a dict to a RdbmsSchemaSnapshot.

    The format and version are checked before the keys, so a document of
    another format or version is named as such rather than by its keys. CruftFree
    reads one format at one version; a snapshot written by another CruftFree is
    regenerated, never read under rules it was not written by.
    """
    if "format" in value and value["format"] != SCHEMA_FORMAT:
        raise ValueError(
            f"Unsupported snapshot format: '{value['format']}'. "
            f"Expected '{SCHEMA_FORMAT}'. Fix: regenerate the snapshot with this CruftFree."
        )
    if "version" in value and value["version"] != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported snapshot version: {value['version']}. "
            f"Expected {SCHEMA_VERSION}. Fix: regenerate the snapshot with this CruftFree."
        )
    d = _SNAPSHOT_KEYS.read(value, "snapshot")
    service = _SERVICE_KEYS.read(d["service"], "service")
    container = _CONTAINER_KEYS.read(d["container"], "container")
    block = _BLOCK_KEYS.read(d["block"], "block")
    enums_raw = _expect_list(d["enums"], "enums")

    return RdbmsSchemaSnapshot(
        format=str(d["format"]),
        version=_expect_int(d["version"], "version"),
        rdbms_id=str(d["rdbms_id"]),
        service=SnapshotServiceIdentity(
            name=str(service["name"]),
            version=str(service["version"]) if service["version"] is not None else None,
        ),
        container=SnapshotContainerIdentity(
            name=str(container["name"]),
            kind=str(container["kind"]),
        ),
        block=SnapshotBlockIdentity(
            name=str(block["name"]),
        ),
        entities=_dict_to_tables(d["entities"], "entities"),
        cqrs_views=_dict_to_tables(d["cqrs_views"], "cqrs_views"),
        enums=tuple(
            _dict_to_snapshot_enum(e, f"enums[{position}]")
            for position, e in enumerate(enums_raw)
        ),
        schema_name=(
            str(d["schema_name"]) if d.get("schema_name") is not None else None
        ),
        audit_log_tables=_dict_to_tables(d.get("audit_log_tables", {}), "audit_log_tables"),
        junction_tables=_dict_to_tables(d.get("junction_tables", {}), "junction_tables"),
        framework_tables=_dict_to_tables(d.get("framework_tables", {}), "framework_tables"),
    )
