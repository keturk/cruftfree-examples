"""Type map merges: a language's base type map plus its extension type maps.

Standard library plus the plugin errors only, so a carried runtime module may
import them without reaching the type registry.
"""

from __future__ import annotations

from typing import TypeVar

from cruftfree_common.errors.plugin import ExtensionNotSupportedError

T = TypeVar("T")


# @canonical(kernel/type-map-build): A language's type map: base types plus the app's declared extension types
# @rule: A declared extension the language has no mappings for fails with ExtensionNotSupportedError
# @anti-pattern: A language merging its extension maps itself, or skipping an unmapped declared extension
def build_type_map(
    base_map: dict[str, T],
    extension_maps: dict[str, dict[str, T]],
    declared_extensions: list[str],
    *,
    language: str,
) -> dict[str, T]:
    """Build a merged type map: base types plus declared extension types.

    Shared implementation of ``build_{lang}_type_map()`` used by language
    code generators (Python, TypeScript, SQL).

    Args:
        base_map: Core type mappings (e.g. ``PYTHON_TYPE_MAP``).
        extension_maps: Extension-keyed dicts of additional mappings
            (e.g. ``PYTHON_EXTENSION_MAPS``).
        declared_extensions: Extension names from ``app.extension_directives``.
        language: Language name for error messages (e.g. ``"Python"``).

    Returns:
        Merged type map with core plus extension mappings.

    Raises:
        ExtensionNotSupportedError: If a declared extension has no mappings.
    """
    merged = dict(base_map)
    for ext_name in declared_extensions:
        ext_mappings = extension_maps.get(ext_name)
        if ext_mappings is None:
            supported = sorted(extension_maps.keys())
            raise ExtensionNotSupportedError(
                f"Extension '{ext_name}' is declared in system.cfree but the "
                f"{language} generator does not have mappings for it.\n"
                f"Supported extensions: {supported or '(none)'}"
            )
        merged.update(ext_mappings)
    return merged


def static_type_map(
    base_map: dict[str, T],
    extension_maps: dict[str, dict[str, T]],
) -> dict[str, T]:
    """Build a merged type map with all extensions (a plugin's ``static_type_map``).

    The map a plugin hands to the run, from which the run builds its
    :class:`TypeMappingRegistry`. Includes every known extension regardless
    of user declarations.

    Args:
        base_map: Core type mappings.
        extension_maps: All extension mappings.

    Returns:
        Merged type map with core plus all extension mappings.
    """
    merged = dict(base_map)
    for ext_name in sorted(extension_maps.keys()):
        merged.update(extension_maps[ext_name])
    return merged
