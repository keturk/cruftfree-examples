"""The base class of the shipped SQL dialects."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, NoReturn

from cruftfree_common.errors.generation import GenerationError
from cruftfree_common.utils.sql_text import sql_line_comment_lines
from cruftfree_rdbms_schema.sql_lowering.dialect_rows import dialect_rows
from cruftfree_rdbms_schema.type_change_cast import type_change_using_clause

from cruftfree_codegen_kernel.sql_facts.constants import FEATURE_GUARDED_INDEX_CREATION
from cruftfree_codegen_kernel.sql_facts.dialects.catalog_read import CatalogReadRefusals
from cruftfree_codegen_kernel.sql_facts.dialects.table_triggers import (
    TableTriggerRefusals,
)
from cruftfree_codegen_kernel.sql_facts.errors import DialectFeatureError
from cruftfree_codegen_kernel.sql_facts.referential_actions import (
    sql_referential_action,
)

if TYPE_CHECKING:
    from cruftfree_rdbms_schema.catalog_reader import CatalogQuery

    from cruftfree_codegen_kernel.sql_facts.column_facts import ColumnDefinition
from cruftfree_codegen_kernel.sql_facts.dialects._dialect_statement_types import (
    _GUARDED_INDEX_HEADS,
    _GUARDED_TABLE_HEADS,
    CREATE_INDEX_HEAD,
    CREATE_TABLE_HEAD,
    IF_NOT_EXISTS,
    EnumLabelChange,
    EnumNeighbour,
    IndexRename,
    StatementReader,
    statement_head,
)


class DialectBase(CatalogReadRefusals, TableTriggerRefusals):
    """Concrete base class with shared dialect implementations.

    Provides default implementations for:
    - quote_identifier, quote_literal: the dialect's rows
      (``cruftfree_rdbms_schema.sql_lowering.dialect_rows``), keyed by ``name``
    - table_options: empty string (PostgreSQL)

    - render_fulltext_index: refuses (:class:`DialectFeatureError`) -- a fulltext
      index has exactly one realization (a PostgreSQL GIN expression index), so a
      dialect that does not override it does not realize the kind

    Subclasses MUST override:
    - name (property)
    - auto_increment_type
    - supports_feature
    - array_column_type
    - render_spatial_index
    - render_rename_index
    - render_promote_unique_index

    Subclasses with no unique-constraint syntax of their own inherit the ANSI form
    (``ALTER TABLE ... ADD CONSTRAINT ... UNIQUE``), which every supported engine
    accepts:
    - render_add_unique_constraint
    - render_drop_unique_constraint (PostgreSQL's ``DROP CONSTRAINT``)

    Table and column DDL is shared: ``render_create_table``, ``render_add_column``
    and ``render_drop_column`` state one column definition for every dialect;
    ``render_alter_column_type`` and ``render_alter_nullability`` default to the
    PostgreSQL ``ALTER COLUMN`` forms, and ``render_drop_table`` to the PostgreSQL
    ``CASCADE`` form. The named-enum and schema-namespace statements
    (``render_create_enum_type``, ``render_add_enum_value``,
    ``render_rename_enum_value``, ``render_relocate_schema``,
    ``render_create_schema``, ``render_drop_schema``, ``render_set_search_path``),
    ``rename_foreign_key_sql``,
    ``catalog_query`` and the catalog-read statements (``abort_unless_sql``,
    ``server_version_sql``, ``catalog_search_path_sql``, ``catalog_read_begin_sql``,
    ``catalog_read_commit_sql``,
    ``catalog_client``, ``catalog_document_sql``, ``catalog_fingerprint_guard_sql``, from
    :class:`CatalogReadRefusals`)
    refuse unless a
    dialect overrides them.
    """

    def _refuse_unguardable(self, statement: str, constraint_name: str) -> NoReturn:
        """Raise: this dialect has no existence guard for *statement*.

        Raises:
            DialectFeatureError: Always.
        """
        raise DialectFeatureError(
            f"The {self.name} dialect cannot make '{statement}' of constraint "  # type: ignore[attr-defined]
            f"'{constraint_name}' conditional on its existence: the engine has no "
            "such guard. Only PostgreSQL does."
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
        """``ALTER TABLE t ADD CONSTRAINT name UNIQUE (cols);`` -- the ANSI form."""
        if if_not_exists:
            self._refuse_unguardable("ADD CONSTRAINT UNIQUE", constraint_name)
        quoted_cols = ", ".join(self.quote_identifier(c) for c in columns)
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ADD CONSTRAINT {self.quote_identifier(constraint_name)} UNIQUE ({quoted_cols});"
        )

    def render_drop_unique_constraint(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
        if_exists: bool = False,
    ) -> str:
        """``ALTER TABLE t DROP CONSTRAINT name;`` -- the ANSI form."""
        if if_exists:
            self._refuse_unguardable("DROP CONSTRAINT", constraint_name)
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"DROP CONSTRAINT {self.quote_identifier(constraint_name)};"
        )

    def render_add_check_constraint(
        self,
        constraint_name: str,
        table_name: str,
        predicate_sql: str,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER TABLE t ADD CONSTRAINT name CHECK (<predicate>);`` -- the ANSI form."""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ADD CONSTRAINT {self.quote_identifier(constraint_name)} CHECK ({predicate_sql});"
        )

    def render_drop_check_constraint(
        self, constraint_name: str, table_name: str, *, schema: str | None = None
    ) -> str:
        """``ALTER TABLE t DROP CONSTRAINT name;`` -- the ANSI form."""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"DROP CONSTRAINT {self.quote_identifier(constraint_name)};"
        )

    def _identifier_quote(self) -> str:
        """The character this dialect quotes an identifier with (ANSI double quote)."""
        return '"'

    def _reader(self, sql: str) -> StatementReader:
        """A reader over *sql* in this dialect's identifier quoting."""
        return StatementReader(sql, self._identifier_quote())

    def _guarded_heads(self) -> tuple[str, ...]:
        """The guarded statement heads this dialect renders."""
        if self.supports_feature(FEATURE_GUARDED_INDEX_CREATION):  # type: ignore[attr-defined]
            return _GUARDED_TABLE_HEADS + _GUARDED_INDEX_HEADS
        return _GUARDED_TABLE_HEADS

    def _drops_constraint_if_exists(self, head: str) -> bool:
        """Whether *head* is ``ALTER TABLE t DROP CONSTRAINT IF EXISTS c;``."""
        reader = self._reader(head)
        return (
            reader.keyword("ALTER TABLE ")
            and reader.qualified() is not None
            and reader.keyword(" DROP CONSTRAINT IF EXISTS ")
        )

    def tolerates_existence(self, sql: str) -> bool:
        """See :meth:`SQLDialect.tolerates_existence` (the guards every dialect spells alike)."""
        head = statement_head(sql)
        return head.startswith(
            self._guarded_heads()
        ) or self._drops_constraint_if_exists(head)

    def index_rename(self, sql: str) -> IndexRename | None:
        """No rename spelling of its own: a dialect rendering one reads it back."""
        del sql
        return None

    def enum_label_change(self, sql: str) -> EnumLabelChange | None:
        """No named enum types of its own: a dialect rendering them reads them back."""
        del sql
        return None

    def guarded_creation(self, sql: str) -> str | None:
        """``IF NOT EXISTS`` after ``CREATE TABLE`` / ``CREATE INDEX`` where the engine takes it."""
        head = statement_head(sql)
        note = sql[: len(sql) - len(head)]
        if head.startswith(CREATE_TABLE_HEAD + IF_NOT_EXISTS):
            return None
        if head.startswith(CREATE_TABLE_HEAD):
            return (
                note
                + CREATE_TABLE_HEAD
                + IF_NOT_EXISTS
                + head[len(CREATE_TABLE_HEAD) :]
            )
        guards_index = self.supports_feature(FEATURE_GUARDED_INDEX_CREATION)  # type: ignore[attr-defined]
        if (
            guards_index
            and head.startswith(CREATE_INDEX_HEAD)
            and not head.startswith(CREATE_INDEX_HEAD + IF_NOT_EXISTS)
        ):
            return (
                note
                + CREATE_INDEX_HEAD
                + IF_NOT_EXISTS
                + head[len(CREATE_INDEX_HEAD) :]
            )
        return None

    def render_drop_column_unique_constraints(
        self,
        table_name: str,
        column_name: str,
        *,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """Refuse: finding a constraint by what it constrains needs the engine's catalog.

        Raises:
            DialectFeatureError: Always; a dialect with a catalog lookup overrides it.
        """
        raise DialectFeatureError(
            f"The {self.name} dialect cannot drop the unique constraint of column "  # type: ignore[attr-defined]
            f"'{table_name}.{column_name}': the constraint may carry any name its creator "
            "gave it, and this dialect declares no catalog lookup to find it by its "
            "column. Fix: implement render_drop_column_unique_constraints for the dialect."
        )

    def render_set_column_default(
        self,
        table_name: str,
        column_name: str,
        default_sql: str,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER TABLE t ALTER COLUMN c SET DEFAULT <expr>;`` -- the ANSI form."""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ALTER COLUMN {self.quote_identifier(column_name)} SET DEFAULT {default_sql};"
        )

    def render_drop_column_default(
        self,
        table_name: str,
        column_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER TABLE t ALTER COLUMN c DROP DEFAULT;`` -- the ANSI form."""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ALTER COLUMN {self.quote_identifier(column_name)} DROP DEFAULT;"
        )

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
        """The ANSI ``ADD CONSTRAINT ... FOREIGN KEY`` form, both actions stated.

        ``not_valid`` is not consulted here: this form validates the rows as it adds
        the constraint, so there is no deferred form to request (PostgreSQL overrides).
        """
        quoted_cols = ", ".join(self.quote_identifier(c) for c in columns)
        quoted_referred = ", ".join(self.quote_identifier(c) for c in referred_columns)
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ADD CONSTRAINT {self.quote_identifier(constraint_name)} "
            f"FOREIGN KEY ({quoted_cols}) "
            f"REFERENCES {self.qualified_identifier(referred_table, schema)} ({quoted_referred}) "
            f"ON DELETE {sql_referential_action(on_delete)} "
            f"ON UPDATE {sql_referential_action(on_update)};"
        )

    def render_validate_foreign_key(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Nothing to validate: this form checked the rows when it added the constraint."""
        return ""

    def render_drop_foreign_key(
        self,
        constraint_name: str,
        table_name: str,
        *,
        schema: str | None = None,
        if_exists: bool = False,
    ) -> tuple[str, ...]:
        """``ALTER TABLE t DROP CONSTRAINT name;`` -- the ANSI form."""
        if if_exists:
            self._refuse_unguardable("DROP CONSTRAINT", constraint_name)
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"DROP CONSTRAINT {self.quote_identifier(constraint_name)};",
        )

    def rename_foreign_key_sql(
        self,
        old_name: str,
        new_name: str,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Refuse: this dialect declares no statement that renames a constraint."""
        self._refuse_feature(
            "a foreign-key rename",
            old_name,
            "the engine declares no statement that renames a constraint in place, so the "
            "key is dropped under its old name and added, validated, under the new one.",
        )

    def _column_definition(self, column: ColumnDefinition) -> str:
        """*column* as it is defined inside ``CREATE TABLE`` and ``ADD COLUMN``.

        Quoted name, type, ``NOT NULL``, ``DEFAULT``, then the inline comment (a
        dialect with one).
        """
        parts = [self.quote_identifier(column.name), column.sql_type]  # type: ignore[attr-defined]
        if not column.nullable:
            parts.append("NOT NULL")
        if column.default is not None:
            parts.append(f"DEFAULT {column.default}")
        return " ".join(parts) + self.inline_column_comment(column.comment)

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
        """``CREATE TABLE`` with one column or constraint per line (see :class:`SQLDialect`)."""
        if not columns:
            raise GenerationError(
                f"Cannot render CREATE TABLE for '{table_name}': no columns were given. "
                "Expected at least one column definition; a table with no columns is "
                "refused by every supported engine. Fix: declare a field on the entity."
            )
        lines = list(sql_line_comment_lines(source_note))
        lines.append(f"CREATE TABLE {self.qualified_identifier(table_name, schema)} (")
        for position, column in enumerate(columns, start=1):
            lines.extend(f"    {note}" for note in column.source_note_lines)
            separator = "," if position < len(columns) or constraints else ""
            lines.append(f"    {self._column_definition(column)}{separator}")
        for position, constraint in enumerate(constraints, start=1):
            separator = "," if position < len(constraints) else ""
            lines.append(f"    {constraint}{separator}")
        lines.append(f"){self.table_options()}{self.inline_table_comment(comment)};")
        return "\n".join(lines)

    def render_add_column(
        self,
        table_name: str,
        column: ColumnDefinition,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER TABLE t ADD COLUMN <definition>;``."""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ADD COLUMN {self._column_definition(column)};"
        )

    def render_drop_column(
        self,
        table_name: str,
        column_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER TABLE t DROP COLUMN c;``."""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"DROP COLUMN {self.quote_identifier(column_name)};"
        )

    def render_alter_column_type(
        self,
        table_name: str,
        column: ColumnDefinition,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER COLUMN c TYPE t`` with the dialect's cast clause (PostgreSQL form; a dialect may override)."""
        using_clause = type_change_using_clause(column.name, column.sql_type, self.name)  # type: ignore[attr-defined]
        cast = f" {using_clause}" if using_clause else ""
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ALTER COLUMN {self.quote_identifier(column.name)} TYPE {column.sql_type}{cast};"
        )

    def render_alter_nullability(
        self,
        table_name: str,
        column: ColumnDefinition,
        *,
        schema: str | None = None,
    ) -> str:
        """``ALTER COLUMN c SET NOT NULL`` / ``DROP NOT NULL`` (PostgreSQL form; a dialect may override)."""
        change = "DROP NOT NULL" if column.nullable else "SET NOT NULL"
        return (
            f"ALTER TABLE {self.qualified_identifier(table_name, schema)} "
            f"ALTER COLUMN {self.quote_identifier(column.name)} {change};"
        )

    def _refuse_feature(self, feature: str, subject: str, reason: str) -> NoReturn:
        """Raise: this dialect does not realize *feature*.

        Raises:
            DialectFeatureError: Always, naming the subject and why.
        """
        raise DialectFeatureError(
            f"The {self.name} dialect cannot render {feature} for '{subject}': {reason} "  # type: ignore[attr-defined]
            "Only PostgreSQL realizes it."
        )

    def render_create_enum_type(
        self,
        type_name: str,
        labels: Sequence[str],
        *,
        schema: str | None = None,
    ) -> str:
        """Refuse: this dialect keeps an enum's labels in each column, not in a named type."""
        self._refuse_feature(
            "an enum type creation",
            type_name,
            "the engine keeps an enum's labels inline in each column's type, so there is "
            "no type to create; the columns carry the labels.",
        )

    def render_drop_enum_type(
        self,
        type_name: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Refuse: this dialect keeps an enum's labels in each column, not in a named type."""
        self._refuse_feature(
            "an enum type drop",
            type_name,
            "the engine keeps an enum's labels inline in each column's type, so there is "
            "no type to drop; dropping the columns drops the labels.",
        )

    def render_add_enum_value(
        self,
        type_name: str,
        label: str,
        columns: Sequence[tuple[str, ColumnDefinition]],
        *,
        neighbour: EnumNeighbour | None,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """Refuse: this dialect declares no way to extend an enum (PostgreSQL overrides)."""
        self._refuse_feature(
            "an enum value append",
            type_name,
            f"no statement is declared that appends label {label!r} to the enum.",
        )

    def render_relocate_schema(
        self,
        old_schema: str | None,
        new_schema: str | None,
        enum_types: Sequence[str],
        tables: Sequence[str],
    ) -> tuple[str, ...]:
        """Refuse: this dialect has no schema namespaces to move objects between."""
        self._refuse_feature(
            "a schema relocation",
            f"{old_schema} -> {new_schema}",
            "a schema of this engine is the database the connection chose, not a "
            "namespace an RDBMS block moves its tables and types between.",
        )

    def render_drop_table(
        self,
        table_name: str,
        *,
        schema: str | None = None,
    ) -> tuple[str, ...]:
        """``DROP TABLE IF EXISTS t CASCADE;`` (PostgreSQL form; a dialect may override)."""
        return (
            f"DROP TABLE IF EXISTS {self.qualified_identifier(table_name, schema)} CASCADE;",
        )

    def render_rename_enum_value(
        self,
        type_name: str,
        old_label: str,
        new_label: str,
        *,
        schema: str | None = None,
    ) -> str:
        """Refuse: this dialect keeps an enum's labels in each column, not in a named type."""
        self._refuse_feature(
            "an enum label rename",
            type_name,
            f"the engine keeps an enum's labels inline in each column's type, so label "
            f"{old_label!r} is renamed by restating every column typed with the enum.",
        )

    def render_create_schema(self, schema: str) -> str:
        """Refuse: this dialect has no schema namespaces to create."""
        self._refuse_feature(
            "a schema creation",
            schema,
            "a schema of this engine is the database the connection chose, not a "
            "namespace a revision creates.",
        )

    def render_drop_schema(self, schema: str) -> str:
        """Refuse: this dialect has no schema namespaces to drop."""
        self._refuse_feature(
            "a schema removal",
            schema,
            "a schema of this engine is the database the connection chose, not a "
            "namespace a revision drops.",
        )

    def render_set_search_path(self, schema: str) -> str:
        """Refuse: this dialect has no schema namespaces to resolve names in."""
        self._refuse_feature(
            "a search path",
            schema,
            "a schema of this engine is the database the connection chose, so names "
            "resolve in it without a search path.",
        )

    def catalog_query(
        self,
        name: str,
        columns: tuple[tuple[str, str], ...],
        source: str,
        key_columns: tuple[str, ...],
    ) -> CatalogQuery:
        """Refuse: this dialect declares no JSON aggregation to return a catalog fact as one document."""
        self._refuse_feature(
            "a catalog query",
            name,
            "its rows are returned as one JSON array ordered by their key columns, and this "
            "dialect declares no JSON aggregation to render that with.",
        )

    def render_fulltext_index(
        self,
        index_name: str,
        table_name: str,
        columns: tuple[str, ...],
        *,
        if_not_exists: bool = False,
    ) -> str:
        """Refuse: this dialect has no fulltext-index realization.

        Raises:
            DialectFeatureError: Always. Names the index, the table and the one
                engine that realizes the kind.
        """
        raise DialectFeatureError(
            f"The {self.name} dialect does not support fulltext indexes. "  # type: ignore[attr-defined]
            f"Requested fulltext index '{index_name}' on '{table_name}' columns: "
            f"{list(columns)}. A fulltext index is realized only on PostgreSQL "
            "(a GIN index over to_tsvector); use PostgreSQL, or a SearchBlock with "
            "Elasticsearch/OpenSearch for this engine."
        )

    def quote_identifier(self, name: str) -> str:
        """*name* as a quoted identifier, through this dialect's identifier row."""
        return dialect_rows(self.name).quote_identifier(name)  # type: ignore[attr-defined]

    def qualified_identifier(self, name: str, schema: str | None) -> str:
        """*name* quoted, behind its quoted *schema* when there is one (ANSI form)."""
        quoted = self.quote_identifier(name)
        if schema is None:
            return quoted
        return f"{self.quote_identifier(schema)}.{quoted}"

    def quote_literal(self, value: str) -> str:
        """*value* as a string constant, through this dialect's string-literal row."""
        return dialect_rows(self.name).quote_string(value)  # type: ignore[attr-defined]

    def json_column_default(self, document: str) -> str:
        """The quoted document, a literal default (PostgreSQL form; a dialect may override)."""
        return self.quote_literal(document)

    def table_options(self) -> str:
        """Return empty table options (a dialect may override)."""
        return ""

    def render_drop_index(
        self, index_name: str, table_name: str, *, if_exists: bool = False
    ) -> str:
        """Render DROP INDEX SQL (PostgreSQL form; a dialect may override).

        PostgreSQL drops an index by name without referencing the table.
        """
        guard = "IF EXISTS " if if_exists else ""
        return f"DROP INDEX {guard}{self.quote_identifier(index_name)};"

    def comment_literal(self, comment: str | None) -> str:
        """*comment* as a SQL literal, or ``NULL`` when it is being cleared.

        Routes through :meth:`quote_literal` (the dialect's string-literal row):
        comment bodies are DSL author text, so this is an injection surface,
        not a formatting convenience.
        """
        if comment is None:
            return "NULL"
        return self.quote_literal(comment)

    def render_table_comment(self, table_name: str, comment: str | None) -> str:
        """Render ``COMMENT ON TABLE`` (PostgreSQL form; a dialect may override)."""
        return (
            f"COMMENT ON TABLE {self.quote_identifier(table_name)} "
            f"IS {self.comment_literal(comment)};"
        )

    def render_column_comment(
        self,
        table_name: str,
        column_name: str,
        column_definition: str,
        comment: str | None,
    ) -> str:
        """Render ``COMMENT ON COLUMN`` (PostgreSQL form; a dialect may override).

        *column_definition* is unused here: PostgreSQL sets a column comment
        without restating the column.
        """
        del column_definition
        return (
            f"COMMENT ON COLUMN {self.quote_identifier(table_name)}."
            f"{self.quote_identifier(column_name)} IS {self.comment_literal(comment)};"
        )

    def inline_column_comment(self, comment: str | None) -> str:
        """No inline column comment (PostgreSQL form; a dialect may override)."""
        del comment
        return ""

    def inline_table_comment(self, comment: str | None) -> str:
        """No inline table comment (PostgreSQL form; a dialect may override)."""
        del comment
        return ""
