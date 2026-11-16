"""PostgreSQL catalog reader: read a live catalog into a canonical snapshot.

The reader reads ``pg_catalog`` in a read-only transaction and builds the SAME
``Snapshot*`` structures the source AST path builds, so the shared
canonicalization layer (decision D25) can collapse cosmetic differences and
diff source vs. live with zero false positives.

The catalog is read by a fixed set of queries, :data:`CATALOG_QUERIES`, one per
catalog fact. Each is a constant rendered by the PostgreSQL dialect: it reads
the places bound as ``$1`` (a text array of schemas), returns ``schema_name``
and ``table_name`` instead of filtering by them, and holds no value in its
text. :meth:`PostgresReflector.parse_catalog` is a pure function from the
queries' JSON documents to the snapshot.

It performs NO DDL and NO writes. It never imports a database driver: the
generated environment-side exporter (where the DB is reachable) runs the
queries over its own driver. The CruftFree side never executes this module — it
only imports the produced ``live-schema-snapshot.json`` artifact offline.

Type reversal is delegated to :func:`reverse_postgres_type`, the inverse of the
forward ``SQL_TYPE_MAP`` postgresql column. An unmapped DB type fails loud naming
the type and ``table.column`` — the reader never guesses.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from cruftfree_codegen_kernel.sql_facts.referential_actions import dsl_referential_action
from cruftfree_codegen_kernel.sql_facts.type_mappings import reverse_postgres_type
from cruftfree_common.cruftfree_model.constants import DEFAULT_RDBMS_SCHEMA
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotColumn,
    SnapshotDefault,
    SnapshotEnum,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotTable,
    SnapshotType,
)
from cruftfree_rdbms_schema.catalog_reader import (
    CatalogQuery,
    ReflectionIdentity,
)
from cruftfree_rdbms_schema.recorded_default import builtin_call_default
from cruftfree_rdbms_schema.sql_lowering.render import builtin_call_for_sql

from cruftfree_codegen_sql.dialects._postgres_catalog_queries import (
    _DDL_DIALECT,
    _FK_ACTION_CODES,
    _TYPTYPE_ENUM,
    CHECKS_QUERY,
    COLUMNS_QUERY,
    ENGINE_NAME,
    ENUMS_QUERY,
    FOREIGN_KEYS_QUERY,
    INDEX_COLUMNS_QUERY,
    INDEXES_QUERY,
    PRIMARY_KEYS_QUERY,
    TRIGGERS_QUERY,
    UNIQUE_COLUMNS_QUERY,
)
from cruftfree_codegen_sql.dialects._postgres_table_facts import (
    _SPATIAL_ACCESS_METHOD,
    CATALOG_QUERIES,
    COLUMN_SEQUENCES_QUERY,
    _checks_from_rows,
    _column_names,
    _fulltext_index,
    _optional_str,
    _owned_sequences,
    _reads_owned_sequence,
    _reject_unrepresentable_index,
    _require_str,
    _rows_per_table,
    _TableRows,
    _triggers_from_rows,
)
from cruftfree_codegen_sql.dialects._reflection_common import (
    CatalogRow,
    ReflectionError,
    as_identity,
    catalog_rows,
    group_foreign_keys,
    opt_int,
    reflect_columns,
    reflected_column,
    reflected_snapshot,
    reflected_table,
    require_place,
)
from cruftfree_codegen_sql.dialects.postgres_default_reader import read_postgres_default


def _label_sort_order(row: Mapping[str, object], enum_name: str) -> float:
    """The catalog sort order of an enum label: a number, fractional after an insert."""
    value = row.get("sort_order")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReflectionError(
            f"Enum '{enum_name}' has {type(value).__name__} as a label's sort order "
            "where a number was expected. The PostgreSQL catalog query returned an "
            "unexpected shape; verify the reflector SQL matches the server version."
        )
    return float(value)


class PostgresReflector:
    """The PostgreSQL catalog reader (read-only).

    :meth:`catalog_queries` are the fixed queries a client runs over the block's
    places; :meth:`parse_catalog` builds the snapshot from their documents.
    """

    @property
    def engine(self) -> str:
        return ENGINE_NAME

    def catalog_queries(self, schema: str | None) -> tuple[CatalogQuery, ...]:
        """Every catalog query, bound to read *schema*.

        ``None`` is the engine default placement: the queries read
        ``DEFAULT_RDBMS_SCHEMA``, as the source-built snapshot records it.
        """
        places = (schema if schema is not None else DEFAULT_RDBMS_SCHEMA,)
        return tuple(query.at_places(places) for query in CATALOG_QUERIES)

    def parse_catalog(
        self, documents: Mapping[str, str], identity: ReflectionIdentity
    ) -> RdbmsSchemaSnapshot:
        """The snapshot the catalog documents describe, keyed by query name.

        A pure function of its arguments: every document is checked against its
        query (:func:`catalog_rows`), every row must come from the identity's
        place, and every table fact must belong to a table the table query
        lists. The rows are then built into the snapshot table by table.

        Args:
            documents: One JSON document per query of :data:`CATALOG_QUERIES`,
                keyed by the query's name.
            identity: The source-side identity; its ``schema_name`` is the place
                the documents were read from (``None``: the engine default)
                and is stamped on the snapshot.

        Returns:
            A fully-hashed snapshot of the place's tables, columns, types,
            nullability, defaults, primary keys, unique constraints, indexes,
            foreign keys, check constraint names, and enums.

        Raises:
            ReflectionError: On a missing or malformed document or row, a row of
                another place or of an unlisted table, or an index the snapshot
                cannot represent, naming the query or the object.
            TypeMappingError: If a column carries an unmapped DB type.
        """
        checked = as_identity(identity)
        schema_name = checked.schema_name
        place = schema_name if schema_name is not None else DEFAULT_RDBMS_SCHEMA
        rows = catalog_rows(documents, CATALOG_QUERIES)
        require_place(rows, place)
        enums = self._enums_from_rows(rows[ENUMS_QUERY.name].rows)
        enum_lookup = {enum.database_name: enum for enum in enums}
        entities = {
            table_name: self._table_from_rows(table_name, table, enum_lookup, place)
            for (_, table_name), table in _rows_per_table(rows).items()
        }
        return reflected_snapshot(
            checked, entities=entities, enums=enums, schema_name=schema_name
        )

    def _table_from_rows(
        self,
        table_name: str,
        table: _TableRows,
        enum_lookup: Mapping[str, SnapshotEnum],
        schema: str,
    ) -> SnapshotTable:
        return reflected_table(
            table_name,
            fields=self._columns_from_rows(
                table.of(COLUMNS_QUERY),
                table_name,
                enum_lookup,
                pk_columns=_column_names(
                    table.of(PRIMARY_KEYS_QUERY), f"in PK of '{table_name}'"
                ),
                unique_columns=_column_names(
                    table.of(UNIQUE_COLUMNS_QUERY),
                    f"in unique constraint of '{table_name}'",
                ),
                owned_sequences=_owned_sequences(
                    table.of(COLUMN_SEQUENCES_QUERY), table_name
                ),
            ),
            indexes=self._indexes_from_rows(
                table.of(INDEX_COLUMNS_QUERY),
                table.of(INDEXES_QUERY),
                table_name,
                schema,
            ),
            foreign_keys=self._foreign_keys_from_rows(
                table.of(FOREIGN_KEYS_QUERY), table_name
            ),
            checks=_checks_from_rows(table.of(CHECKS_QUERY), table_name),
            triggers=_triggers_from_rows(table.of(TRIGGERS_QUERY), table_name),
            comment=table.comment,
        )

    def _columns_from_rows(
        self,
        rows: Sequence[CatalogRow],
        table_name: str,
        enum_lookup: Mapping[str, SnapshotEnum],
        *,
        pk_columns: frozenset[str],
        unique_columns: frozenset[str],
        owned_sequences: Mapping[str, str],
    ) -> dict[str, SnapshotColumn]:
        """Every column of the table, in catalog order.

        A column whose default draws from the sequence it owns (*owned_sequences*,
        column name to sequence) records no default, as the source-built
        snapshot records an auto-numbered key; a ``nextval`` of any other
        sequence stays a server function.

        Raises:
            ReflectionError: If *owned_sequences* names a column the table does
                not have.
        """

        def build_column(
            row: Mapping[str, object], column_name: str, qualified: str
        ) -> SnapshotColumn:
            owned = _reads_owned_sequence(row, owned_sequences.get(column_name))
            return reflected_column(
                column_name,
                self._build_column_type(row, qualified, enum_lookup),
                nullable=bool(row.get("nullable")),
                primary_key=column_name in pk_columns,
                default=None if owned else self._build_default(row),
                unique=column_name in unique_columns,
                comment=_optional_str(row, "column_comment"),
            )

        columns = reflect_columns(list(rows), table_name, _require_str, build_column)
        unknown = sorted(set(owned_sequences) - set(columns))
        if unknown:
            raise ReflectionError(
                f"Table '{table_name}' owns sequences through the columns {unknown}, "
                f"which its columns ({sorted(columns)}) do not include. The column and "
                "column-sequence queries read different catalogs; run every catalog "
                "query in one transaction."
            )
        return columns

    def _build_column_type(
        self,
        row: Mapping[str, object],
        qualified: str,
        enum_lookup: Mapping[str, SnapshotEnum],
    ) -> SnapshotType:
        udt_name = row.get("udt_name")
        udt_str = udt_name if isinstance(udt_name, str) else None
        typtype = row.get("typtype")
        data_type = row.get("data_type")
        data_type_str = data_type if isinstance(data_type, str) else ""

        is_enum = typtype == _TYPTYPE_ENUM
        enum_name: str | None = None
        enum_values: tuple[str, ...] = ()
        if is_enum:
            if udt_str is None or udt_str not in enum_lookup:
                raise ReflectionError(
                    f"Column '{qualified}' is an enum type '{udt_str}' that was "
                    "not found in the reflected enum catalog. Enum reflection and "
                    "column reflection disagree; verify both queries target the "
                    "same schema."
                )
            matched = enum_lookup[udt_str]
            enum_name = matched.name
            enum_values = matched.values

        return reverse_postgres_type(
            data_type=data_type_str,
            char_max_length=opt_int(row, "char_max_length"),
            numeric_precision=opt_int(row, "numeric_precision"),
            numeric_scale=opt_int(row, "numeric_scale"),
            udt_name=udt_str,
            is_enum=is_enum,
            enum_name=enum_name,
            enum_values=enum_values,
            table_column=qualified,
        )

    def _build_default(self, row: Mapping[str, object]) -> SnapshotDefault | None:
        raw = row.get("column_default")
        if raw is None:
            return None
        value = str(raw)
        generated = row.get("generated_kind")
        if isinstance(generated, str) and generated.strip() and generated != " ":
            # attgenerated is 's' for STORED generated columns, '' otherwise.
            return SnapshotDefault(kind="generated", value=value, name="generated")
        # A builtin call default reads back as the SQL its lowering row wrote
        # (gen_random_uuid()); the snapshot records the call the row is keyed by
        # (uuid()), as the source-built snapshot does.
        builtin = builtin_call_for_sql(value, _DDL_DIALECT)
        if builtin is not None:
            return builtin_call_default(builtin)
        # A nextval(...) sequence default, another function call or a compound expression
        # is a server-side expression, not a literal; "(" reliably distinguishes it from
        # bare literals such as 0 / 'x' / true. A compound default the renderer wrote reads
        # back to its lowered tree (read_postgres_default), so the comparison can match it
        # to the declared default's tree; one it did not write carries none.
        if "(" in value:
            return SnapshotDefault(
                kind="server_function",
                value=value,
                name="server_default",
                tree=read_postgres_default(value),
            )
        return SnapshotDefault(kind="literal", value=value, name="literal")

    def _indexes_from_rows(
        self,
        column_rows: Sequence[CatalogRow],
        meta_rows: Sequence[CatalogRow],
        table_name: str,
        schema: str,
    ) -> tuple[SnapshotIndex, ...]:
        """The table's indexes, carrying each one's KIND, or fail loud.

        A ``SnapshotIndex`` distinguishes a plain b-tree from a spatial (GiST)
        index because they are different schema objects with different DDL and
        different query semantics. Reading the catalog without its access
        method reports all three as plain, which makes a correctly-migrated
        database look like it had its fulltext and spatial indexes removed --
        a change the migration policy refuses unconditionally, so a false
        blocking drift.

        An index this snapshot model cannot represent faithfully raises rather
        than being flattened into a plain b-tree: a drift report that quietly
        describes a different schema than the database has is worse than no
        report, because it is believed.

        Args:
            column_rows: One row per simple key column, in key order per index.
            meta_rows: One row per index, in index-name order.
            table_name: The indexes' table, for the messages.
            schema: The table's schema, for the messages.
        """
        grouped: dict[str, list[str]] = {}
        unique_by_name: dict[str, bool] = {}
        for row in column_rows:
            index_name = _require_str(
                row, "index_name", context=f"for table '{table_name}'"
            )
            column_name = _require_str(
                row, "column_name", context=f"in index of '{table_name}'"
            )
            grouped.setdefault(index_name, []).append(column_name)
            unique_by_name[index_name] = bool(row.get("is_unique"))

        indexes: list[SnapshotIndex] = []
        for meta_row in meta_rows:
            index_name = _require_str(
                meta_row, "index_name", context=f"for table '{table_name}'"
            )
            method = _require_str(
                meta_row, "index_method", context=f"of index '{index_name}'"
            )
            fulltext = _fulltext_index(meta_row, index_name, method)
            if fulltext is not None:
                indexes.append(fulltext)
                continue
            _reject_unrepresentable_index(
                index_name,
                table_name=table_name,
                schema=schema,
                method=method,
                has_expression=bool(meta_row.get("has_expression")),
                has_predicate=bool(meta_row.get("has_predicate")),
            )
            if index_name not in grouped:
                raise ReflectionError(
                    f"Index \"{schema}\".\"{table_name}\".\"{index_name}\" "
                    f"(access method '{method}') reported no key columns, "
                    "though it carries neither an expression nor a predicate. "
                    "The two reflector index queries disagree about this "
                    "table; verify the reflector SQL matches the server "
                    "version."
                )
            unique = unique_by_name[index_name]
            indexes.append(
                SnapshotIndex(
                    columns=tuple(grouped[index_name]),
                    unique=unique,
                    name=index_name,
                    spatial=method == _SPATIAL_ACCESS_METHOD,
                    constraint_backed=not unique or bool(meta_row.get("constraint_backed")),
                )
            )
        return tuple(indexes)

    def _foreign_keys_from_rows(
        self, rows: Sequence[CatalogRow], table_name: str
    ) -> tuple[SnapshotForeignKey, ...]:
        return group_foreign_keys(
            list(rows),
            table_name,
            _require_str,
            self._fk_action,
            on_delete_key="on_delete_code",
            on_update_key="on_update_code",
        )

    def _fk_action(self, row: Mapping[str, object], key: str) -> str:
        # confdeltype / confupdtype are NOT NULL, so a missing or non-text code
        # means the query shape drifted -- never a reason to assume NO ACTION.
        code = _require_str(row, key, context="in a foreign-key row")
        action = _FK_ACTION_CODES.get(code)
        if action is None:
            raise ReflectionError(
                f"Unknown foreign-key referential action code '{code}' for "
                f"'{key}'. Known codes: {sorted(_FK_ACTION_CODES)}."
            )
        return dsl_referential_action(action)

    def _enums_from_rows(self, rows: Sequence[CatalogRow]) -> tuple[SnapshotEnum, ...]:
        """The enum types *rows* describe, each label in its catalog sort order."""
        grouped: dict[str, list[tuple[float, str]]] = {}
        for row in rows:
            enum_name = _require_str(row, "enum_name", context="in enum list")
            enum_value = _require_str(row, "enum_value", context="in enum list")
            grouped.setdefault(enum_name, []).append(
                (_label_sort_order(row, enum_name), enum_value)
            )
        enums = [
            SnapshotEnum(
                name=self._enum_pascal_name(database_name),
                database_name=database_name,
                values=tuple(value for _, value in sorted(labels)),
            )
            for database_name, labels in grouped.items()
        ]
        return tuple(sorted(enums, key=lambda e: e.name))

    def _enum_pascal_name(self, database_name: str) -> str:
        """Derive the CruftFree PascalCase enum name from the snake_case DB type.

        The source builder stores ``database_name = to_snake_case(name)``; the
        canonicalization layer leaves enum names as-is, so the reflected
        PascalCase name must reproduce the source enum's PascalCase identifier.
        """
        from cruftfree_common.utils.identifier_case import to_pascal_case

        return to_pascal_case(database_name)
