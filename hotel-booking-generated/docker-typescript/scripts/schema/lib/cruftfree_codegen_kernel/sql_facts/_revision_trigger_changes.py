"""Trigger statements: a baseline's triggers and the trigger change renderings.

A trigger is the realization of a rule over a table's rows (append-only, an aggregate
invariant checked at commit). The snapshot records the rule; the block's dialect writes the
function and the triggers that call it (``SQLDialect.render_create_append_only_trigger`` and
its siblings), and nothing here spells SQL. The trigger's name carries the digest of the
rule's definition (:mod:`cruftfree_rdbms_schema.trigger_naming`), so the renderer proves the rule
it writes is the one the name was derived from: a name naming another definition would make
a live trigger of that name look declared when it is not.
"""

from __future__ import annotations

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotTable,
    SnapshotTrigger,
)
from cruftfree_rdbms_schema.definition_naming import definition_digest
from cruftfree_rdbms_schema.differ import SchemaChange
from cruftfree_rdbms_schema.sql_lowering.render import render_sql
from cruftfree_rdbms_schema.trigger_naming import (
    TRIGGER_AGGREGATE_INVARIANT,
    TRIGGER_APPEND_ONLY,
    trigger_definition,
)

from cruftfree_codegen_kernel.sql_facts._revision_model import (
    SqlObjectKind,
    SqlStatement,
    SqlStatementKind,
)
from cruftfree_codegen_kernel.sql_facts._revision_statements import _RevisionContext
from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    TriggerCreation,
    TriggerRemoval,
)
from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_change_lookup import (
    change_subject,
    snapshot_table_for,
)
from cruftfree_codegen_kernel.sql_facts.type_mappings import supported_ddl_dialect


def _predicate_sql(dialect: SQLDialect, table: SnapshotTable, trigger: SnapshotTrigger) -> str | None:
    """The condition an aggregate invariant checks, as *dialect* writes it; ``None`` for append-only.

    Raises:
        GenerationError: The invariant carries no condition (a live catalog reflected it,
            so its definition is unknown), or the renderer refuses it.
    """
    if trigger.kind is None:
        raise GenerationError(
            "Trigger '%s' of table '%s' carries no definition to create it from: the snapshot "
            "recording it was reflected from a live database, which records a trigger's name "
            "only. Expected: a trigger is created from the snapshot the DSL declares, which "
            "records its kind. Fix: regenerate from the declared schema so the snapshot "
            "records the trigger's definition." % (trigger.name, table.table_name)
        )
    if trigger.kind != TRIGGER_AGGREGATE_INVARIANT:
        return None
    if trigger.predicate is None:
        raise GenerationError(
            "Trigger '%s' of table '%s' carries no condition to create it from: the snapshot "
            "recording it was reflected from a live database, which records a trigger's name "
            "only. Expected: a trigger is created from the snapshot the DSL declares, which "
            "records its lowered condition. Fix: regenerate from the declared schema so the "
            "snapshot records the trigger's definition." % (trigger.name, table.table_name)
        )
    ddl_dialect = supported_ddl_dialect(dialect.name)
    try:
        return render_sql(trigger.predicate, ddl_dialect)
    except (LookupError, TypeError, ValueError) as exc:
        raise GenerationError(
            "Trigger '%s' of table '%s' cannot be written for the %s dialect: %s"
            % (trigger.name, table.table_name, ddl_dialect, exc)
        ) from exc


def _verified_predicate(dialect: SQLDialect, table: SnapshotTable, trigger: SnapshotTrigger) -> str | None:
    """The trigger's condition SQL, after proving its name ends in the digest of its definition.

    Raises:
        GenerationError: The name was derived from a different definition.
    """
    predicate_sql = _predicate_sql(dialect, table, trigger)
    definition = trigger_definition(trigger.kind, trigger.columns, predicate_sql)
    digest = definition_digest(definition)
    if not trigger.name.endswith(digest):
        raise GenerationError(
            "Trigger '%s' of table '%s' has the definition %r for the %s dialect, whose "
            "digest is '%s', but the name ends in another digest: the name was derived from "
            "a different definition, so it no longer identifies this one. Expected: the "
            "snapshot names each trigger from the definition this dialect writes for it. "
            "Fix: regenerate the snapshot for the block's engine."
            % (trigger.name, table.table_name, definition, dialect.name, digest)
        )
    return predicate_sql


def _creation(dialect: SQLDialect, table: SnapshotTable, trigger: SnapshotTrigger) -> TriggerCreation:
    """The dialect's creation of *trigger*'s rule on *table*."""
    predicate_sql = _verified_predicate(dialect, table, trigger)
    if trigger.kind == TRIGGER_APPEND_ONLY:
        return dialect.render_create_append_only_trigger(
            trigger.name, table.table_name, trigger.columns
        )
    if trigger.kind == TRIGGER_AGGREGATE_INVARIANT and predicate_sql is not None:
        return dialect.render_create_aggregate_invariant_trigger(
            trigger.name, table.table_name, trigger.columns, predicate_sql
        )
    raise GenerationError(
        "Trigger '%s' of table '%s' has the kind %r, which no dialect renders. Expected: one "
        "of %s." % (trigger.name, table.table_name, trigger.kind, [TRIGGER_APPEND_ONLY, TRIGGER_AGGREGATE_INVARIANT])
    )


def _removal(dialect: SQLDialect, table: SnapshotTable, trigger: SnapshotTrigger) -> TriggerRemoval:
    """The dialect's removal of *trigger*'s rule from *table*."""
    if trigger.kind == TRIGGER_APPEND_ONLY:
        return dialect.render_drop_append_only_trigger(trigger.name, table.table_name)
    if trigger.kind == TRIGGER_AGGREGATE_INVARIANT:
        return dialect.render_drop_aggregate_invariant_trigger(trigger.name, table.table_name)
    raise GenerationError(
        "Trigger '%s' of table '%s' has the kind %r, which no dialect renders. Expected: one "
        "of %s." % (trigger.name, table.table_name, trigger.kind, [TRIGGER_APPEND_ONLY, TRIGGER_AGGREGATE_INVARIANT])
    )


def _create_trigger_statements(
    dialect: SQLDialect, table: SnapshotTable, trigger: SnapshotTrigger
) -> list[SqlStatement]:
    """The function and the triggers that realize *trigger* on *table*, in the order they run."""
    creation = _creation(dialect, table, trigger)
    return [
        SqlStatement(
            SqlStatementKind.CREATE_TRIGGER_FUNCTION,
            SqlObjectKind.FUNCTION,
            trigger.name,
            table.table_name,
            creation.function,
        ),
        *(
            SqlStatement(
                SqlStatementKind.CREATE_TRIGGER,
                SqlObjectKind.TRIGGER,
                statement.name,
                table.table_name,
                statement.sql,
            )
            for statement in creation.triggers
        ),
    ]


def _add_trigger_statements(dialect: SQLDialect, table: SnapshotTable) -> list[SqlStatement]:
    """The creation of every trigger *table* declares, in the snapshot's (name) order."""
    return [
        statement
        for trigger in table.triggers
        for statement in _create_trigger_statements(dialect, table, trigger)
    ]


def _trigger_of_change(
    snapshot: RdbmsSchemaSnapshot, change: SchemaChange
) -> tuple[SnapshotTable, SnapshotTrigger]:
    """The table *snapshot* holds the change's trigger in, and the trigger, its subject."""
    table = snapshot_table_for(snapshot, change.entity, change.kind.value)
    return table, change_subject(change, SnapshotTrigger)


def _render_trigger_added(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The creation of the added trigger from the rule the current snapshot records."""
    table, trigger = _trigger_of_change(ctx.current, change)
    return _create_trigger_statements(ctx.dialect, table, trigger)


def _render_trigger_removed(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The drop of the removed trigger under the name the previous snapshot records."""
    table, trigger = _trigger_of_change(ctx.previous_snapshot(change), change)
    removal = _removal(ctx.dialect, table, trigger)
    return [
        *(
            SqlStatement(
                SqlStatementKind.DROP_TRIGGER,
                SqlObjectKind.TRIGGER,
                statement.name,
                table.table_name,
                statement.sql,
            )
            for statement in removal.triggers
        ),
        SqlStatement(
            SqlStatementKind.DROP_TRIGGER_FUNCTION,
            SqlObjectKind.FUNCTION,
            trigger.name,
            table.table_name,
            removal.function,
        ),
    ]
