"""The statements a generator obtains from a dialect, failing closed for a dialect without them."""

from __future__ import annotations

from cruftfree_common.errors.generation import GenerationError

from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    ExternalQueueControlSql,
    ScheduledJobStateSql,
    SessionLockSql,
    WorkRecoverySql,
    WorkRecoveryUpdate,
)
from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect


# @canonical(sql/session-lock): The one way a generator obtains a dialect session-lock statement
# @rule: Callers never build lock SQL; the dialect derives its engine identifier from the text key
# @rule: A dialect without session_lock_sql fails generation closed, never migrates unlocked
def session_lock_for(dialect: SQLDialect, key: str) -> SessionLockSql:
    """The session-lock statements *dialect* declares for the text *key*.

    Raises:
        GenerationError: *dialect* declares no ``session_lock_sql``, or *key* is
            empty. Running without the lock would let concurrent runs race the work
            it serializes, so generation stops instead.
    """
    if not key:
        raise GenerationError(
            "A session lock needs a non-empty key (the block or the work it serializes)."
        )
    method = getattr(dialect, "session_lock_sql", None)
    if method is None:
        raise GenerationError(
            f"The {dialect.name} SQL dialect declares no session_lock_sql, so the work "
            "it serves (a schema converge, a startup seed, a scheduled job) cannot run under its lock. "
            "Implement session_lock_sql(key) on the dialect (a session-scoped advisory "
            "lock), or use a dialect that has one: postgresql."
        )
    return method(key)


# @canonical(sql/scheduled-job-state): The one way a generator obtains the in-process job-state statements
# @rule: Callers never spell the job-state DDL or upsert; the dialect owns column types and conflict syntax
# @rule: A dialect without scheduled_job_state_sql fails generation closed, never schedules without durable state
def scheduled_job_state_for(dialect: SQLDialect) -> ScheduledJobStateSql:
    """The scheduled-job state statements *dialect* declares.

    Raises:
        GenerationError: *dialect* declares no ``scheduled_job_state_sql``. A
            scheduler without its durable last-fire record would lose every
            occurrence missed while the process was down, so generation stops.
    """
    method = getattr(dialect, "scheduled_job_state_sql", None)
    if method is None:
        raise GenerationError(
            f"The {dialect.name} SQL dialect declares no scheduled_job_state_sql, so "
            "an in-process scheduled job on it has no durable last-fire record. "
            "Implement scheduled_job_state_sql() on the dialect, or use a dialect "
            "that has one: postgresql."
        )
    return method()


# @canonical(sql/external-queue-control): The one way a generator obtains the external-queue control statements
# @rule: No language spells the control tables' DDL, upserts or state ranking; the dialect owns them
# @rule: A dialect without external_queue_control_sql fails generation closed, never controls a consumer per process
def external_queue_control_for(dialect: SQLDialect) -> ExternalQueueControlSql:
    """The external-queue control statements *dialect* declares.

    Raises:
        GenerationError: *dialect* declares no ``external_queue_control_sql``.
            Without the durable control record a ``start()`` or ``stop()`` would
            act on one process only, so generation stops.
    """
    method = getattr(dialect, "external_queue_control_sql", None)
    if method is None:
        raise GenerationError(
            f"The {dialect.name} SQL dialect declares no external_queue_control_sql, so "
            "an external-queue consumer stored on it has no durable desired state. "
            "Implement external_queue_control_sql() on the dialect, or use a dialect "
            "that has one: postgresql."
        )
    return method()


# @canonical(sql/work-recovery): The one way a generator obtains the startup work-recovery statements
# @rule: Callers never spell the recovery UPDATE or its lock timeout; the dialect owns both
# @rule: A dialect without work_recovery_sql fails generation closed, never emits another engine's SQL
def work_recovery_for(
    dialect: SQLDialect, update: WorkRecoveryUpdate
) -> WorkRecoverySql:
    """The startup work-recovery statements *dialect* declares for *update*.

    Raises:
        GenerationError: *dialect* declares no ``work_recovery_sql``, *update*
            names no in-flight label, or its lock timeout is not positive. A
            recovery spelled for another engine would fail at every startup, and
            one without a bounded lock wait could stall startup indefinitely, so
            generation stops instead.
    """
    if not update.in_flight_labels:
        raise GenerationError(
            f"The work recovery of {update.table} names no in-flight state, so it would "
            "relabel nothing. Declare at least one inFlight member in its work { } block."
        )
    if update.lock_timeout_seconds <= 0:
        raise GenerationError(
            f"The work recovery of {update.table} has lock timeout "
            f"{update.lock_timeout_seconds}s; it needs a positive bound so a stale row "
            "lock cannot stall startup."
        )
    method = getattr(dialect, "work_recovery_sql", None)
    if method is None:
        raise GenerationError(
            f"The {dialect.name} SQL dialect declares no work_recovery_sql, so an entity "
            "declaring work { onOrphan: failAtStartup; } on it has no startup recovery. "
            "Implement work_recovery_sql(update) on the dialect, or use a dialect that "
            "has one: postgresql."
        )
    return method(update)
