"""Shared SQL constants: dialect feature names and tenant scoping.

Read by the SQL generator's DDL and migration paths and by every language
generator's migration adapter. The DDL dialect names are not here: they live in
:mod:`cruftfree_common.config.datasource.ddl_dialect_names`. Index and constraint NAMES
are not here either: they come from :mod:`cruftfree_rdbms_schema.index_naming`, the one
naming rule.
"""

from __future__ import annotations

# --- Dialect features (``SQLDialect.supports_feature``) ----------------------
#: The engine keeps an enum as a standalone named type (``CREATE TYPE ... AS ENUM``)
#: rather than carrying the labels inline in each column's type.
FEATURE_NAMED_ENUM_TYPES: str = "named_enum_types"
#: The engine has schema namespaces a block places its tables and types in, reached
#: through the search path; an engine without them treats a schema as the database.
FEATURE_SCHEMA_NAMESPACES: str = "schema_namespaces"
#: The engine can make an index creation a no-op where the index exists
#: (``CREATE INDEX IF NOT EXISTS``).
FEATURE_GUARDED_INDEX_CREATION: str = "guarded_index_creation"
#: The engine realizes a database-enforced rule over a table's rows (append-only, an
#: aggregate invariant checked at commit) as triggers.
FEATURE_TABLE_TRIGGERS: str = "table_triggers"
#: The engine renames a foreign-key constraint in place; an engine without it drops the
#: key under its old name and adds it, validated, under the new one.
FEATURE_RENAME_FOREIGN_KEY: str = "rename_foreign_key"
#: A label the engine adds to a named enum type can be used only once the transaction that
#: added it commits (PostgreSQL *ALTER TYPE*: "the new value cannot be used until after the
#: transaction has been committed", SQLSTATE 55P04), so an apply commits its label additions
#: before every other change.
FEATURE_ENUM_LABEL_COMMITTED_BEFORE_USE: str = "enum_label_committed_before_use"

# --- Tenant scoping ---------------------------------------------------------
TENANT_ID_COLUMN: str = "tenant_id"
