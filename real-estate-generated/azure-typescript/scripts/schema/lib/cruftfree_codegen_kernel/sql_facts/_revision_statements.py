"""Revision context, enum types, schema prelude and table statements."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotColumn,
    SnapshotEnum,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotTable,
)
from cruftfree_rdbms_schema.differ import SchemaChange
from cruftfree_rdbms_schema.index_naming import realized_index_name, unique_constraint_name

from cruftfree_codegen_kernel.sql_facts._revision_columns import (
    _column_definition,
    _snapshot_enum,
    _statements,
)
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
from cruftfree_codegen_kernel.sql_facts.constants import (
    FEATURE_NAMED_ENUM_TYPES,
    FEATURE_SCHEMA_NAMESPACES,
)
from cruftfree_codegen_kernel.sql_facts.dialects.base import (
    SQLDialect,
)
from cruftfree_codegen_kernel.sql_facts.enum_member_change import (
    DefaultSqlOf,
    EnumColumn,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_change_lookup import (
    change_subject,
    snapshot_table_for,
)


@dataclass
class _RevisionContext:
    """The snapshots a rendering reads, and the enum types it has created.

    Attributes:
        current: The snapshot the statements bring the database to (``D``).
        previous: The live catalog the database holds (``L``), ``None`` for a whole
            schema rendered from empty.
        dialect: The block's SQL dialect.
        existing_enum_types: Enums a column of *previous* is typed with -- types the
            database already holds.
        created_enum_types: Enums this rendering has created so far, so each type is
            created once.
        added_enum_labels: The stored labels this rendering has added so far, by enum
            name, so each later addition is placed beside a label the type holds.
    """

    current: RdbmsSchemaSnapshot
    previous: RdbmsSchemaSnapshot | None
    dialect: SQLDialect
    existing_enum_types: frozenset[str]
    created_enum_types: set[str] = field(default_factory=set)
    added_enum_labels: dict[str, set[str]] = field(default_factory=dict)

    def previous_snapshot(self, change: SchemaChange) -> RdbmsSchemaSnapshot:
        """The live catalog, which records what a removal or relocation is about.

        Raises:
            GenerationError: The rendering has no live catalog.
        """
        if self.previous is None:
            raise GenerationError(
                "A %s change needs the live catalog, which records the object it removes "
                "or moves, but the rendering has none. Expected: a change is rendered "
                "against the live catalog it was computed from." % change.kind.value
            )
        return self.previous


def _enum_types_in_use(snapshot: RdbmsSchemaSnapshot) -> frozenset[str]:
    """The enums some column of *snapshot*'s tables is typed with."""
    return frozenset(
        column.type.name
        for table in snapshot.declared_tables().values()
        for column in table.fields.values()
        if column.type.kind == _ENUM_TYPE_KIND
    )


def _enum_type_statements(
    ctx: _RevisionContext, columns: Iterable[tuple[str, SnapshotColumn]]
) -> list[SqlStatement]:
    """The creation of each named enum type *columns* use that the database lacks, once.

    Ordered by enum name, so a revision's bytes do not depend on iteration order;
    nothing on an inline-enum engine.
    """
    if not ctx.dialect.supports_feature(FEATURE_NAMED_ENUM_TYPES):
        return []
    needed: dict[str, SnapshotEnum] = {}
    for table_name, column in columns:
        if column.type.kind == _ENUM_TYPE_KIND:
            needed[column.type.name] = _snapshot_enum(ctx.current, column, table_name)
    missing = sorted(needed.keys() - ctx.existing_enum_types - ctx.created_enum_types)
    if not missing:
        return []
    labels = _enum_labels(ctx.current)
    statements: list[SqlStatement] = []
    for name in missing:
        database_name = needed[name].database_name
        ctx.created_enum_types.add(name)
        statements.extend(
            _statements(
                SqlStatementKind.CREATE_ENUM_TYPE,
                SqlObjectKind.ENUM_TYPE,
                database_name,
                None,
                [ctx.dialect.render_create_enum_type(database_name, labels[name])],
            )
        )
    return statements


def _schema_prelude(ctx: _RevisionContext, *, create: bool) -> list[SqlStatement]:
    """The statements pointing the revision at the block's schema; none without one."""
    schema = ctx.current.schema_name
    if schema is None or not ctx.dialect.supports_feature(FEATURE_SCHEMA_NAMESPACES):
        return []
    statements: list[SqlStatement] = []
    if create:
        statements.extend(
            _statements(
                SqlStatementKind.CREATE_SCHEMA,
                SqlObjectKind.SCHEMA,
                schema,
                None,
                [ctx.dialect.render_create_schema(schema)],
            )
        )
    statements.extend(
        _statements(
            SqlStatementKind.SET_SEARCH_PATH,
            SqlObjectKind.SCHEMA,
            schema,
            None,
            [ctx.dialect.render_set_search_path(schema)],
        )
    )
    return statements


def _create_table_statements(ctx: _RevisionContext, table: SnapshotTable) -> list[SqlStatement]:
    """``CREATE TABLE`` for *table*, its columns and primary key; keys and indexes follow."""
    dialect = ctx.dialect
    columns = [
        _column_definition(dialect, ctx.current, table, column, created=True)
        for column in table.fields.values()
    ]
    primary_keys = [c.column_name for c in table.fields.values() if c.primary_key]
    constraints = (
        ("PRIMARY KEY (%s)" % ", ".join(dialect.quote_identifier(c) for c in primary_keys),)
        if primary_keys
        else ()
    )
    return _statements(
        SqlStatementKind.CREATE_TABLE,
        SqlObjectKind.TABLE,
        table.table_name,
        table.table_name,
        [dialect.render_create_table(table.table_name, columns, constraints, comment=table.comment)],
    )


def _column_unique_statements(ctx: _RevisionContext, table: SnapshotTable) -> list[SqlStatement]:
    """The ``uq_`` constraint of every ``: unique`` column of a created *table*.

    A column whose constraint name is already the name of one of the table's
    declared indexes is created by that index.
    """
    index_names = {realized_index_name(table, index) for index in table.indexes}
    statements: list[SqlStatement] = []
    for column in table.fields.values():
        if not column.unique or column.primary_key:
            continue
        name = unique_constraint_name(table.table_name, [column.column_name])
        if name in index_names:
            continue
        statements.extend(
            _statements(
                SqlStatementKind.ADD_UNIQUE_CONSTRAINT,
                SqlObjectKind.CONSTRAINT,
                name,
                table.table_name,
                [ctx.dialect.render_add_unique_constraint(name, table.table_name, (column.column_name,))],
            )
        )
    return statements


def _standalone_comment_statements(
    ctx: _RevisionContext, table: SnapshotTable
) -> list[SqlStatement]:
    """The comments of a created *table* the dialect does not carry inside ``CREATE TABLE``."""
    dialect = ctx.dialect
    table_name = table.table_name
    statements: list[SqlStatement] = []
    if table.comment is not None and dialect.inline_table_comment(table.comment) == "":
        statements.extend(
            _statements(
                SqlStatementKind.SET_COMMENT,
                SqlObjectKind.TABLE,
                table_name,
                table_name,
                [dialect.render_table_comment(table_name, table.comment)],
            )
        )
    for column in table.fields.values():
        if column.comment is None or dialect.inline_column_comment(column.comment) != "":
            continue
        statements.extend(
            _statements(
                SqlStatementKind.SET_COMMENT,
                SqlObjectKind.COLUMN,
                column.column_name,
                table_name,
                [dialect.render_column_comment(table_name, column.column_name, "", column.comment)],
            )
        )
    return statements


def is_plain_unique(index: SnapshotIndex) -> bool:
    """Whether *index* is a declared unique, which the database holds as a constraint."""
    return index.unique and not index.fulltext and not index.spatial


def _plain_index_sql(
    dialect: SQLDialect, table_name: str, columns: tuple[str, ...], name: str
) -> str:
    """``CREATE INDEX`` of a plain (b-tree) index."""
    return "CREATE INDEX %s ON %s (%s);" % (
        dialect.quote_identifier(name),
        dialect.quote_identifier(table_name),
        ", ".join(dialect.quote_identifier(c) for c in columns),
    )


def _create_index_statements(
    dialect: SQLDialect, table_name: str, index: SnapshotIndex, name: str
) -> list[SqlStatement]:
    """The creation of *index* under *name*: fulltext, spatial, unique constraint or plain index."""
    columns = tuple(index.columns)
    if is_plain_unique(index):
        return _statements(
            SqlStatementKind.ADD_UNIQUE_CONSTRAINT,
            SqlObjectKind.CONSTRAINT,
            name,
            table_name,
            [dialect.render_add_unique_constraint(name, table_name, columns)],
        )
    if index.spatial:
        sql = dialect.render_spatial_index(name, table_name, columns)
    elif index.fulltext:
        sql = dialect.render_fulltext_index(name, table_name, columns)
    else:
        sql = _plain_index_sql(dialect, table_name, columns, name)
    return _statements(SqlStatementKind.CREATE_INDEX, SqlObjectKind.INDEX, name, table_name, [sql])


def _drop_index_statements(
    dialect: SQLDialect, table_name: str, index: SnapshotIndex, name: str
) -> list[SqlStatement]:
    """The drop of *index* named *name*: a unique a constraint owns is dropped as that constraint.

    A unique index no constraint owns (``constraint_backed`` false, as a live catalog
    reports one created on its own) is dropped as an index.
    """
    if is_plain_unique(index) and index.constraint_backed:
        return _statements(
            SqlStatementKind.DROP_UNIQUE_CONSTRAINT,
            SqlObjectKind.CONSTRAINT,
            name,
            table_name,
            [dialect.render_drop_unique_constraint(name, table_name)],
        )
    return _statements(
        SqlStatementKind.DROP_INDEX,
        SqlObjectKind.INDEX,
        name,
        table_name,
        [dialect.render_drop_index(name, table_name)],
    )


def _add_foreign_key_statements(
    dialect: SQLDialect,
    table_name: str,
    name: str,
    foreign_key: SnapshotForeignKey,
    *,
    populated: bool,
) -> list[SqlStatement]:
    """The addition of *foreign_key* under *name*, with the actions the snapshot records.

    On a table that may hold rows (*populated*) the key is added unvalidated and then
    validated where the engine defers validation; an engine that checks the rows on
    add renders no validation statement.
    """
    statements = _statements(
        SqlStatementKind.ADD_FOREIGN_KEY,
        SqlObjectKind.FOREIGN_KEY,
        name,
        table_name,
        [
            dialect.render_add_foreign_key(
                name,
                table_name,
                tuple(foreign_key.columns),
                foreign_key.referred_table,
                tuple(foreign_key.referred_columns),
                foreign_key.on_delete,
                foreign_key.on_update,
                not_valid=populated,
            )
        ],
    )
    if populated:
        statements.extend(
            _statements(
                SqlStatementKind.VALIDATE_FOREIGN_KEY,
                SqlObjectKind.FOREIGN_KEY,
                name,
                table_name,
                [dialect.render_validate_foreign_key(name, table_name)],
            )
        )
    return statements


def _column_restatements(
    kind: SqlStatementKind, columns: Sequence[EnumColumn], sqls: Sequence[str]
) -> list[SqlStatement]:
    """One statement per enum-typed column, each restating or updating that column."""
    if len(columns) != len(sqls):
        raise GenerationError(
            "An enum change rendered %d statements for %d columns typed with the enum. "
            "Expected: one statement per column." % (len(sqls), len(columns))
        )
    statements: list[SqlStatement] = []
    for ref, sql in zip(columns, sqls, strict=True):
        statements.extend(
            _statements(kind, SqlObjectKind.COLUMN, ref.column.column_name, ref.table_name, [sql])
        )
    return statements


def _enum_default_of(ctx: _RevisionContext) -> DefaultSqlOf:
    """The default an inline-enum restatement keeps, per column, from the current snapshot."""

    def default_sql_of(ref: EnumColumn) -> str | None:
        if ref.column.default is None:
            return None
        return _default_sql(ref.table_name, ref.column, ctx.dialect)

    return default_sql_of


# -- One renderer per change kind ---------------------------------------------


def _changed_column(
    snapshot: RdbmsSchemaSnapshot, change: SchemaChange
) -> tuple[SnapshotTable, SnapshotColumn]:
    """The table *snapshot* holds the change's column in, and the column, the change's subject."""
    table = snapshot_table_for(snapshot, change.entity, change.kind.value)
    return table, change_subject(change, SnapshotColumn)
