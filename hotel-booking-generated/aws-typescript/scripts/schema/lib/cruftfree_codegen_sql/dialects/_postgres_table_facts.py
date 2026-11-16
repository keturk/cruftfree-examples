"""Table fact readers of the PostgreSQL reflector."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from cruftfree_codegen_kernel.algorithms.postgresql_fulltext import (
    FULLTEXT_INDEX_METHOD,
)
from cruftfree_codegen_kernel.algorithms.postgresql_spatial import SPATIAL_INDEX_METHOD
from cruftfree_rdbms_schema._snapshot_models import (
    SnapshotCheck,
    SnapshotIndex,
    SnapshotTrigger,
)
from cruftfree_rdbms_schema.catalog_reader import (
    SCHEMA_NAME_KEY,
    CatalogQuery,
)

from cruftfree_codegen_sql.dialects._postgres_catalog_queries import (
    _BLOCK_TABLE,
    _DIALECT,
    _IN_PLACES,
    _SCHEMA_COLUMN,
    _TABLE_COLUMN,
    CHECKS_QUERY,
    COLUMNS_QUERY,
    ENUMS_QUERY,
    FOREIGN_KEYS_QUERY,
    INDEX_COLUMNS_QUERY,
    INDEXES_QUERY,
    PRIMARY_KEYS_QUERY,
    TABLES_QUERY,
    TRIGGERS_QUERY,
    UNIQUE_COLUMNS_QUERY,
)
from cruftfree_codegen_sql.dialects._reflection_common import (
    TABLE_NAME_KEY,
    CatalogRow,
    CatalogRows,
    ReflectionError,
    TablePlace,
    opt_int,
    rows_by_table,
    rows_of_tables,
)
from cruftfree_codegen_sql.dialects.postgres_fulltext_reflection import (
    fulltext_index_columns,
)

#: The sequence each column owns: the automatic dependency (``deptype 'a'``) a
#: ``SERIAL`` column's sequence records on it. ``sequence_name`` is the sequence
#: as ``regclass`` prints it, the spelling a ``nextval`` default deparses it in
#: within the same session.
COLUMN_SEQUENCES_QUERY = _DIALECT.catalog_query(
    "column_sequences",
    (
        _SCHEMA_COLUMN,
        _TABLE_COLUMN,
        ("column_name", "a.attname"),
        ("sequence_name", "s.oid::regclass::text"),
    ),
    f"""
FROM pg_depend d
JOIN pg_class s ON s.oid = d.objid
JOIN pg_class c ON c.oid = d.refobjid
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = d.refobjsubid
WHERE {_IN_PLACES}
  AND {_BLOCK_TABLE}
  AND s.relkind = 'S'
  AND d.classid = 'pg_class'::regclass
  AND d.refclassid = 'pg_class'::regclass
  AND d.deptype = 'a'
""",
    (SCHEMA_NAME_KEY, TABLE_NAME_KEY, "column_name"),
)

#: Every catalog query of the engine, with no places bound.
CATALOG_QUERIES: tuple[CatalogQuery, ...] = (
    TABLES_QUERY,
    COLUMNS_QUERY,
    PRIMARY_KEYS_QUERY,
    UNIQUE_COLUMNS_QUERY,
    INDEX_COLUMNS_QUERY,
    INDEXES_QUERY,
    FOREIGN_KEYS_QUERY,
    ENUMS_QUERY,
    CHECKS_QUERY,
    TRIGGERS_QUERY,
    COLUMN_SEQUENCES_QUERY,
)

#: The queries whose rows belong to a table of :data:`TABLES_QUERY`.
_TABLE_FACT_QUERIES: tuple[CatalogQuery, ...] = tuple(
    query
    for query in CATALOG_QUERIES
    if query is not TABLES_QUERY and TABLE_NAME_KEY in query.keys
)


def _optional_str(row: Mapping[str, object], key: str) -> str | None:
    """Read an optional text column (a catalog comment) from a row.

    ``NULL`` in the catalog means the object carries no comment, which is a
    real state, not a missing value -- unlike :func:`_require_str`'s keys,
    whose absence means the query shape drifted.
    """
    value = row.get(key)
    return value if isinstance(value, str) else None


def _require_str(row: Mapping[str, object], key: str, *, context: str) -> str:
    """Return a required string column from a catalog row or fail loud."""
    value = row.get(key)
    if not isinstance(value, str):
        raise ReflectionError(
            f"Expected string for catalog column '{key}' {context}, got "
            f"{type(value).__name__}. The PostgreSQL catalog query returned an "
            "unexpected shape; verify the reflector SQL matches the server version."
        )
    return value


#: Access method of a plain index. A ``SnapshotIndex`` with neither kind flag
#: set means exactly this and nothing else.
_PLAIN_ACCESS_METHOD = "btree"

#: Access method a ``SnapshotIndex`` with ``spatial=True`` describes. Named
#: from the one shared home so the method the generator EMITS for a geographic
#: column and the method the reflector RECOGNISES can never drift apart.
_SPATIAL_ACCESS_METHOD = SPATIAL_INDEX_METHOD

#: Access methods this reflector can map onto the snapshot's index kinds.
_REPRESENTABLE_ACCESS_METHODS: frozenset[str] = frozenset(
    {_PLAIN_ACCESS_METHOD, _SPATIAL_ACCESS_METHOD}
)


def _reject_unrepresentable_index(
    index_name: str,
    *,
    table_name: str,
    schema: str,
    method: str,
    has_expression: bool,
    has_predicate: bool,
) -> None:
    """Refuse an index the snapshot model cannot describe faithfully.

    Reflection exists so ``diff(recorded, live)`` can be trusted. An index
    recorded as something it is not corrupts that diff in the direction that is
    hardest to notice: it reports drift that does not exist, and it hides drift
    that does. So an index whose kind this model has no field for, or whose key
    columns cannot be read out of ``pg_index.indkey`` because they are
    expressions, stops the reflection instead of being flattened into a plain
    b-tree.

    The one expression index this model does describe -- the GIN index over the
    shared ``to_tsvector(...)`` expression a ``fulltext(...)`` declaration is
    created as -- is recognized by :func:`_fulltext_index` before this check
    runs, so only an expression index of any other shape reaches it.

    Args:
        index_name: The index, for the message.
        table_name: Its table, for the message.
        schema: Its schema, for the message.
        method: The index's access method (``pg_am.amname``).
        has_expression: Whether any key column is an expression.
        has_predicate: Whether the index carries a ``WHERE`` predicate.

    Raises:
        ReflectionError: When the index cannot be represented faithfully.
    """
    qualified = f'"{schema}"."{table_name}"."{index_name}"'
    if has_predicate:
        raise ReflectionError(
            f"Index {qualified} is a partial index (it carries a WHERE "
            "predicate), which the canonical schema snapshot has no field for. "
            "Reflecting it as an unconditional index would report a live "
            "schema this database does not have, so drift for this block "
            "cannot be computed. Drop the partial index, or exclude this "
            "block from live-schema export."
        )
    if has_expression:
        raise ReflectionError(
            f"Index {qualified} is built over an expression rather than plain "
            f"columns (access method '{method}'), and it is not the one "
            "expression index the canonical schema snapshot describes: a "
            f"single-key '{FULLTEXT_INDEX_METHOD}' index over exactly the "
            "coalesce to_tsvector expression a fulltext(...) declaration is "
            "created with. Reflecting it as absent, or as a plain b-tree, would "
            "report drift that does not exist and hide drift that does, so "
            "live-schema export refuses for this block instead. Drop the index, "
            "or recreate it from a fulltext(...) declaration."
        )
    if method not in _REPRESENTABLE_ACCESS_METHODS:
        raise ReflectionError(
            f"Index {qualified} uses access method '{method}', which the "
            "canonical schema snapshot cannot describe. Representable methods: "
            f"{', '.join(sorted(_REPRESENTABLE_ACCESS_METHODS))} "
            f"('{_SPATIAL_ACCESS_METHOD}' is the spatial kind, "
            f"'{_PLAIN_ACCESS_METHOD}' the plain one). Recording it as a plain "
            "b-tree would report a live schema this database does not have. "
            "Drop the index, or exclude this block from live-schema export."
        )


def _fulltext_index(
    meta_row: Mapping[str, object], index_name: str, method: str
) -> SnapshotIndex | None:
    """The fulltext index *meta_row* describes, or ``None`` for any other index.

    A ``fulltext(...)`` declaration is created as a non-unique, unconditional
    ``gin`` index with exactly one key: the shared coalesce ``to_tsvector``
    expression over its columns. Its columns and their declared order are read
    back from that key's deparse (:func:`fulltext_index_columns`), which must be
    exactly the expression the dialect renders for them. An index of any other
    shape is left to :func:`_reject_unrepresentable_index`.

    Args:
        meta_row: The index's row of the per-index metadata query.
        index_name: The index's name.
        method: The index's access method.

    Returns:
        The reflected fulltext :class:`SnapshotIndex`, or ``None``.
    """
    if method != FULLTEXT_INDEX_METHOD:
        return None
    if not meta_row.get("has_expression") or meta_row.get("has_predicate"):
        return None
    if meta_row.get("is_unique") or opt_int(meta_row, "key_count") != 1:
        return None
    leading_key = _optional_str(meta_row, "leading_key")
    columns = None if leading_key is None else fulltext_index_columns(leading_key)
    if columns is None:
        return None
    return SnapshotIndex(
        columns=columns, unique=False, name=index_name, fulltext=True
    )


@dataclass(frozen=True)
class _TableRows:
    """One table's comment and its rows of every table-fact query, by query name."""

    comment: str | None
    rows: Mapping[str, tuple[CatalogRow, ...]]

    def of(self, query: CatalogQuery) -> tuple[CatalogRow, ...]:
        """The table's rows of *query*, in the query's key order."""
        return self.rows.get(query.name, ())


def _rows_per_table(rows: Mapping[str, CatalogRows]) -> dict[TablePlace, _TableRows]:
    """Every table the table query lists, with its rows of each table-fact query.

    Raises:
        ReflectionError: On a table-fact row of a table the table query does
            not list.
    """
    listed = rows_by_table(rows[TABLES_QUERY.name])
    tables = frozenset(listed)
    facts = {
        query.name: rows_of_tables(rows[query.name], tables)
        for query in _TABLE_FACT_QUERIES
    }
    return {
        place: _TableRows(
            comment=_optional_str(table_rows[0], "table_comment"),
            rows={name: grouped.get(place, ()) for name, grouped in facts.items()},
        )
        for place, table_rows in listed.items()
    }


def _column_names(rows: Sequence[CatalogRow], context: str) -> frozenset[str]:
    """The ``column_name`` of every row (a key's or a constraint's columns)."""
    return frozenset(_require_str(row, "column_name", context=context) for row in rows)


def _owned_sequences(rows: Sequence[CatalogRow], table_name: str) -> dict[str, str]:
    """``{column_name: sequence_name}`` for every sequence a column of the table owns."""
    context = f"in a column sequence of '{table_name}'"
    return {
        _require_str(row, "column_name", context=context): _require_str(
            row, "sequence_name", context=context
        )
        for row in rows
    }


def _nextval_default(sequence: str) -> str:
    """The default a column drawing from *sequence* deparses as.

    *sequence* is the sequence as ``regclass`` prints it; ``pg_get_expr``
    prints the same text as a string constant, its single quotes doubled.
    """
    quoted = sequence.replace("'", "''")
    return f"nextval('{quoted}'::regclass)"


def _reads_owned_sequence(row: Mapping[str, object], sequence: str | None) -> bool:
    """Whether the column's default draws from *sequence*, the sequence it owns."""
    return sequence is not None and row.get("column_default") == _nextval_default(sequence)


def _checks_from_rows(
    rows: Sequence[CatalogRow], table_name: str
) -> tuple[SnapshotCheck, ...]:
    """The table's check constraints, by name only.

    The engine re-prints a check's SQL in its own normalized form, so the
    definition is never read back: the name carries the digest of the
    definition CruftFree wrote, and equal names are the same check.
    """
    return tuple(
        SnapshotCheck(
            name=_require_str(
                row, "check_name", context=f"in check constraint of '{table_name}'"
            )
        )
        for row in rows
    )


def _triggers_from_rows(
    rows: Sequence[CatalogRow], table_name: str
) -> tuple[SnapshotTrigger, ...]:
    """The table's CruftFree-named triggers, by name and kind.

    The function a trigger calls is not read back: the name carries the digest of the
    definition CruftFree wrote, and equal names are the same trigger. The kind selects which
    statements drop an undeclared trigger. A reflected trigger carries neither columns nor
    condition, so creating one from it fails the digest proof the renderer makes against
    the name.
    """
    context = f"in trigger of '{table_name}'"
    return tuple(
        SnapshotTrigger(
            name=_require_str(row, "trigger_name", context=context),
            kind=_require_str(row, "trigger_kind", context=context),
        )
        for row in rows
    )
