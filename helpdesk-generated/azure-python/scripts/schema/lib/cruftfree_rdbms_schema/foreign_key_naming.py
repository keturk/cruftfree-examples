"""The one rule that names every foreign-key constraint a table carries.

A constraint's name IS its identity in the database: ``ADD CONSTRAINT`` fails on a
collision and a ``DROP CONSTRAINT`` targets a name, never a column list. So every
producer of a name -- the schema snapshot, the convergence renderer, the SQL
generator's DDL -- derives it from this module and from nothing else, and a name a
snapshot has recorded is read back rather than derived a second time.

The rule is ``fk_<table>_<columns>``, capped by the one identifier-length rule
(:func:`~cruftfree_common.utils.identifier_case.truncate_db_identifier`): a name over the engine's
limit keeps a prefix and gains a digest of the full name, so two long names stay
distinct. A live catalog holding a key under another name is brought to it by a
``FOREIGN_KEY_RENAMED`` the differ reports, from the name the catalog holds.

This module sits in ``cruftfree-rdbms-schema`` because the snapshot builder records the
names it derives, and that package depends on ``cruftfree-common`` alone. It reads the
snapshot's foreign-key and table types structurally and imports them only for type
checking, so the snapshot module can import it without a cycle.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import TYPE_CHECKING

from cruftfree_common.utils.identifier_case import truncate_db_identifier

if TYPE_CHECKING:
    from cruftfree_rdbms_schema._snapshot_models import (
        SnapshotForeignKey,
        SnapshotTable,
    )

__all__ = [
    "FOREIGN_KEY_PREFIX",
    "derived_foreign_key_name",
    "foreign_key_identity",
    "foreign_key_name",
    "realized_foreign_key_name",
    "record_foreign_key_names",
]

#: Prefix of every foreign-key constraint name.
FOREIGN_KEY_PREFIX = "fk"


def foreign_key_identity(
    foreign_key: SnapshotForeignKey,
) -> tuple[tuple[str, ...], str, tuple[str, ...]]:
    """The tuple deciding whether two recorded foreign keys are the SAME constraint.

    Local columns, referred table and referred columns: every structural fact that
    says which rows the constraint ties together. The referential actions are NOT part
    of it -- an action change on the same link is the same constraint changing, which
    is reconciled by one replacement, never read as one key leaving and another
    arriving. The recorded ``name`` is metadata and is not part of it either.

    Args:
        foreign_key: A snapshot foreign key from either side of a comparison.

    Returns:
        A hashable identity usable as a set element or dict key.
    """
    return (
        tuple(foreign_key.columns),
        foreign_key.referred_table,
        tuple(foreign_key.referred_columns),
    )


def foreign_key_name(table_name: str, columns: Sequence[str]) -> str:
    """Name a foreign-key constraint.

    Args:
        table_name: Physical name of the table holding the constraint.
        columns: Physical local column names, in declared order.

    Returns:
        ``fk_<table>_<columns>``, capped at the identifier limit.
    """
    return truncate_db_identifier(
        "%s_%s_%s" % (FOREIGN_KEY_PREFIX, table_name, "_".join(columns))
    )


def derived_foreign_key_name(table_name: str, foreign_key: SnapshotForeignKey) -> str:
    """The shared rule's name for one snapshot foreign key.

    Args:
        table_name: Physical name of the table holding the constraint.
        foreign_key: The constraint to name.

    Returns:
        The name :func:`foreign_key_name` gives its local columns.
    """
    return foreign_key_name(table_name, foreign_key.columns)


def record_foreign_key_names(
    table_name: str, foreign_keys: Sequence[SnapshotForeignKey]
) -> tuple[SnapshotForeignKey, ...]:
    """Return *foreign_keys* with every key carrying the name the shared rule gives it.

    The snapshot builder calls this once per table, so the recorded name is the shared
    rule's output and every later drop or rename reads it back instead of re-deriving it.

    Args:
        table_name: Physical table name.
        foreign_keys: The table's foreign keys, in snapshot order.

    Returns:
        The same keys, in the same order, each with ``name`` set.
    """
    return tuple(
        replace(key, name=derived_foreign_key_name(table_name, key))
        for key in foreign_keys
    )


def realized_foreign_key_name(
    table: SnapshotTable, foreign_key: SnapshotForeignKey
) -> str:
    """The name *foreign_key* has in the database of *table*.

    The table is consulted first: the key it holds under the same identity supplies the
    name the snapshot recorded. A name carried by *foreign_key* itself comes next, and
    for a key carrying none the shared rule's name is the realized one.

    Args:
        table: The key's table.
        foreign_key: A foreign key of *table*.

    Returns:
        The constraint's name.
    """
    identity = foreign_key_identity(foreign_key)
    for candidate in table.foreign_keys:
        if foreign_key_identity(candidate) == identity and candidate.name is not None:
            return candidate.name
    if foreign_key.name is not None:
        return foreign_key.name
    return derived_foreign_key_name(table.table_name, foreign_key)
