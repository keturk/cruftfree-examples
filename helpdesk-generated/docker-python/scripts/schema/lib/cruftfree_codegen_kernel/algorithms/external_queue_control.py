"""The durable control of an external-queue consumer: where it lives and what it is made of.

``<block>.<Topic>.start()/stop()/state()`` act on the whole service, not on the
calling process. The desired state is a row in the service's own database, every
process hosting the consumer reports its own state in a second table, and a
reconciler in each process starts or stops its consumer to match the desired row.
Every language renders the same tables, intervals, state order and values from
this module, so a service behaves the same whichever language generated it.

The store is the service's first own rdbms block
(:func:`~cruftfree_codegen_kernel.algorithms.external_queue_control_store.control_store_block`),
the same block the in-process scheduled jobs take their single-run lock in.

This module imports only the standard library: the SQL dialects that render the
control statements import it, and they are carried into generated scripts, which
run with nothing else installed.
"""

from __future__ import annotations

from typing import Final

#: How often a hosting process upserts its instance row, prunes stale instances,
#: reads the desired state and starts or stops its consumer to match. A call
#: therefore takes effect on every replica within one interval.
RECONCILE_INTERVAL_SECONDS: Final[int] = 5

#: An instance whose heartbeat is older than this, by the database clock, no longer
#: counts towards ``state()``: three missed reconcile ticks.
INSTANCE_STALE_AFTER_SECONDS: Final[int] = 15

#: An instance whose heartbeat is older than this is deleted by the next reconcile tick
#: of any process hosting the block.
INSTANCE_PRUNE_AFTER_SECONDS: Final[int] = 300

#: The longest ``last_error`` text an instance row stores; longer text is cut to it.
LAST_ERROR_MAX_CHARS: Final[int] = 512

#: What ``state()`` returns when the consumer should run and no instance is fresh.
STATE_UNKNOWN: Final[str] = "UNKNOWN"

#: What ``state()`` returns when the consumer should be stopped and no instance is fresh.
STATE_WHEN_STOPPED: Final[str] = "DISCONNECTED"

#: The consumer states, best first: ``state()`` reports the best state among the fresh
#: instances. The members are the consumer states every protocol reports
#: (:data:`cruftfree_common.config.datasource._cache_models.EXTERNAL_QUEUE_CONSUMER_STATES`).
STATE_ORDER: Final[tuple[str, ...]] = (
    "UP",
    "RECONNECTED",
    "RECONNECTING",
    "CONNECT_FAILED",
    "DOWN",
    STATE_WHEN_STOPPED,
)

#: The ``desired_state`` values of the desired-state table.
DESIRED_RUNNING: Final[str] = "running"
DESIRED_STOPPED: Final[str] = "stopped"

#: The ``origin`` values of the desired-state table: ``default`` rows are seeded from
#: the block's ``autoStart`` at every startup; ``call`` rows record a ``start()`` or
#: ``stop()`` call and are never overwritten by a seed.
ORIGIN_DEFAULT: Final[str] = "default"
ORIGIN_CALL: Final[str] = "call"

#: The table holding one desired state per block. Both control tables are tables of the
#: store block's declared schema: the deploy's schema converge creates them under the
#: block's owner login, and a service, holding data rights only, never does.
DESIRED_TABLE: Final[str] = "cruftfree_external_queue_desired"

#: The table holding one row per process hosting a block's consumer.
INSTANCE_TABLE: Final[str] = "cruftfree_external_queue_instance"

#: The columns of the desired-state table: the block's row identity (its primary key),
#: its desired state, where that state came from, and when it was written.
COLUMN_BLOCK: Final[str] = "block"
COLUMN_DESIRED_STATE: Final[str] = "desired_state"
COLUMN_ORIGIN: Final[str] = "origin"
COLUMN_UPDATED_AT: Final[str] = "updated_at"

#: The columns of the instance table besides ``block``: the process (with ``block`` its
#: primary key), its consumer state and that state's error, when the state last changed,
#: and its last heartbeat.
COLUMN_INSTANCE_ID: Final[str] = "instance_id"
COLUMN_STATE: Final[str] = "state"
COLUMN_LAST_ERROR: Final[str] = "last_error"
COLUMN_STATE_CHANGED_AT: Final[str] = "state_changed_at"
COLUMN_HEARTBEAT_AT: Final[str] = "heartbeat_at"
