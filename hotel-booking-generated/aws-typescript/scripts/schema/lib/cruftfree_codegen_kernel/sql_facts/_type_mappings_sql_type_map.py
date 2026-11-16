"""The sql type map part of ``type_mappings``."""

from __future__ import annotations

from dataclasses import dataclass

from cruftfree_common.builtins.domain_format_widths import SLUG_UNSIZED_MAX_LENGTH
from cruftfree_common.config.datasource.ddl_dialect_names import POSTGRESQL_DDL_DIALECT
from cruftfree_common.types.base import TypeMappingBase


@dataclass(frozen=True)
class SqlTypeMapping(TypeMappingBase):
    """SQL type mapping for a CruftFree scalar type, per dialect.

    Extends TypeMappingBase with dialect-specific SQL column types.
    The inherited type_name field uses the PostgreSQL type as the
    canonical representation (PostgreSQL is the default dialect).
    import_stmt is always None for SQL (no language imports).

    Each field holds the SQL column type for that dialect.
    sized_template is a format string for parameterized types:
        VARCHAR({0}) — single param (max length)
        NUMERIC({0},{1}) — two params (precision, scale)
    """

    postgresql: str = ""
    sized_template: str | None = None


SUPPORTED_DIALECTS = frozenset({POSTGRESQL_DDL_DIALECT})


# ─── Complete mapping: every canonical builtin type ─────────────────────
# Keys are canonical builtin names only.  Aliases (e.g. ``Int`` → ``Integer``)
# are resolved by the TypeRegistry before generators reach the type map.
#
# CAPACITY, not just legality, decides a dialect's spelling. A row whose
# postgresql side is unbounded (`TEXT`, `BYTEA`: bounded only by the ~1 GB
# per-field limit) must not get a bounded type on another dialect, or the SAME
# .cfree entity stores less on one engine than on the other.

SQL_TYPE_MAP: dict[str, SqlTypeMapping] = {
    "String": SqlTypeMapping(type_name="TEXT", postgresql="TEXT", sized_template="VARCHAR({0})"),
    "Integer": SqlTypeMapping(type_name="BIGINT", postgresql="BIGINT"),
    "Float": SqlTypeMapping(type_name="DOUBLE PRECISION", postgresql="DOUBLE PRECISION"),
    "Boolean": SqlTypeMapping(type_name="BOOLEAN", postgresql="BOOLEAN"),
    "Decimal": SqlTypeMapping(
        type_name="NUMERIC", postgresql="NUMERIC", sized_template="NUMERIC({0},{1})"
    ),
    "Bytes": SqlTypeMapping(type_name="BYTEA", postgresql="BYTEA"),
    "Void": SqlTypeMapping(type_name="VOID", postgresql="VOID"),
    "Short": SqlTypeMapping(type_name="SMALLINT", postgresql="SMALLINT"),
    "Long": SqlTypeMapping(type_name="BIGINT", postgresql="BIGINT"),
    "Text": SqlTypeMapping(type_name="TEXT", postgresql="TEXT"),
    "ConfigPath": SqlTypeMapping(type_name="TEXT", postgresql="TEXT"),
    "UUID": SqlTypeMapping(type_name="UUID", postgresql="UUID"),
    "Email": SqlTypeMapping(type_name="VARCHAR(320)", postgresql="VARCHAR(320)"),
    "URL": SqlTypeMapping(type_name="TEXT", postgresql="TEXT"),
    "Phone": SqlTypeMapping(type_name="VARCHAR(20)", postgresql="VARCHAR(20)"),
    "IPAddress": SqlTypeMapping(type_name="INET", postgresql="INET"),
    "JSON": SqlTypeMapping(type_name="JSONB", postgresql="JSONB"),
    # A Slug's column is as wide as the boundary lets a value be: its size, or
    # the format's unsized limit.
    "Slug": SqlTypeMapping(
        type_name=f"VARCHAR({SLUG_UNSIZED_MAX_LENGTH})",
        postgresql=f"VARCHAR({SLUG_UNSIZED_MAX_LENGTH})",
        sized_template="VARCHAR({0})",
    ),
    "Money": SqlTypeMapping(type_name="DECIMAL(19,4)", postgresql="DECIMAL(19,4)"),
    "Percentage": SqlTypeMapping(type_name="DECIMAL(5,2)", postgresql="DECIMAL(5,2)"),
    "Color": SqlTypeMapping(type_name="VARCHAR(7)", postgresql="VARCHAR(7)"),
    "CountryCode": SqlTypeMapping(type_name="CHAR(2)", postgresql="CHAR(2)"),
    "LanguageCode": SqlTypeMapping(type_name="CHAR(2)", postgresql="CHAR(2)"),
    "CurrencyCode": SqlTypeMapping(type_name="CHAR(3)", postgresql="CHAR(3)"),
    "PostalCode": SqlTypeMapping(type_name="VARCHAR(20)", postgresql="VARCHAR(20)"),
    "Latitude": SqlTypeMapping(type_name="DECIMAL(9,6)", postgresql="DECIMAL(9,6)"),
    "Longitude": SqlTypeMapping(type_name="DECIMAL(9,6)", postgresql="DECIMAL(9,6)"),
    "CreditCard": SqlTypeMapping(type_name="VARCHAR(20)", postgresql="VARCHAR(20)"),
    "IBAN": SqlTypeMapping(type_name="VARCHAR(34)", postgresql="VARCHAR(34)"),
    "MAC": SqlTypeMapping(type_name="MACADDR", postgresql="MACADDR"),
    "CIDR": SqlTypeMapping(type_name="CIDR", postgresql="CIDR"),
    "Password": SqlTypeMapping(type_name="VARCHAR(255)", postgresql="VARCHAR(255)"),
    "DateTime": SqlTypeMapping(type_name="TIMESTAMPTZ", postgresql="TIMESTAMPTZ"),
    "Date": SqlTypeMapping(type_name="DATE", postgresql="DATE"),
    "Time": SqlTypeMapping(type_name="TIME", postgresql="TIME"),
    "Duration": SqlTypeMapping(type_name="INTERVAL", postgresql="INTERVAL"),
    "Timestamp": SqlTypeMapping(type_name="BIGINT", postgresql="BIGINT"),
    "TimestampMs": SqlTypeMapping(type_name="BIGINT", postgresql="BIGINT"),
    "Exception": SqlTypeMapping(type_name="TEXT", postgresql="TEXT"),
}
