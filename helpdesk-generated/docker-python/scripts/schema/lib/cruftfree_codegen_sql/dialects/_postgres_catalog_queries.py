"""Catalog queries of the PostgreSQL reflector."""

from __future__ import annotations

import logging

from cruftfree_codegen_kernel.sql_facts.dialects.dialect_table import sql_dialect
from cruftfree_common.config.datasource.ddl_dialect_names import POSTGRESQL_DDL_DIALECT
from cruftfree_rdbms_schema.catalog_reader import SCHEMA_NAME_KEY
from cruftfree_rdbms_schema.definition_naming import DEFINITION_DIGEST_LENGTH
from cruftfree_rdbms_schema.trigger_naming import (
    TRIGGER_AGGREGATE_INVARIANT,
    TRIGGER_APPEND_ONLY,
    TRIGGER_KIND,
)

from cruftfree_codegen_sql.dialects._reflection_common import TABLE_NAME_KEY

logger = logging.getLogger(__name__)

# ── Constants ──

ENGINE_NAME = "postgres"

# The snapshot format identity is owned by cruftfree_rdbms_schema.schema_snapshot
# (SCHEMA_FORMAT / SCHEMA_VERSION) and imported, never re-declared here: a
# per-adapter copy of a shared format version is exactly what let a reflector drift
# a version behind the format and stamp version-1 snapshots after the format bumped.

# pg_type.typtype value for enum types.
_TYPTYPE_ENUM = "e"

# The DDL dialect this engine's column defaults were written in, which the
# lowering rows key their SQL by.
_DDL_DIALECT = POSTGRESQL_DDL_DIALECT

# Map pg_constraint confdeltype / confupdtype codes to canonical action strings.
_FK_ACTION_CODES: dict[str, str] = {
    "a": "NO ACTION",
    "r": "RESTRICT",
    "c": "CASCADE",
    "n": "SET NULL",
    "d": "SET DEFAULT",
}


# ── Catalog queries (read-only, fixed text) ──
#
# One query per catalog fact. Each reads every object of the places bound as $1
# and returns the place (schema_name) and, for a table fact, the table
# (table_name) as row columns, so its text holds no value and is the same for
# every block. Every query selects only ordinary tables (relkind 'r'), and
# only objects of the block: an object an extension created is the
# extension's (PostGIS's spatial_ref_sys table lives in the schema it is
# installed in, as on a generated stack).
#
# Every catalog column of PostgreSQL's single-byte internal type "char"
# (pg_type.typtype, pg_attribute.attgenerated, pg_constraint.confdeltype /
# confupdtype, ...) is selected cast to text. Drivers disagree on that type:
# asyncpg decodes it as bytes (b"e"), so an uncast code never equals the str
# codes the reader compares against and every enum column, generated column
# and referential action is misread. Cast, every driver returns str.

_DIALECT = sql_dialect(_DDL_DIALECT)

#: The filter every query reads its places by: the schemas bound as ``$1``.
_IN_PLACES = "n.nspname = ANY($1::text[])"


def _not_an_extension_member(alias: str, catalog: str) -> str:
    """The filter keeping the *catalog* row *alias* only when no extension created it.

    ``CREATE EXTENSION`` records each object it creates as a member: a ``pg_depend``
    row of dependency type ``'e'`` from the object to the extension.
    """
    return (
        "NOT EXISTS (SELECT 1 FROM pg_depend xd"
        f" WHERE xd.classid = '{catalog}'::regclass AND xd.objid = {alias}.oid AND xd.deptype = 'e')"
    )


#: The filter every table fact reads its table ``c`` by: an ordinary table of the block.
_BLOCK_TABLE = f"c.relkind = 'r'\n  AND {_not_an_extension_member('c', 'pg_class')}"

_SCHEMA_COLUMN = (SCHEMA_NAME_KEY, "n.nspname")
_TABLE_COLUMN = (TABLE_NAME_KEY, "c.relname")

TABLES_QUERY = _DIALECT.catalog_query(
    "tables",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("table_comment", "obj_description(c.oid, 'pg_class')"),
    ),
    f"""
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY),
)

COLUMNS_QUERY = _DIALECT.catalog_query(
    "columns",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("ordinal", "a.attnum"),
        ("column_name", "a.attname"),
        ("nullable", "NOT a.attnotnull"),
        ("udt_name", "t.typname"),
        ("typtype", "t.typtype::text"),
        ("data_type", "format_type(a.atttypid, a.atttypmod)"),
        (
            "char_max_length",
            "information_schema._pg_char_max_length(a.atttypid, a.atttypmod)",
        ),
        (
            "numeric_precision",
            "information_schema._pg_numeric_precision(a.atttypid, a.atttypmod)",
        ),
        (
            "numeric_scale",
            "information_schema._pg_numeric_scale(a.atttypid, a.atttypmod)",
        ),
        ("column_default", "pg_get_expr(ad.adbin, ad.adrelid)"),
        ("generated_kind", "a.attgenerated::text"),
        ("column_comment", "col_description(a.attrelid, a.attnum)"),
    ),
    f"""
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_type t ON t.oid = a.atttypid
LEFT JOIN pg_attrdef ad ON ad.adrelid = a.attrelid AND ad.adnum = a.attnum
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND a.attnum > 0
  AND NOT a.attisdropped
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "ordinal"),
)

PRIMARY_KEYS_QUERY = _DIALECT.catalog_query(
    "primary_keys",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("position", "k.ord"),
        ("column_name", "a.attname"),
    ),
    f"""
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND con.contype = 'p'
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "position"),
)

UNIQUE_COLUMNS_QUERY = _DIALECT.catalog_query(
    "unique_columns",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("constraint_name", "con.conname"),
        ("column_name", "a.attname"),
    ),
    f"""
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = con.conkey[1]
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND con.contype = 'u'
  AND array_length(con.conkey, 1) = 1
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "constraint_name"),
)

#: One row per simple key column of an index; an expression key contributes none
#: (see :data:`INDEXES_QUERY`).
INDEX_COLUMNS_QUERY = _DIALECT.catalog_query(
    "index_columns",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("index_name", "ic.relname"),
        ("position", "k.ord"),
        ("column_name", "a.attname"),
        ("is_unique", "ix.indisunique"),
    ),
    f"""
FROM pg_index ix
JOIN pg_class c ON c.oid = ix.indrelid
JOIN pg_class ic ON ic.oid = ix.indexrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN unnest(ix.indkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND k.attnum > 0
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "index_name", "position"),
)

#: One row per index, carrying the facts the column query structurally cannot:
#: its ACCESS METHOD, whether any of its keys is an expression or it carries a
#: WHERE predicate, and its leading key.
#:
#: The column query joins through ``unnest(indkey)`` and keeps only
#: ``attnum > 0``, which is correct for the columns it returns and blind to
#: everything else: ``pg_index.indkey`` records 0 for a key that is an
#: expression rather than a simple column reference, so an expression index
#: contributes no rows there. A ``SnapshotIndex`` carries its KIND, and a
#: fulltext index (GIN over ``to_tsvector(...)``) and a spatial index (GiST over
#: a geographic column) are different schema objects from a b-tree over the same
#: columns: reading every index as a plain b-tree makes a correctly-migrated
#: database report its fulltext and spatial indexes as REMOVED, which the change
#: policy refuses unconditionally, while a b-tree standing where a GIN belongs
#: stays invisible because both sides render the same.
#:
#: ``leading_key`` is the first key as PostgreSQL deparses it, the only place a
#: fulltext index's columns and their order survive: for a one-key expression
#: index it is that expression (``pg_get_indexdef`` with a column number
#: deparses the key alone, without opclass or collation).
#:
#: ``constraint_backed`` tells a unique index a primary key or unique constraint
#: owns from one created on its own: the two are removed by different statements.
INDEXES_QUERY = _DIALECT.catalog_query(
    "indexes",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("index_name", "ic.relname"),
        ("index_method", "am.amname"),
        ("is_unique", "ix.indisunique"),
        ("key_count", "ix.indnatts"),
        ("leading_key", "pg_get_indexdef(ix.indexrelid, 1, false)"),
        ("has_expression", "(ix.indexprs IS NOT NULL)"),
        ("has_predicate", "(ix.indpred IS NOT NULL)"),
        (
            "constraint_backed",
            (
                "EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conindid = ix.indexrelid "
                "AND con.contype IN ('p', 'u'))"
            ),
        ),
    ),
    f"""
FROM pg_index ix
JOIN pg_class c ON c.oid = ix.indrelid
JOIN pg_class ic ON ic.oid = ix.indexrelid
JOIN pg_am am ON am.oid = ic.relam
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "index_name"),
)

FOREIGN_KEYS_QUERY = _DIALECT.catalog_query(
    "foreign_keys",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("fk_name", "con.conname"),
        ("position", "k.ord"),
        ("referred_table", "rc.relname"),
        ("on_delete_code", "con.confdeltype::text"),
        ("on_update_code", "con.confupdtype::text"),
        ("column_name", "a.attname"),
        ("referred_column", "ra.attname"),
    ),
    f"""
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_class rc ON rc.oid = con.confrelid
JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON TRUE
JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
JOIN unnest(con.confkey) WITH ORDINALITY AS rk(attnum, ord) ON rk.ord = k.ord
JOIN pg_attribute ra ON ra.attrelid = con.confrelid AND ra.attnum = rk.attnum
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND con.contype = 'f'
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "fk_name", "position"),
)

#: An enum type belongs to a schema, not a table. A label identifies its row;
#: ``sort_order`` (a ``real``, fractional after ``ADD VALUE ... BEFORE``) orders
#: the labels.
ENUMS_QUERY = _DIALECT.catalog_query(
    "enums",
    (
        _SCHEMA_COLUMN,
        ("enum_name", "t.typname"),
        ("enum_value", "e.enumlabel"),
        ("sort_order", "e.enumsortorder"),
    ),
    f"""
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
JOIN pg_enum e ON e.enumtypid = t.oid
WHERE {_IN_PLACES}
  AND t.typtype = 'e'
  AND {_not_an_extension_member("t", "pg_type")}
""",
    (SCHEMA_NAME_KEY, "enum_name", "enum_value"),
)

#: A check is read by name only (see :func:`_checks_from_rows`).
CHECKS_QUERY = _DIALECT.catalog_query(
    "checks",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("check_name", "con.conname"),
    ),
    f"""
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND con.contype = 'c'
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "check_name"),
)

#: A trigger is read by name and kind (see :func:`_triggers_from_rows`), and only a trigger
#: CruftFree named: ``trg_<table>_<subject>_<digest>``, the digest being hex characters. The
#: kind is what the catalog states: a constraint trigger (deferrable, fired at commit) is an
#: aggregate invariant, any other is an append-only rule. The statement trigger guarding an
#: append-only table's truncates ends in a word, not a digest, so it is not read: it is
#: dropped with the rule it belongs to. Every other trigger of the table (an extension's, a
#: DBA's) is left alone.
_TRIGGER_NAME_PREFIX = f"{TRIGGER_KIND}_"
TRIGGERS_QUERY = _DIALECT.catalog_query(
    "triggers",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("trigger_name", "t.tgname"),
        (
            "trigger_kind",
            f"CASE WHEN t.tgconstraint <> 0 THEN '{TRIGGER_AGGREGATE_INVARIANT}' "
            f"ELSE '{TRIGGER_APPEND_ONLY}' END",
        ),
    ),
    f"""
FROM pg_trigger t
JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND NOT t.tgisinternal
  AND left(t.tgname, {len(_TRIGGER_NAME_PREFIX)}) = '{_TRIGGER_NAME_PREFIX}'
  AND length(t.tgname) > {len(_TRIGGER_NAME_PREFIX) + DEFINITION_DIGEST_LENGTH}
  AND translate(right(t.tgname, {DEFINITION_DIGEST_LENGTH}), '0123456789abcdef', '') = ''
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "trigger_name"),
)
