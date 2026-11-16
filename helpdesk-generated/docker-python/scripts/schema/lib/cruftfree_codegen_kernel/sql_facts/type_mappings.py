"""SQL-specific type mappings for all CruftFree builtin types.

SqlTypeMapping holds per-dialect SQL column types (postgresql)
and an optional sized_template for parameterized types (VARCHAR({0}), NUMERIC({0},{1})).

SQL_TYPE_MAP maps every canonical builtin type name to its mapping.

This is the SINGLE SOURCE OF TRUTH for:
- SQL column types per dialect (postgresql)
- Sized SQL templates for parameterized types

A column default's SQL is not a type's: it is written from the default's lowered tree
(``cruftfree_rdbms_schema.sql_lowering.render.column_default_sql``).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Callable

from cruftfree_common.config.datasource.geo_column_types import (
    POSTGRES_GEOGRAPHY_COLUMN_TYPE,
    POSTGRES_GEOMETRY_COLUMN_TYPE,
)
from cruftfree_common.types.geo_column import GEO_SCALAR_CANONICALS, GEO_SRID_CONSTRAINT

from cruftfree_codegen_kernel.generation.type_map_merge import (
    build_type_map,
    static_type_map,
)
from cruftfree_codegen_kernel.generation.validation import (
    require_mapped_type,
    require_option,
)
from cruftfree_codegen_kernel.sql_facts.errors import TypeMappingError

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import SnapshotStorage, SnapshotType
from cruftfree_codegen_kernel.sql_facts._type_mappings_sql_type_map import (
    SQL_TYPE_MAP,
    SUPPORTED_DIALECTS,
    SqlTypeMapping,
)

# A geographic column is typed with its SRID (``GEO_COLUMN_SRID``), spelled once in
# ``geo_column_types`` (the engine reads the same names), so the database refuses a
# value in another SRID.
_GEO_SQL_TYPE_MAPPINGS: dict[str, SqlTypeMapping] = {
    "Geometry": SqlTypeMapping(
        type_name=POSTGRES_GEOMETRY_COLUMN_TYPE,
        postgresql=POSTGRES_GEOMETRY_COLUMN_TYPE,
    ),
    "Geography": SqlTypeMapping(
        type_name=POSTGRES_GEOGRAPHY_COLUMN_TYPE,
        postgresql=POSTGRES_GEOGRAPHY_COLUMN_TYPE,
    ),
}

SQL_EXTENSION_MAPS: dict[str, dict[str, SqlTypeMapping]] = {
    "postgis": _GEO_SQL_TYPE_MAPPINGS,
    # The "geo" extension (GeoTile/GeoTiff raster builtins +
    # GeoTileSpec/GeoElevationGrid value structs) contributes zero scalar
    # types -- its own `scalar_definitions()` returns `()` -- so this entry
    # is deliberately empty. Its presence (not its content) is what matters:
    # `build_type_map` raises `ExtensionNotSupportedError` for any declared
    # extension key ABSENT from this dict, and `use extension geo;` is what
    # `GeoValidator`'s GEO001 rule requires for any `GeoTile.*`/`GeoTiff.*`
    # call or `GeoTileSpec`/`GeoElevationGrid` reference.
    "geo": {},
}

#: The map a schema-snapshot column type resolves through: the core types plus
#: every extension's. A snapshot records only the scalar types of validated
#: fields, and an extension-provided scalar (``Geometry``) passed its
#: ``use extension`` declaration check before the snapshot was built, so the
#: revision renderer needs no declared-extension list of its own. A name absent
#: from this map still raises ``TypeMappingError``.
SNAPSHOT_SQL_TYPE_MAP: dict[str, SqlTypeMapping] = static_type_map(
    SQL_TYPE_MAP, SQL_EXTENSION_MAPS
)


# @canonical(sql/type-map-build): Merge core SQL_TYPE_MAP with extension maps for declared extensions
# @rule: Every canonical builtin used in generated DDL must appear in the effective map or extension merge raises
# @anti-pattern: Ad-hoc type string branches outside SqlTypeMapping and build_sql_type_map
# @see: common/codegen/type-mapping-registry
# @see: common/codegen/exhaustive-map-lookup
def build_sql_type_map(declared_extensions: list[str]) -> dict[str, SqlTypeMapping]:
    """Build complete SQL type map: core types + declared extension types.

    Delegates to the shared ``build_type_map()`` from cruftfree-common.

    Args:
        declared_extensions: Extension names from ``app.extension_directives``.

    Returns:
        Unified type map with core + extension mappings.

    Raises:
        ExtensionNotSupportedError: If a declared extension has no SQL mappings.
    """
    return build_type_map(
        SQL_TYPE_MAP,
        SQL_EXTENSION_MAPS,
        declared_extensions,
        language="SQL",
    )


# @canonical(sql/type-resolve): Map canonical CruftFree scalar name to SQL column type for a dialect
# @rule: Raises TypeMappingError when type_name is missing from the effective map (no default type)
# @see: sql/type-map-build
# @see: common/codegen/exhaustive-map-lookup
# @see: common/codegen/type-mapping-registry
def get_sql_type(
    type_name: str,
    dialect: str,
    *,
    type_map: dict[str, SqlTypeMapping] | None = None,
) -> str:
    """Look up the SQL type for a canonical type name and dialect.

    Args:
        type_name: Canonical CruftFree type name (e.g. "String", "UUID").
        dialect: DDL dialect name (e.g. ``"postgresql"``); a caller holding an
            engine passes the engine's ``ddl_dialect``.
        type_map: Optional merged map from ``build_sql_type_map``; defaults to
            core-only ``SQL_TYPE_MAP``.

    Returns:
        SQL type string (e.g. "TEXT", "UUID", "BIGINT").

    Raises:
        TypeMappingError: If type_name is not in the effective map.
        GenerationError: If *dialect* is not a supported DDL dialect name.
    """
    table = SQL_TYPE_MAP if type_map is None else type_map
    require_mapped_type(type_name, table, "type", error_type=TypeMappingError)
    mapping = table[type_name]
    resolved: str = getattr(mapping, supported_ddl_dialect(dialect))
    return resolved


def sized_sql_type(
    type_name: str,
    dialect: str,
    *,
    max_length: int | None,
    precision: int | None,
    scale: int | None,
    type_map: dict[str, SqlTypeMapping] | None = None,
) -> str:
    """The SQL type of *type_name* carrying its declared size, on *dialect*.

    A type with a ``sized_template`` (``VARCHAR({0})``, ``NUMERIC({0},{1})``) is
    spelled with the declared ``max_length``, or ``precision`` and ``scale``, or
    ``precision`` alone; a type without one, or with no size declared, is
    :func:`get_sql_type`'s unsized spelling.

    Args:
        type_name: Canonical CruftFree type name.
        dialect: DDL dialect name (e.g. ``"postgresql"``); a caller holding an
            engine passes the engine's ``ddl_dialect``.
        max_length: Declared maximum length, or ``None``.
        precision: Declared precision, or ``None``.
        scale: Declared scale, or ``None``.
        type_map: Optional merged map from ``build_sql_type_map``; defaults to
            core-only ``SQL_TYPE_MAP``.

    Raises:
        TypeMappingError: If type_name is not in the effective map.
        GenerationError: If *dialect* is not a supported DDL dialect name.
    """
    table = SQL_TYPE_MAP if type_map is None else type_map
    require_mapped_type(type_name, table, "type", error_type=TypeMappingError)
    template = table[type_name].sized_template
    if template and max_length is not None:
        return template.format(max_length)
    if template and precision is not None and scale is not None:
        return template.format(precision, scale)
    if template and precision is not None:
        return template.format(precision)
    return get_sql_type(type_name, dialect, type_map=table)


def supported_ddl_dialect(dialect: str) -> str:
    """*dialect*, proven a :data:`SUPPORTED_DIALECTS` member.

    Only a DDL dialect name is accepted. A caller holding an engine resolves the
    DDL dialect it speaks first (its ``RdbmsEngine.ddl_dialect``), so the facts a
    generated script carries never read the engine registry.

    Raises:
        GenerationError: *dialect* is not a supported DDL dialect name, naming the
            supported ones.
    """
    require_option(dialect, SUPPORTED_DIALECTS, label="DDL dialect")
    return dialect


# ─── Postgres reverse type map ──────────────────────────────────────────
#
# Reverse type map: Postgres catalog type -> canonical CruftFree type name.
# This is the INVERSE of the ``postgresql`` column of ``SQL_TYPE_MAP`` and lives
# beside the forward map so the two evolve together (drift reconciliation D24/D25).
# The reflector reads ``information_schema.columns`` / ``pg_catalog`` and resolves
# each column's type through this map; size/precision/scale are carried into
# ``SnapshotType.constraints`` and ``SnapshotStorage`` by the caller, NOT encoded
# in the key here.
#
# Keys are ``pg_type.typname`` values (``information_schema.columns.udt_name``),
# which are stable single tokens — unlike ``data_type`` ("character varying",
# "timestamp with time zone"), which is multi-word and harder to match. The
# reflector passes ``udt_name`` as the lookup key.
#
# AMBIGUOUS REVERSES (many canonical CruftFree types collapse onto one Postgres
# type in the forward map; the reverse therefore cannot recover the original
# CruftFree type and deliberately picks the broadest canonical type, relying on the
# shared canonicalization layer to treat the variants as equivalent):
#
#   - ``text``    -> ``String``  : forward map sends String/Text/ConfigPath/URL/
#                                   Exception all to TEXT, and String to
#                                   ``VARCHAR(n)`` when sized. TEXT and VARCHAR(n)
#                                   both reverse to ``String``; the size (if any)
#                                   is carried via ``max_length`` constraints.
#   - ``varchar`` -> ``String``  : every sized character type (Email, Phone, Slug,
#                                   Password, etc.) is forward-mapped to VARCHAR(n)
#                                   and reverses to ``String`` carrying max_length.
#   - ``bpchar``  -> ``String``  : CHAR(n) (CountryCode/LanguageCode/CurrencyCode)
#                                   reverses to ``String`` carrying max_length.
#   - ``int8``    -> ``Integer`` : forward map sends Integer/Long/Timestamp/
#                                   TimestampMs all to BIGINT; reverse picks
#                                   ``Integer`` (the canonical 64-bit integer).
#   - ``int4``    -> ``Integer`` : Postgres SERIAL/INTEGER columns reverse to the
#                                   same canonical ``Integer``.
#   - ``int2``    -> ``Short``   : SMALLINT reverses to ``Short``.
#   - ``numeric`` -> ``Decimal`` : Decimal/Money/Percentage/Latitude/Longitude all
#                                   forward to NUMERIC/DECIMAL; reverse picks
#                                   ``Decimal`` carrying precision/scale.
#   - ``float8``  -> ``Float``   : DOUBLE PRECISION reverses to ``Float``.
#   - ``interval``-> ``Duration``: forward map sends Duration to INTERVAL.
#
# Postgres enum types are NOT keyed here: a column whose ``udt_name`` is a user
# enum is detected via ``pg_type.typtype = 'e'`` by the reflector and produces a
# ``SnapshotType(kind="enum", ...)`` directly, bypassing this scalar map.
POSTGRES_REVERSE_TYPE_MAP: dict[str, str] = {
    "bigint": "Integer",  # SQL spelling (BIGINT) for DDL-keyed callers
    "int8": "Integer",  # pg_type.typname for bigint
    "int4": "Integer",  # integer / SERIAL
    "integer": "Integer",
    "int2": "Short",  # smallint
    "smallint": "Short",
    "boolean": "Boolean",
    "bool": "Boolean",
    "bytea": "Bytes",
    "bpchar": "String",  # CHAR(n) -> String (max_length carried via constraints)
    "char": "String",
    "character": "String",
    "varchar": "String",  # VARCHAR(n) -> String (max_length carried via constraints)
    "text": "String",  # TEXT and VARCHAR(n) both reverse to String (see above)
    "cidr": "CIDR",
    "date": "Date",
    "numeric": "Decimal",  # precision/scale carried via constraints
    "decimal": "Decimal",
    "float8": "Float",  # DOUBLE PRECISION
    "double precision": "Float",
    "inet": "IPAddress",
    "interval": "Duration",
    "jsonb": "JSON",
    # No SQL forward source (JSON forwards to JSONB), but the Python target's
    # migrations declare sa.JSON(), which PostgreSQL creates as json.
    "json": "JSON",
    # postgis extension (SQL_EXTENSION_MAPS): the typmod naming the SRID lives
    # only in data_type (format_type); udt_name is the bare type. The SRID is
    # carried into the constraints (_typmod_srid).
    "geometry": "Geometry",
    "geography": "Geography",
    "macaddr": "MAC",
    "time": "Time",
    "timetz": "Time",
    "timestamptz": "DateTime",
    "uuid": "UUID",
    "void": "Void",  # function-only; never appears as a real column type
}

# Logical category of each canonical CruftFree type that the reverse map can emit.
# Decides which storage facet (max_length vs precision/scale) is meaningful so we
# never invent constraints a type does not carry. Exhaustive over the *values* of
# POSTGRES_REVERSE_TYPE_MAP; an unmapped value fails loud (no silent default).
_REVERSE_SIZED_STRING_TYPES = frozenset({"String"})
_REVERSE_PRECISION_TYPES = frozenset({"Decimal"})

#: A PostGIS column type as ``format_type`` spells it: the base type, then an
#: optional typmod naming the geometry subtype and, when it has one, the SRID
#: (``geometry(Point,4326)``, ``geography(Geometry,4326)``, ``geometry(Point)``).
_GEO_TYPMOD_RE = re.compile(
    r"^(?P<base>[A-Za-z]+)\s*"
    r"(?:\(\s*(?P<subtype>[A-Za-z][A-Za-z0-9]*)\s*(?:,\s*(?P<srid>\d+)\s*)?\))?$"
)


def _typmod_srid(data_type: str) -> int | None:
    """The SRID a geographic column's typmod names, or ``None`` when it names none.

    ``format_type`` writes no SRID for an unconstrained column (``geometry``) or a
    typmod with SRID 0 (``geometry(Point)``).

    Raises:
        TypeMappingError: *data_type* is not a PostGIS type spelling.
    """
    match = _GEO_TYPMOD_RE.match(data_type.strip())
    if match is None:
        raise TypeMappingError(
            f"Cannot read the SRID of geographic column type '{data_type}': expected "
            "a PostGIS spelling such as 'geometry', 'geometry(Point)' or "
            "'geography(Geometry,4326)'."
        )
    srid = match.group("srid")
    return int(srid) if srid is not None and int(srid) > 0 else None


def _reverse_constraints(
    canonical_name: str,
    *,
    data_type: str,
    char_max_length: int | None,
    numeric_precision: int | None,
    numeric_scale: int | None,
) -> dict[str, int]:
    """Build SnapshotType.constraints for a reversed scalar type.

    Carries ``max_length`` for sized string types, ``precision``/``scale`` for
    precision types and the SRID of a geographic column's typmod; never invents
    a facet the canonical type does not carry.
    """
    constraints: dict[str, int] = {}
    if canonical_name in _REVERSE_SIZED_STRING_TYPES and char_max_length is not None:
        constraints["max_length"] = char_max_length
    if canonical_name in _REVERSE_PRECISION_TYPES:
        if numeric_precision is not None:
            constraints["precision"] = numeric_precision
        if numeric_scale is not None:
            constraints["scale"] = numeric_scale
    if canonical_name in GEO_SCALAR_CANONICALS:
        srid = _typmod_srid(data_type)
        if srid is not None:
            constraints[GEO_SRID_CONSTRAINT] = srid
    return constraints


def reverse_postgres_type(
    *,
    data_type: str,
    char_max_length: int | None,
    numeric_precision: int | None,
    numeric_scale: int | None,
    udt_name: str | None,
    is_enum: bool = False,
    enum_name: str | None = None,
    enum_values: tuple[str, ...] = (),
    table_column: str = "<unknown>",
) -> "SnapshotType":
    """Build a canonical :class:`SnapshotType` from a Postgres catalog row.

    Inverts the ``postgresql`` column of :data:`SQL_TYPE_MAP`. The DB type is
    matched on ``udt_name`` (``pg_type.typname``) first, falling back to
    ``data_type`` — both are normalized to lower case. Size, precision, scale and
    a geographic column's SRID (read from the typmod ``data_type`` spells) are
    carried into ``SnapshotType.constraints``; ``SnapshotStorage`` is built
    separately by the reflector.

    FAILS LOUD on an unmapped DB type rather than guessing (no ``map.get`` default).

    Args:
        data_type: The column's catalog type spelling (e.g. "character
            varying", "timestamp with time zone", or ``format_type``'s
            "geometry(Geometry,4326)").
        char_max_length: ``character_maximum_length`` for sized character types.
        numeric_precision: ``numeric_precision`` for NUMERIC/DECIMAL.
        numeric_scale: ``numeric_scale`` for NUMERIC/DECIMAL.
        udt_name: ``pg_type.typname`` (e.g. "int8", "varchar", "timestamptz").
            Preferred lookup key; single-token and stable.
        is_enum: True when the column's underlying type is a user enum
            (``pg_type.typtype = 'e'``).
        enum_name: CruftFree enum name for enum-typed columns.
        enum_values: Ordered enum member names for enum-typed columns.
        table_column: ``"table.column"`` for error messages.

    Returns:
        A canonical :class:`SnapshotType`.

    Raises:
        TypeMappingError: If the DB type is not in :data:`POSTGRES_REVERSE_TYPE_MAP`.
    """
    from cruftfree_rdbms_schema._snapshot_models import SnapshotType

    if is_enum:
        if enum_name is None:
            raise TypeMappingError(
                f"Enum column '{table_column}' has udt_name '{udt_name}' but no "
                "enum name was resolved. The reflector must pass enum_name and "
                "enum_values for enum-typed columns."
            )
        return SnapshotType(
            kind="enum",
            name=enum_name,
            constraints={},
            values=enum_values,
        )

    key = (udt_name or data_type or "").strip().lower()
    canonical_name = POSTGRES_REVERSE_TYPE_MAP.get(key)
    if canonical_name is None:
        # Second chance on data_type when udt_name failed (e.g. domain types).
        fallback_key = (data_type or "").strip().lower()
        canonical_name = POSTGRES_REVERSE_TYPE_MAP.get(fallback_key)
    if canonical_name is None:
        available = ", ".join(sorted(POSTGRES_REVERSE_TYPE_MAP))
        raise TypeMappingError(
            f"Unmapped PostgreSQL type for column '{table_column}': "
            f"udt_name='{udt_name}', data_type='{data_type}'. No reverse mapping "
            f"exists. Add it to POSTGRES_REVERSE_TYPE_MAP in type_mappings.py "
            f"(beside the forward SQL_TYPE_MAP). Known DB types: {available}."
        )

    constraints = _reverse_constraints(
        canonical_name,
        data_type=data_type,
        char_max_length=char_max_length,
        numeric_precision=numeric_precision,
        numeric_scale=numeric_scale,
    )

    return SnapshotType(
        kind="scalar",
        name=canonical_name,
        constraints=constraints,
        values=(),
    )


# ─── Declared type, read back from a live catalog ──────────────────────
#
# A reflected catalog can only name the BROAD type of each column (the reverse
# maps above): a ``Latitude`` column reads back as ``Decimal`` carrying
# precision 9 and scale 6, an ``Email`` as ``String`` carrying max_length 320.
# Comparing a declared schema with a live one therefore asks, per column, what
# the reflector reports for the declared type -- the forward map's spelling read
# back through the engine's reverse map, never a second table of equivalences.

#: A SQL column type as the forward maps spell it: a base type of one or more
#: words, then an optional ``(n)`` or ``(p,s)`` size.
_SQL_TYPE_SPELLING_RE = re.compile(
    r"^(?P<base>[A-Za-z][A-Za-z ]*?)\s*"
    r"(?:\(\s*(?P<first>\d+)\s*(?:,\s*(?P<second>\d+)\s*)?\))?$"
)


def _optional_size(text: str | None) -> int | None:
    """A size argument of a type spelling, or ``None`` when the spelling has none."""
    return int(text) if text is not None else None


def reflected_snapshot_type(
    type_name: str,
    ddl_dialect: str,
    *,
    max_length: int | None,
    precision: int | None,
    scale: int | None,
) -> "SnapshotType":
    """The type a *ddl_dialect* catalog reports for a column declared as *type_name*.

    The declared type is spelled as the forward map spells it for the DDL
    dialect (:func:`sized_sql_type` over :data:`SNAPSHOT_SQL_TYPE_MAP`,
    exactly as a revision renders the column), and that spelling is read back
    through the dialect's reverse map, as the reflector reads the catalog row
    the column produced.

    Args:
        type_name: Canonical CruftFree scalar type name.
        ddl_dialect: DDL dialect name the catalog's engine speaks (e.g. ``"postgresql"``).
        max_length: Declared maximum length, or ``None``.
        precision: Declared precision, or ``None``.
        scale: Declared scale, or ``None``.

    Returns:
        The reflected :class:`SnapshotType`.

    Raises:
        TypeMappingError: If *type_name* has no forward mapping, or its spelling
            is not a base type with an optional size.
        GenerationError: If *ddl_dialect* is not a supported DDL dialect name.
    """
    dialect = supported_ddl_dialect(ddl_dialect)
    spelling = sized_sql_type(
        type_name,
        dialect,
        max_length=max_length,
        precision=precision,
        scale=scale,
        type_map=SNAPSHOT_SQL_TYPE_MAP,
    ).strip()
    match = _SQL_TYPE_SPELLING_RE.match(spelling) or _GEO_TYPMOD_RE.match(spelling)
    if match is None:
        raise TypeMappingError(
            f"Cannot read type '{type_name}' back from {ddl_dialect}: its forward "
            f"spelling '{spelling}' is not a base type with an optional (n) or "
            "(p,s) size or a (Subtype,srid) typmod, so no reverse map can name it. "
            "Expected a spelling such as 'TEXT', 'VARCHAR(320)', 'DECIMAL(9,6)' or "
            "'geometry(Geometry,4326)'; fix the forward row in SQL_TYPE_MAP or "
            "SQL_EXTENSION_MAPS."
        )
    groups = match.groupdict()
    base = groups["base"].strip().lower()
    first = _optional_size(groups.get("first"))
    second = _optional_size(groups.get("second"))
    return reverse_postgres_type(
        data_type=spelling,
        char_max_length=first,
        numeric_precision=first,
        numeric_scale=second,
        udt_name=base,
        table_column=f"<{type_name} declared on {ddl_dialect}>",
    )


def live_type_resolver(
    ddl_dialect: str,
) -> Callable[["SnapshotType", "SnapshotStorage"], "SnapshotType"]:
    """The reflected-type function a live-catalog comparison in *ddl_dialect* reads.

    Args:
        ddl_dialect: The DDL dialect name the live catalog's engine speaks (a caller
            holding the live snapshot artifact's ``engine`` resolves its ``ddl_dialect``).

    Returns:
        A function from a declared scalar type and its storage to the type
        :func:`reflected_snapshot_type` says the dialect's catalog reports for it.

    Raises:
        GenerationError: *ddl_dialect* is not a supported DDL dialect name.
    """
    supported_ddl_dialect(ddl_dialect)

    def resolve(declared: "SnapshotType", storage: "SnapshotStorage") -> "SnapshotType":
        return reflected_snapshot_type(
            declared.name,
            ddl_dialect,
            max_length=storage.max_length,
            precision=storage.precision,
            scale=storage.scale,
        )

    return resolve
