"""The dialect table: the registered SQL dialect implementations, keyed by DDL dialect name.

A schema script the generated output carries reaches its dialect here, by the DDL dialect
name the block's facts record, so it never loads the engine registry. Resolving an engine's
``sql_dialect`` to its DDL dialect is generation's
(:func:`~cruftfree_codegen_kernel.sql_facts.dialects.registry.get_sql_dialect`).
"""

from __future__ import annotations

from cruftfree_common.config.datasource.ddl_dialect_names import POSTGRESQL_DDL_DIALECT

from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect
from cruftfree_codegen_kernel.sql_facts.dialects.postgresql import PostgreSQLDialect
from cruftfree_codegen_kernel.sql_facts.errors import DialectNotFoundError

_DIALECTS: dict[str, type[SQLDialect]] = {
    POSTGRESQL_DDL_DIALECT: PostgreSQLDialect,
}


def registered_ddl_dialects() -> frozenset[str]:
    """The DDL dialect names a :class:`SQLDialect` implementation is registered for."""
    return frozenset(_DIALECTS)


# @canonical(sql/dialect-table): Instantiate the SQLDialect registered for a DDL dialect name
# @rule: Takes a DDL dialect name only; an engine's sql_dialect is resolved by get_sql_dialect at generation
# @rule: An unregistered name raises DialectNotFoundError naming every registered DDL dialect
def sql_dialect(ddl_dialect: str) -> SQLDialect:
    """The SQL dialect registered for *ddl_dialect*.

    Args:
        ddl_dialect: A DDL dialect name (``'postgresql'``).

    Returns:
        The instantiated dialect; its ``name`` is *ddl_dialect*.

    Raises:
        DialectNotFoundError: No SQL dialect implementation is registered for *ddl_dialect*.
    """
    dialect = _DIALECTS.get(ddl_dialect)
    if dialect is None:
        raise DialectNotFoundError(
            f"No SQL dialect implementation is registered for the DDL dialect '{ddl_dialect}'. "
            f"Registered: {', '.join(sorted(_DIALECTS))}. Fix: pass a registered DDL dialect "
            "name, or register a SQLDialect for it in "
            "cruftfree_codegen_kernel.sql_facts.dialects.dialect_table."
        )
    return dialect()
