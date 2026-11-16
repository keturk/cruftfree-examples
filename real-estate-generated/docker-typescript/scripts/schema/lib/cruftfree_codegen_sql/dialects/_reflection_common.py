"""Shared reflection contract for the RDBMS dialect reflectors.

This consolidation stays package-local by ownership, not by a dependency
fence: the dialect reflection contract is specific to this package's
reflectors (`postgres_reflector.py`), so it lives here rather than in a
shared codegen layer (architecture Decision 34's shared-layer consolidation covers
target-agnostic logic used across packages -- this contract has exactly one
consumer package and is not that). It is NOT promoted or relocated to a
shared layer. Each dialect's catalog queries, driver-specific column
coercion, type reversal, default classification and referential-action
decoding stay in their own module; the reflection CONTRACT, its
input-validation helpers, the engine-neutral checks of the catalog documents
(:func:`catalog_rows`, :func:`rows_by_table`), and the dialect-neutral assembly
of catalog rows into ``Snapshot*`` structures live here.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from itertools import pairwise
from typing import Protocol

from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotBlockIdentity,
    SnapshotCheck,
    SnapshotColumn,
    SnapshotContainerIdentity,
    SnapshotDefault,
    SnapshotEnum,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotServiceIdentity,
    SnapshotStorage,
    SnapshotTable,
    SnapshotTrigger,
    SnapshotType,
)
from cruftfree_rdbms_schema._snapshot_versions import SCHEMA_FORMAT, SCHEMA_VERSION
from cruftfree_rdbms_schema.catalog_reader import (
    SCHEMA_NAME_KEY,
    CatalogQuery,
    ReflectionIdentity,
)

from cruftfree_codegen_sql.errors import SQLGeneratorError


class ReflectionError(SQLGeneratorError):
    """Raised when a live RDBMS catalog cannot be faithfully reflected."""


_REQUIRED_IDENTITY_ATTRS = (
    "rdbms_id",
    "service_name",
    "service_version",
    "container_name",
    "container_kind",
    "block_name",
    "schema_name",
)


def as_identity(rdbms_block: object) -> ReflectionIdentity:
    """Validate that ``rdbms_block`` carries the required identity attributes."""
    missing = [attr for attr in _REQUIRED_IDENTITY_ATTRS if not hasattr(rdbms_block, attr)]
    if missing:
        raise ReflectionError(
            f"rdbms_block is missing required identity attributes "
            f"{missing}. The reflector stamps source-side identity onto the "
            "live snapshot; pass a ReflectionIdentity carrying rdbms_id, "
            "service_name, service_version, container_name, container_kind, "
            "block_name, and schema_name."
        )
    return rdbms_block  # type: ignore[return-value]


def opt_int(row: Mapping[str, object], key: str) -> int | None:
    """Return an optional integer column from a catalog row."""
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        # bool is an int subclass; a boolean here means the query shape is wrong.
        raise ReflectionError(
            f"Catalog column '{key}' is a boolean where an integer was expected. "
            "Verify the reflector SQL."
        )
    if isinstance(value, int):
        return value
    raise ReflectionError(
        f"Expected integer or NULL for catalog column '{key}', got "
        f"{type(value).__name__}."
    )


class RequireStr(Protocol):
    """A dialect's required-string reader: returns the column's text or fails loud."""

    def __call__(self, row: Mapping[str, object], key: str, *, context: str) -> str:
        """Return ``row[key]`` as text, raising ``ReflectionError`` otherwise."""
        ...


ColumnBuilder = Callable[[Mapping[str, object], str, str], SnapshotColumn]
"""Builds one column from its catalog row, its name, and ``table.column``."""

ForeignKeyAction = Callable[[Mapping[str, object], str], str]
"""Decodes a referential action from a catalog row column into its canonical string."""


def reflected_snapshot(
    identity: ReflectionIdentity,
    *,
    entities: dict[str, SnapshotTable],
    enums: tuple[SnapshotEnum, ...],
    schema_name: str | None,
) -> RdbmsSchemaSnapshot:
    """Stamp the source-side identity onto the reflected objects.

    The snapshot format identity is owned by ``cruftfree_rdbms_schema.schema_snapshot``
    and imported, never re-declared per reflector. A reflector never reflects
    CQRS views (they are not catalog tables of their own).
    """
    return RdbmsSchemaSnapshot(
        format=SCHEMA_FORMAT,
        version=SCHEMA_VERSION,
        rdbms_id=identity.rdbms_id,
        service=SnapshotServiceIdentity(
            name=identity.service_name,
            version=identity.service_version,
        ),
        container=SnapshotContainerIdentity(
            name=identity.container_name,
            kind=identity.container_kind,
        ),
        block=SnapshotBlockIdentity(name=identity.block_name),
        entities=entities,
        cqrs_views={},
        enums=enums,
        schema_name=schema_name,
    )


def reflected_table(
    table_name: str,
    *,
    fields: dict[str, SnapshotColumn],
    indexes: tuple[SnapshotIndex, ...],
    foreign_keys: tuple[SnapshotForeignKey, ...],
    checks: tuple[SnapshotCheck, ...],
    triggers: tuple[SnapshotTrigger, ...],
    comment: str | None,
) -> SnapshotTable:
    """Assemble one reflected table.

    Catalog table options are not reflected, so ``table_options`` is always
    empty -- the source builder records none either. A reflected check or trigger
    carries its name only: the name carries the digest of its definition, so the
    name alone decides whether it is the declared one.
    """
    return SnapshotTable(
        table_name=table_name,
        fields=fields,
        indexes=indexes,
        foreign_keys=foreign_keys,
        table_options={},
        comment=comment,
        checks=tuple(sorted(checks, key=lambda check: check.name)),
        triggers=tuple(sorted(triggers, key=lambda trigger: trigger.name)),
    )


def reflect_columns(
    rows: list[Mapping[str, object]],
    table_name: str,
    require_str: RequireStr,
    build_column: ColumnBuilder,
) -> dict[str, SnapshotColumn]:
    """Build every column of ``table_name`` from its catalog rows, in catalog order.

    Raises:
        ReflectionError: If the table has no columns, or a row has no name.
    """
    if not rows:
        raise ReflectionError(
            f"Table '{table_name}' has no columns in the catalog. A reflected "
            "table must have at least one column; verify the schema is intact."
        )
    columns: dict[str, SnapshotColumn] = {}
    for row in rows:
        column_name = require_str(row, "column_name", context=f"for table '{table_name}'")
        columns[column_name] = build_column(row, column_name, f"{table_name}.{column_name}")
    return columns


def reflected_column(
    column_name: str,
    snap_type: SnapshotType,
    *,
    nullable: bool,
    primary_key: bool,
    default: SnapshotDefault | None,
    unique: bool,
    comment: str | None,
) -> SnapshotColumn:
    """Assemble one reflected, migration-owned column.

    Mirrors the source builder: storage carries ONLY the facets the canonical
    type actually constrains (max_length for sized strings, precision/scale for
    decimals). A catalog reports incidental numeric precision for plain
    integers; copying it verbatim would manufacture false drift against the
    source snapshot, which leaves those facets None. The dialect's type
    reversal already decided the meaningful facets, so storage is sourced from
    the reversed type's constraints.
    """
    storage = SnapshotStorage(
        max_length=snap_type.constraints.get("max_length"),
        precision=snap_type.constraints.get("precision"),
        scale=snap_type.constraints.get("scale"),
    )
    return SnapshotColumn(
        column_name=column_name,
        type=snap_type,
        storage=storage,
        nullable=nullable,
        primary_key=primary_key,
        default=default,
        unique=unique,
        comment=comment,
    )


@dataclass
class _ForeignKeyRows:
    """One foreign key's catalog rows, accumulated column by column."""

    referred_table: str
    on_delete: str
    on_update: str
    columns: list[str] = field(default_factory=list)
    referred_columns: list[str] = field(default_factory=list)


def group_foreign_keys(
    rows: list[Mapping[str, object]],
    table_name: str,
    require_str: RequireStr,
    fk_action: ForeignKeyAction,
    *,
    on_delete_key: str,
    on_update_key: str,
) -> tuple[SnapshotForeignKey, ...]:
    """Group per-column foreign-key catalog rows into one key per constraint name.

    Rows of one constraint share its referred table and referential actions, so
    the constraint records those from its first row; every row is still read
    and validated, so a malformed later row fails loud. Column pairs keep
    catalog order.
    """
    grouped: dict[str, _ForeignKeyRows] = {}
    context = f"in FK of '{table_name}'"
    for row in rows:
        fk_name = require_str(row, "fk_name", context=f"for table '{table_name}'")
        row_key = _ForeignKeyRows(
            referred_table=require_str(row, "referred_table", context=context),
            on_delete=fk_action(row, on_delete_key),
            on_update=fk_action(row, on_update_key),
        )
        entry = grouped.setdefault(fk_name, row_key)
        entry.columns.append(require_str(row, "column_name", context=context))
        entry.referred_columns.append(require_str(row, "referred_column", context=context))
    return tuple(
        SnapshotForeignKey(
            columns=tuple(entry.columns),
            referred_table=entry.referred_table,
            referred_columns=tuple(entry.referred_columns),
            on_delete=entry.on_delete,
            on_update=entry.on_update,
            name=fk_name,
        )
        for fk_name, entry in grouped.items()
    )


TABLE_NAME_KEY = "table_name"
"""The key every per-table catalog query returns, naming the table a row belongs to."""

CatalogRow = Mapping[str, object]
"""One row of a catalog document: exactly its query's keys, mapped to their JSON values."""

RowKey = tuple[str | int, ...]
"""A row's values in its query's ``key_columns``, in order."""

TablePlace = tuple[str, str]
"""A table's ``(schema_name, table_name)``."""


@dataclass(frozen=True)
class CatalogRows:
    """One catalog query's checked rows, sorted by its ``key_columns``."""

    query: CatalogQuery
    rows: tuple[CatalogRow, ...]


def catalog_rows(
    documents: Mapping[str, str], queries: tuple[CatalogQuery, ...]
) -> dict[str, CatalogRows]:
    """Check every query's document and return its rows, keyed by query name.

    Requires exactly one document per query, each a JSON array of objects whose
    members are exactly the query's keys, with a string or integer in every key
    column, no two rows sharing a key. The rows are sorted by ``key_columns``,
    so the result does not depend on the order the engine returned them in.

    Raises:
        ReflectionError: On a missing document, a document naming no query, or
            a malformed document or row, naming the query (and the row's key
            where it has one).
    """
    by_name = _queries_by_name(queries)
    _require_document_set(documents, by_name)
    return {name: _document_rows(query, documents[name]) for name, query in by_name.items()}


def rows_by_table(rows: CatalogRows) -> dict[TablePlace, tuple[CatalogRow, ...]]:
    """Group one per-table query's rows by ``(schema_name, table_name)``, in row order.

    Raises:
        ReflectionError: If the query returns no ``table_name`` (its rows belong
            to a schema, not a table), or a row's schema or table is not a
            non-empty string, naming the query and the row's key.
    """
    query = rows.query
    if TABLE_NAME_KEY not in query.keys:
        raise ReflectionError(
            f"Catalog query '{query.name}' returns no '{TABLE_NAME_KEY}' "
            f"(keys: {list(query.keys)}), so its rows cannot be grouped by table. "
            f"Its rows belong to a schema: read them by '{SCHEMA_NAME_KEY}'."
        )
    grouped: dict[TablePlace, list[CatalogRow]] = {}
    for row in rows.rows:
        place = (
            _text_member(query, row, SCHEMA_NAME_KEY),
            _text_member(query, row, TABLE_NAME_KEY),
        )
        grouped.setdefault(place, []).append(row)
    return {place: tuple(group) for place, group in grouped.items()}


def rows_of_tables(
    rows: CatalogRows, tables: frozenset[TablePlace]
) -> dict[TablePlace, tuple[CatalogRow, ...]]:
    """Group one per-table query's rows by table, every table among *tables*.

    *tables* are the places the engine's table query listed. A row of any other
    table belongs to an object the snapshot would hold without its table, so
    the two queries disagree about the catalog and the read stops.

    Raises:
        ReflectionError: On a row of a table *tables* does not hold, naming the
            query and the tables.
    """
    grouped = rows_by_table(rows)
    unknown = sorted(set(grouped) - tables)
    if unknown:
        raise ReflectionError(
            f"Catalog query '{rows.query.name}' returned rows of the tables {unknown} "
            f"(schema, table), which the table query does not list (it lists "
            f"{sorted(tables)}). The queries read the catalog of different tables; "
            "run every query of catalog_queries in one transaction."
        )
    return grouped


def require_place(rows: Mapping[str, CatalogRows], place: str) -> None:
    """Require every row of every query to come from *place*, the block's schema.

    A snapshot records one placement for all of its objects, so an object of
    another schema is one it cannot represent.

    Raises:
        ReflectionError: On a row of another place, naming the query, the row's
            key and both places.
    """
    for checked in rows.values():
        query = checked.query
        for row in checked.rows:
            row_place = _text_member(query, row, SCHEMA_NAME_KEY)
            if row_place != place:
                raise ReflectionError(
                    f"Catalog query '{query.name}' returned the row "
                    f"{_describe_key(query, row)} of the schema '{row_place}', but the "
                    f"block is placed in '{place}'. A snapshot records one placement "
                    "for all its objects; bind the queries to the block's schema only."
                )


def _queries_by_name(queries: tuple[CatalogQuery, ...]) -> dict[str, CatalogQuery]:
    by_name: dict[str, CatalogQuery] = {}
    for query in queries:
        if query.name in by_name:
            raise ReflectionError(
                f"Two catalog queries are named '{query.name}'. Documents are keyed by "
                "query name, so each query of an engine needs a name of its own."
            )
        by_name[query.name] = query
    return by_name


def _require_document_set(
    documents: Mapping[str, str], by_name: Mapping[str, CatalogQuery]
) -> None:
    missing = sorted(set(by_name) - set(documents))
    if missing:
        raise ReflectionError(
            f"No document for the catalog queries {missing}. Every query returns one "
            "document ('[]' when it reads no rows), so a missing document means the "
            "query did not run: run every query of catalog_queries once and pass its "
            "document under the query's name."
        )
    unknown = sorted(set(documents) - set(by_name))
    if unknown:
        raise ReflectionError(
            f"The documents {unknown} name no catalog query (queries: "
            f"{sorted(by_name)}). Pass exactly one document per query, keyed by the "
            "query's name."
        )


def _document_rows(query: CatalogQuery, document: str) -> CatalogRows:
    parsed = _parse_document(query, document)
    if not isinstance(parsed, list):
        raise ReflectionError(
            f"Catalog query '{query.name}' returned {_json_kind(parsed)} where a JSON "
            "array of row objects was expected. Every query is wrapped to return one "
            "array, '[]' when it reads no rows; rerun the query as catalog_queries "
            "renders it."
        )
    keyed = [_checked_row(query, position, element) for position, element in enumerate(parsed)]
    _require_uniform_key_types(query, keyed)
    keyed.sort(key=lambda pair: pair[0])
    _require_unique_keys(query, keyed)
    return CatalogRows(query=query, rows=tuple(row for _, row in keyed))


def _parse_document(query: CatalogQuery, document: str) -> object:
    if not isinstance(document, str):
        raise ReflectionError(
            f"Catalog query '{query.name}' has a {type(document).__name__} document "
            "where the JSON text the query returned was expected. Pass the query's "
            "result text as it came from the engine."
        )

    def unique_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
        members = dict(pairs)
        if len(members) != len(pairs):
            names = [name for name, _ in pairs]
            repeated = sorted({name for name in names if names.count(name) > 1})
            raise ReflectionError(
                f"Catalog query '{query.name}' returned an object naming the members "
                f"{repeated} more than once. A row names each key once; rerun the query "
                "as catalog_queries renders it."
            )
        return members

    def refuse_constant(constant: str) -> object:
        raise ReflectionError(
            f"Catalog query '{query.name}' returned the non-JSON number '{constant}'. "
            "A catalog document holds only JSON values; rerun the query as "
            "catalog_queries renders it."
        )

    try:
        return json.loads(
            document, object_pairs_hook=unique_members, parse_constant=refuse_constant
        )
    except json.JSONDecodeError as error:
        raise ReflectionError(
            f"Catalog query '{query.name}' returned a document that is not JSON "
            f"({error.msg} at character {error.pos} of {len(document)}); a document "
            "cut short is refused. Rerun the query and pass its whole result."
        ) from error


def _checked_row(
    query: CatalogQuery, position: int, element: object
) -> tuple[RowKey, CatalogRow]:
    if not isinstance(element, dict):
        raise ReflectionError(
            f"Catalog query '{query.name}' row {position} is {_json_kind(element)} "
            "where a JSON object of the query's keys was expected."
        )
    row: dict[str, object] = element
    expected = set(query.keys)
    if set(row) != expected:
        raise ReflectionError(
            f"Catalog query '{query.name}' row {position} lacks the keys "
            f"{sorted(expected - set(row))} and has the extra keys "
            f"{sorted(set(row) - expected)}. Every row carries exactly the query's keys "
            f"{list(query.keys)}; rerun the query as catalog_queries renders it."
        )
    return _row_key(query, position, row), row


def _row_key(query: CatalogQuery, position: int, row: CatalogRow) -> RowKey:
    values: list[str | int] = []
    for column in query.key_columns:
        value = row[column]
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ReflectionError(
                f"Catalog query '{query.name}' row {position} has {_json_kind(value)} in "
                f"its key column '{column}'. A key column identifies the row, so it holds "
                "a string or an integer, never null."
            )
        values.append(value)
    return tuple(values)


def _require_uniform_key_types(
    query: CatalogQuery, keyed: list[tuple[RowKey, CatalogRow]]
) -> None:
    for index, column in enumerate(query.key_columns):
        kinds = sorted({type(key[index]).__name__ for key, _ in keyed})
        if len(kinds) > 1:
            raise ReflectionError(
                f"Catalog query '{query.name}' key column '{column}' holds the types "
                f"{kinds} across its rows. A key column holds one JSON type in every "
                "row; verify its catalog expression."
            )


def _require_unique_keys(
    query: CatalogQuery, keyed: list[tuple[RowKey, CatalogRow]]
) -> None:
    for (previous, _), (key, row) in pairwise(keyed):
        if previous == key:
            raise ReflectionError(
                f"Catalog query '{query.name}' returned two rows with the key "
                f"{_describe_key(query, row)}. Its key columns {list(query.key_columns)} "
                "must identify one row; verify the query's key columns."
            )


def _text_member(query: CatalogQuery, row: CatalogRow, key: str) -> str:
    value = row[key]
    if not isinstance(value, str) or not value:
        raise ReflectionError(
            f"Catalog query '{query.name}' row {_describe_key(query, row)} has "
            f"{_json_kind(value)} in '{key}' where a non-empty name was expected."
        )
    return value


def _describe_key(query: CatalogQuery, row: CatalogRow) -> str:
    return "(" + ", ".join(f"{column}={row[column]!r}" for column in query.key_columns) + ")"


def _json_kind(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, (int, float)):
        return "a number"
    if isinstance(value, str):
        return "an empty string" if not value else "a string"
    if isinstance(value, list):
        return "an array"
    return "an object"
