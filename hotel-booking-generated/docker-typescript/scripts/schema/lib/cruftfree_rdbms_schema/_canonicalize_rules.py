"""Index and type rules of snapshot canonicalization."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, replace

from cruftfree_rdbms_schema._snapshot_models import (
    RdbmsSchemaSnapshot,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotStorage,
    SnapshotTable,
    SnapshotType,
)

logger = logging.getLogger(__name__)


# ── Canonical default representations ──
#
# Each logical type category has ONE canonical literal form.  Equivalent literals
# from a source AST and a reflected live catalog must collapse to the same string,
# or drift detection produces false positives.

CANONICAL_TRUE = "true"
CANONICAL_FALSE = "false"
# Every "current timestamp" spelling collapses to the DSL call it is declared as, so
# a canonical snapshot stays one every DDL renderer can render.
CANONICAL_NOW = "DateTime.now()"

# Boolean literal spellings observed across source ASTs and engine catalogs.
_TRUE_LITERALS = frozenset({"true", "t", "1", "yes", "y"})
_FALSE_LITERALS = frozenset({"false", "f", "0", "no", "n"})

# Server-side "current timestamp" function spellings across engines.
_NOW_FUNCTIONS = frozenset(
    {
        "now()",
        "now",
        "datetime.now()",
        "current_timestamp",
        "current_timestamp()",
        "getdate()",
        "statement_timestamp()",
        "transaction_timestamp()",
    }
)

# Logical categories that map canonical CruftFree type names onto a default-literal
# normalization strategy.  Every canonical builtin must fall into exactly one.
_BOOLEAN_TYPES = frozenset({"Boolean"})

_NUMERIC_TYPES = frozenset(
    {
        "Integer",
        "Short",
        "Long",
        "Float",
        "Decimal",
        "Money",
        "Percentage",
        "Latitude",
        "Longitude",
        "Timestamp",
        "TimestampMs",
        "Duration",
    }
)

_TIMESTAMP_TYPES = frozenset({"DateTime", "Date", "Time"})

_STRING_TYPES = frozenset(
    {
        "String",
        "Text",
        "ConfigPath",
        "UUID",
        "Email",
        "URL",
        "Phone",
        "IPAddress",
        "Slug",
        "Color",
        "CountryCode",
        "LanguageCode",
        "CurrencyCode",
        "PostalCode",
        "CreditCard",
        "IBAN",
        "MAC",
        "CIDR",
        "Password",
        "Exception",
    }
)

# Types whose default literals are passed through verbatim (opaque payloads /
# binary / spatial / void) — there is no cosmetic variance to normalize, but the
# category is still explicit so unknown types fail loud rather than silently pass.
_OPAQUE_TYPES = frozenset({"JSON", "Bytes", "Void", "Geometry", "Geography"})

# Only "literal" defaults carry a normalizable literal value; "server_function"
# and "generated" defaults are opaque expressions compared verbatim.
_LITERAL_KIND = "literal"
# The quote ``render_expression_source`` wraps a DSL string literal in.
_DSL_STRING_QUOTE = "'"
# A trailing ``::type`` cast a catalog appends to a literal default: a type name of
# words, dots, spaces or quoted identifiers, an optional ``(n)``/``(p,s)`` size and
# array brackets, anchored at the end so a ``::`` inside a quoted literal is kept.
_TRAILING_CAST_RE = re.compile(
    r"::\s*[A-Za-z_\"][\w .\"]*(?:\(\s*\d+(?:\s*,\s*\d+)?\s*\))?(?:\[\])*$"
)
_SCALAR_KIND = "scalar"
_ENUM_KIND = "enum"

# The kinds a snapshot files its tables as, each the name of its table map.
_ENTITIES = "entities"
_CQRS_VIEWS = "cqrs_views"
_AUDIT_LOG_TABLES = "audit_log_tables"
_JUNCTION_TABLES = "junction_tables"
_FRAMEWORK_TABLES = "framework_tables"


@dataclass(frozen=True)
class LiveCatalogFacts:
    """What a comparison against a live catalog must know about the target and engine.

    A declared schema and the catalog a database reports for it spell some facts
    differently, and only the target's own plugins can say how. The comparison is
    handed them rather than importing them, so this package stays target-neutral.

    Attributes:
        stored_type: The type the live engine reports for a declared scalar type and
            its storage (``Latitude`` is reported as ``Decimal(9,6)``).
        ddl_dialect: The DDL dialect the engine speaks, whose rows wrote every default
            the catalog holds (a compound default's regex pattern is compared as the
            constant they write it as).
    """

    stored_type: Callable[[SnapshotType, SnapshotStorage], SnapshotType]
    ddl_dialect: str


def _fk_sort_key(fk: SnapshotForeignKey) -> tuple[str, str, str]:
    """Deterministic ordering key for foreign keys (order is not significant)."""
    return (",".join(fk.columns), fk.referred_table, ",".join(fk.referred_columns))


def _index_sort_key(index: SnapshotIndex) -> tuple[str, bool, bool, bool, str]:
    """Deterministic ordering key for indexes (set membership, not order)."""
    return (
        ",".join(index.columns),
        index.unique,
        index.fulltext,
        index.spatial,
        index.name or "",
    )


def _canonicalize_type(type_: SnapshotType) -> SnapshotType:
    """Check a column type's kind and return the type unchanged.

    Both operands are written in canonical form by their producers: the
    snapshot builder records each scalar's canonical builtin name, and a reader
    records the name its engine's reverse type map holds, every value of which
    is a canonical name.  So no scalar name is resolved here; a non-canonical
    name is caught statically, at its producer, never at run time.  Enum type
    names are identifiers and are left as-is too.

    Raises:
        ValueError: If the type kind is neither ``scalar`` nor ``enum``.
    """
    if type_.kind not in ("scalar", "enum"):
        raise ValueError(
            f"Unrecognized snapshot type kind '{type_.kind}' for type "
            f"'{type_.name}'. Expected 'scalar' or 'enum'."
        )
    return type_


def canonical_index_identity(
    index: SnapshotIndex,
) -> tuple[tuple[str, ...], bool, bool, bool]:
    """The identity two indexes share when canonicalization treats them as one.

    Exactly the fields :func:`_canonicalize_index` keeps: lower-cased columns in
    order, uniqueness, and the two kind flags. ``name`` is excluded because it is
    not part of what an index is: the same index under another name is a rename,
    which the differ reports, never a different index.

    Published because a caller holding a RAW snapshot sometimes needs to ask
    whether canonicalization kept a given index: an index's physical NAME is
    derived from its position in the RAW table (a fulltext index's ordinal), so a
    caller that must reproduce the emitted name has to realize the raw index while
    still consulting the canonical form for whether the index is expected to exist
    at all. Re-deriving this tuple at that call site would be a second definition
    of canonical identity, free to drift from this one.

    Args:
        index: Any snapshot index, raw or canonical.

    Returns:
        Its canonical identity.
    """
    return (
        tuple(col.lower() for col in index.columns),
        index.unique,
        index.fulltext,
        index.spatial,
    )


def _canonicalize_index(index: SnapshotIndex) -> SnapshotIndex:
    """Normalize index identifier casing.

    Index column order is semantically significant for composite indexes (it
    governs which query predicates the index can serve), so it is preserved.
    Identifier casing is cosmetic and normalized to lower case (the snapshot
    convention).  The index keeps its ``name`` and ``constraint_backed``, which
    equality ignores: identity is the (columns, unique, fulltext, spatial) shape,
    and a name the two sides disagree on is a rename the differ reports.
    The ``fulltext`` and
    ``spatial`` flags are preserved because a fulltext, a spatial, and a plain
    b-tree index over the same columns are three distinct schema objects
    (different DDL and different query semantics).
    """
    columns, unique, fulltext, spatial = canonical_index_identity(index)
    return SnapshotIndex(
        columns=columns,
        unique=unique,
        name=index.name,
        fulltext=fulltext,
        spatial=spatial,
        constraint_backed=index.constraint_backed,
    )


def _drop_implicit_indexes(table: SnapshotTable) -> tuple[SnapshotIndex, ...]:
    """Remove indexes implied by PK/unique constraints or FK backing.

    Removal is conservative and structural — an index is dropped only when it is
    provably derived from a constraint already represented elsewhere in the
    canonical column/FK data, identified by columns + uniqueness, never by name
    heuristics:

    - The unique index over the primary-key column(s) (auto-derived from the PK).
    - A single-column unique index whose column already carries ``unique=True``.

    **A foreign key's backing index is NOT in that list, and must never be.** A
    primary key and a unique constraint create their index on every engine, so an
    index describing one is the constraint restated. A foreign key does not: some
    engines auto-create a backing index and PostgreSQL does not. Treating an index
    over an FK's columns as implied therefore deleted, before any comparison ran,
    the index a ``belongsTo … : index`` declaration asks for -- so it appeared on
    neither side of the diff, no revision created it, and the later
    never-created-index audit compared two sets that agreed on its absence. It
    was silent on every profile and every regeneration: twenty declared indexes
    across nine blocks of one real project, every one a foreign-key column.

    An index a live catalog auto-created for a foreign key that the source never
    declared is a real concern, but it is a PAIRWISE fact -- it depends on what
    the other side declares -- so it is settled by
    :func:`suppress_undeclared_fk_backing_indexes` at the four sites that compare
    against a live catalog, never by deleting schema here.

    Args:
        table: Table whose columns and foreign keys have already been
            canonicalized (PK-derived ``unique`` flags set).

    Returns:
        The indexes that are NOT implied by a constraint, in original order.
    """
    pk_columns = tuple(
        col.column_name.lower()
        for col in table.fields.values()
        if col.primary_key
    )
    unique_columns = frozenset(
        col.column_name.lower() for col in table.fields.values() if col.unique
    )

    kept: list[SnapshotIndex] = []
    for index in table.indexes:
        if _is_implicit_index(index, pk_columns, unique_columns):
            logger.debug(
                "Dropping implicit index on columns %s (unique=%s) for table %s",
                index.columns,
                index.unique,
                table.table_name,
            )
            continue
        kept.append(index)
    return tuple(kept)


def _is_implicit_index(
    index: SnapshotIndex,
    pk_columns: tuple[str, ...],
    unique_columns: frozenset[str],
) -> bool:
    """Return True if the index is provably derived from a constraint.

    Both cases describe an index the constraint itself creates on every engine,
    so the index is the constraint restated rather than a separate object.
    """
    if index.fulltext:
        return False

    index_columns = tuple(col.lower() for col in index.columns)

    if index.unique and pk_columns and index_columns == pk_columns:
        return True

    if (
        index.unique
        and len(index_columns) == 1
        and index_columns[0] in unique_columns
    ):
        return True

    return False


def _fk_backing_index_columns(table: SnapshotTable) -> frozenset[tuple[str, ...]]:
    """The local-column tuples a table's foreign keys are declared over."""
    return frozenset(
        tuple(col.lower() for col in fk.columns) for fk in table.foreign_keys
    )


def _declared_index_identities(
    table: SnapshotTable | None,
) -> frozenset[tuple[tuple[str, ...], bool, bool, bool]]:
    """Canonical identities of the indexes a reference table declares."""
    if table is None:
        return frozenset()
    return frozenset(canonical_index_identity(index) for index in table.indexes)


def _suppress_table_fk_backing(
    live_table: SnapshotTable, reference_table: SnapshotTable | None
) -> SnapshotTable:
    """Drop from one live table the FK-backing indexes the reference never declares."""
    fk_columns = _fk_backing_index_columns(live_table)
    if not fk_columns:
        return live_table
    declared = _declared_index_identities(reference_table)

    kept = tuple(
        index
        for index in live_table.indexes
        if not (
            not index.unique
            and not index.fulltext
            and not index.spatial
            and tuple(col.lower() for col in index.columns) in fk_columns
            and canonical_index_identity(index) not in declared
        )
    )
    if len(kept) == len(live_table.indexes):
        return live_table
    logger.debug(
        "Suppressing %d undeclared FK-backing index(es) on live table %s",
        len(live_table.indexes) - len(kept),
        live_table.table_name,
    )
    return replace(live_table, indexes=kept)


def _table_maps(snapshot: RdbmsSchemaSnapshot) -> dict[str, dict[str, SnapshotTable]]:
    """*snapshot*'s tables by the kind it files them as."""
    return {
        _ENTITIES: snapshot.entities,
        _CQRS_VIEWS: snapshot.cqrs_views,
        _AUDIT_LOG_TABLES: snapshot.audit_log_tables,
        _JUNCTION_TABLES: snapshot.junction_tables,
        _FRAMEWORK_TABLES: snapshot.framework_tables,
    }
