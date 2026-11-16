"""PostgreSQL dialect implementation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from cruftfree_common.config.datasource.ddl_dialect_names import POSTGRESQL_DDL_DIALECT
from cruftfree_common.cruftfree_model.constants import DEFAULT_RDBMS_SCHEMA
from cruftfree_common.utils.sql_text import dollar_quoted
from cruftfree_rdbms_schema.catalog_reader import CatalogQuery

from cruftfree_codegen_kernel.algorithms.external_queue_control import (
    COLUMN_BLOCK,
    COLUMN_DESIRED_STATE,
    COLUMN_HEARTBEAT_AT,
    COLUMN_INSTANCE_ID,
    COLUMN_LAST_ERROR,
    COLUMN_ORIGIN,
    COLUMN_STATE,
    COLUMN_STATE_CHANGED_AT,
    COLUMN_UPDATED_AT,
    DESIRED_STOPPED,
    DESIRED_TABLE,
    INSTANCE_PRUNE_AFTER_SECONDS,
    INSTANCE_STALE_AFTER_SECONDS,
    INSTANCE_TABLE,
    LAST_ERROR_MAX_CHARS,
    ORIGIN_CALL,
    ORIGIN_DEFAULT,
    STATE_ORDER,
    STATE_UNKNOWN,
    STATE_WHEN_STOPPED,
)
from cruftfree_codegen_kernel.algorithms.postgresql_fulltext import (
    FULLTEXT_INDEX_METHOD,
    build_fulltext_migration_expression,
)
from cruftfree_codegen_kernel.sql_facts.constants import (
    FEATURE_ENUM_LABEL_COMMITTED_BEFORE_USE,
    FEATURE_GUARDED_INDEX_CREATION,
    FEATURE_NAMED_ENUM_TYPES,
    FEATURE_RENAME_FOREIGN_KEY,
    FEATURE_SCHEMA_NAMESPACES,
    FEATURE_TABLE_TRIGGERS,
)
from cruftfree_codegen_kernel.sql_facts.dialects._dialect_base import DialectBase
from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    EXTERNAL_QUEUE_PARAM_BLOCK,
    EXTERNAL_QUEUE_PARAM_DEFAULT_DESIRED,
    EXTERNAL_QUEUE_PARAM_DESIRED_STATE,
    EXTERNAL_QUEUE_PARAM_INSTANCE_ID,
    EXTERNAL_QUEUE_PARAM_LAST_ERROR,
    EXTERNAL_QUEUE_PARAM_STATE,
    JOB_STATE_COLUMN_JOB_ID,
    JOB_STATE_COLUMN_LAST_FIRE_TIME,
    JOB_STATE_PARAM_FIRE_TIME,
    JOB_STATE_PARAM_JOB_ID,
    SCHEDULED_JOB_STATE_TABLE,
    EnumLabelChange,
    EnumNeighbour,
    ExternalQueueControlSql,
    IndexRename,
    ScheduledJobStateSql,
    SessionLockSql,
    StatementReader,
    WorkRecoverySql,
    WorkRecoveryUpdate,
    statement_head,
)
from cruftfree_codegen_kernel.sql_facts.dialects.catalog_read import (
    CatalogClient,
    ServerVersionSql,
    catalog_fingerprint,
    catalog_read_queries,
)
from cruftfree_codegen_kernel.sql_facts.dialects.postgresql_triggers import (
    PostgreSQLTableTriggers,
)
from cruftfree_codegen_kernel.sql_facts.errors import DialectFeatureError

if TYPE_CHECKING:
    from cruftfree_codegen_kernel.sql_facts.column_facts import ColumnDefinition
from cruftfree_codegen_kernel.sql_facts.dialects._postgresql_text import (
    _ADD_VALUE,
    _ADD_VALUE_AFTER,
    _ADD_VALUE_BEFORE,
    _ALTER_TYPE,
    _CATALOG_CLIENT,
    _CATALOG_ROW_ALIAS,
    _COMMIT,
    _DO_HEAD,
    _DOCUMENT_DIGEST,
    _DROP_TYPE_IF_EXISTS,
    _ENUM_TYPE_AS_ENUM,
    _ENUM_TYPE_GUARD_CLOSE,
    _ENUM_TYPE_GUARD_OPEN,
    _FUNCTION_ARGUMENT_LIMIT,
    _GUARD_DIGEST_VARIABLE,
    _IF_BLOCK_CLOSE,
    _LABEL_LIST_SEPARATOR,
    _LABEL_PREDICATE_CLOSE,
    _LABEL_PREDICATE_LABEL,
    _LABEL_PREDICATE_OPEN,
    _LABEL_PREDICATE_SCHEMA,
    _LABEL_PREDICATE_VISIBLE,
    _PROMOTE_GUARD_OPEN,
    _PROMOTE_GUARD_THEN,
    _PROMOTE_USING_INDEX,
    _RENAME_GUARD_CONFLICT,
    _RENAME_GUARD_OPEN,
    _UNIQUE_GUARD_OPEN,
    _do_block_body,
    _label_list,
    _label_predicate,
    _read_neighbour,
    _schema_and_name,
)


class PostgreSQLDialect(PostgreSQLTableTriggers, DialectBase):
    """PostgreSQL dialect implementation.

    Inherits from DialectBase:
    - quote_identifier, quote_literal: the ``postgresql`` dialect rows
      (``sql_quoted_identifier``; a standard string constant, or ``U&'…'`` for
      a value holding a hidden code point)
    - table_options: empty string
    """

    @property
    def name(self) -> str:
        return POSTGRESQL_DDL_DIALECT

    def session_lock_sql(self, key: str) -> SessionLockSql:
        """``pg_advisory_lock`` over ``hashtext`` of the text key (PostgreSQL *Advisory Lock Functions*).

        The lock is session-scoped: it is held until ``pg_advisory_unlock`` or the end of
        the session. ``pg_try_advisory_lock`` returns a boolean without waiting, and
        ``pg_advisory_unlock`` returns false when the session did not hold the lock.
        """
        identifier = f"hashtext({self.quote_literal(key)})"
        try_acquire_condition = f"pg_try_advisory_lock({identifier})"
        release_condition = f"pg_advisory_unlock({identifier})"
        return SessionLockSql(
            try_acquire=f"SELECT {try_acquire_condition}",
            acquire=f"SELECT pg_advisory_lock({identifier})",
            release=f"SELECT {release_condition}",
            acquired_value=True,
            try_acquire_condition=try_acquire_condition,
            release_condition=release_condition,
        )

    def abort_unless_sql(
        self, condition: str, guard: str, *, reported: str | None = None
    ) -> str:
        """A ``DO`` block raising *guard* when *condition* is false (PL/pgSQL *RAISE*).

        ``RAISE EXCEPTION USING MESSAGE`` takes the message as an expression, so a ``%``
        in *guard* is never a format placeholder; *guard* is a quoted literal, the value
        of *reported* (a dialect expression, never block text) is appended with ``||``,
        and the body's dollar-quote tag is one neither holds.
        """
        if not condition.strip():
            raise ValueError(f"The guard '{guard}' has no condition to check.")
        if not guard.strip():
            raise ValueError(f"A guard on '{condition}' must name what it guards.")
        message = self.quote_literal(guard)
        if reported is not None:
            if not reported.strip():
                raise ValueError(
                    f"The guard '{guard}' reports an empty expression. Pass the dialect "
                    "expression whose value the error carries, or report nothing."
                )
            message = f"{message} || ({reported})"
        body = (
            f"BEGIN IF NOT ({condition}) THEN RAISE EXCEPTION USING MESSAGE = "
            f"{message};{_IF_BLOCK_CLOSE}"
        )
        return f"{_DO_HEAD}{dollar_quoted(body)};"

    def server_version_sql(self) -> ServerVersionSql:
        """``server_version_num`` and ``server_version`` (PostgreSQL *Preset Options*).

        ``server_version_num`` is major * 10000 + minor since PostgreSQL 10, the numbering
        the engine's minimum is stated in.
        """
        return ServerVersionSql(
            number="current_setting('server_version_num')::integer",
            text="current_setting('server_version')",
        )

    def catalog_search_path_sql(self, queries: Sequence[CatalogQuery]) -> str:
        """``SET search_path`` for the session: the places, then ``public`` (PostgreSQL *SET*).

        ``s.oid::regclass::text`` and ``pg_get_expr`` print a relation unqualified exactly
        when its schema is on the search path, so the read, the apply's fingerprint guard
        and its closing catalog statement print one document only under one path.

        Raises:
            ValueError: As :func:`catalog_read_queries`.
        """
        places = catalog_read_queries(queries)[0].places
        return f"SET search_path TO {self._search_path(places)};"

    def catalog_read_begin_sql(self) -> str:
        """``REPEATABLE READ READ ONLY``: one snapshot for every statement (PostgreSQL *SET TRANSACTION*)."""
        return "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;"

    def catalog_read_commit_sql(self) -> str:
        """``COMMIT``: ends the read-only transaction."""
        return _COMMIT

    def apply_begin_sql(self) -> str:
        """``BEGIN``: PostgreSQL DDL is transactional, so an apply's changes commit as one."""
        return "BEGIN;"

    def apply_commit_sql(self) -> str:
        """``COMMIT``: commits the apply's changes."""
        return _COMMIT

    def catalog_client(self) -> CatalogClient:
        """``psql -X -A -t -q -f -``, the places bound by ``\\bind :places \\g`` (psql manual)."""
        return _CATALOG_CLIENT

    def catalog_document_sql(self, queries: Sequence[CatalogQuery]) -> str:
        """``json_build_object`` of every document, its ``length`` and ``sha256`` (PostgreSQL *JSON*, *Binary String Functions*).

        ``json`` keeps its members in the order built, so the text is a function of the
        rows alone; the length and digest are computed over that text in the same
        statement, as UTF-8, for the client to check the transfer against.

        Raises:
            ValueError: As :func:`catalog_read_queries`, or more members than one
                function call takes.
        """
        select = self._catalog_document_select(
            catalog_read_queries(queries), f"d.doc, length(d.doc), {_DOCUMENT_DIGEST}"
        )
        return f"{select} {_CATALOG_CLIENT.run_bound}"

    def catalog_fingerprint_guard_sql(
        self, queries: Sequence[CatalogQuery], fingerprint: str, guard: str
    ) -> str:
        """A ``DO`` block recomputing the read's digest (PL/pgSQL *EXECUTE … INTO … USING*) and raising *guard* unless it is *fingerprint*.

        The digest is selected from the read's own document select, passed to
        ``EXECUTE`` as a quoted literal with the places bound as its ``$1``, so the
        guard computes exactly what the read printed; ``IS DISTINCT FROM`` raises on a
        missing digest too. The message is a quoted literal, never a format string.

        Raises:
            ValueError: As :meth:`catalog_document_sql` and :func:`catalog_fingerprint`,
                or *guard* is empty.
        """
        ordered = catalog_read_queries(queries)
        expected = catalog_fingerprint(fingerprint)
        if not guard.strip():
            raise ValueError(
                f"A guard on the catalog fingerprint {expected} must name what it guards."
            )
        select = self._catalog_document_select(ordered, _DOCUMENT_DIGEST)
        places = ", ".join(self.quote_literal(place) for place in ordered[0].places)
        body = (
            f"DECLARE {_GUARD_DIGEST_VARIABLE} text; BEGIN EXECUTE "
            f"{self.quote_literal(select)} INTO {_GUARD_DIGEST_VARIABLE} "
            f"USING ARRAY[{places}]::text[]; IF {_GUARD_DIGEST_VARIABLE} IS DISTINCT FROM "
            f"{self.quote_literal(expected)} THEN RAISE EXCEPTION USING MESSAGE = "
            f"{self.quote_literal(guard)};{_IF_BLOCK_CLOSE}"
        )
        return f"{_DO_HEAD}{dollar_quoted(body)};"

    def _catalog_document_select(
        self, ordered: Sequence[CatalogQuery], columns: str
    ) -> str:
        """``SELECT <columns>`` over ``d.doc``, the ``json_build_object`` of *ordered*'s documents.

        The one spelling of a read's document: the read selects the document, its length
        and digest; the fingerprint guard selects the digest.

        Raises:
            ValueError: More members than one function call takes.
        """
        if 2 * len(ordered) > _FUNCTION_ARGUMENT_LIMIT:
            raise ValueError(
                f"The catalog queries {[query.name for query in ordered]} are "
                f"{len(ordered)} members; json_build_object takes at most "
                f"{_FUNCTION_ARGUMENT_LIMIT // 2}. Read them in fewer queries."
            )
        members = ", ".join(
            f"{self.quote_literal(query.name)}, ({query.text})" for query in ordered
        )
        return (
            f"SELECT {columns} "
            f"FROM (SELECT json_build_object({members})::text AS doc) AS d"
        )

    def scheduled_job_state_sql(self) -> ScheduledJobStateSql:
        """The statements over the last-fire table of in-process scheduled jobs, in PostgreSQL syntax.

        ``last_fire_time`` is a ``DateTime`` column, ``TIMESTAMPTZ`` here: a UTC instant
        read back timezone-aware.
        """
        table = self.quote_identifier(SCHEDULED_JOB_STATE_TABLE)
        job_column = self.quote_identifier(JOB_STATE_COLUMN_JOB_ID)
        fire_column = self.quote_identifier(JOB_STATE_COLUMN_LAST_FIRE_TIME)
        job_id = f":{JOB_STATE_PARAM_JOB_ID}"
        fire_time = f":{JOB_STATE_PARAM_FIRE_TIME}"
        insert = f"INSERT INTO {table} ({job_column}, {fire_column}) VALUES ({job_id}, {fire_time})"
        return ScheduledJobStateSql(
            select_last_fire=f"SELECT {fire_column} FROM {table} WHERE {job_column} = {job_id}",
            insert_if_absent=f"{insert} ON CONFLICT ({job_column}) DO NOTHING",
            upsert_fire=(
                f"{insert} ON CONFLICT ({job_column}) DO UPDATE SET "
                f"{fire_column} = EXCLUDED.{fire_column}"
            ),
            stores_naive_utc=False,
        )

    def external_queue_control_sql(self) -> ExternalQueueControlSql:
        """The external-queue control tables in PostgreSQL syntax (*INSERT … ON CONFLICT*).

        Every timestamp is ``NOW()``, the database clock (``TIMESTAMPTZ``). The ages
        are ``INTERVAL`` literals and the state ranking a ``CASE`` over the kernel's
        state order, so a statement binds only its named placeholders and carries no
        ``::`` cast a positional rewrite could misread. No statement creates a table:
        the deploy's schema converge creates both from the store block's snapshot.
        """
        desired = self.quote_identifier(DESIRED_TABLE)
        instance = self.quote_identifier(INSTANCE_TABLE)
        block = f":{EXTERNAL_QUEUE_PARAM_BLOCK}"
        desired_state = f":{EXTERNAL_QUEUE_PARAM_DESIRED_STATE}"
        origin_default = self.quote_literal(ORIGIN_DEFAULT)
        origin_call = self.quote_literal(ORIGIN_CALL)
        write_desired = (
            f"INSERT INTO {desired} ({COLUMN_BLOCK}, {COLUMN_DESIRED_STATE}, {COLUMN_ORIGIN}, "
            f"{COLUMN_UPDATED_AT}) VALUES "
        )
        on_block = (
            f"ON CONFLICT ({COLUMN_BLOCK}) DO UPDATE SET "
            f"{COLUMN_DESIRED_STATE} = EXCLUDED.{COLUMN_DESIRED_STATE}"
        )
        stamp_desired = f"{COLUMN_UPDATED_AT} = EXCLUDED.{COLUMN_UPDATED_AT}"
        return ExternalQueueControlSql(
            seed_default=(
                f"{write_desired}({block}, {desired_state}, {origin_default}, NOW()) "
                f"{on_block}, {stamp_desired} "
                f"WHERE {desired}.{COLUMN_ORIGIN} = {origin_default}"
            ),
            set_desired=(
                f"{write_desired}({block}, {desired_state}, {origin_call}, NOW()) "
                f"{on_block}, {COLUMN_ORIGIN} = EXCLUDED.{COLUMN_ORIGIN}, {stamp_desired}"
            ),
            select_desired=(
                f"SELECT {COLUMN_DESIRED_STATE} FROM {desired} WHERE {COLUMN_BLOCK} = {block}"
            ),
            upsert_instance=self._external_queue_upsert_instance(instance),
            prune_instances=(
                f"DELETE FROM {instance} WHERE {COLUMN_BLOCK} = {block} "
                f"AND {COLUMN_HEARTBEAT_AT} < NOW() - "
                f"INTERVAL '{INSTANCE_PRUNE_AFTER_SECONDS} seconds'"
            ),
            select_state=self._external_queue_select_state(desired, instance),
        )

    def _external_queue_upsert_instance(self, instance: str) -> str:
        """An instance's state, error and heartbeat; its state-change time moves only on a change."""
        return (
            f"INSERT INTO {instance} "
            f"({COLUMN_BLOCK}, {COLUMN_INSTANCE_ID}, {COLUMN_STATE}, {COLUMN_LAST_ERROR}, "
            f"{COLUMN_STATE_CHANGED_AT}, {COLUMN_HEARTBEAT_AT}) "
            f"VALUES (:{EXTERNAL_QUEUE_PARAM_BLOCK}, :{EXTERNAL_QUEUE_PARAM_INSTANCE_ID}, "
            f":{EXTERNAL_QUEUE_PARAM_STATE}, "
            f"LEFT(:{EXTERNAL_QUEUE_PARAM_LAST_ERROR}, {LAST_ERROR_MAX_CHARS}), NOW(), NOW()) "
            f"ON CONFLICT ({COLUMN_BLOCK}, {COLUMN_INSTANCE_ID}) DO UPDATE SET "
            f"{COLUMN_STATE} = EXCLUDED.{COLUMN_STATE}, "
            f"{COLUMN_LAST_ERROR} = EXCLUDED.{COLUMN_LAST_ERROR}, "
            f"{COLUMN_HEARTBEAT_AT} = EXCLUDED.{COLUMN_HEARTBEAT_AT}, "
            f"{COLUMN_STATE_CHANGED_AT} = CASE WHEN {instance}.{COLUMN_STATE} = "
            f"EXCLUDED.{COLUMN_STATE} THEN {instance}.{COLUMN_STATE_CHANGED_AT} "
            f"ELSE EXCLUDED.{COLUMN_STATE_CHANGED_AT} END"
        )

    def _external_queue_select_state(self, desired: str, instance: str) -> str:
        """``state()`` as one scalar: the best fresh instance state, else the desired-state fallback."""
        block = f":{EXTERNAL_QUEUE_PARAM_BLOCK}"
        ranks = " ".join(
            f"WHEN {self.quote_literal(state)} THEN {rank}"
            for rank, state in enumerate(STATE_ORDER)
        )
        best_fresh = (
            f"(SELECT i.{COLUMN_STATE} FROM {instance} i WHERE i.{COLUMN_BLOCK} = {block} "
            f"AND i.{COLUMN_HEARTBEAT_AT} > NOW() - "
            f"INTERVAL '{INSTANCE_STALE_AFTER_SECONDS} seconds' "
            f"ORDER BY CASE i.{COLUMN_STATE} {ranks} ELSE {len(STATE_ORDER)} END LIMIT 1)"
        )
        desired_or_default = (
            f"COALESCE((SELECT d.{COLUMN_DESIRED_STATE} FROM {desired} d "
            f"WHERE d.{COLUMN_BLOCK} = {block}), "
            f":{EXTERNAL_QUEUE_PARAM_DEFAULT_DESIRED})"
        )
        fallback = (
            f"CASE {desired_or_default} WHEN {self.quote_literal(DESIRED_STOPPED)} "
            f"THEN {self.quote_literal(STATE_WHEN_STOPPED)} "
            f"ELSE {self.quote_literal(STATE_UNKNOWN)} END"
        )
        return f"SELECT COALESCE({best_fresh}, {fallback})"

    def work_recovery_sql(self, update: WorkRecoveryUpdate) -> WorkRecoverySql:
        """``SET LOCAL lock_timeout`` then ``UPDATE … RETURNING`` (PostgreSQL *SET*, *UPDATE*).

        ``SET LOCAL`` lasts until the end of the enclosing transaction, so the bound
        never leaks to the pooled connection. A label is spliced as a literal, not
        bound: asyncpg binds a string as ``VARCHAR``, which PostgreSQL will not
        assign to an enum column.
        """
        status = self.quote_identifier(update.status_column)
        assignments = [f"{status} = {self.quote_literal(update.interrupted_label)}"]
        if update.completed_at_column is not None:
            assignments.append(
                f"{self.quote_identifier(update.completed_at_column)} = NOW()"
            )
        if update.error is not None:
            error = self.quote_identifier(update.error.column)
            assignments.append(
                f"{error} = COALESCE({error}, {self.quote_literal(update.error.message)})"
            )
        in_flight = _LABEL_LIST_SEPARATOR.join(
            self.quote_literal(label) for label in update.in_flight_labels
        )
        return WorkRecoverySql(
            lock_timeout=(
                f"SET LOCAL lock_timeout = {self.quote_literal(f'{update.lock_timeout_seconds}s')}"
            ),
            update=(
                f"UPDATE {self.qualified_identifier(update.table, update.schema)} "
                f"SET {', '.join(assignments)} "
                f"WHERE {status} IN ({in_flight}) "
                f"RETURNING {self.quote_identifier(update.primary_key_column)}"
            ),
        )

    def auto_increment_type(self, base_type: str) -> str:
        type_map = {
            "SMALLINT": "SMALLSERIAL",
            "INTEGER": "SERIAL",
            "INT": "SERIAL",
            "BIGINT": "BIGSERIAL",
        }
        if base_type not in type_map:
            raise DialectFeatureError(
                f"Cannot create auto-increment column with type '{base_type}' "
                f"in PostgreSQL. Supported base types: {', '.join(sorted(type_map.keys()))}"
            )
        return type_map[base_type]

    def supports_feature(self, feature: str) -> bool:
        return feature in {
            "arrays",
            "fulltext_index",
            "spatial_index",
            "json_native",
            "uuid_native",
            "interval_type",
            "inet_type",
            FEATURE_ENUM_LABEL_COMMITTED_BEFORE_USE,
            FEATURE_GUARDED_INDEX_CREATION,
            FEATURE_NAMED_ENUM_TYPES,
            FEATURE_SCHEMA_NAMESPACES,
            FEATURE_TABLE_TRIGGERS,
            FEATURE_RENAME_FOREIGN_KEY,
        }

    def array_column_type(self, element_type: str) -> str:
        return f"{element_type}[]"

    def render_fulltext_index(
        self,
        index_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        if_not_exists: bool = False,
    ) -> str:
        """A GIN index over the shared coalesce ``to_tsvector`` expression.

        The expression is the one every emitter and every query uses
        (:func:`~cruftfree_codegen_kernel.algorithms.postgresql_fulltext.build_fulltext_migration_expression`):
        PostgreSQL uses the index only for a query built over the identical
        expression, and a NULL column left uncoalesced would collapse the whole
        concatenation to NULL and leave the row unindexed.
        """
        quoted_table = self.quote_identifier(table_name)
        quoted_index = self.quote_identifier(index_name)
        expression = build_fulltext_migration_expression(
            [self.quote_identifier(c) for c in columns]
        )
        guard = "IF NOT EXISTS " if if_not_exists else ""
        return (
            f"CREATE INDEX {guard}{quoted_index} ON {quoted_table} "
            f"USING {FULLTEXT_INDEX_METHOD.upper()} ({expression});"
        )

    def render_spatial_index(
        self,
        index_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        if_not_exists: bool = False,
    ) -> str:
        quoted_table = self.quote_identifier(table_name)
        quoted_index = self.quote_identifier(index_name)
        quoted_cols = ", ".join(self.quote_identifier(c) for c in columns)
        guard = "IF NOT EXISTS " if if_not_exists else ""
        return (
            f"CREATE INDEX {guard}{quoted_index} ON {quoted_table} "
            f"USING GIST ({quoted_cols});"
        )

    def render_add_unique_constraint(
        self,
        constraint_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        schema: str | None = None,
        if_not_exists: bool = False,
    ) -> str:
        quoted_cols = ", ".join(self.quote_identifier(c) for c in columns)
        table = self.qualified_identifier(table_name, schema)
        statement = (
            f"ALTER TABLE {table} "
            f"ADD CONSTRAINT {self.quote_identifier(constraint_name)} UNIQUE ({quoted_cols});"
        )
        if not if_not_exists:
            return statement
        return self._unique_constraint_guard(statement, table, constraint_name)

    def _unique_constraint_guard(
        self, statement: str, table: str, constraint_name: str
    ) -> str:
        """*statement* (an ``ADD CONSTRAINT ... UNIQUE``) run only where *table* lacks the constraint.

        Args:
            statement: The unguarded ``ALTER TABLE ... ADD CONSTRAINT ... UNIQUE (...);``.
            table: The table as *statement* spells it (quoted, schema-qualified or not).
            constraint_name: The constraint's name, unquoted.
        """
        body = (
            f"{_UNIQUE_GUARD_OPEN}{self.quote_literal(constraint_name)} "
            f"AND conrelid = to_regclass({self.quote_literal(table)})) "
            f"THEN {statement}{_IF_BLOCK_CLOSE}"
        )
        return f"DO {dollar_quoted(body)};"

    def render_drop_unique_constraint(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
        if_exists: bool = False,
    ) -> str:
        guard = "IF EXISTS " if if_exists else ""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"DROP CONSTRAINT {guard}{self.quote_identifier(constraint_name)};"
        )

    def render_drop_column_unique_constraints(
        self,
        table_name: str,
        column_name: str,
        *,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """A ``DO`` block dropping each ``pg_constraint`` unique row over exactly the column.

        The constraint is found by ``contype = 'u'`` over a one-element ``conkey``
        naming the column, so ``uq_<table>_<col>``, the engine's own
        ``<table>_<col>_key`` and a truncated spelling of either are all found; each
        is dropped through ``format('%I')``, which quotes the name the catalog holds.
        """
        qualified_table = self.qualified_identifier(table_name, schema)
        drop_target = "%I.%I" if schema is not None else "%I"
        target_arguments = (
            f"{self.quote_literal(schema)}, {self.quote_literal(table_name)}"
            if schema is not None
            else self.quote_literal(table_name)
        )
        body = (
            "DECLARE constraint_row record; BEGIN "
            "FOR constraint_row IN SELECT c.conname FROM pg_constraint c "
            "JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1] "
            f"WHERE c.conrelid = to_regclass({self.quote_literal(qualified_table)}) "
            "AND c.contype = 'u' AND array_length(c.conkey, 1) = 1 "
            f"AND a.attname = {self.quote_literal(column_name)} LOOP "
            f"EXECUTE format('ALTER TABLE {drop_target} DROP CONSTRAINT %I', "
            f"{target_arguments}, constraint_row.conname); "
            "END LOOP; END"
        )
        return (f"DO {dollar_quoted(body)};",)

    def render_add_foreign_key(
        self,
        constraint_name: str,
        table_name: str,
        columns: tuple[str, ...],
        referred_table: str,
        referred_columns: tuple[str, ...],
        on_delete: str,
        on_update: str,
        *,
        schema: str | None = None,
        not_valid: bool = False,
    ) -> str:
        """The ANSI form; ``not_valid`` appends ``NOT VALID`` (rows checked later)."""
        statement = super().render_add_foreign_key(
            constraint_name,
            table_name,
            columns,
            referred_table,
            referred_columns,
            on_delete,
            on_update,
            schema=schema,
        )
        if not not_valid:
            return statement
        return statement[: -len(";")] + " NOT VALID;"

    def render_validate_foreign_key(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"VALIDATE CONSTRAINT {self.quote_identifier(constraint_name)};"
        )

    def render_drop_foreign_key(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
        if_exists: bool = False,
    ) -> tuple[str, ...]:
        guard = "IF EXISTS " if if_exists else ""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"DROP CONSTRAINT {guard}{self.quote_identifier(constraint_name)};",
        )

    def rename_foreign_key_sql(
        self,
        old_name: str,
        new_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"RENAME CONSTRAINT {self.quote_identifier(old_name)} "
            f"TO {self.quote_identifier(new_name)};"
        )

    def render_rename_index(
        self,
        index_name: str,
        new_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        return (
            f"ALTER INDEX IF EXISTS {self.qualified_identifier(index_name, schema)} "
            f"RENAME TO {self.quote_identifier(new_name)};"
        )

    def render_create_enum_type(
        self,
        type_name: str,
        labels: Sequence[str],
        *,
        schema: str | None = None,
    ) -> str:
        """``CREATE TYPE ... AS ENUM`` inside a ``DO`` block that tolerates an existing type.

        PostgreSQL has no ``CREATE TYPE ... IF NOT EXISTS``. ``unique_violation`` is
        caught with ``duplicate_object`` because concurrent creators race on
        ``pg_type``'s unique index rather than on the object check; nothing else is
        swallowed.
        """
        quoted_labels = _LABEL_LIST_SEPARATOR.join(
            self.quote_literal(label) for label in labels
        )
        body = (
            f"{_ENUM_TYPE_GUARD_OPEN}{self.qualified_identifier(type_name, schema)}"
            f"{_ENUM_TYPE_AS_ENUM}{quoted_labels}); {_ENUM_TYPE_GUARD_CLOSE}"
        )
        return f"DO {dollar_quoted(body)};"

    def render_drop_enum_type(
        self,
        type_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """``DROP TYPE IF EXISTS``, qualified with the block's schema like its creation."""
        return f"{_DROP_TYPE_IF_EXISTS}{self.qualified_identifier(type_name, schema)};"

    # @canonical(migration/enum-value-add-statement): the DDL that adds one label to a native enum type
    # @rule: Always IF NOT EXISTS -- a runtime enum reconciler may already have added the
    #   label to a running database before the revision that adds it is applied
    # @rule: Placed AFTER/BEFORE its declared neighbour -- the label order is the type's
    #   sort order, and a bare ADD VALUE appends, so every database would sort differently
    #   from one created from the declaration
    # @rule: Qualified with the block's schema, matching how the baseline created the type
    def render_add_enum_value(
        self,
        type_name: str,
        label: str,
        columns: Sequence[tuple[str, ColumnDefinition]],
        *,
        neighbour: EnumNeighbour | None,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """``ALTER TYPE ... ADD VALUE IF NOT EXISTS ... AFTER|BEFORE``; the columns follow the type.

        Guarded because a database can already hold the label -- a runtime enum
        reconciler may have added it before the revision applies.
        """
        del columns
        placement = ""
        if neighbour is not None:
            keyword = _ADD_VALUE_BEFORE if neighbour.before else _ADD_VALUE_AFTER
            placement = f"{keyword}{self.quote_literal(neighbour.label)}"
        return (
            f"{_ALTER_TYPE}{self.qualified_identifier(type_name, schema)}"
            f"{_ADD_VALUE}{self.quote_literal(label)}{placement};",
        )

    def render_relocate_schema(
        self,
        old_schema: str | None,
        new_schema: str | None,
        enum_types: Sequence[str],
        tables: Sequence[str],
    ) -> tuple[str, ...]:
        """``SET SCHEMA`` for every enum type, then every table.

        A column typed with an enum follows its type when the type moves, so only
        the types and the tables are moved.
        """
        source = old_schema if old_schema is not None else DEFAULT_RDBMS_SCHEMA
        target = self.quote_identifier(
            new_schema if new_schema is not None else DEFAULT_RDBMS_SCHEMA
        )
        return (
            *(
                f"ALTER TYPE {self.qualified_identifier(name, source)} SET SCHEMA {target};"
                for name in enum_types
            ),
            *(
                f"ALTER TABLE {self.qualified_identifier(name, source)} SET SCHEMA {target};"
                for name in tables
            ),
        )

    def _enum_label_exists_predicate(
        self, type_name: str, schema: str | None, label: str
    ) -> str:
        """A predicate true when named enum *type_name* holds *label*.

        With no *schema* the type is the one visible on the ``search_path``.
        """
        namespace = (
            f"{_LABEL_PREDICATE_SCHEMA}{self.quote_literal(schema)}"
            if schema
            else _LABEL_PREDICATE_VISIBLE
        )
        return (
            f"{_LABEL_PREDICATE_OPEN}{self.quote_literal(type_name)}{namespace}"
            f"{_LABEL_PREDICATE_LABEL}{self.quote_literal(label)}{_LABEL_PREDICATE_CLOSE}"
        )

    # @canonical(migration/enum-label-rename-statement): the DDL that renames one label of a native enum type
    # @rule: Idempotent -- a database whose type no longer holds the old label (the baseline
    #   already created the new one, or the rename already ran) is left alone
    # @rule: Fails closed when the type holds BOTH labels: rows under the old label would be
    #   stranded, and PostgreSQL has no ALTER TYPE ... DROP VALUE to retire it
    def render_rename_enum_value(
        self,
        type_name: str,
        old_label: str,
        new_label: str,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER TYPE ... RENAME VALUE`` while the type holds *old_label*; both labels held raises."""
        has_old = self._enum_label_exists_predicate(type_name, schema, old_label)
        has_new = self._enum_label_exists_predicate(type_name, schema, new_label)
        conflict = self.quote_literal(
            f"Enum type {type_name} already holds both label {old_label} and label "
            f"{new_label}, so rows still under {old_label} cannot be renamed in place. "
            "Move them with an UPDATE and retire the duplicate label by hand."
        )
        body = (
            f"{_RENAME_GUARD_OPEN}{has_old}{_RENAME_GUARD_CONFLICT}"
            f"{has_new} THEN RAISE EXCEPTION USING MESSAGE = {conflict}; END IF; "
            f"{_ALTER_TYPE}{self.qualified_identifier(type_name, schema)} "
            f"RENAME VALUE {self.quote_literal(old_label)} TO {self.quote_literal(new_label)}; "
            "END IF; "
            "END"
        )
        return f"DO {dollar_quoted(body)};"

    def render_create_schema(self, schema: str) -> str:
        """``CREATE SCHEMA`` behind a ``pg_namespace`` probe, never ``IF NOT EXISTS``."""
        body = (
            "BEGIN IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = "
            f"{self.quote_literal(schema)}) "
            f"THEN CREATE SCHEMA {self.quote_identifier(schema)}; END IF; END"
        )
        return f"DO {dollar_quoted(body)};"

    def render_drop_schema(self, schema: str) -> str:
        """``DROP SCHEMA IF EXISTS``, never ``CASCADE``: a schema holding an object is refused."""
        return f"DROP SCHEMA IF EXISTS {self.quote_identifier(schema)};"

    def render_set_search_path(self, schema: str) -> str:
        """``SET LOCAL search_path``: *schema* first, ``public`` behind it, for the transaction only."""
        return f"SET LOCAL search_path TO {self._search_path((schema,))};"

    def _search_path(self, schemas: Sequence[str]) -> str:
        """*schemas* as quoted identifiers, then ``public`` unless one of them is it: a ``search_path`` value.

        ``public`` stays behind them for the extension types and functions that live there.
        """
        path = [self.quote_identifier(schema) for schema in schemas]
        if DEFAULT_RDBMS_SCHEMA not in schemas:
            path.append(DEFAULT_RDBMS_SCHEMA)
        return ", ".join(path)

    def catalog_query(
        self,
        name: str,
        columns: tuple[tuple[str, str], ...],
        source: str,
        key_columns: tuple[str, ...],
    ) -> CatalogQuery:
        """``json_agg`` of ``row_to_json`` ordered by the keys, ``COALESCE``'d to ``'[]'`` (PostgreSQL *JSON Functions*).

        ``json_agg`` over no rows is SQL NULL, so ``COALESCE`` makes an empty
        catalog fact the document ``[]``. The whole-row reference ``q.*`` keeps a
        key named like the subquery alias from being read as that column.
        """
        selected = ", ".join(
            f"{expression} AS {self.quote_identifier(key)}"
            for key, expression in columns
        )
        order = ", ".join(
            f"{_CATALOG_ROW_ALIAS}.{self.quote_identifier(key)}" for key in key_columns
        )
        text = (
            f"SELECT COALESCE(json_agg(row_to_json({_CATALOG_ROW_ALIAS}.*) ORDER BY {order}), "
            f"'[]'::json) FROM (SELECT {selected} {source}) AS {_CATALOG_ROW_ALIAS}"
        )
        return CatalogQuery(
            name=name,
            columns=columns,
            source=source,
            key_columns=key_columns,
            text=text,
        )

    def render_promote_unique_index(
        self,
        index_name: str,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        existing_index = self.quote_literal(
            self.qualified_identifier(index_name, schema)
        )
        body = (
            f"{_PROMOTE_GUARD_OPEN}{existing_index}{_PROMOTE_GUARD_THEN}"
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ADD CONSTRAINT {self.quote_identifier(constraint_name)}"
            f"{_PROMOTE_USING_INDEX}{self.quote_identifier(index_name)};"
            f"{_IF_BLOCK_CLOSE}"
        )
        return f"DO {dollar_quoted(body)};"

    def tolerates_existence(self, sql: str) -> bool:
        """The ANSI guards, the enum type drop, plus the ``DO`` blocks that probe the catalog first.

        The guarded unique constraint (:meth:`render_add_unique_constraint` with
        ``if_not_exists``) and the enum type creation (:meth:`render_create_enum_type`,
        always guarded) are recognised by the exact block their renderers build; the
        enum type drop (:meth:`render_drop_enum_type`, always guarded) by its exact text.
        """
        if super().tolerates_existence(sql):
            return True
        head = statement_head(sql)
        if self._drops_enum_type_if_exists(head):
            return True
        body = _do_block_body(head)
        if body is None:
            return False
        guards_constraint = body.startswith(_UNIQUE_GUARD_OPEN) and body.endswith(
            _IF_BLOCK_CLOSE
        )
        guards_type = body.startswith(_ENUM_TYPE_GUARD_OPEN) and body.endswith(
            _ENUM_TYPE_GUARD_CLOSE
        )
        return guards_constraint or guards_type

    def _drops_enum_type_if_exists(self, head: str) -> bool:
        """Whether *head* is the statement :meth:`render_drop_enum_type` builds, read back."""
        reader = self._reader(head)
        if not reader.keyword(_DROP_TYPE_IF_EXISTS):
            return False
        target = _schema_and_name(reader)
        if target is None:
            return False
        schema, type_name = target
        return self.render_drop_enum_type(type_name, schema=schema) == head

    def index_rename(self, sql: str) -> IndexRename | None:
        """``ALTER INDEX [IF EXISTS] ... RENAME TO ...``, or a guarded unique-index promotion."""
        head = statement_head(sql)
        reader = self._reader(head)
        if not reader.keyword("ALTER INDEX "):
            return self._promotion(head)
        guarded = reader.keyword("IF EXISTS ")
        old_name = reader.qualified()
        if old_name is None or not reader.keyword(" RENAME TO "):
            return None
        new_name = reader.identifier()
        if new_name is None or not reader.keyword(";") or not reader.at_end():
            return None
        return IndexRename(old_name=old_name, new_name=new_name, guarded=guarded)

    def _promotion(self, head: str) -> IndexRename | None:
        """Read the ``DO`` block :meth:`render_promote_unique_index` builds back."""
        body = _do_block_body(head)
        if body is None:
            return None
        reader = self._reader(body)
        if not reader.keyword(_PROMOTE_GUARD_OPEN) or reader.literal() is None:
            return None
        if (
            not reader.keyword(_PROMOTE_GUARD_THEN + "ALTER TABLE ")
            or reader.qualified() is None
        ):
            return None
        if not reader.keyword(" ADD CONSTRAINT "):
            return None
        new_name = reader.identifier()
        if new_name is None or not reader.keyword(_PROMOTE_USING_INDEX):
            return None
        old_name = reader.identifier()
        if (
            old_name is None
            or not reader.keyword(";" + _IF_BLOCK_CLOSE)
            or not reader.at_end()
        ):
            return None
        return IndexRename(old_name=old_name, new_name=new_name, guarded=True)

    def enum_label_change(self, sql: str) -> EnumLabelChange | None:
        """A guarded ``CREATE TYPE ... AS ENUM``, an ``ADD VALUE`` or a guarded ``RENAME VALUE``.

        Each is read into its type and labels, then accepted only when this
        dialect's own renderer reproduces the statement from them exactly.
        """
        head = statement_head(sql)
        reader = self._reader(head)
        if reader.keyword(_ALTER_TYPE):
            return self._enum_value_added(head, reader)
        body = _do_block_body(head)
        if body is None:
            return None
        created = self._enum_type_created(head, body)
        return created if created is not None else self._enum_value_renamed(head, body)

    def _enum_value_added(
        self, head: str, reader: StatementReader
    ) -> EnumLabelChange | None:
        """Read the statement :meth:`render_add_enum_value` builds back."""
        target = _schema_and_name(reader)
        if target is None or not reader.keyword(_ADD_VALUE):
            return None
        label = reader.literal()
        if label is None:
            return None
        neighbour = _read_neighbour(reader)
        schema, type_name = target
        rendered = self.render_add_enum_value(
            type_name, label, (), neighbour=neighbour, schema=schema
        )
        if rendered != (head,):
            return None
        return EnumLabelChange(type_name=type_name, added=label, neighbour=neighbour)

    def _enum_type_created(self, head: str, body: str) -> EnumLabelChange | None:
        """Read the ``DO`` block :meth:`render_create_enum_type` builds back."""
        reader = self._reader(body)
        if not reader.keyword(_ENUM_TYPE_GUARD_OPEN):
            return None
        target = _schema_and_name(reader)
        if target is None or not reader.keyword(_ENUM_TYPE_AS_ENUM):
            return None
        labels = _label_list(reader)
        if labels is None:
            return None
        schema, type_name = target
        if self.render_create_enum_type(type_name, labels, schema=schema) != head:
            return None
        return EnumLabelChange(type_name=type_name, created=labels)

    def _enum_value_renamed(self, head: str, body: str) -> EnumLabelChange | None:
        """Read the ``DO`` block :meth:`render_rename_enum_value` builds back."""
        reader = self._reader(body)
        if not reader.keyword(_RENAME_GUARD_OPEN):
            return None
        old = _label_predicate(reader)
        if old is None or not reader.keyword(_RENAME_GUARD_CONFLICT):
            return None
        new = _label_predicate(reader)
        if new is None:
            return None
        type_name, schema, old_label = old
        new_label = new[2]
        if (
            self.render_rename_enum_value(
                type_name, old_label, new_label, schema=schema
            )
            != head
        ):
            return None
        return EnumLabelChange(type_name=type_name, renamed=(old_label, new_label))

    def guarded_creation(self, sql: str) -> str | None:
        """The ANSI guards, plus the ``DO`` guard of an ``ADD CONSTRAINT ... UNIQUE``."""
        guarded = super().guarded_creation(sql)
        if guarded is not None:
            return guarded
        head = statement_head(sql)
        reader = self._reader(head)
        if not reader.keyword("ALTER TABLE "):
            return None
        table_start = reader.position
        if reader.qualified() is None:
            return None
        table = head[table_start : reader.position]
        if not reader.keyword(" ADD CONSTRAINT "):
            return None
        constraint_name = reader.identifier()
        if constraint_name is None or not reader.keyword(" UNIQUE ("):
            return None
        return self._unique_constraint_guard(head, table, constraint_name)
