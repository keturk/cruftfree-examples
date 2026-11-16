"""SQL dialect protocol and base class with shared implementations.

SQLDialect is the structural Protocol that all dialects satisfy.
DialectBase is an optional concrete base that provides default implementations
for methods that are identical across multiple dialects (identifier and literal
quoting through the dialect's rows in ``cruftfree_rdbms_schema.sql_lowering``, empty
table_options). Subclasses override only what differs.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from cruftfree_codegen_kernel.sql_facts.dialects.catalog_read import (
    CatalogReadStatements,
)
from cruftfree_codegen_kernel.sql_facts.dialects.table_triggers import (
    TableTriggerStatements,
)

if TYPE_CHECKING:
    from cruftfree_rdbms_schema.catalog_reader import CatalogQuery

    from cruftfree_codegen_kernel.sql_facts.column_facts import ColumnDefinition
from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    EnumLabelChange,
    EnumNeighbour,
    ExternalQueueControlSql,
    IndexRename,
    ScheduledJobStateSql,
    SessionLockSql,
    WorkRecoverySql,
    WorkRecoveryUpdate,
)


# @pattern(sql/dialect-protocol): Structural contract for SQL dialect behavior (quoting, AI, features, fulltext)
# @rule: New engines extend SQLDialect implementations; shared defaults live on DialectBase where applicable
# @anti-pattern: Dialect-specific SQL string assembly scattered without dispatch through SQLDialect
@runtime_checkable
class SQLDialect(CatalogReadStatements, TableTriggerStatements, Protocol):
    """Protocol for SQL dialect-specific behavior.

    TypeRegistry handles type mappings; the dialect handles
    quoting, auto-increment syntax, table options, and feature flags.
    """

    @property
    def name(self) -> str:
        """Dialect name (e.g. 'postgresql')."""
        ...

    def quote_identifier(self, name: str) -> str:
        """Quote a SQL identifier (table name, column name) through the dialect's rows.

        PostgreSQL: "name". A name the dialect cannot quote safely (an embedded
        ``"`` or a NUL) raises ``ValueError``; it is never repaired.
        """
        ...

    def qualified_identifier(self, name: str, schema: str | None) -> str:
        """Quote *name*, behind its quoted *schema* when the block places objects in one.

        PostgreSQL: ``"schema"."name"`` (or ``"name"`` with no schema).

        Args:
            name: The object's name (table, index, type).
            schema: The block's PostgreSQL schema, or ``None``.
        """
        ...

    def quote_literal(self, value: str) -> str:
        """Quote *value* as a dialect-correct SQL string literal through the dialect's rows.

        The dialect's ``quote_string`` row (``cruftfree_rdbms_schema.sql_lowering.dialect_rows``)
        is the one home of its literal quoting. PostgreSQL (standard_conforming_strings
        on, the default): single quotes doubled, backslash treated as literal data.

        No code point ``hidden_in_source`` flags stands raw in the result:
        each dialect writes such a value in its engine's escape form, which
        decodes to exactly *value* (PostgreSQL: ``U&'…'``). A value the engine
        cannot store (a NUL, a lone surrogate) raises ``ValueError``.

        Returns the FULLY QUOTED literal, including its surrounding quotes.
        """
        ...

    def json_column_default(self, document: str) -> str:
        """The expression after ``DEFAULT`` on a JSON column whose default is *document*.

        PostgreSQL: the quoted document (``'[]'``), which the column's ``JSONB``
        type casts on insert.

        Args:
            document: The JSON text the column defaults to, such as ``[]``.
        """
        ...

    def session_lock_sql(self, key: str) -> SessionLockSql:
        """The statements of a session-scoped advisory lock named by the text *key*.

        The dialect derives its engine's lock identifier from *key* and quotes
        the text through ``quote_literal``; no caller concatenates the key into
        SQL. Callers reach this through :func:`session_lock_for`, which fails
        closed for a dialect that does not declare it.
        """
        ...

    def scheduled_job_state_sql(self) -> ScheduledJobStateSql:
        """The statements over the in-process scheduler's durable last-fire table.

        The table itself is part of the block's declared schema, created by the
        deploy's schema converge (``scheduled_job_state_table``); the dialect owns
        the select, insert-if-absent and upsert forms over it and whether its
        ``DateTime`` column stores naive UTC. Callers reach this through
        :func:`scheduled_job_state_for`,
        which fails closed for a dialect that does not declare it.
        """
        ...

    def external_queue_control_sql(self) -> ExternalQueueControlSql:
        """The statements over the durable control tables of external-queue consumers.

        Both tables are part of the store block's declared schema, created by the
        deploy's schema converge (``external_queue_control_tables``); the dialect owns
        the database-clock expression, the upsert forms and the state ranking over
        them. Callers reach this through
        :func:`external_queue_control_for`, which fails closed for a dialect that
        does not declare it.
        """
        ...

    def work_recovery_sql(self, update: WorkRecoveryUpdate) -> WorkRecoverySql:
        """The statements of one startup work recovery described by *update*.

        The dialect owns the transaction-scoped lock timeout, the update that
        returns each relabelled row's key, the current-timestamp expression,
        identifier quoting and every label's literal. Callers reach this through
        :func:`work_recovery_for`, which fails closed for a dialect without it.
        """
        ...

    def catalog_query(
        self,
        name: str,
        columns: tuple[tuple[str, str], ...],
        source: str,
        key_columns: tuple[str, ...],
    ) -> CatalogQuery:
        """The catalog query *name*: its rows as one JSON array, ordered by *key_columns*.

        *columns* are ``(key, expression)`` pairs selected from *source* (the
        ``FROM`` and ``WHERE`` text); the text is derived from them, so the column
        list is stated once. Each key is quoted as an identifier. No value is
        written into the text: the places the query reads are its first bound
        parameter, attached with :meth:`CatalogQuery.at_places`.

        PostgreSQL: ``SELECT COALESCE(json_agg(row_to_json(q.*) ORDER BY q."k", ...),
        '[]'::json) FROM (SELECT <expression> AS "k", ... <source>) AS q`` -- no rows
        is ``[]``, never SQL NULL.

        Raises:
            DialectFeatureError: The dialect declares no JSON aggregation.
            CatalogQueryDeclarationError: The declaration cannot identify its rows.
            ValueError: A key the dialect cannot quote as an identifier.
        """
        ...

    def auto_increment_type(self, base_type: str) -> str:
        """Get the auto-increment column type.

        PostgreSQL: BIGSERIAL (replaces BIGINT)
        """
        ...

    def supports_feature(self, feature: str) -> bool:
        """Check if dialect supports a specific feature.

        Features: 'arrays', 'fulltext_index', 'json_native',
                  'uuid_native', 'interval_type', 'inet_type'
        """
        ...

    def array_column_type(self, element_type: str) -> str:
        """Get the column type for an array of the given element type.

        PostgreSQL: element_type + '[]'
        """
        ...

    def table_options(self) -> str:
        """Get dialect-specific table options appended after CREATE TABLE.

        PostgreSQL: ''
        """
        ...

    def render_fulltext_index(
        self,
        index_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        if_not_exists: bool = False,
    ) -> str:
        """Render dialect-specific fulltext index SQL.

        Args:
            index_name: The index's name.
            table_name: The indexed table.
            columns: The indexed columns, in order.
            if_not_exists: Make the creation a no-op where the index exists
                (PostgreSQL's ``CREATE INDEX IF NOT EXISTS``).

        Raises DialectFeatureError if fulltext is not supported.
        """
        ...

    def render_spatial_index(
        self,
        index_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        if_not_exists: bool = False,
    ) -> str:
        """Render dialect-specific spatial index SQL for a geographic column.

        PostgreSQL: ``CREATE INDEX ... USING GIST (...)``

        A geographic column gets one of these automatically, so this is reached
        without any index declaration in the DSL.

        Args:
            index_name: The index's name.
            table_name: The indexed table.
            columns: The indexed columns.
            if_not_exists: Make the creation a no-op where the index exists
                (a dialect without the guard raises DialectFeatureError).

        Raises DialectFeatureError if spatial indexing is not supported.
        """
        ...

    def render_drop_index(
        self, index_name: str, table_name: str, *, if_exists: bool = False
    ) -> str:
        """Render dialect-specific DROP INDEX SQL.

        PostgreSQL: DROP INDEX "name";

        Args:
            index_name: The index's name.
            table_name: The indexed table.
            if_exists: Make the drop a no-op where the index is absent
                (PostgreSQL's ``DROP INDEX IF EXISTS``; a dialect without
                such a guard raises DialectFeatureError).
        """
        ...

    def render_add_unique_constraint(
        self,
        constraint_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        schema: str | None = None,
        if_not_exists: bool = False,
    ) -> str:
        """Render ``ALTER TABLE ... ADD CONSTRAINT <name> UNIQUE (<columns>)``.

        A declared unique is a unique CONSTRAINT, not a bare ``CREATE UNIQUE INDEX``.

        Args:
            constraint_name: The constraint's name.
            table_name: The table it constrains.
            columns: The constrained columns, in order.
            schema: The PostgreSQL schema holding the table, when the block places
                its tables in one; ignored by an engine without schemas.
            if_not_exists: Make the statement a no-op where the constraint already
                exists (PostgreSQL only; a dialect that cannot guard it raises
                :class:`~cruftfree_codegen_kernel.sql_facts.errors.DialectFeatureError`).
        """
        ...

    def render_drop_unique_constraint(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
        if_exists: bool = False,
    ) -> str:
        """Render the statement that drops a unique constraint.

        PostgreSQL: ``ALTER TABLE "t" DROP CONSTRAINT "name";``

        Args:
            constraint_name: The constraint's name.
            table_name: The constrained table.
            schema: The PostgreSQL schema holding the table, when the block places
                its tables in one; ignored by an engine without schemas.
            if_exists: Make the statement a no-op where the constraint is absent
                (PostgreSQL only; a dialect that cannot guard it raises
                :class:`~cruftfree_codegen_kernel.sql_facts.errors.DialectFeatureError`).
        """
        ...

    def render_add_check_constraint(
        self,
        constraint_name: str,
        table_name: str,
        predicate_sql: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render ``ALTER TABLE ... ADD CONSTRAINT <name> CHECK (<predicate_sql>)``.

        Args:
            constraint_name: The check's name.
            table_name: The table it constrains.
            predicate_sql: The row predicate, as the one SQL lowering renders it for
                this dialect (never author text).
            schema: The schema holding the table, when the block places its tables
                in one; ignored by an engine without schemas.
        """
        ...

    def render_drop_check_constraint(
        self, constraint_name: str, table_name: str, *, schema: str | None = None
    ) -> str:
        """Render the statement that drops the check constraint *constraint_name*."""
        ...

    def render_drop_column_unique_constraints(
        self,
        table_name: str,
        column_name: str,
        *,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """Render the statements that drop every single-column unique constraint on a column.

        A column's ``: unique`` constraint carries whatever name its creator gave it:
        the shared ``uq_`` name, or the engine's own (PostgreSQL ``<table>_<col>_key``)
        when an ORM or a migration declared the column
        ``UNIQUE`` inline. The constraints are therefore found in the catalog by
        what they constrain -- exactly this one column -- and dropped whatever they
        are called; a column holding none is left as it is.

        Args:
            table_name: The table holding the column.
            column_name: The constrained column.
            schema: The PostgreSQL schema holding the table, when the block places
                its tables in one; ignored by an engine without schemas.

        Returns:
            The statements, in execution order.
        """
        ...

    def render_set_column_default(
        self,
        table_name: str,
        column_name: str,
        default_sql: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render ``ALTER TABLE ... ALTER COLUMN ... SET DEFAULT <default_sql>``.

        PostgreSQL takes any expression. No row is rewritten: the default applies to rows
        inserted afterwards.

        Args:
            table_name: The table holding the column.
            column_name: The column.
            default_sql: The default as the dialect's SQL expression -- the same text
                a ``CREATE TABLE`` or ``ADD COLUMN`` places after ``DEFAULT``.
            schema: The PostgreSQL schema holding the table, when the block places
                its tables in one; ignored by an engine without schemas.
        """
        ...

    def render_drop_column_default(
        self,
        table_name: str,
        column_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render ``ALTER TABLE ... ALTER COLUMN ... DROP DEFAULT``.

        Every supported engine accepts it on a column that carries no default.
        """
        ...

    def render_rename_index(
        self,
        index_name: str,
        new_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the statement that renames index *index_name* to *new_name*.

        PostgreSQL: ``ALTER INDEX IF EXISTS "schema"."old" RENAME TO "new";`` --
        absent *index_name* is a no-op, so a rename is safe to run against a
        database that already carries the new name.

        Args:
            index_name: The index's current name.
            new_name: The name to give it.
            table_name: The table the index belongs to.
            schema: The PostgreSQL schema holding the index, when the block
                places its tables in one; ignored by an engine without schemas.
        """
        ...

    def render_promote_unique_index(
        self,
        index_name: str,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the statement that turns unique index *index_name* into a constraint.

        PostgreSQL: a guarded ``ALTER TABLE ... ADD CONSTRAINT "uq" UNIQUE USING INDEX
        "old"``, which adopts the existing index (renaming it to the constraint's
        name) instead of building a second one; when *index_name* is absent the
        statement is a no-op, so it is safe against a database already migrated.

        Args:
            index_name: The unique index's current name.
            constraint_name: The unique constraint's name.
            table_name: The table the index belongs to.
            schema: The PostgreSQL schema holding the table, when the block places
                its tables in one; ignored by an engine without schemas.
        """
        ...

    def tolerates_existence(self, sql: str) -> bool:
        """Whether statement *sql*, as this dialect renders it, runs whether or not its object exists.

        True for an existence-guarded creation or drop (``IF [NOT] EXISTS``, a
        catalog-probing ``DO`` block) and for a statement that does not touch the
        object (a session-setting toggle around a table drop). A spelling
        this dialect does not render reads ``False``: a chain replay then treats the
        statement as one that fails on a present (or absent) object, never the reverse.
        """
        ...

    def index_rename(self, sql: str) -> IndexRename | None:
        """Read the index rename (or unique-index promotion) statement *sql* back.

        Returns:
            The old and new names and whether the statement is guarded, or ``None``
            when *sql* is not a rename this dialect renders.
        """
        ...

    def enum_label_change(self, sql: str) -> EnumLabelChange | None:
        """Read the named-enum-type statement *sql* back: a creation, an append or a rename.

        Only the exact spelling this dialect's own ``render_create_enum_type``,
        ``render_add_enum_value`` and ``render_rename_enum_value`` emit is read; an
        engine with no named enum types reads every statement as ``None``.

        Returns:
            The labels the statement creates, appends or renames, or ``None`` when
            *sql* is not one of those statements as this dialect renders it.
        """
        ...

    def guarded_creation(self, sql: str) -> str | None:
        """*sql*, a creation this dialect renders, made a no-op where its object exists.

        The guarded form is the one the dialect's own renderer emits for the same
        creation with its existence guard on, so it leaves the same object behind on
        every database.

        Returns:
            The guarded statement, or ``None`` when the engine has no guard for this
            creation (or *sql* is not a creation this dialect renders).
        """
        ...

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
        """Render ``ALTER TABLE ... ADD CONSTRAINT <name> FOREIGN KEY ... ON DELETE <a> ON UPDATE <u>``.

        Both actions are stated, always: a constraint created with no action clause
        means ``NO ACTION``, which is neither the DSL's default (``restrict``) nor
        anything the author declared. They are DSL actions, spelled through the one
        shared mapping (:func:`~cruftfree_codegen_kernel.sql_facts.referential_actions.sql_referential_action`).

        Args:
            constraint_name: The constraint's name.
            table_name: The table that holds the foreign-key columns.
            columns: The local columns, in order.
            referred_table: The referred table (in the same schema as *table_name*).
            referred_columns: The referred columns, in order.
            on_delete: The DSL ``ON DELETE`` action.
            on_update: The DSL ``ON UPDATE`` action.
            schema: The PostgreSQL schema holding both tables, when the block places
                its tables in one; ignored by an engine without schemas.
            not_valid: Add the constraint without checking the rows already in the
                table, to be checked by :meth:`render_validate_foreign_key` -- the
                form that does not hold a long lock on a populated table
                (PostgreSQL). An engine that validates on add has no such form: the
                statement is the ordinary one and :meth:`render_validate_foreign_key`
                renders nothing.

        Raises:
            GenerationError: An action is not a DSL referential action.
        """
        ...

    def render_validate_foreign_key(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the statement that checks the rows against a ``not_valid`` constraint.

        PostgreSQL: ``ALTER TABLE ... VALIDATE CONSTRAINT "name";``. A dialect that
        validates the rows when the constraint is added returns ``""``.
        """
        ...

    def render_drop_foreign_key(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
        if_exists: bool = False,
    ) -> tuple[str, ...]:
        """Render the statements that drop a foreign key.

        PostgreSQL: ``ALTER TABLE "t" DROP CONSTRAINT [IF EXISTS] "name";``. A
        dialect without a guard of its own may answer *if_exists* with several
        statements, executed in order.

        Args:
            constraint_name: The constraint's name.
            table_name: The constrained table.
            schema: The PostgreSQL schema holding the table, when the block places
                its tables in one; ignored by an engine without schemas.
            if_exists: Make the drop a no-op where the constraint is absent.

        Returns:
            The statements, in execution order.
        """
        ...

    def rename_foreign_key_sql(
        self,
        old_name: str,
        new_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the statement that renames foreign key *old_name* of *table_name* to *new_name*.

        PostgreSQL: ``ALTER TABLE "t" RENAME CONSTRAINT "old" TO "new";``, unguarded: an
        absent *old_name* fails the statement. A dialect that does not declare
        :data:`~cruftfree_codegen_kernel.sql_facts.constants.FEATURE_RENAME_FOREIGN_KEY`
        refuses (:class:`DialectFeatureError`). *schema* is the PostgreSQL schema holding
        the table; an engine without schemas ignores it.
        """
        ...

    def render_create_table(
        self,
        table_name: str,
        columns: Sequence[ColumnDefinition],
        constraints: Sequence[str] = (),
        *,
        comment: str | None = None,
        source_note: str | None = None,
        schema: str | None = None,
    ) -> str:
        """Render ``CREATE TABLE`` with its columns and table constraints.

        Each column is its definition (:meth:`render_add_column` states the same
        one): quoted name, type, auto-increment suffix, ``NOT NULL``, ``DEFAULT``,
        and the inline comment of a dialect that has one. A column's source note,
        and *source_note* for the table, are ``--`` lines in the emitted file that
        never reach the catalog. Foreign keys, indexes and standalone comments are
        separate statements: a key may name a table created after this one.

        PostgreSQL: no table options, no inline comments.

        Args:
            table_name: The table.
            columns: The columns, in order.
            constraints: Table constraint clauses (primary key, unique, check), in
                order, each already a complete clause.
            comment: The table's database comment, carried inline where the
                dialect has an inline form.
            source_note: The table's source-channel note, or ``None``.
            schema: The PostgreSQL schema holding the table; ignored by an engine
                without schemas.
        """
        ...

    def render_add_column(
        self,
        table_name: str,
        column: ColumnDefinition,
        *,
        schema: str | None = None,
    ) -> str:
        """Render ``ALTER TABLE ... ADD COLUMN <definition>``.

        The definition is the one :meth:`render_create_table` gives the column. A
        column comment on a dialect with no inline form is a separate
        :meth:`render_column_comment` statement.
        """
        ...

    def render_drop_column(
        self,
        table_name: str,
        column_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render ``ALTER TABLE ... DROP COLUMN <column>``."""
        ...

    def render_alter_column_type(
        self,
        table_name: str,
        column: ColumnDefinition,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the statement that gives *column* its new type, ``column.sql_type``.

        PostgreSQL: ``ALTER COLUMN "c" TYPE <type> USING "c"::<type>`` -- the cast
        rule is :func:`~cruftfree_rdbms_schema.type_change_cast.type_change_using_clause`.
        """
        ...

    def render_alter_nullability(
        self,
        table_name: str,
        column: ColumnDefinition,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the statement that makes *column* as nullable as ``column.nullable``.

        PostgreSQL: ``ALTER COLUMN "c" SET NOT NULL`` / ``DROP NOT NULL``.

        Rows already holding NULL fail a move to ``NOT NULL``; the backfill that
        precedes it is the caller's statement, not part of this one.
        """
        ...

    def render_create_enum_type(
        self,
        type_name: str,
        labels: Sequence[str],
        *,
        schema: str | None = None,
    ) -> str:
        """Render the idempotent creation of a named enum type holding *labels*.

        PostgreSQL: a ``DO`` block running ``CREATE TYPE ... AS ENUM`` that
        swallows only ``duplicate_object`` / ``unique_violation``, so a revision
        re-applied over an existing type succeeds. A dialect that carries the
        labels inline in each column's type refuses: there is no type to create.

        Raises:
            DialectFeatureError: The dialect keeps no named enum types.
        """
        ...

    def render_drop_enum_type(
        self,
        type_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the drop of named enum type *type_name* where the database holds it.

        PostgreSQL: ``DROP TYPE IF EXISTS ...`` -- guarded, so a rollback over a
        database that never held the type succeeds. A dialect that carries the
        labels inline in each column's type refuses: there is no type to drop.

        Raises:
            DialectFeatureError: The dialect keeps no named enum types.
        """
        ...

    def render_add_enum_value(
        self,
        type_name: str,
        label: str,
        columns: Sequence[tuple[str, ColumnDefinition]],
        *,
        neighbour: EnumNeighbour | None,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """Render the statements that add *label* to enum type *type_name*.

        PostgreSQL: ``ALTER TYPE ... ADD VALUE IF NOT EXISTS '<label>'``, then
        ``AFTER``/``BEFORE`` *neighbour* -- guarded, because a database may already
        hold the label, and placed, because the type's label order is its sort
        order and a bare ``ADD VALUE`` appends; *columns* is not consulted. A
        dialect that keeps the labels in every column typed with the enum restates
        each ``(table, column)`` in *columns* whole, its ``sql_type`` already the
        full label list in declared order.

        Args:
            type_name: The enum type's database name.
            label: The stored label being added.
            columns: Every ``(table name, column)`` typed with the enum, with the
                column's definition after the addition.
            neighbour: Where the label goes (:func:`enum_label_neighbour`);
                ``None`` appends it, which only a statement recorded before labels
                were placed, or a type with no other label, carries.
            schema: The PostgreSQL schema holding the type.

        Returns:
            The statements, in execution order.
        """
        ...

    def render_relocate_schema(
        self,
        old_schema: str | None,
        new_schema: str | None,
        enum_types: Sequence[str],
        tables: Sequence[str],
    ) -> tuple[str, ...]:
        """Render the statements that move a block's enum types and tables to *new_schema*.

        PostgreSQL: ``ALTER TYPE ... SET SCHEMA`` for each type, then ``ALTER
        TABLE ... SET SCHEMA`` for each table; ``None`` on either side is the
        default schema, ``public``. The target schema must already exist.

        Raises:
            DialectFeatureError: The dialect has no schema namespaces.
        """
        ...

    def render_drop_table(
        self,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """Render the drop of *table_name* together with the foreign keys other tables hold on it.

        Two tables created in one revision may reference each other, so no drop order is
        safe by itself. PostgreSQL: ``DROP TABLE IF EXISTS ... CASCADE;`` (the dependent
        constraints go with it). A dialect without such a clause may need several
        statements, executed in order. Each item is one statement,
        because a driver without multi-statement support runs one statement per call.
        """
        ...

    def render_rename_enum_value(
        self,
        type_name: str,
        old_label: str,
        new_label: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Render the rename of one label of a named enum type.

        PostgreSQL: a ``DO`` block running ``ALTER TYPE ... RENAME VALUE`` only while the
        type holds *old_label*, so a re-applied revision is a no-op, and raising when the
        type holds both labels (rows under the old one would be stranded: there is no
        ``ALTER TYPE ... DROP VALUE``). *schema* names where the catalog looks for the
        type; ``None`` matches the type visible on the ``search_path``.

        Raises:
            DialectFeatureError: The dialect keeps no named enum types.
        """
        ...

    def render_create_schema(self, schema: str) -> str:
        """Render the creation of *schema* when the database does not hold it yet.

        PostgreSQL: a ``DO`` block creating the schema behind a ``pg_namespace`` probe --
        not ``CREATE SCHEMA IF NOT EXISTS``, which the engine checks for CREATE-on-database
        first, refusing a least-privilege migration role on a schema that exists.

        Raises:
            DialectFeatureError: The dialect has no schema namespaces.
        """
        ...

    def render_drop_schema(self, schema: str) -> str:
        """Render the removal of *schema* when the database holds it.

        PostgreSQL: ``DROP SCHEMA IF EXISTS "schema";`` -- without ``CASCADE``, so a
        schema still holding an object is refused rather than emptied.

        Raises:
            DialectFeatureError: The dialect has no schema namespaces.
        """
        ...

    def render_set_search_path(self, schema: str) -> str:
        """Render the statement that resolves unqualified names in *schema* for the transaction.

        PostgreSQL: ``SET LOCAL search_path TO "schema", public;`` -- scoped to the
        transaction, so no pooled session keeps it; ``public`` stays behind it for the
        extension types and functions that live there.

        Raises:
            DialectFeatureError: The dialect has no schema namespaces.
        """
        ...

    def render_table_comment(self, table_name: str, comment: str | None) -> str:
        """Render the statement that sets (or clears) a table's comment.

        PostgreSQL: ``COMMENT ON TABLE "t" IS '...';``

        A ``None`` *comment* clears it, which is what a DSL edit that removes
        the entity's ``///`` documentation means.
        """
        ...

    def render_column_comment(
        self,
        table_name: str,
        column_name: str,
        column_definition: str,
        comment: str | None,
    ) -> str:
        """Render the statement that sets (or clears) a column's comment.

        PostgreSQL has a standalone ``COMMENT ON COLUMN``. *column_definition*
        is the column's current type and modifiers (everything after its name
        in a ``CREATE TABLE`` body), which only a dialect that restates the
        column to change its comment needs; a dialect with a standalone
        statement ignores it.
        """
        ...

    def inline_column_comment(self, comment: str | None) -> str:
        """The fragment appended to a column definition inside CREATE TABLE.

        A dialect may carry a column's comment inline (`` COMMENT '...'``);
        PostgreSQL has no inline form and returns ``""``, emitting separate
        ``COMMENT ON`` statements after the table instead.
        """
        ...

    def inline_table_comment(self, comment: str | None) -> str:
        """The fragment appended to the CREATE TABLE options clause.

        PostgreSQL returns ``""`` -- see
        :meth:`inline_column_comment`.
        """
        ...
