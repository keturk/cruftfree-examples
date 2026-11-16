"""Check constraint statements: a baseline's checks and the check change renderings.

A check's SQL is written from its lowered tree by the one SQL renderer
(:func:`~cruftfree_rdbms_schema.sql_lowering.render.render_sql`) for the block's DDL
dialect; nothing here spells a predicate. The check's name carries the digest of
that SQL (:mod:`cruftfree_rdbms_schema.definition_naming`), so the renderer proves the
SQL it writes is the definition the name was derived from: a name naming another
definition would make a live check of that name look declared when it is not.
"""

from __future__ import annotations

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotCheck,
    SnapshotTable,
)
from cruftfree_rdbms_schema.definition_naming import definition_digest
from cruftfree_rdbms_schema.differ import SchemaChange
from cruftfree_rdbms_schema.sql_lowering.render import render_sql

from cruftfree_codegen_kernel.sql_facts._revision_model import (
    SqlObjectKind,
    SqlStatement,
    SqlStatementKind,
)
from cruftfree_codegen_kernel.sql_facts._revision_statements import _RevisionContext
from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_change_lookup import (
    change_subject,
    snapshot_table_for,
)
from cruftfree_codegen_kernel.sql_facts.type_mappings import supported_ddl_dialect


def _check_predicate_sql(dialect: SQLDialect, table: SnapshotTable, check: SnapshotCheck) -> str:
    """*check*'s predicate as *dialect* writes it, from the tree the snapshot records.

    Raises:
        GenerationError: The check carries no tree (a live catalog reflected it, so
            its definition is unknown), the renderer refuses the tree, or the SQL's
            digest is not the one the check's name ends in.
    """
    if check.tree is None:
        raise GenerationError(
            "Check constraint '%s' of table '%s' carries no definition to create it "
            "from: the snapshot recording it was reflected from a live database, which "
            "records a check's name only. Expected: a check is created from the snapshot "
            "the DSL declares, which records its lowered tree. Fix: regenerate from the "
            "declared schema so the snapshot records the check's definition."
            % (check.name, table.table_name)
        )
    ddl_dialect = supported_ddl_dialect(dialect.name)
    try:
        sql = render_sql(check.tree, ddl_dialect)
    except (LookupError, TypeError, ValueError) as exc:
        raise GenerationError(
            "Check constraint '%s' of table '%s' cannot be written for the %s dialect: %s"
            % (check.name, table.table_name, ddl_dialect, exc)
        ) from exc
    digest = definition_digest(sql)
    if not check.name.endswith(digest):
        raise GenerationError(
            "Check constraint '%s' of table '%s' renders as %r for the %s dialect, whose "
            "digest is '%s', but the name ends in another digest: the name was derived "
            "from a different definition, so it no longer identifies this one. Expected: "
            "the snapshot names each check from the SQL this dialect writes for its tree. "
            "Fix: regenerate the snapshot for the block's engine."
            % (check.name, table.table_name, sql, ddl_dialect, digest)
        )
    return sql


def _add_check_statement(dialect: SQLDialect, table: SnapshotTable, check: SnapshotCheck) -> SqlStatement:
    """``ADD CONSTRAINT ... CHECK`` of *check* on *table*."""
    return SqlStatement(
        SqlStatementKind.ADD_CHECK_CONSTRAINT,
        SqlObjectKind.CONSTRAINT,
        check.name,
        table.table_name,
        dialect.render_add_check_constraint(
            check.name, table.table_name, _check_predicate_sql(dialect, table, check)
        ),
    )


def _add_check_statements(dialect: SQLDialect, table: SnapshotTable) -> list[SqlStatement]:
    """The creation of every check *table* declares, in the snapshot's (name) order."""
    return [_add_check_statement(dialect, table, check) for check in table.checks]


def _check_of_change(snapshot: RdbmsSchemaSnapshot, change: SchemaChange) -> tuple[SnapshotTable, SnapshotCheck]:
    """The table *snapshot* holds the change's check in, and the check, its subject."""
    table = snapshot_table_for(snapshot, change.entity, change.kind.value)
    return table, change_subject(change, SnapshotCheck)


def _render_check_added(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The creation of the added check from the tree the current snapshot records."""
    table, check = _check_of_change(ctx.current, change)
    return [_add_check_statement(ctx.dialect, table, check)]


def _render_check_removed(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The drop of the removed check under the name the previous snapshot records."""
    table, check = _check_of_change(ctx.previous_snapshot(change), change)
    return [
        SqlStatement(
            SqlStatementKind.DROP_CHECK_CONSTRAINT,
            SqlObjectKind.CONSTRAINT,
            check.name,
            table.table_name,
            ctx.dialect.render_drop_check_constraint(check.name, table.table_name),
        )
    ]
