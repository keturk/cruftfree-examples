"""Shared snapshot canonicalization layer for the schema converge (``L`` vs ``D``).

A live catalog and a source AST describe the same schema differently (implicit
PK/unique indexes, default-literal formatting, identifier casing, cosmetic
index-column ordering).  Both the source-built and the imported-live
``RdbmsSchemaSnapshot`` pass through :func:`canonicalize_snapshot` *before*
diffing so that equivalent schemas canonicalize to no change (architecture
decision D25).

One live-catalog artifact is deliberately NOT normalized here: the index some
engines create behind a foreign key.  Whether it is noise or a declared index is
not knowable from one snapshot -- the two are recorded identically -- so it is
settled against the declared side by
:func:`suppress_undeclared_fk_backing_indexes`, which the comparison sites that
face a live catalog call before canonicalizing.

There is exactly ONE canonical form.  The SAME function normalizes both sides —
no "source path" vs "live path" divergence.  No DB access, no engine branching,
no target-language metadata.  All snapshot dataclasses are frozen: canonicalization
returns NEW instances and never mutates inputs.  The transform is pure and
idempotent: ``canonicalize_snapshot(canonicalize_snapshot(x))`` equals
``canonicalize_snapshot(x)``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Context, Decimal, InvalidOperation

from cruftfree_rdbms_schema._canonicalize_align import (
    _aligned_enum,
    _aligned_scalar_column,
    _enum_alignments,
    _EnumAlignment,
    _fold_unique_indexes,
    _logical_category,
    _map_live_tables,
    _member_for_label,
    _rebuild_default,
    _strip_literal_wrapping,
    align_live_table_names,
    suppress_undeclared_fk_backing_indexes,
)
from cruftfree_rdbms_schema._canonicalize_rules import (
    _DSL_STRING_QUOTE,
    _ENUM_KIND,
    _FALSE_LITERALS,
    _LITERAL_KIND,
    _NOW_FUNCTIONS,
    _TRAILING_CAST_RE,
    _TRUE_LITERALS,
    CANONICAL_FALSE,
    CANONICAL_NOW,
    CANONICAL_TRUE,
    LiveCatalogFacts,
    _canonicalize_index,
    _canonicalize_type,
    _drop_implicit_indexes,
    _fk_sort_key,
    _index_sort_key,
)
from cruftfree_rdbms_schema._compound_default_alignment import (
    aligned_compound_default,
    is_scalar_tree,
)
from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotColumn,
    SnapshotDefault,
    SnapshotTable,
    SnapshotType,
)


# @canonical(rdbms-schema/snapshot-canonicalization): One shared canonicalization
# layer that normalizes source-built and imported-live RDBMS snapshots into a single
# canonical form before diffing (decision D25).
# @rule: The SAME function normalizes both sides — no source-path vs live-path divergence.
# @rule: Pure and idempotent; frozen in, frozen out; never mutate inputs.
# @rule: No DB access, no engine branching, no target-language metadata.
# @rule: Unrecognized default/type shapes raise — never silently pass through.
# @rule: NEVER delete an index a declaration could have asked for. Only a PK- or
#   unique-constraint-derived index is implied on every engine; a foreign key's
#   backing index is not, and suppressing it here destroyed `belongsTo … : index`.
#   A live catalog's own FK bookkeeping is settled pairwise by
#   suppress_undeclared_fk_backing_indexes.
# @anti-pattern: Dropping implicit indexes by name heuristics instead of structural match.
# @anti-pattern: Per-engine special-casing here (engine reverse mapping lives in reflectors).
# @see: rdbms-schema/schema-snapshot
# @see: rdbms-schema/schema-differ
def canonicalize_snapshot(snapshot: RdbmsSchemaSnapshot) -> RdbmsSchemaSnapshot:
    """Return a new snapshot in canonical form.

    Applied identically to source-built and imported-live snapshots before
    diffing.  Pure and idempotent — returns new frozen instances and never
    mutates the input.

    Args:
        snapshot: Snapshot to canonicalize (source-built or imported-live).

    Returns:
        A new :class:`RdbmsSchemaSnapshot` in canonical form.

    Raises:
        ValueError: If a column carries an unrecognized type kind, or a column
            default has an unrecognized shape for its logical type.
    """
    canonical_entities = {
        name: _canonicalize_table(table) for name, table in snapshot.entities.items()
    }
    # A read model's backing table normalizes through the SAME rules as an
    # entity's -- it is the same shape and the same kind of physical table.
    canonical_views = {
        name: _canonicalize_table(view) for name, view in snapshot.cqrs_views.items()
    }
    # An audit-log table is a physical table like the others and normalizes
    # through the same rules.
    canonical_audit_tables = {
        name: _canonicalize_table(table)
        for name, table in snapshot.audit_log_tables.items()
    }
    # A junction table is a physical table like the others, too.
    canonical_junction_tables = {
        name: _canonicalize_table(table)
        for name, table in snapshot.junction_tables.items()
    }
    # And so is a framework table.
    canonical_framework_tables = {
        name: _canonicalize_table(table)
        for name, table in snapshot.framework_tables.items()
    }

    return replace(
        snapshot,
        entities=canonical_entities,
        cqrs_views=canonical_views,
        audit_log_tables=canonical_audit_tables,
        junction_tables=canonical_junction_tables,
        framework_tables=canonical_framework_tables,
    )


def _canonicalize_table(table: SnapshotTable) -> SnapshotTable:
    """Canonicalize a single entity table: fields, indexes, foreign keys, checks."""
    canonical_fields = {
        name: _canonicalize_column(col) for name, col in table.fields.items()
    }
    table_with_fields = replace(
        table,
        fields=canonical_fields,
        # A key keeps its name: the differ reports a name the two sides disagree on as a
        # rename, and equality ignores it.
        foreign_keys=tuple(sorted(table.foreign_keys, key=_fk_sort_key)),
        # A check is identified by its name and nothing else, so set order is the
        # only spelling two sides can differ in.
        checks=tuple(sorted(table.checks, key=lambda check: check.name)),
        # A trigger is identified by its name alone, like a check.
        triggers=tuple(sorted(table.triggers, key=lambda trigger: trigger.name)),
    )
    kept_indexes = _drop_implicit_indexes(table_with_fields)
    canonical_indexes = tuple(
        sorted(
            (_canonicalize_index(idx) for idx in kept_indexes),
            key=_index_sort_key,
        )
    )
    return replace(table_with_fields, indexes=canonical_indexes)


def _canonicalize_column(column: SnapshotColumn) -> SnapshotColumn:
    """Canonicalize a column: type, PK-derived constraints, and default literal.

    A primary key implies NOT NULL and uniqueness; normalize both consistently so
    a source snapshot (which may omit the redundant flags) and a reflected live
    snapshot (which surfaces them) agree.
    """
    canonical_type = _canonicalize_type(column.type)
    nullable = column.nullable and not column.primary_key
    unique = column.unique or column.primary_key
    canonical_default = _canonicalize_default(column.default, canonical_type)
    return SnapshotColumn(
        column_name=column.column_name.lower(),
        type=canonical_type,
        storage=column.storage,
        nullable=nullable,
        primary_key=column.primary_key,
        default=canonical_default,
        unique=unique,
        comment=column.comment,
    )


# @canonical(rdbms-schema/live-catalog-preparation): The one preparation every
#   comparison against a live catalog runs before canonicalizing both sides.
# @rule: Every fact a catalog spells differently from a declaration is settled here,
#   pairwise against the declared side -- never by loosening the differ.
# @rule: Target and engine facts arrive as LiveCatalogFacts; this package imports none.
# @anti-pattern: Reading a catalog's own spelling (a label, a reported type) as drift,
#   which makes every comparison against a real database dirty.
# @see: rdbms-schema/snapshot-canonicalization
def prepare_live_for_comparison(
    reference: RdbmsSchemaSnapshot | None,
    live: RdbmsSchemaSnapshot,
    facts: LiveCatalogFacts,
) -> RdbmsSchemaSnapshot:
    """The live snapshot, ready to be canonicalized and diffed against *reference*.

    Every comparison against a live catalog calls this first:

    1. tables are keyed by the declared names the reference uses
       (:func:`align_live_table_names`);
    2. the facts a catalog spells differently from a declaration -- enum labels,
       reported types, a unique index stored as a constraint -- take the reference's
       spelling where they describe the same schema (:func:`align_live_spelling`);
    3. the foreign-key backing indexes the reference never declared are dropped
       (:func:`suppress_undeclared_fk_backing_indexes`).

    ``reference=None`` means nothing is declared, so there is nothing to align to.

    Args:
        reference: The declared side of the comparison, or None.
        live: The imported live snapshot. Never mutated.
        facts: The target's and engine's facts about the live catalog.

    Returns:
        The prepared live snapshot.
    """
    if reference is None:
        return suppress_undeclared_fk_backing_indexes(None, live)
    named = align_live_table_names(reference, live)
    aligned = align_live_spelling(reference, named, facts)
    return suppress_undeclared_fk_backing_indexes(reference, aligned)


def _aligned_enum_default(
    default: SnapshotDefault | None, alignment: _EnumAlignment
) -> SnapshotDefault | None:
    """A catalog's ``'label'::type`` default as the declaration spells it, ``Enum.Member``."""
    if default is None or default.kind != _LITERAL_KIND:
        return default
    label = _strip_literal_wrapping(default.value)
    if label not in alignment.member_by_label:
        return default
    return SnapshotDefault(
        kind=default.kind,
        value="%s.%s" % (alignment.reference.name, alignment.member_by_label[label]),
        name=default.name,
        tree=default.tree,
    )


def _aligned_enum_column(
    column: SnapshotColumn, alignments: Mapping[str, _EnumAlignment]
) -> SnapshotColumn:
    """An enum-typed live column typed with the reference enum and its member names."""
    if column.type.name not in alignments:
        return column
    alignment = alignments[column.type.name]
    return replace(
        column,
        type=SnapshotType(
            kind=_ENUM_KIND,
            name=alignment.reference.name,
            constraints=column.type.constraints,
            values=tuple(
                _member_for_label(alignment, label) for label in column.type.values
            ),
        ),
        default=_aligned_enum_default(column.default, alignment),
    )


def _aligned_table(
    declared: SnapshotTable | None,
    live: SnapshotTable,
    alignments: Mapping[str, _EnumAlignment],
    facts: LiveCatalogFacts,
) -> SnapshotTable:
    """One live table spelled as *declared* wherever both describe the same schema."""
    declared_columns = (
        {}
        if declared is None
        else {col.column_name.lower(): col for col in declared.fields.values()}
    )

    def aligned(column: SnapshotColumn) -> SnapshotColumn:
        if column.type.kind == _ENUM_KIND:
            return _aligned_enum_column(column, alignments)
        declared_column = declared_columns.get(column.column_name.lower())
        if declared_column is None:
            return column
        typed = _aligned_scalar_column(declared_column, column, facts)
        default = aligned_compound_default(
            declared_column.default, typed.default, facts.ddl_dialect
        )
        return typed if default is typed.default else replace(typed, default=default)

    table = replace(
        live, fields={name: aligned(col) for name, col in live.fields.items()}
    )
    if declared is None:
        return table
    return _fold_unique_indexes(declared, table)


def align_live_spelling(
    reference: RdbmsSchemaSnapshot,
    live: RdbmsSchemaSnapshot,
    facts: LiveCatalogFacts,
) -> RdbmsSchemaSnapshot:
    """*live* spelled as *reference* wherever the two describe the same schema.

    A catalog reports what the database stores, which is not always how the declaration
    states it:

    - an enum's members as their stored labels, under a name derived from the type's
      database name, with no record of which label a ``value(...)`` declared -- read back
      as the reference enum's members through the labels they are stored as;
    - an enum default as ``'label'::type`` -- read back as ``Enum.Member``;
    - a declared type as the type the engine stores it as -- read back as the declared
      type when the engine reports exactly that for it (:attr:`LiveCatalogFacts.stored_type`);
    - a single-column unique index as a unique constraint (:func:`_fold_unique_indexes`).

    Anything else is left as the catalog reports it, so a real difference still shows.
    Tables must already be keyed as the reference keys them (:func:`align_live_table_names`).

    Args:
        reference: The declared side of the comparison.
        live: The imported live snapshot. Never mutated.
        facts: The target's and engine's facts about the live catalog.

    Returns:
        A new snapshot, or ``live`` itself when it already spells everything as the
        reference does.
    """
    alignments = _enum_alignments(reference, live)
    reference_tables = reference.declared_tables()
    tables = _map_live_tables(
        live,
        lambda name, table: _aligned_table(
            reference_tables.get(name), table, alignments, facts
        ),
    )
    aligned = replace(
        tables,
        enums=tuple(
            _aligned_enum(live_enum, alignments[live_enum.name])
            if live_enum.name in alignments
            else live_enum
            for live_enum in live.enums
        ),
    )
    return live if aligned == live else aligned


def _canonicalize_default(
    default: SnapshotDefault | None,
    type_: SnapshotType,
) -> SnapshotDefault | None:
    """Normalize a default literal to a canonical representation per logical type.

    Numeric, boolean, timestamp-now, and string literals each have ONE canonical
    spelling so equivalent source and live defaults collapse to the same value.
    Server-function and generated defaults are normalized only for the
    timestamp-now case; otherwise the expression is compared verbatim.

    The mapping is exhaustive per logical type and fails loud on an unrecognized
    default shape — a silent pass-through would reintroduce false-positive drift.

    Args:
        default: The column default, or None.
        type_: The already-canonicalized column type.

    Returns:
        A new canonical :class:`SnapshotDefault`, or None.

    Raises:
        ValueError: If the default value is not recognized for its logical type.
    """
    if default is None:
        return None

    # A compound default (``1 + 2``, ``'a' + 'b'``) is recorded as the renderer's
    # spelling of its lowered tree, a pure function of the tree: there is no other
    # spelling of it to collapse, and no per-type literal form it could take.
    if default.tree is not None and not is_scalar_tree(default.tree):
        return default

    if type_.kind == "enum":
        return _rebuild_default(default, default.value)

    category = _logical_category(type_.name)

    if category == "boolean":
        return _rebuild_default(default, _canonicalize_boolean_default(default))
    if category == "numeric":
        return _rebuild_default(default, _canonicalize_numeric_default(default))
    if category == "timestamp":
        return _rebuild_default(default, _canonicalize_timestamp_default(default))
    if category == "string":
        return _rebuild_default(default, _canonicalize_string_default(default))
    # category == "opaque": the payload is compared as written, but the quoting and
    # cast a catalog wraps around a literal one (``'[]'::json``) are its own spelling.
    if default.kind == _LITERAL_KIND and _TRAILING_CAST_RE.search(
        default.value.strip()
    ):
        return _rebuild_default(default, _strip_literal_wrapping(default.value))
    return _rebuild_default(default, default.value)


def _canonicalize_boolean_default(default: SnapshotDefault) -> str:
    """Normalize a boolean default to ``true`` / ``false``.

    Server functions and generated expressions (``(1 < 2)`` as a catalog reports a compound
    default it could not be read back from) are compared verbatim; only literal boolean
    defaults have their spelling normalized.

    Raises:
        ValueError: If a literal value is not a recognized boolean literal.
    """
    if default.kind != _LITERAL_KIND:
        return default.value
    token = _strip_literal_wrapping(default.value).lower()
    if token in _TRUE_LITERALS:
        return CANONICAL_TRUE
    if token in _FALSE_LITERALS:
        return CANONICAL_FALSE
    raise ValueError(
        f"Unrecognized boolean default '{default.value}'. Expected one of "
        f"{sorted(_TRUE_LITERALS | _FALSE_LITERALS)} (case-insensitive, "
        f"optionally quoted or cast)."
    )


def _canonicalize_numeric_default(default: SnapshotDefault) -> str:
    """Normalize a numeric default to the plain decimal text of its value.

    A literal is canonicalized by its value, never its spelling: the stripped token
    is parsed exactly as a decimal and rendered with no trailing fractional zeros,
    no fractional part when integral, no exponent and no sign on zero. A source
    ``1.0`` and a catalog's ``'1'::double precision`` both become ``1``; ``2.50``
    and ``'2.5'::numeric`` both become ``2.5``. Exact decimal parsing keeps every
    significant digit a high-precision literal carries. A non-finite value
    (``'Infinity'::double precision``) has no digits to normalize and keeps its
    stripped spelling.

    Server functions (e.g. sequence/UUID generators) and generated expressions
    are not numeric literals and are compared verbatim.

    Raises:
        ValueError: If a literal default is not a parseable number.
    """
    if default.kind != _LITERAL_KIND:
        return default.value
    token = _strip_literal_wrapping(default.value)
    try:
        parsed = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError(
            f"Unrecognized numeric default '{default.value}': stripped form "
            f"'{token}' is not a number."
        ) from exc
    if not parsed.is_finite():
        return token
    if parsed.is_zero():
        return "0"
    # The context's precision is the literal's own digit count, so normalizing never rounds.
    exact = Context(prec=len(parsed.as_tuple().digits))
    return format(parsed.normalize(exact), "f")


def _canonicalize_timestamp_default(default: SnapshotDefault) -> str:
    """Normalize a timestamp default; collapse all "now" spellings to ``now()``.

    Non-now timestamp literals (e.g. ``'00:00:00'``, ``CURRENT_DATE``) are
    compared by their stripped literal form.
    """
    token = _strip_literal_wrapping(default.value).lower()
    if token in _NOW_FUNCTIONS:
        return CANONICAL_NOW
    return _strip_literal_wrapping(default.value)


def _canonicalize_string_default(default: SnapshotDefault) -> str:
    """Normalize a string default to the DSL's own single-quoted spelling.

    An engine's quoting and cast (``'foo'::text``, ``"foo"``) are stripped and the
    text is wrapped back in the single quotes ``render_expression_source`` gives a
    string literal, so a reflected and a declared default compare equal AND the
    canonical value stays the DSL source every DDL renderer reads -- a
    statement rendered from a canonical snapshot quotes it like any other.

    Server functions and generated expressions are compared verbatim; only
    literal string defaults have their quoting normalized.
    """
    if default.kind != _LITERAL_KIND:
        return default.value
    return f"{_DSL_STRING_QUOTE}{_strip_literal_wrapping(default.value)}{_DSL_STRING_QUOTE}"
