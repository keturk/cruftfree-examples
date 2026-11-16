"""Alignment of live names and defaults during canonicalization."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace

from cruftfree_common.cruftfree_model.enum_literal_text import (
    stored_enum_literal_from_parts,
)

from cruftfree_rdbms_schema._canonicalize_rules import (
    _AUDIT_LOG_TABLES,
    _BOOLEAN_TYPES,
    _CQRS_VIEWS,
    _ENTITIES,
    _FRAMEWORK_TABLES,
    _JUNCTION_TABLES,
    _NUMERIC_TYPES,
    _OPAQUE_TYPES,
    _SCALAR_KIND,
    _STRING_TYPES,
    _TIMESTAMP_TYPES,
    _TRAILING_CAST_RE,
    LiveCatalogFacts,
    _canonicalize_type,
    _suppress_table_fk_backing,
    _table_maps,
    canonical_index_identity,
)
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotColumn,
    SnapshotDefault,
    SnapshotEnum,
    SnapshotIndex,
    SnapshotTable,
    SnapshotType,
)


def align_live_table_names(
    reference: RdbmsSchemaSnapshot,
    live: RdbmsSchemaSnapshot,
) -> RdbmsSchemaSnapshot:
    """File every live table where *reference* records the same table, under its declared name.

    A source-built snapshot keys a table by its declared entity name (``Payment``) and files it
    as an entity, a CQRS view, an audit-log, junction or framework table; a reflected catalog can
    only know the physical table name (``payments``), and files every table as an entity. The
    differ pairs tables by key, so without this step every declared table would be reported
    removed and every physical table added whatever the schema holds, and a comparison that
    reads each kind of table on its own would find every view, audit-log and junction table
    missing. The one fact that joins the two is ``SnapshotTable.table_name``: a live table whose
    physical name the reference records takes the reference's declared name and kind; a live
    table the reference does not know keeps its own name and kind, and is reported as added
    under it.

    Args:
        reference: The declared side of the comparison.
        live: The imported live snapshot. Never mutated.

    Returns:
        A new snapshot with re-filed tables, or ``live`` itself when every table already sits
        under the reference's name and kind.
    """
    declared_by_table = {
        table.table_name: (kind, name)
        for kind, tables in _table_maps(reference).items()
        for name, table in tables.items()
    }
    live_maps = _table_maps(live)
    filed: dict[str, dict[str, SnapshotTable]] = {kind: {} for kind in live_maps}
    for kind, tables in live_maps.items():
        for name, table in tables.items():
            declared_kind, declared_name = declared_by_table.get(
                table.table_name, (kind, name)
            )
            filed[declared_kind][declared_name] = table
    if all(list(filed[kind]) == list(tables) for kind, tables in live_maps.items()):
        return live
    return replace(
        live,
        entities=filed[_ENTITIES],
        cqrs_views=filed[_CQRS_VIEWS],
        audit_log_tables=filed[_AUDIT_LOG_TABLES],
        junction_tables=filed[_JUNCTION_TABLES],
        framework_tables=filed[_FRAMEWORK_TABLES],
    )


def _map_live_tables(
    live: RdbmsSchemaSnapshot,
    transform: Callable[[str, SnapshotTable], SnapshotTable],
) -> RdbmsSchemaSnapshot:
    """*live* with *transform* applied to every table of every kind, keys kept."""
    return replace(
        live,
        entities={
            name: transform(name, table) for name, table in live.entities.items()
        },
        cqrs_views={
            name: transform(name, table) for name, table in live.cqrs_views.items()
        },
        audit_log_tables={
            name: transform(name, table)
            for name, table in live.audit_log_tables.items()
        },
        junction_tables={
            name: transform(name, table) for name, table in live.junction_tables.items()
        },
        framework_tables={
            name: transform(name, table)
            for name, table in live.framework_tables.items()
        },
    )


@dataclass(frozen=True)
class _EnumAlignment:
    """How one live enum's labels read as the members of the reference enum stored as them."""

    reference: SnapshotEnum
    member_by_label: Mapping[str, str]
    declared_by_member: Mapping[str, str | None]


def _enum_alignments(
    reference: RdbmsSchemaSnapshot, live: RdbmsSchemaSnapshot
) -> dict[str, _EnumAlignment]:
    """Per live enum name, the reference enum stored under the same database name.

    Only a reference enum that records every member's declared value can say which label
    each member is stored as (:func:`stored_enum_literal_from_parts`); any other is left
    unaligned and compared as the catalog reports it.
    """
    by_database_name = {
        snap_enum.database_name: snap_enum
        for snap_enum in reference.enums
        if snap_enum.values and len(snap_enum.member_values) == len(snap_enum.values)
    }
    alignments: dict[str, _EnumAlignment] = {}
    for live_enum in live.enums:
        declared = by_database_name.get(live_enum.database_name)
        if declared is None:
            continue
        pairs = tuple(zip(declared.values, declared.member_values, strict=True))
        alignments[live_enum.name] = _EnumAlignment(
            reference=declared,
            member_by_label={
                stored_enum_literal_from_parts(member, value): member
                for member, value in pairs
            },
            declared_by_member=dict(pairs),
        )
    return alignments


def _member_for_label(alignment: _EnumAlignment, label: str) -> str:
    """The reference member stored as *label*; a label no member is stored as names itself.

    A label no reference member is stored as is a member the database holds and the
    declaration does not, so it must stay visible to the differ under a name of its own,
    never a declared member's. When a declared member bears the label's name, its stored
    label differs (a ``value(...)`` added or changed on it), and the label is named as a
    catalog spells it, quoted (``'closed'``), which no declared member name can be. Read
    as that member it would be a relabel: a claim that the label and the member are one,
    which a catalog cannot make.
    """
    if label in alignment.member_by_label:
        return alignment.member_by_label[label]
    if label in alignment.declared_by_member:
        return f"'{label}'"
    return label


def _aligned_enum(live_enum: SnapshotEnum, alignment: _EnumAlignment) -> SnapshotEnum:
    """*live_enum* named and membered as the reference, with each member's declared value."""
    members = tuple(_member_for_label(alignment, label) for label in live_enum.values)
    member_values = tuple(
        alignment.declared_by_member[alignment.member_by_label[label]]
        if label in alignment.member_by_label
        else label
        for label in live_enum.values
    )
    return SnapshotEnum(
        name=alignment.reference.name,
        database_name=live_enum.database_name,
        values=members,
        member_values=member_values,
    )


def _same_type(left: SnapshotType, right: SnapshotType) -> bool:
    """Whether two canonical scalar types are the one the differ would not tell apart."""
    return left.name == right.name and left.constraints == right.constraints


def _aligned_scalar_column(
    declared: SnapshotColumn, column: SnapshotColumn, facts: LiveCatalogFacts
) -> SnapshotColumn:
    """*column* typed as *declared* when the engine reports *declared*'s type as *column*'s.

    A declared ``Latitude`` is stored as ``DECIMAL(9,6)`` and reflected as a ``Decimal``
    of precision 9 and scale 6; asking the engine's reported type for the declaration
    (:attr:`LiveCatalogFacts.stored_type`) is what tells that from a column whose type
    really changed.
    """
    if declared.type.kind != _SCALAR_KIND or column.type.kind != _SCALAR_KIND:
        return column
    declared_type = _canonicalize_type(declared.type)
    live_type = _canonicalize_type(column.type)
    if _same_type(declared_type, live_type):
        return column
    reported = _canonicalize_type(facts.stored_type(declared_type, declared.storage))
    if not _same_type(reported, live_type):
        return column
    return replace(column, type=declared.type, storage=declared.storage)


def _single_column_unique_index_columns(
    table: SnapshotTable,
) -> dict[str, SnapshotIndex]:
    """Per column, the plain single-column unique index *table* declares over it."""
    return {
        index.columns[0].lower(): index
        for index in table.indexes
        if index.unique
        and len(index.columns) == 1
        and not index.fulltext
        and not index.spatial
    }


def _fold_unique_indexes(declared: SnapshotTable, live: SnapshotTable) -> SnapshotTable:
    """*live* with a unique constraint read as the unique index *declared* states.

    A single-column unique index and a unique constraint over the same column make the
    same promise, and a catalog can report the one a declaration spells as the other.
    Where *declared* states the index and *live* holds the constraint, the live column
    is read as the index so the two compare equal.
    """
    declared_columns = {
        col.column_name.lower(): col for col in declared.fields.values()
    }
    live_identities = {canonical_index_identity(index) for index in live.indexes}
    fields = dict(live.fields)
    added: list[SnapshotIndex] = []
    for column_name, index in _single_column_unique_index_columns(declared).items():
        declared_column = declared_columns.get(column_name)
        live_key = next(
            (
                key
                for key, col in live.fields.items()
                if col.column_name.lower() == column_name
            ),
            None,
        )
        if declared_column is None or live_key is None:
            continue
        if (
            declared_column.unique
            or declared_column.primary_key
            or not fields[live_key].unique
        ):
            continue
        fields[live_key] = replace(fields[live_key], unique=False)
        if canonical_index_identity(index) not in live_identities:
            added.append(index)
    if fields == live.fields:
        return live
    return replace(live, fields=fields, indexes=live.indexes + tuple(added))


def suppress_undeclared_fk_backing_indexes(
    reference: RdbmsSchemaSnapshot | None,
    live: RdbmsSchemaSnapshot,
) -> RdbmsSchemaSnapshot:
    """Drop from *live* the FK-backing indexes *reference* does not declare.

    Some engines create an index behind every foreign key; PostgreSQL does not.
    An index a live catalog carries for a foreign key that the declared side never
    asked for is that engine's own bookkeeping, and reporting it as drift would
    make every comparison against such a database permanently dirty.

    **Pairwise on purpose, and that is the whole correctness argument.** The same
    suppression applied per-snapshot -- which is where it used to live, inside
    canonicalization -- cannot tell an index the engine invented from one a
    ``belongsTo … : index`` declaration asked for, because the snapshot records
    both as the same plain single-column entry. So it deleted declared schema
    before any comparison ran. Here the declared side is in hand: an index the
    reference declares is kept on both sides and compared normally, and only an
    index that exists *solely* in the live catalog and sits exactly on a foreign
    key's columns is dropped.

    ``reference=None`` means nothing is declared -- a block being adopted with no
    recorded baseline -- and every FK-backing index in the live catalog is then
    the engine's, so all of them are suppressed.

    Unique, fulltext and spatial indexes are never suppressed: no engine invents
    one behind a foreign key, so such an index is always somebody's deliberate
    object.

    Args:
        reference: The declared side of the comparison (``D``), or None when
            nothing is declared.
        live: The imported live snapshot to filter. Never mutated.

    Returns:
        A new snapshot with the undeclared FK-backing indexes removed, or ``live``
        itself when there is nothing to suppress.
    """
    reference_tables = {} if reference is None else reference.declared_tables()
    live_entities = {
        name: _suppress_table_fk_backing(table, reference_tables.get(name))
        for name, table in live.entities.items()
    }
    live_views = {
        name: _suppress_table_fk_backing(view, reference_tables.get(name))
        for name, view in live.cqrs_views.items()
    }
    live_audit_tables = {
        name: _suppress_table_fk_backing(table, reference_tables.get(name))
        for name, table in live.audit_log_tables.items()
    }
    live_junction_tables = {
        name: _suppress_table_fk_backing(table, reference_tables.get(name))
        for name, table in live.junction_tables.items()
    }
    live_framework_tables = {
        name: _suppress_table_fk_backing(table, reference_tables.get(name))
        for name, table in live.framework_tables.items()
    }
    unchanged = (
        all(live_entities[name] is table for name, table in live.entities.items())
        and all(live_views[name] is view for name, view in live.cqrs_views.items())
        and all(
            live_audit_tables[name] is table
            for name, table in live.audit_log_tables.items()
        )
        and all(
            live_junction_tables[name] is table
            for name, table in live.junction_tables.items()
        )
        and all(
            live_framework_tables[name] is table
            for name, table in live.framework_tables.items()
        )
    )
    if unchanged:
        return live
    return replace(
        live,
        entities=live_entities,
        cqrs_views=live_views,
        audit_log_tables=live_audit_tables,
        junction_tables=live_junction_tables,
        framework_tables=live_framework_tables,
    )


def _logical_category(canonical_type_name: str) -> str:
    """Map a canonical type name to its default-literal logical category.

    Raises:
        ValueError: If the type name belongs to no known logical category.
    """
    if canonical_type_name in _BOOLEAN_TYPES:
        return "boolean"
    if canonical_type_name in _NUMERIC_TYPES:
        return "numeric"
    if canonical_type_name in _TIMESTAMP_TYPES:
        return "timestamp"
    if canonical_type_name in _STRING_TYPES:
        return "string"
    if canonical_type_name in _OPAQUE_TYPES:
        return "opaque"
    raise ValueError(
        f"Cannot canonicalize default for type '{canonical_type_name}': the type "
        f"belongs to no known logical category (boolean, numeric, timestamp, "
        f"string, opaque). Add it to the appropriate category set in "
        f"canonicalize.py."
    )


def _rebuild_default(default: SnapshotDefault, value: str) -> SnapshotDefault:
    """Return a new SnapshotDefault with a normalized value, preserving kind, name and tree.

    The tree is kept: a canonical spelling of the same value lowers to the same tree.
    """
    if value == default.value:
        return default
    return SnapshotDefault(
        kind=default.kind, value=value, name=default.name, tree=default.tree
    )


def _strip_literal_wrapping(value: str) -> str:
    """Strip outer single/double quotes and a trailing ``::type`` cast.

    PostgreSQL reflects literals with explicit casts (``0::integer``,
    ``'foo'::text``) and quoting that a source AST omits.  Normalize both away so
    the underlying literal is compared.
    """
    stripped = _TRAILING_CAST_RE.sub("", value.strip()).strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in "'\"":
        stripped = stripped[1:-1]
    return stripped
