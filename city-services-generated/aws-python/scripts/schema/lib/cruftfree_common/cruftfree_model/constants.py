"""Domain constants for the CruftFree data model.

Centralizes frozenset constants for HTTP methods,
lifecycle hooks, trait events, cascade types, and resource operations,
and the default RDBMS schema. These are referenced by model classes,
semantic validators and the schema runtime, so the module imports only the
standard library.
"""

from enum import StrEnum
from typing import Final

# --- HTTP Methods ---
HTTP_READ_METHODS: frozenset[str] = frozenset(
    {
        "get",
        "head",
        "options",
    }
)

HTTP_MUTATING_METHODS: frozenset[str] = frozenset(
    {
        "post",
        "put",
        "patch",
        "delete",
    }
)

HTTP_BODY_METHODS: frozenset[str] = frozenset(
    {
        "post",
        "put",
        "patch",
    }
)

# --- Cascade types (ORM-level) ---
VALID_CASCADE_TYPES: frozenset[str] = frozenset(
    {
        "all",
        "save-update",
        "delete",
        "delete-orphan",
        "none",
    }
)

# --- Referential actions (onDelete/onUpdate, SQL-level) ---
VALID_REFERENTIAL_ACTIONS: frozenset[str] = frozenset(
    {
        "cascade",
        "restrict",
        "setNull",
    }
)

DEFAULT_REFERENTIAL_ACTION: str = "restrict"

# --- RDBMS placement ---
#: The PostgreSQL schema a block lives in when it declares none.
DEFAULT_RDBMS_SCHEMA: Final[str] = "public"

# --- Resource operations ---
VALID_RESOURCE_OPERATIONS: frozenset[str] = frozenset(
    {
        "list",
        "get",
        "create",
        "update",
        "delete",
    }
)

#: The resource operation that expands to the entity's paged list route.
RESOURCE_LIST_OPERATION: str = "list"


# --- Entity write operations ---
class EntityWriteOperation(StrEnum):
    """The three writes an entity undergoes: the batch operations a
    ``rest_api`` expands, and the operations an entity audit captures.

    The one home of this vocabulary: every table keyed by a write operation --
    here, and in each target's audit rendering -- names its keys through these
    members, so no package re-spells the set.
    """

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# --- Batch operations ---
VALID_BATCH_OPERATIONS: frozenset[str] = frozenset(
    {
        EntityWriteOperation.CREATE,
        EntityWriteOperation.UPDATE,
        EntityWriteOperation.DELETE,
    }
)

# --- Operation orders (tuples for deterministic expansion) ---
RESOURCE_OPERATIONS: tuple[str, ...] = (
    "list",
    "get",
    "create",
    "update",
    "delete",
)

BATCH_OPERATIONS: tuple[str, ...] = (
    EntityWriteOperation.CREATE,
    EntityWriteOperation.UPDATE,
    EntityWriteOperation.DELETE,
)

# --- Operation → endpoint mapping specs ---
RESOURCE_OP_SPEC: dict[str, tuple[str, str]] = {
    # operation → (http_method, path_suffix)
    "list": ("get", "/"),
    "get": ("get", "/:id"),
    "create": ("post", "/"),
    "update": ("put", "/:id"),
    "delete": ("delete", "/:id"),
}

BATCH_OP_SPEC: dict[str, tuple[str, str]] = {
    # operation → (http_method, path_suffix)
    EntityWriteOperation.CREATE: ("post", "/batch"),
    EntityWriteOperation.UPDATE: ("put", "/batch"),
    EntityWriteOperation.DELETE: ("delete", "/batch"),
}

# --- Lifecycle hooks (entity-level) ---
VALID_LIFECYCLE_HOOKS: frozenset[str] = frozenset(
    {
        "beforeCreate",
        "afterCreate",
        "beforeUpdate",
        "afterUpdate",
        "beforeDelete",
        "afterDelete",
    }
)


class LifecycleHookType:
    """Type-hinted lifecycle hook constants to prevent typos and enable IDE autocomplete."""

    BEFORE_CREATE: str = "beforeCreate"
    AFTER_CREATE: str = "afterCreate"
    BEFORE_UPDATE: str = "beforeUpdate"
    AFTER_UPDATE: str = "afterUpdate"
    BEFORE_DELETE: str = "beforeDelete"
    AFTER_DELETE: str = "afterDelete"


# Validate that LifecycleHookType constants match VALID_LIFECYCLE_HOOKS
_hook_type_values = {
    LifecycleHookType.BEFORE_CREATE,
    LifecycleHookType.AFTER_CREATE,
    LifecycleHookType.BEFORE_UPDATE,
    LifecycleHookType.AFTER_UPDATE,
    LifecycleHookType.BEFORE_DELETE,
    LifecycleHookType.AFTER_DELETE,
}
if _hook_type_values != VALID_LIFECYCLE_HOOKS:
    raise RuntimeError(
        "LifecycleHookType constants must match VALID_LIFECYCLE_HOOKS exactly. "
        f"constants={_hook_type_values!r} expected={VALID_LIFECYCLE_HOOKS!r}",
    )
del _hook_type_values
