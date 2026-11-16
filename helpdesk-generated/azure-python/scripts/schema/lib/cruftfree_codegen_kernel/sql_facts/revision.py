"""The SQL of a block's schema, as an ordered list of typed statements.

:func:`render_schema` renders the statements that build a schema snapshot from an
empty schema, for any
:class:`~cruftfree_codegen_kernel.sql_facts.dialects.base.SQLDialect`.
:func:`render_convergence` renders the changes that bring a live catalog to the
declared schema; :func:`render_convergence_by_change` is the same rendering with
each statement paired with the change it renders. The SQL text of every statement
is the dialect's; this module decides which statements are rendered, what each one
is about (:class:`SqlStatement`), and their order.

Order:

* **Whole schema** -- the schema prelude (``create_schema``, ``set_search_path``),
  every enum type, every table, every foreign key (separate statements, because a
  key may name a table created later), every check constraint, then every index and
  unique constraint, then every comment the dialect sets outside ``CREATE TABLE``,
  then every table trigger (its function and the triggers that call it).
* **Convergence** -- ``set_search_path`` (preceded by ``create_schema`` when the
  changes relocate the block into a schema, or when the live catalog holds no table
  and no enum type: a catalog reader reads only the block's place, so a schema the
  database lacks reads as one holding nothing), then each change in
  :func:`~cruftfree_rdbms_schema.differ.schema_change_order`.

Every statement names its tables and types unqualified: the schema is reached
through ``set_search_path`` on an engine with schema namespaces
(:data:`~cruftfree_codegen_kernel.sql_facts.constants.FEATURE_SCHEMA_NAMESPACES`).
An enum is a named type only on an engine that keeps one
(:data:`~cruftfree_codegen_kernel.sql_facts.constants.FEATURE_NAMED_ENUM_TYPES`); an
inline-enum engine restates every column typed with the enum instead.

Every :class:`~cruftfree_rdbms_schema.differ.ChangeKind` is either rendered
(:data:`CHANGE_KIND_STATEMENT_KINDS`, the statement kinds it may produce) or refused
by name (:data:`REFUSED_CHANGE_KINDS`); a kind in neither raises. A change is read
against the snapshot that records what it is about: an added or changed object
against the declared schema, a removed one against the live catalog.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, TypeVar

from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema.differ import ChangeKind, SchemaChange, schema_change_order
from cruftfree_rdbms_schema.foreign_key_naming import realized_foreign_key_name
from cruftfree_rdbms_schema.index_naming import realized_index_name

from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot
from cruftfree_codegen_kernel.sql_facts._revision_check_changes import (
    _add_check_statements,
    _render_check_added,
    _render_check_removed,
)
from cruftfree_codegen_kernel.sql_facts._revision_entity_field_changes import (
    _render_entity_added,
    _render_entity_removed,
    _render_field_added,
    _render_field_default_changed,
    _render_field_nullable_changed,
    _render_field_removed,
    _render_field_type_changed,
    _render_field_unique_changed,
)
from cruftfree_codegen_kernel.sql_facts._revision_enum_comment_changes import (
    _render_entity_comment_changed,
    _render_enum_type_removed,
    _render_enum_value_added,
    _render_enum_value_relabeled,
    _render_field_comment_changed,
)
from cruftfree_codegen_kernel.sql_facts._revision_index_relationship_changes import (
    _render_foreign_key_renamed,
    _render_foreign_key_replaced,
    _render_index_added,
    _render_index_removed,
    _render_index_renamed,
    _render_relationship_added,
    _render_relationship_removed,
    _render_schema_relocated,
)
from cruftfree_codegen_kernel.sql_facts._revision_model import (
    REFUSED_CHANGE_KINDS,
    ChangeStatement,
    RenderedRevision,
    SqlStatement,
    SqlStatementKind,
)
from cruftfree_codegen_kernel.sql_facts._revision_statements import (
    _add_foreign_key_statements,
    _column_unique_statements,
    _create_index_statements,
    _create_table_statements,
    _enum_type_statements,
    _enum_types_in_use,
    _RevisionContext,
    _schema_prelude,
    _standalone_comment_statements,
)
from cruftfree_codegen_kernel.sql_facts._revision_trigger_changes import (
    _add_trigger_statements,
    _render_trigger_added,
    _render_trigger_removed,
)

logger = logging.getLogger(__name__)

__all__ = [
    "CHANGE_KIND_STATEMENT_KINDS",
    "render_convergence",
    "render_convergence_by_change",
    "render_schema",
]


# -- The mapping ------------------------------------------------------------------

_ChangeRenderer = Callable[[_RevisionContext, SchemaChange], list[SqlStatement]]


@dataclass(frozen=True)
class _ChangeRendering:
    """How one change kind is rendered, and the statement kinds it may produce."""

    statement_kinds: frozenset[SqlStatementKind]
    render: _ChangeRenderer


_K = SqlStatementKind

#: Every rendered change kind. Disjoint from :data:`REFUSED_CHANGE_KINDS`; together
#: they are exactly :class:`~cruftfree_rdbms_schema.differ.ChangeKind`.
_CHANGE_RENDERINGS: Final[Mapping[ChangeKind, _ChangeRendering]] = {
    ChangeKind.ENTITY_ADDED: _ChangeRendering(
        frozenset(
            {
                _K.CREATE_ENUM_TYPE,
                _K.CREATE_TABLE,
                _K.ADD_UNIQUE_CONSTRAINT,
                _K.SET_COMMENT,
            }
        ),
        _render_entity_added,
    ),
    ChangeKind.ENTITY_REMOVED: _ChangeRendering(
        frozenset({_K.DROP_TABLE}), _render_entity_removed
    ),
    ChangeKind.FIELD_ADDED: _ChangeRendering(
        frozenset(
            {
                _K.CREATE_ENUM_TYPE,
                _K.ADD_COLUMN,
                _K.SET_DEFAULT,
                _K.ADD_UNIQUE_CONSTRAINT,
                _K.SET_COMMENT,
            }
        ),
        _render_field_added,
    ),
    ChangeKind.FIELD_REMOVED: _ChangeRendering(
        frozenset({_K.DROP_COLUMN}), _render_field_removed
    ),
    ChangeKind.FIELD_TYPE_CHANGED: _ChangeRendering(
        frozenset({_K.CREATE_ENUM_TYPE, _K.ALTER_COLUMN_TYPE}),
        _render_field_type_changed,
    ),
    ChangeKind.FIELD_NULLABLE_CHANGED: _ChangeRendering(
        frozenset({_K.RAW_BACKFILL, _K.ALTER_NULLABILITY}),
        _render_field_nullable_changed,
    ),
    ChangeKind.FIELD_DEFAULT_CHANGED: _ChangeRendering(
        frozenset({_K.SET_DEFAULT, _K.DROP_DEFAULT}), _render_field_default_changed
    ),
    ChangeKind.FIELD_UNIQUE_CHANGED: _ChangeRendering(
        frozenset({_K.ADD_UNIQUE_CONSTRAINT, _K.DROP_UNIQUE_CONSTRAINT}),
        _render_field_unique_changed,
    ),
    ChangeKind.INDEX_ADDED: _ChangeRendering(
        frozenset({_K.CREATE_INDEX, _K.ADD_UNIQUE_CONSTRAINT}), _render_index_added
    ),
    ChangeKind.INDEX_REMOVED: _ChangeRendering(
        frozenset({_K.DROP_INDEX, _K.DROP_UNIQUE_CONSTRAINT}), _render_index_removed
    ),
    ChangeKind.INDEX_RENAMED: _ChangeRendering(
        frozenset({_K.RENAME_INDEX}), _render_index_renamed
    ),
    ChangeKind.RELATIONSHIP_ADDED: _ChangeRendering(
        frozenset({_K.ADD_FOREIGN_KEY, _K.VALIDATE_FOREIGN_KEY}),
        _render_relationship_added,
    ),
    ChangeKind.RELATIONSHIP_REMOVED: _ChangeRendering(
        frozenset({_K.DROP_FOREIGN_KEY}), _render_relationship_removed
    ),
    ChangeKind.FOREIGN_KEY_REPLACED: _ChangeRendering(
        frozenset({_K.DROP_FOREIGN_KEY, _K.ADD_FOREIGN_KEY, _K.VALIDATE_FOREIGN_KEY}),
        _render_foreign_key_replaced,
    ),
    ChangeKind.FOREIGN_KEY_RENAMED: _ChangeRendering(
        frozenset(
            {
                _K.RENAME_FOREIGN_KEY,
                _K.DROP_FOREIGN_KEY,
                _K.ADD_FOREIGN_KEY,
                _K.VALIDATE_FOREIGN_KEY,
            }
        ),
        _render_foreign_key_renamed,
    ),
    ChangeKind.SCHEMA_RELOCATED: _ChangeRendering(
        frozenset({_K.RELOCATE_SCHEMA}), _render_schema_relocated
    ),
    ChangeKind.ENUM_VALUE_ADDED: _ChangeRendering(
        frozenset({_K.ADD_ENUM_VALUE, _K.ALTER_COLUMN_TYPE}), _render_enum_value_added
    ),
    ChangeKind.ENUM_VALUE_RELABELED: _ChangeRendering(
        frozenset({_K.RENAME_ENUM_VALUE, _K.ALTER_COLUMN_TYPE, _K.RAW_BACKFILL}),
        _render_enum_value_relabeled,
    ),
    ChangeKind.ENUM_TYPE_REMOVED: _ChangeRendering(
        frozenset({_K.DROP_ENUM_TYPE}), _render_enum_type_removed
    ),
    ChangeKind.ENTITY_COMMENT_CHANGED: _ChangeRendering(
        frozenset({_K.SET_COMMENT}), _render_entity_comment_changed
    ),
    ChangeKind.FIELD_COMMENT_CHANGED: _ChangeRendering(
        frozenset({_K.SET_COMMENT}), _render_field_comment_changed
    ),
    ChangeKind.CHECK_ADDED: _ChangeRendering(
        frozenset({_K.ADD_CHECK_CONSTRAINT}), _render_check_added
    ),
    ChangeKind.CHECK_REMOVED: _ChangeRendering(
        frozenset({_K.DROP_CHECK_CONSTRAINT}), _render_check_removed
    ),
    ChangeKind.TRIGGER_ADDED: _ChangeRendering(
        frozenset({_K.CREATE_TRIGGER_FUNCTION, _K.CREATE_TRIGGER}),
        _render_trigger_added,
    ),
    ChangeKind.TRIGGER_REMOVED: _ChangeRendering(
        frozenset({_K.DROP_TRIGGER, _K.DROP_TRIGGER_FUNCTION}), _render_trigger_removed
    ),
}

#: The statement kinds each rendered change kind may produce.
CHANGE_KIND_STATEMENT_KINDS: Final[Mapping[ChangeKind, frozenset[SqlStatementKind]]] = {
    kind: rendering.statement_kinds for kind, rendering in _CHANGE_RENDERINGS.items()
}


def _rendering_for(kind: ChangeKind) -> _ChangeRendering:
    """The rendering of *kind*.

    Raises:
        GenerationError: *kind* is refused, or has no rendering.
    """
    if kind in REFUSED_CHANGE_KINDS:
        raise GenerationError(
            "A %s change cannot be rendered as forward DDL: %s. Expected: the change "
            "policy blocks this change before a revision is rendered."
            % (kind.value, REFUSED_CHANGE_KINDS[kind])
        )
    if kind not in _CHANGE_RENDERINGS:
        raise GenerationError(
            "Change kind '%s' has no revision rendering. Rendered kinds: %s; refused "
            "kinds: %s. Fix: add its rendering to the revision renderer."
            % (
                kind.value,
                sorted(k.value for k in _CHANGE_RENDERINGS),
                sorted(k.value for k in REFUSED_CHANGE_KINDS),
            )
        )
    return _CHANGE_RENDERINGS[kind]


def _render_change(ctx: _RevisionContext, change: SchemaChange) -> list[SqlStatement]:
    """The statements of *change*, each of a kind its rendering declares.

    Raises:
        GenerationError: The rendering produced a statement kind it does not declare.
    """
    rendering = _rendering_for(change.kind)
    statements = rendering.render(ctx, change)
    undeclared = {s.kind for s in statements} - rendering.statement_kinds
    if undeclared:
        raise GenerationError(
            "The %s rendering produced statement kinds %s it does not declare (declared: "
            "%s). Fix: declare them in the revision renderer's mapping."
            % (
                change.kind.value,
                sorted(k.value for k in undeclared),
                sorted(k.value for k in rendering.statement_kinds),
            )
        )
    return statements


# -- Whole schemas and convergences ------------------------------------------------


def _schema_statements(ctx: _RevisionContext) -> list[SqlStatement]:
    """Every statement of a whole schema, in dependency order (see the module docstring)."""
    tables = list(ctx.current.declared_tables().values())
    statements = _schema_prelude(ctx, create=True)
    statements.extend(
        _enum_type_statements(
            ctx, [(t.table_name, c) for t in tables for c in t.fields.values()]
        )
    )
    for table in tables:
        statements.extend(_create_table_statements(ctx, table))
    for table in tables:
        for foreign_key in table.foreign_keys:
            statements.extend(
                _add_foreign_key_statements(
                    ctx.dialect,
                    table.table_name,
                    realized_foreign_key_name(table, foreign_key),
                    foreign_key,
                    populated=False,
                )
            )
    for table in tables:
        statements.extend(_add_check_statements(ctx.dialect, table))
    for table in tables:
        for index in table.indexes:
            statements.extend(
                _create_index_statements(
                    ctx.dialect,
                    table.table_name,
                    index,
                    realized_index_name(table, index),
                )
            )
        statements.extend(_column_unique_statements(ctx, table))
    for table in tables:
        statements.extend(_standalone_comment_statements(ctx, table))
    for table in tables:
        statements.extend(_add_trigger_statements(ctx.dialect, table))
    return statements


#: The statement kinds that create an index or a unique constraint under a name.
_NAMED_CREATION_KINDS: Final[frozenset[SqlStatementKind]] = frozenset(
    {SqlStatementKind.CREATE_INDEX, SqlStatementKind.ADD_UNIQUE_CONSTRAINT}
)


_Rendered = TypeVar("_Rendered")


def _itself(statement: SqlStatement) -> SqlStatement:
    return statement


def _once_per_created_name(
    items: Sequence[_Rendered], statement_of: Callable[[_Rendered], SqlStatement]
) -> list[_Rendered]:
    """*items* with each index or unique constraint created once under its name.

    Two declarations can realize to one name (a trait's index and the entity's own,
    say). The engine rejects a second creation under a name it already holds, so an
    identical repeat is dropped; two different definitions under one name are a
    conflict no order resolves. *statement_of* reads the statement an item carries.

    Raises:
        GenerationError: Two creations share a name but not their statement.
    """
    created: dict[str, SqlStatement] = {}
    kept: list[_Rendered] = []
    for item in items:
        statement = statement_of(item)
        if statement.kind not in _NAMED_CREATION_KINDS:
            kept.append(item)
            continue
        earlier = created.get(statement.object_name)
        if earlier is None:
            created[statement.object_name] = statement
            kept.append(item)
            continue
        if earlier.sql != statement.sql:
            raise GenerationError(
                "The revision creates '%s' twice with different definitions: %r on "
                "table '%s', then %r on table '%s'. An index or unique constraint name is "
                "one object in the database. Fix: give one of the declarations its own "
                "name, or remove the duplicate declaration."
                % (
                    statement.object_name,
                    earlier.sql,
                    earlier.table,
                    statement.sql,
                    statement.table,
                )
            )
    return kept


def render_schema(
    snapshot: RdbmsSchemaSnapshot, dialect: SQLDialect
) -> RenderedRevision:
    """The ordered *dialect* statements that build *snapshot* from an empty schema.

    The one rendering of a whole block schema from empty: any output of a whole schema
    renders through it rather than assembling tables, keys, uniques, checks or indexes
    of its own.

    Args:
        snapshot: The block's schema snapshot.
        dialect: The block's SQL dialect.

    Returns:
        The schema's statements, in the order they run (see the module docstring).

    Raises:
        GenerationError: Two different creations share an index or constraint name, or
            a column cannot be rendered (each error names the object and the fix).
        DialectFeatureError: A statement the dialect cannot express.
    """
    ctx = _RevisionContext(snapshot, None, dialect, frozenset())
    statements = _once_per_created_name(_schema_statements(ctx), _itself)
    return RenderedRevision(statements=tuple(statements))


def _relocates_into_schema(changes: Sequence[SchemaChange]) -> bool:
    """Whether *changes* move the block from another place into a named schema."""
    return any(
        c.kind is ChangeKind.SCHEMA_RELOCATED and c.new_value is not None
        for c in changes
    )


def _holds_no_object(live: RdbmsSchemaSnapshot) -> bool:
    """Whether *live* holds no table and no enum type.

    A catalog reader reads only the block's place and stamps that place on the
    snapshot whether the database holds it or not, so a schema the database lacks
    reads as one holding nothing. An existing empty schema reads the same, and the
    dialect's ``create_schema`` creates a schema only where the database lacks it.
    """
    return not live.declared_tables() and not live.enums


def _ordered_change_statements(
    ctx: _RevisionContext, changes: Sequence[SchemaChange], *, create_schema: bool
) -> tuple[ChangeStatement, ...]:
    """The schema prelude, then every change in schema-change order, each name created once.

    Each statement is paired with the change it renders, the prelude's with none.
    """
    rendered = [
        ChangeStatement(statement, None)
        for statement in _schema_prelude(ctx, create=create_schema)
    ]
    for change in sorted(changes, key=schema_change_order):
        rendered.extend(ChangeStatement(s, change) for s in _render_change(ctx, change))
    return tuple(_once_per_created_name(rendered, lambda item: item.statement))


def _statements_of(rendered: Sequence[ChangeStatement]) -> RenderedRevision:
    return RenderedRevision(statements=tuple(item.statement for item in rendered))


def render_convergence_by_change(
    live: RdbmsSchemaSnapshot,
    desired: RdbmsSchemaSnapshot,
    changes: Sequence[SchemaChange],
    dialect: SQLDialect,
) -> tuple[ChangeStatement, ...]:
    """The statements :func:`render_convergence` renders, each with the change it renders.

    Args:
        live: ``L``, the block's live catalog prepared for comparison.
        desired: ``D``, the block's schema as generation wrote it.
        changes: The changes to render, in any order.
        dialect: The block's SQL dialect.

    Returns:
        The statements in the order they run; a statement of the schema prelude is paired
        with no change.

    Raises:
        GenerationError: As :func:`render_convergence`.
        DialectFeatureError: As :func:`render_convergence`.
    """
    ctx = _RevisionContext(desired, live, dialect, _enum_types_in_use(live))
    rendered = _ordered_change_statements(
        ctx,
        changes,
        create_schema=_holds_no_object(live) or _relocates_into_schema(changes),
    )
    logger.debug(
        "rendered_convergence block=%s dialect=%s changes=%d statements=%d",
        desired.block.name,
        dialect.name,
        len(changes),
        len(rendered),
    )
    return rendered


def render_convergence(
    live: RdbmsSchemaSnapshot,
    desired: RdbmsSchemaSnapshot,
    changes: Sequence[SchemaChange],
    dialect: SQLDialect,
) -> RenderedRevision:
    """The ordered *dialect* statements of *changes*, which bring *live* to *desired*.

    The changes run in schema-change order behind the search-path prelude, with no
    baseline path: an empty catalog is a *live* holding nothing, and its changes create
    all of *desired*. A removal is read from *live*, under the name the database holds;
    an addition from *desired*. The prelude creates the block's schema when *live*
    lacks it: when *live* holds no table and no enum type (how a catalog reader reads a
    place the database does not hold), or when *changes* relocate the block into it.

    Args:
        live: ``L``, the block's live catalog prepared for comparison.
        desired: ``D``, the block's schema as generation wrote it.
        changes: The changes to render, in any order.
        dialect: The block's SQL dialect.

    Returns:
        The statements, in the order they run.

    Raises:
        GenerationError: A change kind is refused or unmapped, a change names an object
            the snapshot it is read from does not hold, or two different creations
            share an index or constraint name (each error names the change and the fix).
        DialectFeatureError: A statement the dialect cannot express.
    """
    return _statements_of(render_convergence_by_change(live, desired, changes, dialect))
