"""Default value rendering for revision statements."""

from __future__ import annotations

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotColumn,
    SnapshotTable,
)
from cruftfree_rdbms_schema.schema_snapshot import stored_enum_labels

from cruftfree_codegen_kernel.sql_facts.dialects.base import (
    SQLDialect,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.column_constraint_change import (
    RenderColumnDefault,
)
from cruftfree_codegen_kernel.sql_facts.snapshot.snapshot_default_literal import (
    render_snapshot_default_sql,
)


def _enum_labels(snapshot: RdbmsSchemaSnapshot) -> dict[str, tuple[str, ...]]:
    """The stored labels of every enum *snapshot* declares.

    Raises:
        GenerationError: The snapshot cannot say which label a member is stored as.
    """
    try:
        return stored_enum_labels(snapshot)
    except ValueError as exc:
        raise GenerationError(str(exc)) from exc


def _default_sql(table_name: str, column: SnapshotColumn, dialect: SQLDialect) -> str:
    """*column*'s snapshot default as the SQL expression after ``DEFAULT``.

    A ``SET DEFAULT`` reads the default from the snapshot column, never from the
    change: a change records the default's kind and value, not its lowered tree.

    Raises:
        GenerationError: The column has no default, or it cannot be a database default.
    """
    default = column.default
    if default is None:
        raise GenerationError(
            "Column '%s' of table '%s' has no default to render. Expected: a default is "
            "rendered only for a column that carries one." % (column.column_name, table_name)
        )
    return render_snapshot_default_sql(column, default, table_name, dialect.name)


def _default_renderer(dialect: SQLDialect) -> RenderColumnDefault:
    """The default renderer the shared column-change builders call back."""

    def render(table: SnapshotTable, column: SnapshotColumn) -> str:
        return _default_sql(table.table_name, column, dialect)

    return render
