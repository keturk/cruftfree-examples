"""Reflector registry: resolve an engine name to a ``CatalogReader``.

Mirrors :mod:`cruftfree_codegen_kernel.sql_facts.dialects.registry` (the dialect registry) for
the live-schema catalog readers. ``postgres`` resolves to :class:`PostgresReflector`. An
unknown engine fails loud, naming the valid options — there is no silent fallback.

The registry never opens a database connection and never imports a driver: it
only instantiates a reader. The generated environment-side exporter is the
only component that owns a live connection.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from cruftfree_rdbms_schema.catalog_reader import CatalogReader

from cruftfree_codegen_sql.dialects.postgres_reflector import PostgresReflector

logger = logging.getLogger(__name__)

# Engine identifier -> reader factory.
_REFLECTORS: dict[str, Callable[[], CatalogReader]] = {
    "postgres": PostgresReflector,
}


def reflector_engines() -> frozenset[str]:
    """The engine identifiers a reader is registered for."""
    return frozenset(_REFLECTORS)


# @canonical(sql/reflector-resolve): Instantiate the CatalogReader for an engine name
# @rule: postgres -> PostgresReflector
# @rule: Unknown engines raise ValueError naming the sorted allowlist; no silent fallback
# @anti-pattern: Instantiating PostgresReflector directly at call sites
# @see: sql/dialect-resolve
def get_reflector(engine: str) -> CatalogReader:
    """Resolve an engine name to a :class:`CatalogReader`.

    Args:
        engine: RDBMS engine identifier (``postgres``).

    Returns:
        A catalog reader instance for the engine.

    Raises:
        ValueError: If ``engine`` is not a supported engine. The message names
            the valid options.
    """
    factory = _REFLECTORS.get(engine)
    if factory is None:
        raise ValueError(
            f"No reflector for engine {engine!r}. "
            f"Valid engines: {sorted(_REFLECTORS)}."
        )
    return factory()
