"""Enum snapshots and column definitions."""

from __future__ import annotations

from collections.abc import Iterable

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotColumn,
    SnapshotEnum,
    SnapshotTable,
)
from cruftfree_rdbms_schema.schema_snapshot import stored_enum_labels

from cruftfree_codegen_kernel.sql_facts._revision_literals import (
    _default_sql,
    _enum_labels,
)
from cruftfree_codegen_kernel.sql_facts._revision_model import (
    _ENUM_TYPE_KIND,
    SqlObjectKind,
    SqlStatement,
    SqlStatementKind,
)
from cruftfree_codegen_kernel.sql_facts.column_facts import (
    AUTO_INCREMENT_BASE_TYPES,
    ColumnDefinition,
)
from cruftfree_codegen_kernel.sql_facts.constants import (
    FEATURE_NAMED_ENUM_TYPES,
)
from cruftfree_codegen_kernel.sql_facts.dialects.base import (
    SQLDialect,
)
from cruftfree_codegen_kernel.sql_facts.enum_member_change import (
    inline_enum_type_sql,
)
from cruftfree_codegen_kernel.sql_facts.type_mappings import (
    SNAPSHOT_SQL_TYPE_MAP,
    sized_sql_type,
)


def _require_renderable_enum(
    snapshot: RdbmsSchemaSnapshot,
    snap_enum: SnapshotEnum,
    column: SnapshotColumn,
    table_name: str,
) -> None:
    """Refuse the enum *column* is typed with when no statement can realize it.

    Raises:
        GenerationError: The enum declares no members (its type could hold no row,
            and an inline-enum engine rejects an empty label list), or *snapshot*
            cannot say which label a member of one of its enums is stored as (the
            wrapped message names that enum). Each names the column and table that
            need the enum.
    """
    if not snap_enum.values:
        raise GenerationError(
            "Enum '%s' types column '%s' of table '%s' but declares no members, so the "
            "type the revision would create could hold no row. Expected: an enum "
            "declares at least one member. Fix: declare the enum's members in the .cfree "
            "source and regenerate." % (snap_enum.name, column.column_name, table_name)
        )
    try:
        stored_enum_labels(snapshot)
    except ValueError as exc:
        raise GenerationError(
            "Column '%s' of table '%s' is typed with enum '%s', but the snapshot's enum "
            "labels cannot be rendered: %s"
            % (column.column_name, table_name, snap_enum.name, exc)
        ) from exc


def _snapshot_enum(
    snapshot: RdbmsSchemaSnapshot, column: SnapshotColumn, table_name: str
) -> SnapshotEnum:
    """The block-level enum *column* is typed with.

    Raises:
        GenerationError: *snapshot* declares no such enum, or the enum cannot be
            rendered (see :func:`_require_renderable_enum`).
    """
    for snap_enum in snapshot.enums:
        if snap_enum.name == column.type.name:
            _require_renderable_enum(snapshot, snap_enum, column, table_name)
            return snap_enum
    raise GenerationError(
        "Enum '%s' types column '%s' of table '%s' but is not among the enums the "
        "snapshot declares (%s), so the revision cannot name the type or its labels. "
        "Fix: regenerate so the snapshot records the enum."
        % (
            column.type.name,
            column.column_name,
            table_name,
            sorted(e.name for e in snapshot.enums),
        )
    )


def _column_base_type(
    dialect: SQLDialect, snapshot: RdbmsSchemaSnapshot, table_name: str, column: SnapshotColumn
) -> str:
    """*column*'s SQL type: its enum's named type or inline labels, or its sized scalar type."""
    if column.type.kind == _ENUM_TYPE_KIND:
        snap_enum = _snapshot_enum(snapshot, column, table_name)
        if dialect.supports_feature(FEATURE_NAMED_ENUM_TYPES):
            return dialect.quote_identifier(snap_enum.database_name)
        return inline_enum_type_sql(dialect, _enum_labels(snapshot)[snap_enum.name])
    return sized_sql_type(
        column.type.name,
        dialect.name,
        max_length=column.storage.max_length,
        precision=column.storage.precision,
        scale=column.storage.scale,
        type_map=SNAPSHOT_SQL_TYPE_MAP,
    )


def _is_auto_increment(table: SnapshotTable, column: SnapshotColumn, base_type: str) -> bool:
    """Whether *column* is its table's sole integer primary key, numbered by the database."""
    primary_keys = [c for c in table.fields.values() if c.primary_key]
    return (
        column.primary_key
        and len(primary_keys) == 1
        and base_type.upper() in AUTO_INCREMENT_BASE_TYPES
    )


def _column_definition(
    dialect: SQLDialect,
    snapshot: RdbmsSchemaSnapshot,
    table: SnapshotTable,
    column: SnapshotColumn,
    *,
    created: bool,
) -> ColumnDefinition:
    """*column*'s whole definition: type, nullability, default and comment.

    A created column (``CREATE TABLE``, ``ADD COLUMN``) that the database numbers
    takes the dialect's auto-increment type; a restated one (``ALTER COLUMN``,
    ``MODIFY COLUMN``) keeps its base type and the dialect's auto-increment suffix,
    so a restatement never drops the numbering. A numbered column carries no default.
    """
    base_type = _column_base_type(dialect, snapshot, table.table_name, column)
    auto_increment = _is_auto_increment(table, column, base_type)
    sql_type = dialect.auto_increment_type(base_type) if auto_increment and created else base_type
    default = None
    if column.default is not None and not auto_increment:
        default = _default_sql(table.table_name, column, dialect)
    return ColumnDefinition(
        name=column.column_name,
        sql_type=sql_type,
        nullable=column.nullable,
        default=default,
        auto_increment=auto_increment,
        comment=column.comment,
    )


def _definition_text(definition: ColumnDefinition) -> str:
    """*definition* without its name and comment: what a comment restatement keeps."""
    parts = [definition.sql_type]
    if not definition.nullable:
        parts.append("NOT NULL")
    if definition.default is not None:
        parts.append("DEFAULT %s" % definition.default)
    return " ".join(parts)


# -- Statements -----------------------------------------------------------------


def _statements(
    kind: SqlStatementKind,
    object_kind: SqlObjectKind,
    object_name: str,
    table: str | None,
    sqls: Iterable[str],
) -> list[SqlStatement]:
    """One :class:`SqlStatement` per non-empty SQL text: an empty text is no statement."""
    return [SqlStatement(kind, object_kind, object_name, table, sql) for sql in sqls if sql]
