"""The one explicit-cast rule an ALTER COLUMN TYPE needs, per DDL dialect.

Defined here, in the schema machinery every DDL renderer depends on, so the shared SQL dialects and the fixture adapter render one rule.
The schema runtime carries it, so it takes a DDL dialect name and never an
engine: a caller holding an engine resolves its DDL dialect first.
"""

from __future__ import annotations

from typing import Final

from cruftfree_common.config.datasource.ddl_dialect_names import POSTGRESQL_DDL_DIALECT
from cruftfree_common.errors.generation import GenerationError
from cruftfree_common.utils.sql_text import sql_quoted_identifier

#: DDL dialects whose ALTER COLUMN TYPE needs an explicit cast expression.
_USING_CAST_DIALECTS: Final[frozenset[str]] = frozenset({POSTGRESQL_DDL_DIALECT})
#: DDL dialects whose ALTER COLUMN TYPE converts implicitly and takes no cast clause.
#: No registered dialect does today.
_NO_CAST_DIALECTS: Final[frozenset[str]] = frozenset()


def type_change_using_clause(column: str, new_type_sql: str, ddl_dialect: str) -> str:
    """The explicit cast clause an ALTER COLUMN TYPE needs on *ddl_dialect*.

    PostgreSQL refuses an implicit conversion for most type changes (and an
    explicit cast makes a widening's conversion deterministic), so every
    adapter renders ``USING "<col>"::<new type>``; a dialect whose ALTER
    converts implicitly takes none.

    Args:
        column: The column's SQL identifier (unqualified).
        new_type_sql: The column's new SQL type expression, rendered verbatim
            after the cast operator.
        ddl_dialect: The DDL dialect name the ALTER is rendered in (an engine's
            ``ddl_dialect``, never its engine or ``sql_dialect`` name).

    Returns:
        ``USING "<column>"::<new_type_sql>`` for a dialect that needs an
        explicit cast; ``""`` for a dialect whose ALTER converts implicitly.

    Raises:
        GenerationError: *ddl_dialect* is in neither the cast nor the no-cast
            set, naming it and both known sets.
    """
    if ddl_dialect in _USING_CAST_DIALECTS:
        return f"USING {sql_quoted_identifier(column)}::{new_type_sql}"
    if ddl_dialect in _NO_CAST_DIALECTS:
        return ""
    raise GenerationError(
        f"Unknown DDL dialect '{ddl_dialect}' for the ALTER COLUMN TYPE cast rule. "
        f"Dialects needing an explicit USING cast: {sorted(_USING_CAST_DIALECTS)}. "
        f"Dialects converting implicitly (no cast): {sorted(_NO_CAST_DIALECTS)}. "
        "Pass the engine's ddl_dialect, or add the dialect to whichever set matches "
        "its ALTER COLUMN TYPE semantics."
    )


__all__ = ["type_change_using_clause"]
