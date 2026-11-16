"""Statement kinds, rendered revision, statements by change and refused change kinds."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Final

from cruftfree_rdbms_schema.differ import ChangeKind, SchemaChange


class SqlStatementKind(Enum):
    """What one statement of a revision does. A closed set: every renderer emits only these."""

    CREATE_SCHEMA = "create_schema"
    SET_SEARCH_PATH = "set_search_path"
    CREATE_TABLE = "create_table"
    DROP_TABLE = "drop_table"
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    ALTER_COLUMN_TYPE = "alter_column_type"
    ALTER_NULLABILITY = "alter_nullability"
    SET_DEFAULT = "set_default"
    DROP_DEFAULT = "drop_default"
    ADD_UNIQUE_CONSTRAINT = "add_unique_constraint"
    DROP_UNIQUE_CONSTRAINT = "drop_unique_constraint"
    ADD_CHECK_CONSTRAINT = "add_check_constraint"
    DROP_CHECK_CONSTRAINT = "drop_check_constraint"
    CREATE_TRIGGER_FUNCTION = "create_trigger_function"
    CREATE_TRIGGER = "create_trigger"
    DROP_TRIGGER = "drop_trigger"
    DROP_TRIGGER_FUNCTION = "drop_trigger_function"
    CREATE_INDEX = "create_index"
    DROP_INDEX = "drop_index"
    RENAME_INDEX = "rename_index"
    ADD_FOREIGN_KEY = "add_foreign_key"
    VALIDATE_FOREIGN_KEY = "validate_foreign_key"
    DROP_FOREIGN_KEY = "drop_foreign_key"
    RENAME_FOREIGN_KEY = "rename_foreign_key"
    CREATE_ENUM_TYPE = "create_enum_type"
    DROP_ENUM_TYPE = "drop_enum_type"
    ADD_ENUM_VALUE = "add_enum_value"
    RENAME_ENUM_VALUE = "rename_enum_value"
    SET_COMMENT = "set_comment"
    RELOCATE_SCHEMA = "relocate_schema"
    RAW_BACKFILL = "raw_backfill"


class SqlObjectKind(Enum):
    """The kind of database object one statement is about."""

    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"
    INDEX = "index"
    CONSTRAINT = "constraint"
    FOREIGN_KEY = "foreign_key"
    ENUM_TYPE = "enum_type"
    TRIGGER = "trigger"
    FUNCTION = "function"


@dataclass(frozen=True)
class SqlStatement:
    """One statement of a revision and the object it is about.

    Attributes:
        kind: What the statement does.
        object_kind: The kind of object it is about.
        object_name: That object's name: the schema, table, column, index,
            constraint or enum type. A statement dropping every single-column
            unique constraint of a column is about the column: its object kind
            is ``column`` and it names the column, since the constraints it
            drops are whatever the catalog holds under any name.
        table: The table the object belongs to (the table itself for a table
            statement); ``None`` for a schema or an enum type.
        sql: The statement's SQL text, as the dialect renders it.
    """

    kind: SqlStatementKind
    object_kind: SqlObjectKind
    object_name: str
    table: str | None
    sql: str


@dataclass(frozen=True)
class RenderedRevision:
    """Every statement of one revision, in the order they run."""

    statements: tuple[SqlStatement, ...]


@dataclass(frozen=True)
class ChangeStatement:
    """One statement of a set of rendered changes, and the change it renders.

    Attributes:
        statement: The statement.
        change: The change it renders; ``None`` for a statement of the schema prelude
            (``create_schema``, ``set_search_path``), which no one change owns.
    """

    statement: SqlStatement
    change: SchemaChange | None


#: The kinds no forward DDL realizes on any engine, each with the reason it is refused.
REFUSED_CHANGE_KINDS: Final[Mapping[ChangeKind, str]] = {
    ChangeKind.ENUM_VALUE_REMOVED: (
        "a removed enum label may still be held by existing rows, and no engine retires "
        "a label in place (PostgreSQL has no DROP VALUE; an inline-enum engine rejects "
        "the restatement while a row holds it)"
    ),
    ChangeKind.ENUM_VALUES_REORDERED: (
        "member order is the type's sort order, which drives ORDER BY on every column "
        "using it, and no engine reorders the labels of an existing type in place"
    ),
    ChangeKind.FIELD_PRIMARY_KEY_CHANGED: (
        "a column joining or leaving its table's primary key re-keys every row and every "
        "foreign key that references the table, and no engine changes a primary key in place"
    ),
    ChangeKind.ENTITY_TABLE_RENAMED: (
        "the generated code already reads and writes the new table name, and no engine "
        "renames a table in place"
    ),
    ChangeKind.ENTITY_OPTIONS_CHANGED: (
        "no engine's DDL realizes an engine-neutral table option in place"
    ),
    ChangeKind.ENUM_TYPE_ADDED: (
        "a type no column uses is created by no column's DDL, and no engine's DDL is "
        "rendered for a type alone"
    ),
    ChangeKind.ENUM_TYPE_RENAMED: (
        "the generated code already addresses the type by its new database name, and no "
        "engine renames a type in place"
    ),
}

_ENUM_TYPE_KIND: Final[str] = "enum"
