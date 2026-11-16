"""Shared validation utilities for code generation.

Generic validation helpers that can be used by any generator package.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from pathlib import Path
from typing import TypeVar, overload

from cruftfree_common.errors.codegen import TypeMappingError
from cruftfree_common.errors.generation import GenerationError

_T = TypeVar("_T")
_K = TypeVar("_K")
_V = TypeVar("_V")

_OPTION_SEPARATOR = ", "
_NO_OPTIONS_TEXT = "(none)"


# @pattern(common/codegen/exhaustive-map-lookup): Require key in type map or raise with sorted available keys
# @anti-pattern: type_map.get(name, default) hiding unmapped types
def require_mapped_type(
    type_name: str,
    type_map: Mapping[str, object],
    context: str = "type",
    *,
    error_type: type[TypeMappingError] = TypeMappingError,
) -> None:
    """Ensure type_name is a key in type_map; raise with available list otherwise.

    Use for exhaustive type mappings (e.g. canonical scalar -> language type).
    Raises TypeMappingError with "Available: ..." so error messages stay consistent.

    Args:
        type_name: The type name to look up.
        type_map: Mapping of supported type names to language-specific values
            (e.g. PythonTypeMapping, TypeScriptTypeMapping). Values are opaque
            per generator; only key membership is used here.
        context: Short label for the error message (e.g. "scalar type", "dialect").
        error_type: The ``TypeMappingError`` subclass to raise; a package that
            owns a narrower error class (the SQL facts) passes its own so callers
            catching that class keep working.

    Raises:
        TypeMappingError: If type_name not in type_map (``error_type`` when given).
    """
    if type_name not in type_map:
        available = ", ".join(sorted(type_map))
        raise error_type(f"Unmapped {context} '{type_name}'. Available: {available}")


def validate_template_dir(template_dir: Path) -> None:
    """Ensure template directory exists and is a directory.

    Raises:
        FileNotFoundError: If template_dir is not an existing directory.
    """
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")


@overload
def require_option(
    value: _K, table: Mapping[_K, _V], *, label: str, hint: str | None = None
) -> _V: ...


@overload
def require_option(
    value: _K, table: Collection[_K], *, label: str, hint: str | None = None
) -> None: ...


# @pattern(common/codegen/option-membership): Require value in a closed option table or raise one GenerationError shape
# @rule: Every engine/SKU/mode membership check raises through this function; no hand-rolled `not in ... raise`
# @anti-pattern: A per-validator `if value not in TABLE: raise GenerationError(...)` with its own option formatting
def require_option(
    value: object,
    table: Collection[object],
    *,
    label: str,
    hint: str | None = None,
) -> object | None:
    """Ensure ``value`` is one of the options in ``table``.

    Args:
        value: The candidate (a string, or an enum/identity member).
        table: The closed set of valid options: any collection of options, or a
            mapping from option to its entry.
        label: What is being validated, as it should read in the message
            (e.g. ``"Azure Event Hubs tier"``).
        hint: Optional fix text appended verbatim after the option list
            (e.g. ``"Set platforms.azure.pythonVersion in your platform configuration."``).

    Returns:
        ``table[value]`` when ``table`` is a ``Mapping``; ``None`` otherwise.

    Raises:
        GenerationError: ``value`` is not in ``table``. The message names the
            label, the value, the sorted comma-joined options (``str()`` of each)
            and the hint.
    """
    if value not in table:
        options = _OPTION_SEPARATOR.join(sorted(str(option) for option in table))
        message = (
            f"Unsupported {label} '{value}'. Available: {options or _NO_OPTIONS_TEXT}."
        )
        if hint:
            message = f"{message} {hint}"
        raise GenerationError(message)
    if isinstance(table, Mapping):
        return table[value]
    return None


# @invariant(config/require-deployment-fields): Deployment config fields must be explicitly present
# @rule: None values raise GenerationError with engine and field context instead of propagating silent defaults
# @anti-pattern: Returning a guessed default when config omits a required deployment value
# @invariant(config/require-platform-fields): Platform deployment config fields must be explicitly present
# @rule: None/empty values raise GenerationError with platform + field context instead of silent defaults
# @anti-pattern: Baking sizing/cost values (cpu, memory, replicas, node type) into the generator
def require_platform_field(
    value: _T | None,
    field_name: str,
    platform: str,
) -> _T:
    """Require a deployment value from a platform config model.

    Platform sizing/cost values (cpu, memory, replicas, node type, instance
    class, storage) MUST come from the resolved ``platform.<name>`` section of
    the application config. When a field is None or empty, the config is
    incomplete and generation must fail with an actionable message — the
    deployment target contract forbids hidden defaults and placeholder values.

    Args:
        value: The platform config field value (may be None).
        field_name: Field name for the error message (e.g. "container_app_cpu").
        platform: Platform name for context (e.g. "azure", "aws").

    Returns:
        The non-None, non-empty value.

    Raises:
        GenerationError: If value is None or an empty string, with an actionable message.
    """
    if value is None or value == "":
        raise GenerationError(
            f"Missing '{field_name}' in {platform} platform config. "
            f"Add '{field_name}' to the 'platform.{platform}' section of the .ccfg file. "
            "The deployment target contract forbids hidden defaults and placeholder values."
        )
    return value


def require_deployment_field(
    value: _T | None,
    field_name: str,
    config_type: str,
    engine: str,
) -> _T:
    """Require a deployment field from a config model.

    Deployment values (port, container_image, volume_path, async_driver, etc.)
    MUST come from the resolved ``.ccfg`` profile. When a field is None,
    the config is incomplete and generation must fail with an actionable message.

    Args:
        value: The config field value (may be None).
        field_name: Field name for the error message (e.g. "port", "dockerImage").
        config_type: Config model type for context (e.g. "rdbms", "cache").
        engine: Engine name for context (e.g. "postgresql", "redis").

    Returns:
        The non-None value.

    Raises:
        GenerationError: If value is None, with an actionable message.
    """
    if value is None:
        raise GenerationError(
            f"Missing '{field_name}' in {config_type} config for engine '{engine}'. "
            f"Add '{field_name}' to the relevant section in the referenced service/shared .ccfg file."
        )
    return value
