"""Session lock, scheduled job state, external-queue control, index rename and enum label change facts, and the statement reader."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


@dataclass(frozen=True, slots=True)
class SessionLockSql:
    """The statements that take and release one engine-level, session-scoped lock.

    Each statement is a complete ``SELECT`` that returns one scalar. The lock is
    held by the database session that took it and is released when that session
    ends, so a crashed holder never strands it. The two conditions are the boolean
    expressions ``try_acquire`` and ``release`` select, for a guard that stops a
    client when the lock is not taken or not released.
    """

    try_acquire: str
    """Take the lock if it is free; the scalar equals ``acquired_value`` on success."""

    acquire: str
    """Wait for the lock; returns once it is held."""

    release: str
    """Release the lock this session holds."""

    acquired_value: bool | int
    """The scalar ``try_acquire`` returns when the lock was obtained."""

    try_acquire_condition: str
    """Takes the lock if it is free, without waiting; true when this session now holds it."""

    release_condition: str
    """Releases the lock; true when this session held it."""


@dataclass(frozen=True, slots=True)
class TriggerStatement:
    """One ``CREATE TRIGGER`` or ``DROP TRIGGER`` statement and the trigger it is about."""

    name: str
    """The trigger's name on its table."""

    sql: str
    """The statement."""


@dataclass(frozen=True, slots=True)
class TriggerCreation:
    """The statements that realize one table rule, in the order they run.

    A rule is realized as a function and the triggers that call it; the function is
    created first.
    """

    function: str
    """The ``CREATE FUNCTION`` statement."""

    triggers: tuple[TriggerStatement, ...]
    """The ``CREATE TRIGGER`` statements."""


@dataclass(frozen=True, slots=True)
class TriggerRemoval:
    """The statements that remove one table rule, in the order they run.

    The triggers are dropped first, then the function they call.
    """

    triggers: tuple[TriggerStatement, ...]
    """The ``DROP TRIGGER`` statements."""

    function: str
    """The ``DROP FUNCTION`` statement."""


#: The framework-owned table that records each in-process scheduled job's last fire.
SCHEDULED_JOB_STATE_TABLE = "cruftfree_scheduled_job_state"

#: The columns of :data:`SCHEDULED_JOB_STATE_TABLE`: the job's identity (the primary
#: key) and the UTC instant of its last fire.
JOB_STATE_COLUMN_JOB_ID = "job_id"
JOB_STATE_COLUMN_LAST_FIRE_TIME = "last_fire_time"

#: Named placeholders every :class:`ScheduledJobStateSql` statement binds. A language
#: renders them in its driver's parameter style.
JOB_STATE_PARAM_JOB_ID = "job_id"
JOB_STATE_PARAM_FIRE_TIME = "fire_time"


@dataclass(frozen=True, slots=True)
class ScheduledJobStateSql:
    """The statements over the durable last-fire table of in-process scheduled jobs.

    The table is part of the block's declared schema, which the deploy's schema
    converge creates under the owner login; a service holds data rights only and
    runs no DDL. The statements bind the named placeholders
    :data:`JOB_STATE_PARAM_JOB_ID` (``:job_id``) and
    :data:`JOB_STATE_PARAM_FIRE_TIME` (``:fire_time``, a UTC instant).
    """

    select_last_fire: str
    """Returns the job's last fire time as one scalar, or no row."""

    insert_if_absent: str
    """Records a baseline fire time only when the job has none."""

    upsert_fire: str
    """Records the fire time, replacing any earlier one."""

    stores_naive_utc: bool
    """True when the column has no timezone: the writer binds a UTC instant as a naive
    value and the reader attaches UTC. False when the column is timezone-aware."""


#: Named placeholders the :class:`ExternalQueueControlSql` statements bind. A language
#: renders them in its driver's parameter style.
EXTERNAL_QUEUE_PARAM_BLOCK = "block"
EXTERNAL_QUEUE_PARAM_DESIRED_STATE = "desired_state"
EXTERNAL_QUEUE_PARAM_DEFAULT_DESIRED = "default_desired"
EXTERNAL_QUEUE_PARAM_INSTANCE_ID = "instance_id"
EXTERNAL_QUEUE_PARAM_STATE = "state"
EXTERNAL_QUEUE_PARAM_LAST_ERROR = "last_error"

#: Every placeholder an :class:`ExternalQueueControlSql` statement may bind.
EXTERNAL_QUEUE_CONTROL_PARAMS: frozenset[str] = frozenset({
    EXTERNAL_QUEUE_PARAM_BLOCK,
    EXTERNAL_QUEUE_PARAM_DESIRED_STATE,
    EXTERNAL_QUEUE_PARAM_DEFAULT_DESIRED,
    EXTERNAL_QUEUE_PARAM_INSTANCE_ID,
    EXTERNAL_QUEUE_PARAM_STATE,
    EXTERNAL_QUEUE_PARAM_LAST_ERROR,
})

#: Each placeholder under the constant name a language's control runtime declares it by.
EXTERNAL_QUEUE_CONTROL_PARAM_CONSTANTS: dict[str, str] = {
    "PARAM_BLOCK": EXTERNAL_QUEUE_PARAM_BLOCK,
    "PARAM_DESIRED_STATE": EXTERNAL_QUEUE_PARAM_DESIRED_STATE,
    "PARAM_DEFAULT_DESIRED": EXTERNAL_QUEUE_PARAM_DEFAULT_DESIRED,
    "PARAM_INSTANCE_ID": EXTERNAL_QUEUE_PARAM_INSTANCE_ID,
    "PARAM_STATE": EXTERNAL_QUEUE_PARAM_STATE,
    "PARAM_LAST_ERROR": EXTERNAL_QUEUE_PARAM_LAST_ERROR,
}


@dataclass(frozen=True, slots=True)
class ExternalQueueControlSql:
    """The statements over the durable control tables of external-queue consumers.

    One table holds each block's desired state, the other one row per process
    hosting the block's consumer. Every timestamp is the database clock, so the
    clocks of the processes never matter. Each statement binds only the named
    placeholders listed on it. None creates a table: both are tables of the store
    block's declared schema
    (:func:`~cruftfree_codegen_kernel.sql_facts.external_queue_control_tables.external_queue_control_tables`),
    created by the deploy's schema converge, and a service holds data rights only.
    """

    seed_default: str
    """Writes the authored default (``:block``, ``:desired_state``) with origin ``default``
    where the block has no row or its row's origin is ``default``; a row a call wrote
    is left unchanged."""

    set_desired: str
    """Writes ``:desired_state`` for ``:block`` with origin ``call``, replacing any row."""

    select_desired: str
    """Returns ``:block``'s desired state as one scalar, or no row."""

    upsert_instance: str
    """Records ``:instance_id``'s ``:state`` and ``:last_error`` for ``:block`` (the error
    cut to its column's length) and its heartbeat; the time of the last state change
    moves only when the state differs from the stored one."""

    prune_instances: str
    """Deletes ``:block``'s instances whose heartbeat is older than the prune age."""

    select_state: str
    """Returns ``:block``'s state as one scalar: the best-ranked state among the
    instances whose heartbeat is younger than the stale age; with none, the stopped
    state when the desired state (else ``:default_desired``) is stopped, otherwise
    the unknown state."""


@dataclass(frozen=True, slots=True)
class WorkRecoveryUpdate:
    """What a startup work-recovery statement does, in names and stored labels only.

    Every row of *table* whose *status_column* holds one of *in_flight_labels* is
    moved to *interrupted_label*; the optional columns are stamped only when the
    declaring contract names them. A dialect renders it; no caller spells the SQL.
    """

    table: str
    schema: str | None
    """The block's schema, or ``None`` when the table lives on the search path."""

    status_column: str
    interrupted_label: str
    in_flight_labels: tuple[str, ...]
    primary_key_column: str
    """The column the statement returns, one value per row it relabelled."""

    lock_timeout_seconds: int
    """How long the statement waits for a row lock before it fails."""

    completed_at_column: str | None = None
    """Stamped with the current time when declared."""

    error: WorkRecoveryErrorStamp | None = None
    """Filled in when declared and still empty."""


@dataclass(frozen=True, slots=True)
class WorkRecoveryErrorStamp:
    """The error column a recovery fills, and the text it fills an empty one with."""

    column: str
    message: str


@dataclass(frozen=True, slots=True)
class WorkRecoverySql:
    """The statements of one startup work recovery, run in order in one transaction."""

    lock_timeout: str
    """Bounds every lock wait of the enclosing transaction (only)."""

    update: str
    """Relabels the stranded rows; returns the primary key of each one, one scalar per row."""


@dataclass(frozen=True, slots=True)
class IndexRename:
    """What one rendered index-rename statement does, read back from its SQL."""

    old_name: str
    """The name the index carries before the statement runs."""

    new_name: str
    """The name it carries after."""

    guarded: bool
    """True when the statement is a no-op where *old_name* is absent."""


@dataclass(frozen=True, slots=True)
class EnumLabelChange:
    """What one rendered named-enum-type statement does to the type's labels, read back from its SQL.

    Exactly one of the three shapes: a type creation (``created`` lists every label
    the type is created with), a label added (``added``, placed beside ``neighbour``),
    or a label renamed in place (``renamed``, old then new).
    """

    type_name: str
    """The enum type's own name, without its schema."""

    created: tuple[str, ...] = ()
    """The labels a creation gives the type, in order; empty for any other statement."""

    added: str | None = None
    """The label an addition adds; ``None`` for any other statement."""

    neighbour: EnumNeighbour | None = None
    """Where an addition places its label; ``None`` when it appends, or for any other statement."""

    renamed: tuple[str, str] | None = None
    """The old and new label of an in-place rename; ``None`` for any other statement."""


@dataclass(frozen=True, slots=True)
class EnumNeighbour:
    """Where an added label sits in a named enum type: next to one label the type holds.

    A native enum's label order is its sort order, so a label added in the middle of
    the declaration is placed beside its declared neighbour rather than appended.
    """

    label: str
    """The stored label of the neighbour."""

    before: bool
    """True when the added label goes before *label*; False when it goes after it."""


def enum_label_neighbour(held_as: Sequence[str | None], position: int) -> EnumNeighbour | None:
    """The neighbour that places the label declared at *position* where it is declared.

    *held_as* walks the type's declaration: for each declared member, the label the
    type holds it under at the moment the addition runs, or ``None`` when it does
    not hold it yet. The label goes after the nearest earlier member the type holds,
    else before the nearest later one. The labels a type holds are always in
    declared order -- every addition keeps them so -- and no member declared
    between the neighbour and the label is held, so it lands in its declared place
    whatever order a revision's additions run in.

    Args:
        held_as: Per declared member, the label the type holds it under, or ``None``.
        position: The declared position of the label being added.

    Returns:
        The neighbour, or ``None`` when the type holds no other member to place it by.
    """
    for label in reversed(held_as[:position]):
        if label is not None:
            return EnumNeighbour(label=label, before=False)
    for label in held_as[position + 1 :]:
        if label is not None:
            return EnumNeighbour(label=label, before=True)
    return None


#: The line-comment introducer a rendered statement may open with (a source note).
_LINE_COMMENT = "--"

#: Statement heads every dialect spells the same way, and their guarded forms.
CREATE_TABLE_HEAD = "CREATE TABLE "
CREATE_INDEX_HEAD = "CREATE INDEX "
IF_NOT_EXISTS = "IF NOT EXISTS "
_GUARDED_TABLE_HEADS = ("CREATE TABLE IF NOT EXISTS ", "DROP TABLE IF EXISTS ")
_GUARDED_INDEX_HEADS = ("CREATE INDEX IF NOT EXISTS ", "DROP INDEX IF EXISTS ")


def statement_head(sql: str) -> str:
    """*sql* from its first line that is not a line comment (a renderer's source note)."""
    lines = sql.split("\n")
    for position, line in enumerate(lines):
        if not line.lstrip().startswith(_LINE_COMMENT):
            return "\n".join(lines[position:])
    return ""


class StatementReader:
    """A left-to-right reader over one rendered statement, in one dialect's quoting.

    Every step consumes what it reads and answers ``False`` / ``None`` on a mismatch,
    so a reader built from a sequence of steps recognises exactly the spelling a
    renderer emits and nothing else.
    """

    def __init__(self, text: str, quote: str) -> None:
        self._text = text
        self._quote = quote
        self._pos = 0

    @property
    def position(self) -> int:
        """How much of the text has been consumed."""
        return self._pos

    def keyword(self, token: str) -> bool:
        """Consume *token* when the text continues with it."""
        if not self._text.startswith(token, self._pos):
            return False
        self._pos += len(token)
        return True

    def identifier(self) -> str | None:
        """Consume one quoted identifier and return it unescaped (a doubled quote is one)."""
        quote = self._quote
        if not self._text.startswith(quote, self._pos):
            return None
        chars: list[str] = []
        pos = self._pos + 1
        while pos < len(self._text):
            if self._text[pos] != quote:
                chars.append(self._text[pos])
                pos += 1
            elif self._text.startswith(quote * 2, pos):
                chars.append(quote)
                pos += 2
            else:
                self._pos = pos + 1
                return "".join(chars)
        return None

    def qualified(self) -> str | None:
        """Consume an identifier optionally qualified by a schema; return the object's own name."""
        name = self.identifier()
        if name is None or not self.keyword("."):
            return name
        return self.identifier()

    def literal(self) -> str | None:
        """Consume one standard SQL string literal (a doubled ``'`` is one) and return it."""
        reader = StatementReader(self._text[self._pos:], "'")
        value = reader.identifier()
        if value is not None:
            self._pos += reader.position
        return value

    def at_end(self) -> bool:
        """Whether the whole text has been consumed."""
        return self._pos == len(self._text)
