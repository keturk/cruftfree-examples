"""Index, relationship and foreign key change rendering.

Every renderer reads the index or foreign key it acts on from the change's subject: an
addition's from the declared schema, a removal's and a rename's from the live catalog,
under the name the database holds it by.
"""

from __future__ import annotations

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import SnapshotForeignKey, SnapshotIndex
from cruftfree_rdbms_schema.differ import SchemaChange
from cruftfree_rdbms_schema.foreign_key_naming import realized_foreign_key_name
from cruftfree_rdbms_schema.index_naming import realized_index_name

from cruftfree_codegen_kernel.sql_facts._revision_columns import _statements
from cruftfree_codegen_kernel.sql_facts._revision_model import (
    SqlObjectKind,
    SqlStatement,
    SqlStatementKind,
)
from cruftfree_codegen_kernel.sql_facts._revision_statements import (
    _add_foreign_key_statements,
    _create_index_statements,
    _drop_index_statements,
    _enum_types_in_use,
    _RevisionContext,
    is_plain_unique,
)
from cruftfree_codegen_kernel.sql_facts.constants import (
    FEATURE_NAMED_ENUM_TYPES,
    FEATURE_RENAME_FOREIGN_KEY,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_change_lookup import (
    change_subject,
    snapshot_table_for,
)


def _held_name(
    change: SchemaChange, name: str | None, what: str, table_name: str
) -> str:
    """The name the live catalog holds the change's object under.

    Raises:
        GenerationError: The live catalog records no name for it, so no statement can
            name the object it acts on.
    """
    if name is None:
        raise GenerationError(
            "%s on table '%s' acts on %s the live catalog holds with no name, so no "
            "statement can name it. Expected: a catalog reader records every index's and "
            "foreign key's name. Fix: build the change from the live catalog as its reader "
            "parsed it." % (change.kind.value.upper(), table_name, what)
        )
    return name


def _declared_name(change: SchemaChange, table_name: str) -> str:
    """The name a rename or replacement gives its object, as the declared schema names it.

    Raises:
        GenerationError: The change carries no new name.
    """
    if change.new_value is None:
        raise GenerationError(
            "%s on table '%s' carries no new name. Expected: the name the declared schema "
            "gives the object. Fix: build the change through the snapshot differ."
            % (change.kind.value.upper(), table_name)
        )
    return change.new_value


def _render_index_added(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The creation of the added index under the name the declared schema records."""
    table = snapshot_table_for(ctx.current, change.entity, change.kind.value)
    index = change_subject(change, SnapshotIndex)
    return _create_index_statements(
        ctx.dialect, table.table_name, index, realized_index_name(table, index)
    )


def _render_index_removed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The drop of the removed index under the name the live catalog holds.

    The subject is the live catalog's own index, which records whether a constraint owns
    a unique index, so it decides the statement too.

    Raises:
        GenerationError: The live catalog holds the index with no name.
    """
    table = snapshot_table_for(
        ctx.previous_snapshot(change), change.entity, change.kind.value
    )
    index = change_subject(change, SnapshotIndex)
    name = _held_name(
        change, index.name, "an index on %s" % list(index.columns), table.table_name
    )
    return _drop_index_statements(ctx.dialect, table.table_name, index, name)


def _render_index_renamed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The rename of the index the live catalog holds to the name the declared schema gives it.

    The catalog records whether a constraint owns a unique index: a constraint's index is
    renamed, and the constraint with it (PostgreSQL renames the constraint an index
    backs together with the index); a unique index no constraint owns becomes its
    constraint under the new name.

    Raises:
        GenerationError: The held index has no name, or the change no new name.
    """
    dialect = ctx.dialect
    table = snapshot_table_for(
        ctx.previous_snapshot(change), change.entity, change.kind.value
    )
    held = change_subject(change, SnapshotIndex)
    old_name = _held_name(
        change, held.name, "an index on %s" % list(held.columns), table.table_name
    )
    name = _declared_name(change, table.table_name)
    if is_plain_unique(held) and not held.constraint_backed:
        sql = dialect.render_promote_unique_index(old_name, name, table.table_name)
    else:
        sql = dialect.render_rename_index(old_name, name, table.table_name)
    return _statements(
        SqlStatementKind.RENAME_INDEX,
        SqlObjectKind.INDEX,
        name,
        table.table_name,
        [sql],
    )


def _render_relationship_added(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The added foreign key, unvalidated then validated where the engine defers it."""
    table = snapshot_table_for(ctx.current, change.entity, change.kind.value)
    foreign_key = change_subject(change, SnapshotForeignKey)
    return _add_foreign_key_statements(
        ctx.dialect,
        table.table_name,
        realized_foreign_key_name(table, foreign_key),
        foreign_key,
        populated=True,
    )


def _drop_held_foreign_key(
    ctx: _RevisionContext, table_name: str, name: str
) -> list[SqlStatement]:
    """The drop of the foreign key the live catalog holds under *name*."""
    return _statements(
        SqlStatementKind.DROP_FOREIGN_KEY,
        SqlObjectKind.FOREIGN_KEY,
        name,
        table_name,
        ctx.dialect.render_drop_foreign_key(name, table_name),
    )


def _render_relationship_removed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The drop of the foreign key under the name the live catalog holds.

    Raises:
        GenerationError: The live catalog holds the key with no name.
    """
    table = snapshot_table_for(
        ctx.previous_snapshot(change), change.entity, change.kind.value
    )
    foreign_key = change_subject(change, SnapshotForeignKey)
    name = _held_name(
        change,
        foreign_key.name,
        "a foreign key on %s" % list(foreign_key.columns),
        table.table_name,
    )
    return _drop_held_foreign_key(ctx, table.table_name, name)


def _render_foreign_key_replaced(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The drop of the key under the name the live catalog holds, then the declared key added.

    Exactly the name the database holds is dropped (``old_value``); the declared key, the
    subject, is added under its declared name with its declared actions, validated over
    the rows the table holds.

    Raises:
        GenerationError: The change carries no held name.
    """
    table = snapshot_table_for(ctx.current, change.entity, change.kind.value)
    foreign_key = change_subject(change, SnapshotForeignKey)
    old_name = _held_name(
        change,
        change.old_value,
        "a foreign key on %s" % list(foreign_key.columns),
        table.table_name,
    )
    name = realized_foreign_key_name(table, foreign_key)
    return [
        *_drop_held_foreign_key(ctx, table.table_name, old_name),
        *_add_foreign_key_statements(
            ctx.dialect, table.table_name, name, foreign_key, populated=True
        ),
    ]


def _render_foreign_key_renamed(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The key the live catalog holds, renamed to the name the declared schema gives it.

    A dialect that renames no constraint drops the key under the old name and adds it,
    validated, under the new one.

    Raises:
        GenerationError: The held key has no name, or the change no new name.
    """
    dialect = ctx.dialect
    table = snapshot_table_for(
        ctx.previous_snapshot(change), change.entity, change.kind.value
    )
    held = change_subject(change, SnapshotForeignKey)
    old_name = _held_name(
        change, held.name, "a foreign key on %s" % list(held.columns), table.table_name
    )
    name = _declared_name(change, table.table_name)
    if dialect.supports_feature(FEATURE_RENAME_FOREIGN_KEY):
        return _statements(
            SqlStatementKind.RENAME_FOREIGN_KEY,
            SqlObjectKind.FOREIGN_KEY,
            name,
            table.table_name,
            [dialect.rename_foreign_key_sql(old_name, name, table.table_name)],
        )
    return [
        *_drop_held_foreign_key(ctx, table.table_name, old_name),
        *_add_foreign_key_statements(
            dialect, table.table_name, name, held, populated=True
        ),
    ]


def _render_schema_relocated(
    ctx: _RevisionContext, change: SchemaChange
) -> list[SqlStatement]:
    """The move of every enum type and table the database holds into the new schema.

    A relocation is about the whole block, so it has no subject: the objects moved are
    the ones the live catalog records and the declared schema keeps -- a table this
    revision creates is created in the new schema (the prelude creates it and puts it on
    the search path), and one it drops is gone. The new schema itself is created by the
    incremental prelude.
    """
    previous = ctx.previous_snapshot(change)
    kept_tables = {t.table_name for t in ctx.current.declared_tables().values()}
    tables = [
        t.table_name
        for t in previous.declared_tables().values()
        if t.table_name in kept_tables
    ]
    enum_types: list[str] = []
    if ctx.dialect.supports_feature(FEATURE_NAMED_ENUM_TYPES):
        used = _enum_types_in_use(previous) & _enum_types_in_use(ctx.current)
        enum_types = sorted(e.database_name for e in previous.enums if e.name in used)
    sqls = ctx.dialect.render_relocate_schema(
        change.old_value, change.new_value, enum_types, tables
    )
    objects = [
        *((SqlObjectKind.ENUM_TYPE, name, None) for name in enum_types),
        *((SqlObjectKind.TABLE, name, name) for name in tables),
    ]
    if len(sqls) != len(objects):
        raise GenerationError(
            "The %s dialect rendered %d relocation statements for %d objects (%d enum "
            "types, %d tables). Expected: one statement per enum type and table."
            % (ctx.dialect.name, len(sqls), len(objects), len(enum_types), len(tables))
        )
    statements: list[SqlStatement] = []
    for (object_kind, name, table_name), sql in zip(objects, sqls, strict=True):
        statements.extend(
            _statements(
                SqlStatementKind.RELOCATE_SCHEMA, object_kind, name, table_name, [sql]
            )
        )
    return statements
