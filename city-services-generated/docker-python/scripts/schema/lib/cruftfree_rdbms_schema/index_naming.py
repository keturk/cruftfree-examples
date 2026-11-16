"""The one rule that names every index and unique constraint a table carries.

A name IS the identity of an index in the database: ``CREATE INDEX`` fails on a
collision whatever the two objects cover, and a ``DROP`` or ``RENAME`` targets a
name, never a column list. So every producer of a name -- an ORM model's table
declaration, a convergence statement that creates the object, one that drops or
renames it, the SQL generator's own DDL -- must derive it from this module and from nothing
else, and a name a snapshot has recorded is read back rather than derived a second
time.

Four kinds, one prefix each:

* a plain b-tree index is ``ix_<table>_<columns>``;
* a declared unique index is a unique CONSTRAINT, ``uq_<table>_<columns>``;
* a fulltext index is ``ix_<table>_fulltext`` for the table's first and
  ``ix_<table>_<columns>_fulltext`` for every later one, so two fulltext indexes on one
  table never share a name;
* a spatial index implied by a geographic column is ``gist_<table>_<columns>``.

Every name passes through :func:`~cruftfree_common.utils.identifier_case.truncate_db_identifier`,
the single identifier-length rule: a name over the engine's limit keeps a prefix and
gains a digest of the full name, so two long names stay distinct.

This module sits in ``cruftfree-rdbms-schema`` because the snapshot builder
(:mod:`cruftfree_rdbms_schema.schema_snapshot`) records the names it derives, and that
package depends on ``cruftfree-common`` alone. It reads the snapshot's index and table
types structurally and imports them only for type checking, so the snapshot module can
import it without a cycle.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from cruftfree_common.errors.generation import GenerationError
from cruftfree_common.utils.identifier_case import truncate_db_identifier

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import SnapshotIndex, SnapshotTable

__all__ = [
    "FULLTEXT_NAME_SUFFIX",
    "PLAIN_INDEX_PREFIX",
    "SPATIAL_INDEX_PREFIX",
    "UNIQUE_CONSTRAINT_PREFIX",
    "derived_index_name",
    "fulltext_index_name",
    "fulltext_index_ordinal",
    "held_index",
    "plain_index_name",
    "realized_index_name",
    "record_index_names",
    "spatial_index_name",
    "unique_constraint_name",
]

#: Prefix of a plain (non-unique, non-fulltext, non-spatial) index.
PLAIN_INDEX_PREFIX = "ix"
#: Prefix of a declared unique index, which is realized as a unique constraint.
UNIQUE_CONSTRAINT_PREFIX = "uq"
#: Prefix of the spatial index a geographic column implies.
SPATIAL_INDEX_PREFIX = "gist"
#: Suffix every fulltext index name ends in.
FULLTEXT_NAME_SUFFIX = "fulltext"


def _named(prefix: str, table_name: str, columns: Sequence[str]) -> str:
    """``<prefix>_<table>_<columns>``, length-capped by the shared identifier rule."""
    return truncate_db_identifier("%s_%s_%s" % (prefix, table_name, "_".join(columns)))


def plain_index_name(table_name: str, columns: Sequence[str]) -> str:
    """Name a plain b-tree index.

    Args:
        table_name: Physical table name.
        columns: Physical column names, in declared order.

    Returns:
        ``ix_<table>_<columns>``, capped at the identifier limit.
    """
    return _named(PLAIN_INDEX_PREFIX, table_name, columns)


def unique_constraint_name(table_name: str, columns: Sequence[str]) -> str:
    """Name a unique constraint (a declared unique index).

    Args:
        table_name: Physical table name.
        columns: Physical column names, in declared order.

    Returns:
        ``uq_<table>_<columns>``, capped at the identifier limit.
    """
    return _named(UNIQUE_CONSTRAINT_PREFIX, table_name, columns)


def spatial_index_name(table_name: str, columns: Sequence[str]) -> str:
    """Name the spatial index a geographic column implies.

    Args:
        table_name: Physical table name.
        columns: Index columns (one, for a geographic column).

    Returns:
        ``gist_<table>_<columns>``, capped at the identifier limit.
    """
    return _named(SPATIAL_INDEX_PREFIX, table_name, columns)


def fulltext_index_name(table_name: str, columns: Sequence[str], ordinal: int) -> str:
    """Name a table's *ordinal*-th fulltext index.

    A table's first fulltext index is ``ix_<table>_fulltext`` and every later one
    carries its own columns, so a table declaring two of them never issues two
    ``CREATE INDEX`` statements under one name.

    Args:
        table_name: Physical table name.
        columns: Index columns, in declared order.
        ordinal: How many fulltext indexes precede this one on the table.

    Returns:
        The index name, capped at the identifier limit.
    """
    if ordinal == 0:
        return truncate_db_identifier(
            "%s_%s_%s" % (PLAIN_INDEX_PREFIX, table_name, FULLTEXT_NAME_SUFFIX)
        )
    return truncate_db_identifier(
        "%s_%s_%s_%s"
        % (PLAIN_INDEX_PREFIX, table_name, "_".join(columns), FULLTEXT_NAME_SUFFIX)
    )


def derived_index_name(
    table_name: str, index: SnapshotIndex, fulltext_ordinal: int
) -> str:
    """The shared rule's name for one snapshot index, whatever its kind.

    Args:
        table_name: Physical table name.
        index: The index to name.
        fulltext_ordinal: How many fulltext indexes precede *index* on its table;
            read only when *index* is fulltext.

    Returns:
        The name the kind's rule gives it.
    """
    columns = index.columns
    if index.spatial:
        return spatial_index_name(table_name, columns)
    if index.fulltext:
        return fulltext_index_name(table_name, columns, fulltext_ordinal)
    if index.unique:
        return unique_constraint_name(table_name, columns)
    return plain_index_name(table_name, columns)


def record_index_names(
    table_name: str, indexes: Sequence[SnapshotIndex]
) -> tuple[SnapshotIndex, ...]:
    """Return *indexes* with every index carrying the name its kind's rule gives it.

    The snapshot builder calls this once per table, so the recorded name is the
    shared rule's output and every later drop or rename reads it back instead of
    re-deriving it. A fulltext index's name depends on its position among the
    table's fulltext indexes, which is why the whole list is named together.

    Args:
        table_name: Physical table name.
        indexes: The table's indexes, in snapshot order.

    Returns:
        The same indexes, in the same order, each with ``name`` set.
    """
    named: list[SnapshotIndex] = []
    fulltext_seen = 0
    for index in indexes:
        name = derived_index_name(table_name, index, fulltext_seen)
        if index.fulltext:
            fulltext_seen += 1
        named.append(replace(index, name=name))
    return tuple(named)


def fulltext_index_ordinal(table: SnapshotTable, index: SnapshotIndex) -> int:
    """How many fulltext indexes precede *index* on *table*.

    A fulltext index's name depends on its position among the table's fulltext
    indexes, so the position is read from the table in the CURRENT snapshot rather
    than inferred from a change record, which carries only the one index.

    A non-fulltext index needs no ordinal and reports 0.

    Args:
        table: The index's table in the current snapshot.
        index: The index whose ordinal is wanted.

    Returns:
        The count of fulltext indexes declared before *index* on *table*.

    Raises:
        GenerationError: *index* is fulltext but absent from *table*, which means
            the differ and the snapshot disagree about what exists.
    """
    if not index.fulltext:
        return 0
    ordinal = 0
    for candidate in table.indexes:
        if not candidate.fulltext:
            continue
        if tuple(candidate.columns) == tuple(index.columns):
            return ordinal
        ordinal += 1
    raise GenerationError(
        "Fulltext index over columns (%s) was added to table '%s' but is absent "
        "from that table in the current schema snapshot, so its conventional "
        "name cannot be determined. Expected the added index to be present in "
        "the snapshot the change was diffed against. Snapshot fulltext indexes: "
        "%s. Regenerate the schema snapshot for this RDBMS block."
        % (
            ", ".join(index.columns),
            table.table_name,
            [list(i.columns) for i in table.indexes if i.fulltext],
        )
    )


def held_index(table: SnapshotTable, index: SnapshotIndex) -> SnapshotIndex | None:
    """The index of *table* that *index* stands for; None when *table* holds no equal one.

    Index equality ignores the name, so a table holding identical copies holds several
    indexes equal to *index*. The copy recorded under *index*'s own name is the one a
    change naming it means; otherwise the first copy with a recorded name, then the
    first copy.

    Args:
        table: The index's table.
        index: An index of *table*, as the snapshot or a change record holds it.

    Returns:
        The held copy, or None.
    """
    equal = [candidate for candidate in table.indexes if candidate == index]
    if index.name is not None:
        for candidate in equal:
            if candidate.name == index.name:
                return candidate
    for candidate in equal:
        if candidate.name is not None:
            return candidate
    return equal[0] if equal else None


def realized_index_name(table: SnapshotTable, index: SnapshotIndex) -> str:
    """The name *index* has in the database of *table*.

    *index* may be the snapshot's own index or a copy rebuilt from a change record
    (which carries no name once canonicalized), so the table is consulted first:
    the index it holds under the same identity (columns, kind) supplies the name
    the snapshot recorded -- a drop or rename must hit the object the database
    holds, never a freshly derived spelling. Of identical copies, the one recorded
    under *index*'s own name is that index (:func:`held_index`). A name carried by
    *index* itself comes next. A snapshot written before names were recorded carries
    none; the generated reconciliation revision gives every such database the shared
    rule's names, so for those the rule's name is the realized one.

    Args:
        table: The index's table.
        index: An index of *table*, as the snapshot or a change record holds it.

    Returns:
        The index's name.

    Raises:
        GenerationError: *index* is fulltext, unnamed anywhere, and absent from
            *table* (see :func:`fulltext_index_ordinal`).
    """
    held = held_index(table, index)
    if held is not None and held.name is not None:
        return held.name
    if index.name is not None:
        return index.name
    return derived_index_name(
        table.table_name, index, fulltext_index_ordinal(table, index)
    )
