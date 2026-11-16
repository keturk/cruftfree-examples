"""Index and foreign key identities and the labels a change displays them by."""

from __future__ import annotations

from cruftfree_rdbms_schema._snapshot_models import (
    SnapshotForeignKey,
    SnapshotIndex,
)


def index_identity(index: SnapshotIndex) -> tuple[object, ...]:
    """The tuple deciding whether two recorded indexes are the SAME index.

    Every structural field a renderer consults to produce the index's DDL is in
    here, so a change to any of them is a different index rather than an unnoticed
    edit of the same one: ``fulltext`` and ``spatial`` decide the access method, and
    the column list decides both the covered columns and (for a fulltext index) the
    expression built over them, in order. The recorded ``name`` is NOT part of it --
    it names the physical object, and a name that differs between two sides of one
    index is an ``INDEX_RENAMED``, never one index leaving and another arriving.

    Args:
        index: A snapshot index from either side of a comparison.

    Returns:
        A hashable identity usable as a set element.
    """
    return (index.columns, index.unique, index.fulltext, index.spatial)


def index_label(index: SnapshotIndex) -> str:
    """How a message names *index*: its name when it has one, and its columns."""
    columns = "on columns %s" % ", ".join(index.columns)
    if index.name is None:
        return columns
    return "'%s' %s" % (index.name, columns)


def foreign_key_change_field(foreign_key: SnapshotForeignKey) -> str:
    """The human label of a foreign-key change: ``"<columns>-><referred table>"``.

    A label only, carried in a change's ``field``. Nothing parses it: a reader takes
    the key from the change's subject.

    Args:
        foreign_key: The constraint the change concerns.

    Returns:
        The label, e.g. ``"('customer_id',)->customers"``.
    """
    return "%s->%s" % (str(tuple(foreign_key.columns)), foreign_key.referred_table)


def foreign_key_label(foreign_key: SnapshotForeignKey) -> str:
    """How a message names *foreign_key*: its name when it has one, and what it reads."""
    reference = "(%s) -> %s" % (", ".join(foreign_key.columns), foreign_key.referred_table)
    if foreign_key.name is None:
        return reference
    return "'%s' %s" % (foreign_key.name, reference)
