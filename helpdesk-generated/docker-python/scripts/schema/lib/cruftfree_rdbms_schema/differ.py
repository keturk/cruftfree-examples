"""The schema-change model every schema diff is expressed in.

:mod:`cruftfree_rdbms_schema.snapshot_diff` compares two RDBMS schema snapshots and
reports the result as a :class:`SchemaDiff` of :class:`SchemaChange` records;
the convergence outcomes and the kernel's convergence renderer read that model.

Every change carries its *subject*: the snapshot object it adds, removes or alters,
from the side that holds it (:data:`CHANGE_SUBJECT_TYPES`). A reader takes the object
from the subject, never from ``detail``, which is display text only.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Final

from cruftfree_rdbms_schema._snapshot_models import (
    SnapshotCheck,
    SnapshotColumn,
    SnapshotEnum,
    SnapshotForeignKey,
    SnapshotIndex,
    SnapshotTable,
    SnapshotTrigger,
)


class ChangeKind(Enum):
    """Types of schema changes a snapshot diff detects."""

    ENTITY_ADDED = "entity_added"
    ENTITY_REMOVED = "entity_removed"
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    FIELD_TYPE_CHANGED = "field_type_changed"
    FIELD_NULLABLE_CHANGED = "field_nullable_changed"
    # The DEFAULT an existing column carries in the database was added, changed or
    # removed. An existing database keeps the old DEFAULT until a convergence
    # sets the new one (``ALTER COLUMN ... SET DEFAULT`` / ``DROP DEFAULT``), so a
    # default edit is a real schema change. ``old_value`` / ``new_value`` are the
    # defaults (``None`` for no default), the recorded ``SnapshotDefault``
    # serialized (``snapshot_diff.default_change_value``). The renderer reads the
    # default it sets from the subject, never from these.
    # Non-destructive: a DEFAULT applies to rows inserted afterwards and moves no
    # existing row.
    FIELD_DEFAULT_CHANGED = "field_default_changed"
    # An existing column's single-column UNIQUE constraint (a ``: unique`` field)
    # was added or removed. ``old_value`` / ``new_value`` are ``"True"`` /
    # ``"False"``. Adding one is risky -- rows already holding a duplicate fail the
    # revision -- and removing one loses no row.
    FIELD_UNIQUE_CHANGED = "field_unique_changed"
    # An existing column joined or left its table's primary key. ``old_value`` /
    # ``new_value`` are ``"True"`` / ``"False"``; one change per column, so a
    # composite key that changes reports each column it gains or loses. Never applied:
    # no engine's forward DDL is rendered for a key change, which re-keys every row and
    # every foreign key that references the table.
    FIELD_PRIMARY_KEY_CHANGED = "field_primary_key_changed"
    # A table the schema keeps under the same declared name changes its physical
    # name. ``old_value`` / ``new_value`` are the table names. Never applied: no
    # engine's forward DDL is rendered for a table rename, and the generated code
    # already reads and writes the new name.
    ENTITY_TABLE_RENAMED = "entity_table_renamed"
    # A table's engine-neutral ``table_options`` changed. ``old_value`` /
    # ``new_value`` are the options as sorted JSON. Never applied: no engine's
    # forward DDL is rendered for a table option.
    ENTITY_OPTIONS_CHANGED = "entity_options_changed"
    INDEX_ADDED = "index_added"
    INDEX_REMOVED = "index_removed"
    # An index (or unique constraint) both sides hold with one identity
    # (``index_identity``) changes its NAME. The subject is the index the previous
    # side holds; ``old_value`` is its name, ``new_value`` the name the current side
    # gives it. Non-destructive: a rename moves no row, and the index is never absent.
    INDEX_RENAMED = "index_renamed"
    RELATIONSHIP_ADDED = "relationship_added"
    RELATIONSHIP_REMOVED = "relationship_removed"
    # A foreign key both sides hold with one identity (``foreign_key_identity``) whose
    # ``onDelete`` or ``onUpdate`` differs: the previous side's key is dropped under the
    # name it holds (``old_value``), and the current side's key, the subject, is added
    # under its name (``new_value``), validated over the rows the table holds.
    # Non-destructive: no row moves or is lost; a row that violates the constraint
    # fails the apply, naming it.
    FOREIGN_KEY_REPLACED = "foreign_key_replaced"
    # A foreign key both sides hold with one identity and the same actions changes its
    # NAME. The subject is the key the previous side holds; ``old_value`` is its name,
    # ``new_value`` the name the current side gives it, and ``field`` its label
    # (``foreign_key_change_field``). Non-destructive: a rename moves no row, and the
    # constraint is never absent.
    FOREIGN_KEY_RENAMED = "foreign_key_renamed"
    # The block's PostgreSQL schema (namespace) changed: every table and native
    # enum type moves to the new schema.  Non-destructive (ALTER ... SET SCHEMA
    # preserves data); block-level, so it carries no entity/field and no subject.
    SCHEMA_RELOCATED = "schema_relocated"
    # Member-list changes on a native enum type the block already declares.
    # Block-level (an enum type is shared by every column typed with it), so
    # these carry ``enum`` rather than an entity/field.  Appending a member is
    # non-destructive (``ALTER TYPE ... ADD VALUE``); removing or reordering
    # one is not, and PostgreSQL offers no forward DDL for either -- a removed
    # label is still held by existing rows, and member order is the type's
    # ``enumsortorder``, which drives ``ORDER BY`` on every column using it.
    ENUM_VALUE_ADDED = "enum_value_added"
    ENUM_VALUE_REMOVED = "enum_value_removed"
    ENUM_VALUES_REORDERED = "enum_values_reordered"
    # A member the type already holds changes the LABEL it is stored as (its
    # ``value(...)`` was added, changed or removed), while the member itself stays.
    # Block-level like the other enum kinds. Non-destructive: renaming a label in
    # place (``ALTER TYPE ... RENAME VALUE``, or an ``UPDATE`` on a column that
    # carries its labels as data) moves no row and loses none.
    ENUM_VALUE_RELABELED = "enum_value_relabeled"
    # The PUBLISHED documentation a table or column carries in the database
    # (``COMMENT ON TABLE`` / ``COMMENT ON COLUMN``).  Comment text is DDL --
    # an existing database keeps the old text until a convergence sets
    # the new one -- so a comment edit is a real schema change, not metadata.
    # Both are NON-DESTRUCTIVE: setting a comment cannot lose a row, and
    # clearing one loses only text the DSL no longer declares.
    ENTITY_COMMENT_CHANGED = "entity_comment_changed"
    FIELD_COMMENT_CHANGED = "field_comment_changed"
    # A row-local check constraint was added to or removed from a table. ``entity``
    # is the table's key in the snapshot and the subject the check: a check's name
    # carries the digest of its definition, so two checks are the same check exactly
    # when their names are equal, and a changed definition is one removal and one
    # addition, never a modification. Adding one is risky -- existing rows that
    # violate it fail the revision, and none is deleted -- and removing one loses no
    # row.
    CHECK_ADDED = "check_added"
    CHECK_REMOVED = "check_removed"
    # A table trigger (a database-enforced rule over the table's rows) was added to or
    # removed from a table. ``entity`` is the table's key in the snapshot and the
    # subject the trigger, whose name carries the digest of its definition: a changed
    # definition is one removal and one addition. Adding one loses no row and judges
    # no existing row (a trigger answers writes made after it); removing one lifts the
    # protection it gave, which loses no row either.
    TRIGGER_ADDED = "trigger_added"
    TRIGGER_REMOVED = "trigger_removed"
    # A named enum type the previous side holds and no column of the current side uses:
    # a type nothing declared needs, whether no column of either side uses it or only a
    # column or table the current side removes did. Block-level like the other enum
    # kinds, so it carries ``enum`` (the type's name) and its subject is the type the
    # previous side holds. Destructive: the type goes, and so does anything outside the
    # schema that still depended on it.
    ENUM_TYPE_REMOVED = "enum_type_removed"
    # A named enum type only the current side holds and no column of it uses, so no
    # column change creates it. Never applied: no engine's forward DDL is rendered for
    # a type no column uses.
    ENUM_TYPE_ADDED = "enum_type_added"
    # An enum type both sides hold under the same name changes the name the database
    # holds it under. ``old_value`` / ``new_value`` are the database names. Never
    # applied: no engine's forward DDL is rendered for a type rename.
    ENUM_TYPE_RENAMED = "enum_type_renamed"


#: One column-type constraint set as the differ records it: ``(name, value)``
#: pairs sorted by name, e.g. ``(("max_length", 200),)``.
TypeConstraintPairs = tuple[tuple[str, int], ...]

#: The snapshot object a change is about.
ChangeSubject = (
    SnapshotTable
    | SnapshotColumn
    | SnapshotIndex
    | SnapshotForeignKey
    | SnapshotEnum
    | SnapshotCheck
    | SnapshotTrigger
    | None
)

_NO_SUBJECT: Final[type[None]] = type(None)

# @canonical(rdbms-schema/change-subject-types): The one snapshot type each change
#   kind's subject is
# @rule: Every SchemaChange is built with a subject of exactly its kind's type; the
#   differ produces it and every reader (renderer, convergence outcome) consumes it
# @anti-pattern: Encoding the object a change is about into ``detail`` and parsing it back
#: The type of the subject every change kind carries: the snapshot object the change
#: adds, removes or alters, from the side that holds it. A block-level change about no
#: single object (``SCHEMA_RELOCATED``) carries none. :class:`SchemaChange` refuses a
#: subject of any other type.
CHANGE_SUBJECT_TYPES: Final[Mapping[ChangeKind, type]] = MappingProxyType(
    {
        ChangeKind.ENTITY_ADDED: SnapshotTable,
        ChangeKind.ENTITY_REMOVED: SnapshotTable,
        ChangeKind.ENTITY_TABLE_RENAMED: SnapshotTable,
        ChangeKind.ENTITY_OPTIONS_CHANGED: SnapshotTable,
        ChangeKind.ENTITY_COMMENT_CHANGED: SnapshotTable,
        ChangeKind.FIELD_ADDED: SnapshotColumn,
        ChangeKind.FIELD_REMOVED: SnapshotColumn,
        ChangeKind.FIELD_TYPE_CHANGED: SnapshotColumn,
        ChangeKind.FIELD_NULLABLE_CHANGED: SnapshotColumn,
        ChangeKind.FIELD_DEFAULT_CHANGED: SnapshotColumn,
        ChangeKind.FIELD_UNIQUE_CHANGED: SnapshotColumn,
        ChangeKind.FIELD_PRIMARY_KEY_CHANGED: SnapshotColumn,
        ChangeKind.FIELD_COMMENT_CHANGED: SnapshotColumn,
        ChangeKind.INDEX_ADDED: SnapshotIndex,
        ChangeKind.INDEX_REMOVED: SnapshotIndex,
        ChangeKind.INDEX_RENAMED: SnapshotIndex,
        ChangeKind.RELATIONSHIP_ADDED: SnapshotForeignKey,
        ChangeKind.RELATIONSHIP_REMOVED: SnapshotForeignKey,
        ChangeKind.FOREIGN_KEY_REPLACED: SnapshotForeignKey,
        ChangeKind.FOREIGN_KEY_RENAMED: SnapshotForeignKey,
        ChangeKind.SCHEMA_RELOCATED: _NO_SUBJECT,
        ChangeKind.ENUM_VALUE_ADDED: SnapshotEnum,
        ChangeKind.ENUM_VALUE_REMOVED: SnapshotEnum,
        ChangeKind.ENUM_VALUES_REORDERED: SnapshotEnum,
        ChangeKind.ENUM_VALUE_RELABELED: SnapshotEnum,
        ChangeKind.ENUM_TYPE_REMOVED: SnapshotEnum,
        ChangeKind.ENUM_TYPE_ADDED: SnapshotEnum,
        ChangeKind.ENUM_TYPE_RENAMED: SnapshotEnum,
        ChangeKind.CHECK_ADDED: SnapshotCheck,
        ChangeKind.CHECK_REMOVED: SnapshotCheck,
        ChangeKind.TRIGGER_ADDED: SnapshotTrigger,
        ChangeKind.TRIGGER_REMOVED: SnapshotTrigger,
    }
)


def _subject_type_name(subject_type: type) -> str:
    """How a refusal names a subject type: its class name, or ``no subject``."""
    return "no subject" if subject_type is _NO_SUBJECT else subject_type.__name__


@dataclass(frozen=True)
class SchemaChange:
    """A single detected schema change.

    ``subject`` is the snapshot object the change is about, of the type
    :data:`CHANGE_SUBJECT_TYPES` gives its kind: the one an addition adds and an
    alteration alters from the current side, the one a removal removes from the
    previous side. It is compared but never hashed (a table holds a dict).

    ``detail`` is display text only: nothing parses it.

    ``enum`` names the cruftfree enum type a block-level enum change applies to.
    It is the enum analogue of ``entity``: an enum type is not owned by one
    table, so an enum change carries no entity or field.

    ``old_constraints`` / ``new_constraints`` are the column type's declared
    constraints (``max_length``, ``min_length``, ``precision``, ``scale``)
    before and after a ``FIELD_TYPE_CHANGED``; empty on every other kind.

    Raises:
        ValueError: The subject is missing or not of the kind's type.
    """

    kind: ChangeKind
    service: str
    entity: str | None = None
    field: str | None = None
    detail: str = ""
    old_value: str | None = None
    new_value: str | None = None
    enum: str | None = None
    old_constraints: TypeConstraintPairs = ()
    new_constraints: TypeConstraintPairs = ()
    # ``dataclasses.field``: the class's own ``field`` attribute shadows the bare name here.
    subject: ChangeSubject = dataclasses.field(default=None, hash=False)

    def __post_init__(self) -> None:
        expected = CHANGE_SUBJECT_TYPES[self.kind]
        if type(self.subject) is expected:
            return
        found = "no subject" if self.subject is None else type(self.subject).__name__
        owner = ".".join(
            name for name in (self.enum, self.entity, self.field) if name is not None
        )
        raise ValueError(
            "A %s change%s carries %s as its subject. Expected: %s, the snapshot object "
            "the change is about (CHANGE_SUBJECT_TYPES). Fix: build the change with the "
            "object it adds, removes or alters, from the snapshot side that holds it."
            % (
                self.kind.value,
                " of '%s'" % owner if owner else "",
                found,
                _subject_type_name(expected),
            )
        )


#: The render phase of every change kind, the leading term of
#: :func:`schema_change_order`. Ranks are compared, never counted: a gap between two
#: ranks is room for a kind ordered between them. Every kind has an entry, so a kind
#: added to :class:`ChangeKind` without one fails the first sort that meets it.
#:
#: - 0, ``CHECK_REMOVED`` and ``TRIGGER_REMOVED``: a check or a trigger is dropped while
#:   the columns it reads still exist and hold their old type, so a ``FIELD_REMOVED`` or
#:   ``FIELD_TYPE_CHANGED`` in the same revision never meets a check that reads it
#:   (``ALTER COLUMN ... TYPE`` re-checks every constraint on the column) and never
#:   fires a trigger on the revision's own backfill.
#: - 1, every structural kind that removes nothing: tables, columns, indexes, foreign
#:   keys, enum members and enum types are created or changed. ``FIELD_UNIQUE_CHANGED``
#:   ranks here when it adds a unique constraint; a drop renders at rank 4
#:   (:func:`schema_change_order`).
#: - 2, ``CHECK_ADDED``: a check is created once its table and every column it reads
#:   exist in their final type, so an added entity's checks follow its
#:   ``ENTITY_ADDED`` and ``FIELD_ADDED`` changes.
#: - 3 to 6, the removals, dependents first, so no drop meets an object that still
#:   depends on what it drops: a foreign key (3) before the unique index or
#:   constraint it references (4) and the column it reads (5); an index before the
#:   column it covers; a column before its table (6). PostgreSQL refuses ``DROP
#:   COLUMN`` without ``CASCADE`` while another table's foreign key references the
#:   column, and a dropped unique index while a foreign key depends on it.
#: - 7, ``ENUM_TYPE_REMOVED``: a type is dropped once every table and column that used
#:   it is gone, because ``DROP TYPE`` refuses while an object depends on it.
#: - 8, ``FIELD_DEFAULT_CHANGED``: a column's DEFAULT is set once the column holds its
#:   final type, so ``SET DEFAULT`` never meets the type a ``FIELD_TYPE_CHANGED`` in
#:   the same revision replaces.
SCHEMA_CHANGE_RENDER_RANK: Mapping[ChangeKind, int] = MappingProxyType(
    {
        ChangeKind.CHECK_REMOVED: 0,
        ChangeKind.TRIGGER_REMOVED: 0,
        ChangeKind.ENTITY_ADDED: 1,
        ChangeKind.FIELD_ADDED: 1,
        ChangeKind.FIELD_TYPE_CHANGED: 1,
        ChangeKind.FIELD_NULLABLE_CHANGED: 1,
        ChangeKind.FIELD_UNIQUE_CHANGED: 1,
        ChangeKind.FIELD_PRIMARY_KEY_CHANGED: 1,
        ChangeKind.ENTITY_TABLE_RENAMED: 1,
        ChangeKind.ENTITY_OPTIONS_CHANGED: 1,
        ChangeKind.INDEX_ADDED: 1,
        ChangeKind.INDEX_RENAMED: 1,
        ChangeKind.RELATIONSHIP_ADDED: 1,
        ChangeKind.FOREIGN_KEY_REPLACED: 1,
        ChangeKind.FOREIGN_KEY_RENAMED: 1,
        ChangeKind.SCHEMA_RELOCATED: 1,
        ChangeKind.ENUM_VALUE_ADDED: 1,
        ChangeKind.ENUM_VALUE_REMOVED: 1,
        ChangeKind.ENUM_VALUES_REORDERED: 1,
        ChangeKind.ENUM_VALUE_RELABELED: 1,
        ChangeKind.ENTITY_COMMENT_CHANGED: 1,
        ChangeKind.FIELD_COMMENT_CHANGED: 1,
        ChangeKind.ENUM_TYPE_ADDED: 1,
        ChangeKind.ENUM_TYPE_RENAMED: 1,
        ChangeKind.CHECK_ADDED: 2,
        ChangeKind.TRIGGER_ADDED: 2,
        ChangeKind.RELATIONSHIP_REMOVED: 3,
        ChangeKind.INDEX_REMOVED: 4,
        ChangeKind.FIELD_REMOVED: 5,
        ChangeKind.ENTITY_REMOVED: 6,
        ChangeKind.ENUM_TYPE_REMOVED: 7,
        ChangeKind.FIELD_DEFAULT_CHANGED: 8,
    }
)

#: The sort key of :func:`schema_change_order`.
SchemaChangeOrder = tuple[int, str, str, str, str, str, str, str]


def _render_rank(change: SchemaChange) -> int:
    """*change*'s render phase: its kind's rank, a uniqueness drop ranked with the index removals.

    ``FIELD_UNIQUE_CHANGED`` adds or drops a column's unique constraint. An addition is
    structural; a drop removes the constraint another table's foreign key may reference,
    so it renders where ``INDEX_REMOVED`` does: after every ``RELATIONSHIP_REMOVED``.
    """
    if change.kind is ChangeKind.FIELD_UNIQUE_CHANGED and change.new_value == str(
        False
    ):
        return SCHEMA_CHANGE_RENDER_RANK[ChangeKind.INDEX_REMOVED]
    return SCHEMA_CHANGE_RENDER_RANK[change.kind]


# @canonical(rdbms-schema/schema-change-order): The one order every diff's changes render in
# @rule: Every producer that sorts or merges SchemaChange records sorts by this key
def schema_change_order(change: SchemaChange) -> SchemaChangeOrder:
    """The key every schema diff's changes are sorted by -- their render order.

    Changes sort first by their kind's rank in :data:`SCHEMA_CHANGE_RENDER_RANK`:
    check removals, then every structural change that removes nothing, then check
    additions, then the removals dependents first (foreign keys, indexes, columns,
    tables), then default changes. A column's uniqueness drop ranks with the index
    removals, after the foreign keys that may reference it (:func:`_render_rank`).
    Within a rank, changes group by kind in name
    order (every table creation before any column change, every index addition
    before any relationship change); within a kind the order is stable on the
    change's owner and values, and changes tied on all of them keep the order the
    differ produced them in.
    """
    return (
        _render_rank(change),
        change.kind.value,
        change.service,
        change.entity or "",
        change.enum or "",
        change.field or "",
        change.old_value or "",
        change.new_value or "",
    )


def constraint_pairs(constraints: Mapping[str, int]) -> TypeConstraintPairs:
    """Freeze a ``SnapshotType.constraints`` mapping into sorted ``(name, value)`` pairs."""
    return tuple(sorted((str(name), int(value)) for name, value in constraints.items()))


@dataclass(frozen=True)
class SchemaDiff:
    """Complete diff result between two schema snapshots."""

    changes: tuple[SchemaChange, ...]
    previous_hash: str
    current_hash: str

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0

    @property
    def has_destructive_changes(self) -> bool:
        destructive = {
            ChangeKind.ENTITY_REMOVED,
            ChangeKind.FIELD_REMOVED,
            ChangeKind.FIELD_TYPE_CHANGED,
            ChangeKind.ENUM_VALUE_REMOVED,
            ChangeKind.ENUM_VALUES_REORDERED,
            ChangeKind.ENUM_TYPE_REMOVED,
        }
        return any(c.kind in destructive for c in self.changes)


def schema_change_builder(
    service_name: str, entity_name: str
) -> Callable[..., SchemaChange]:
    """Return a factory that builds a SchemaChange pinned to one service/entity.

    The snapshot differ builds many SchemaChange records within one
    field/index/relationship comparison that all share the same service and
    entity; this factors out exactly that repeated ``SchemaChange(kind=...,
    service=service_name, entity=entity_name, ...)`` construction.
    """

    def build(kind: ChangeKind, **fields: object) -> SchemaChange:
        return SchemaChange(
            kind=kind, service=service_name, entity=entity_name, **fields
        )

    return build
