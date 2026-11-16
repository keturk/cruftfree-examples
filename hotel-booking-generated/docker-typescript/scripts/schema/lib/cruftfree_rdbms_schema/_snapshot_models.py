"""The schema snapshot data model."""

from __future__ import annotations

from dataclasses import dataclass, field

from cruftfree_rdbms_schema.sql_lowering.lowered import SqlNode

# ── Frozen dataclasses ──


@dataclass(frozen=True)
class SnapshotStorage:
    """Storage metadata for a column.

    All fields are None unless the type carries that constraint.
    """

    max_length: int | None
    precision: int | None
    scale: int | None


@dataclass(frozen=True)
class SnapshotDefault:
    """Default value specification for a column.

    Attributes:
        kind: One of "literal", "server_function", or "generated".
        value: The default value expression.
        name: Display name for the default (matches kind for unnamed defaults).
        tree: The default lowered by the one SQL lowering
            (:func:`~cruftfree_rdbms_schema.sql_lowering._lower_operands.lower_expression`), which
            every DDL statement renders it from; ``None`` for a
            collection literal (a JSON document, not a lowered expression). A default a
            live catalog reflected carries the tree its reader read the engine's spelling
            back to (a builtin call, a compound expression), or ``None`` when it read none.
            Excluded from equality: a default is compared by its canonical kind and value,
            and one source text lowers to one tree; a live compound default whose tree is
            the declared one takes the declared default before the comparison
            (``align_live_spelling``).
    """

    kind: str
    value: str
    name: str
    tree: SqlNode | None = field(default=None, compare=False)


@dataclass(frozen=True)
class SnapshotType:
    """Type definition for a column.

    Attributes:
        kind: "scalar" or "enum".
        name: Canonical type name (e.g. "String", "Integer", "OrderStatus").
        constraints: Named constraints from type parameters.
        values: Enum member names (empty tuple for scalar types).
    """

    kind: str
    name: str
    constraints: dict[str, int]
    values: tuple[str, ...]


@dataclass(frozen=True)
class SnapshotColumn:
    """Column definition within a table.

    Attributes:
        column_name: Physical column name (snake_case).
        type: Type definition.
        storage: Storage metadata.
        nullable: Whether the column allows NULL.
        primary_key: Whether this is the primary key column.
        default: Default value, or None.
        unique: Whether this column has a unique constraint.
        comment: The column's database comment (``COMMENT ON COLUMN`` text),
            or None.  Sourced from the field's PUBLISHED DSL documentation
            only -- an unmarked internal note never reaches the catalog
            (:func:`cruftfree_common.documentation.database_comment_text`).
    """

    column_name: str
    type: SnapshotType
    storage: SnapshotStorage
    nullable: bool
    primary_key: bool
    default: SnapshotDefault | None
    unique: bool = False
    comment: str | None = None


@dataclass(frozen=True)
class SnapshotIndex:
    """Index definition for a table.

    Attributes:
        columns: Column names in the index.
        unique: Whether this is a unique index.
        name: The index's physical name as recorded by the snapshot builder
            (:func:`~cruftfree_rdbms_schema.index_naming.record_index_names`), or the
            name a live catalog reports for a reflected snapshot; ``None`` in a
            canonical snapshot.  Excluded from equality and hashing: two snapshots
            describe the same schema whatever their indexes are called, and a name
            that differs is a rename, not schema identity.
        fulltext: Whether this is a fulltext index (GIN/FULLTEXT). Realized
            via the shared SQL dialect, never as a plain b-tree CREATE INDEX
            or a MikroORM @Index on the entity class.
        spatial: Whether this is a spatial index over a geographic column.
            Language- and engine-neutral exactly as ``fulltext`` is: the
            *kind* is recorded here and each dialect realizes it its own way
            (PostgreSQL ``USING GIST``), so the
            snapshot never names a physical index method.
        constraint_backed: Whether the database holds a unique index as the index of
            a unique constraint. CruftFree creates every unique as a constraint, so a
            declared snapshot leaves it true; a live catalog reports false for a
            unique index no constraint owns (``CREATE UNIQUE INDEX``), which is
            dropped as an index, never as a constraint. Excluded from equality and
            hashing like ``name``: both forms make the same promise, and only the
            statement that removes the object differs.
    """

    columns: tuple[str, ...]
    unique: bool
    name: str | None = field(default=None, compare=False)
    fulltext: bool = False
    spatial: bool = False
    constraint_backed: bool = field(default=True, compare=False)


@dataclass(frozen=True)
class SnapshotForeignKey:
    """Foreign key definition for a table.

    Attributes:
        columns: Local column names in the FK.
        referred_table: Target table name.
        referred_columns: Target column names.
        on_delete: The DSL referential action on delete -- one of
            :data:`~cruftfree_common.cruftfree_model.constants.VALID_REFERENTIAL_ACTIONS`
            (``cascade``/``restrict``/``setNull``), resolved from both sides of
            the link. Never a SQL keyword: each SQL dialect maps the
            action onto its own spelling.
        on_update: The DSL referential action on update, same vocabulary.
        name: The constraint's physical name, derived by
            :func:`~cruftfree_rdbms_schema.foreign_key_naming.record_foreign_key_names`, or
            ``None`` in a canonical snapshot.
            Excluded from equality: a name is metadata that names the physical
            object, not part of what the constraint ties together.
    """

    columns: tuple[str, ...]
    referred_table: str
    referred_columns: tuple[str, ...]
    on_delete: str
    on_update: str
    name: str | None = field(default=None, compare=False)


@dataclass(frozen=True)
class SnapshotCheck:
    """Check constraint definition for a table.

    Attributes:
        name: The constraint's physical name, derived from its definition by
            :func:`~cruftfree_rdbms_schema.definition_naming.definition_name`: a changed
            definition is a different name. Two checks are the same check exactly
            when their names are equal.
        tree: The row predicate lowered by the one SQL lowering
            (:func:`~cruftfree_rdbms_schema.sql_lowering._lower_operands.lower_expression`), which
            the renderer writes the check's SQL from; ``None`` for a check a live
            catalog reflected, which carries its name only. Excluded from
            equality: a check is compared by name, never by its SQL or tree.
    """

    name: str
    tree: SqlNode | None = field(default=None, compare=False)


@dataclass(frozen=True)
class SnapshotTrigger:
    """A database-enforced rule over a table's rows, realized as a trigger and its function.

    The snapshot records the rule, never the trigger's SQL: the block's dialect
    writes the function and the trigger from it, the way a check's SQL is written
    from its tree.

    Attributes:
        name: The trigger's physical name, and the name of its function, derived from
            its definition by :func:`~cruftfree_rdbms_schema.trigger_naming.trigger_name`: a
            changed definition is a different name. Two triggers are the same
            trigger exactly when their names are equal.
        kind: The rule's kind, one of :data:`~cruftfree_rdbms_schema.trigger_naming.TRIGGER_KINDS`;
            ``None`` for a trigger a live catalog reflected, which carries its name only.
            Excluded from equality: the name carries the definition.
        columns: The physical columns the rule is stated over: for ``append_only`` the
            columns an update may still change, for ``aggregate_invariant`` the columns
            rows are grouped by. Excluded from equality, like *kind*.
        predicate: For ``aggregate_invariant``, the condition each group must satisfy,
            lowered by the one SQL lowering with its aggregate calls in place; ``None``
            for ``append_only`` and for a trigger a live catalog reflected. Excluded from
            equality, like a check's tree.
    """

    name: str
    kind: str | None = field(default=None, compare=False)
    columns: tuple[str, ...] = field(default=(), compare=False)
    predicate: SqlNode | None = field(default=None, compare=False)


@dataclass(frozen=True)
class SnapshotTable:
    """Table-level schema representation for an entity or CQRS view.

    An entity and a CQRS read model are the same thing to the schema
    converge -- a physical table it creates, indexes, comments and relocates --
    so both are recorded in this one shape. They are held in separate maps on
    the snapshot only because the DSL distinguishes them.

    Attributes:
        table_name: Physical table name.
        fields: Map of cruftfree field name to column definition.
        indexes: Index definitions.
        foreign_keys: Foreign key definitions.
        table_options: Additional table options (engine-neutral).
        comment: The table's database comment (``COMMENT ON TABLE`` text),
            or None -- see :attr:`SnapshotColumn.comment` for the channel
            rule and the unrecorded-vs-absent distinction.
        checks: Check constraint definitions, compared by name. Empty on a
            snapshot written before checks were recorded, which declared none.
        triggers: The database-enforced rules over the table's rows, compared by name.
            Empty for a table that declares none, and on a snapshot written before
            triggers were recorded.
    """

    table_name: str
    fields: dict[str, SnapshotColumn]
    indexes: tuple[SnapshotIndex, ...]
    foreign_keys: tuple[SnapshotForeignKey, ...]
    table_options: dict[str, object]
    comment: str | None = None
    checks: tuple[SnapshotCheck, ...] = ()
    triggers: tuple[SnapshotTrigger, ...] = ()


@dataclass(frozen=True)
class SnapshotEnum:
    """Enum definition.

    Attributes:
        name: CruftFree enum name (PascalCase).
        database_name: Database-level name (snake_case).
        values: Ordered list of enum member NAMES, exactly as the DSL declares
            them.  These are member names, never database labels: only the
            TYPE carries a ``database_name``.
        member_values: Each member's DSL-declared serialized value
            (``value('shipped')``, ``value(1)``) rendered as text, positionally
            parallel to :attr:`values`, ``None`` where a member declares none.

            This is DSL data, not target metadata -- ``value()`` is the
            author's own statement of how a member serializes, and each target
            derives its persisted label from it: a target whose ORM stores the
            member NAME ignores it, while one whose ORM stores the enum's VALUE
            reads it.  Recording it is what lets the schema converge spell the
            same label each target's runtime writes; without it the converge has
            to guess the member name and cannot even detect that it is guessing,
            which is how a converged type comes to hold a label the application
            cannot read back.

            An EMPTY tuple alongside a non-empty :attr:`values` means
            UNRECORDED, never "no member declares a value": a reflected
            snapshot never has it (a database records labels,
            not which of them the DSL declared explicitly).  A consumer that
            needs it must refuse rather than read absence as "undecorated".
    """

    name: str
    database_name: str
    values: tuple[str, ...]
    member_values: tuple[str | None, ...] = ()


@dataclass(frozen=True)
class SnapshotServiceIdentity:
    """Service identity metadata for a snapshot.

    Attributes:
        name: Service name.
        version: Service version (if declared).
    """

    name: str
    version: str | None


@dataclass(frozen=True)
class SnapshotContainerIdentity:
    """Container identity metadata for a snapshot.

    Attributes:
        name: Container name (service or shared block name).
        kind: "service" or "shared".
    """

    name: str
    kind: str


@dataclass(frozen=True)
class SnapshotBlockIdentity:
    """RDBMS block identity metadata for a snapshot.

    Attributes:
        name: Block alias name (e.g. "operationalDb").
    """

    name: str


@dataclass(frozen=True)
class RdbmsSchemaSnapshot:
    """Top-level snapshot container.

    This is the canonical representation of an RDBMS block's schema: the schema the
    block declares, or the one a catalog reader read from its database.
    """

    format: str
    version: int
    rdbms_id: str
    service: SnapshotServiceIdentity
    container: SnapshotContainerIdentity
    block: SnapshotBlockIdentity
    entities: dict[str, SnapshotTable]
    cqrs_views: dict[str, SnapshotTable]
    enums: tuple[SnapshotEnum, ...]
    # PostgreSQL schema (namespace) that every table and native enum type in this
    # block is placed in, or None for the default schema.  Block-uniform: it is
    # the block's ``RdbmsConfig.schema_name``, applied identically to all objects.
    # Serialized only when set (mirrors the ``unique`` field precedent on SnapshotColumn).
    schema_name: str | None = None
    # The audit-log table of every audited entity, keyed by its declared name
    # (``<Entity>AuditLog``; see :func:`audit_log_declared_name`). These are
    # physical tables the audit hooks write on every create/update/delete, so the
    # schema converge must create them exactly as it creates an entity's table.
    # Serialized only when non-empty, so a block with no audited entity hashes
    # exactly as it did before audit tables were recorded.
    audit_log_tables: dict[str, SnapshotTable] = field(default_factory=dict)
    # The junction (join) table of every manyToMany pair of the block, keyed by its
    # physical table name (a junction has no declared name of its own). Like an
    # audit-log table it is a physical table the ORMs query while no entity
    # declares it. Serialized only when non-empty, so a block with no manyToMany
    # hashes exactly as it did before junction tables were recorded.
    junction_tables: dict[str, SnapshotTable] = field(default_factory=dict)
    # The tables the generated runtime itself reads and writes in this block while no
    # declaration names them (the last-fire table of in-process scheduled jobs), keyed
    # by physical table name. A service holds data rights only, so the schema converge
    # creates them under the owner login exactly as it creates an entity's table.
    # Serialized only when non-empty, so a block with none hashes exactly as it did
    # before framework tables were recorded.
    framework_tables: dict[str, SnapshotTable] = field(default_factory=dict)

    def declared_tables(self) -> dict[str, SnapshotTable]:
        """Every table this block's declared schema creates and maintains.

        Entity tables, CQRS read-model backing tables, audit-log tables, junction
        tables and framework tables, in one map keyed by the declared name. This is the set a
        convergence of an empty database must CREATE, the set a relocation must
        MOVE, and the set a change record's ``entity`` name resolves against --
        three questions that must have one answer. A table missing from it is
        moved or written by generated code while no convergence creates it, so a
        fresh database fails its schema converge or its first write.

        Raises:
            ValueError: If two of the maps share a name. They would
                collapse to one table here -- and, upstream of that, to one
                physical table name -- so the collision is reported rather than
                silently resolved in favour of whichever map is merged last.
        """
        maps = {
            "an entity": self.entities,
            "a CQRS view": self.cqrs_views,
            "an audit-log table": self.audit_log_tables,
            "a junction table": self.junction_tables,
            "a framework table": self.framework_tables,
        }
        names = list(maps)
        for position, first in enumerate(names):
            for second in names[position + 1 :]:
                collisions = sorted(set(maps[first]) & set(maps[second]))
                if collisions:
                    raise ValueError(
                        "RDBMS block '%s' declares %s as both %s and %s. "
                        "Both map to one physical table name, so the schema "
                        "converge cannot tell which declaration owns the table. "
                        "Rename one of them."
                        % (
                            self.block.name,
                            ", ".join(repr(c) for c in collisions),
                            first,
                            second,
                        )
                    )
        return {
            **self.entities,
            **self.cqrs_views,
            **self.audit_log_tables,
            **self.junction_tables,
            **self.framework_tables,
        }
