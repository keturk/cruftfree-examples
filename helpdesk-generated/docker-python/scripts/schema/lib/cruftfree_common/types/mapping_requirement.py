"""Tier governing how strictly a canonical type's mapping is required.

Lives in the types layer — the lowest layer that needs it.
ScalarType (types/base.py) carries this as a field default, so it must be
importable from types/ without introducing a types -> generation edge.
Generators (generation/) are allowed to import from types/, so
``cruftfree_codegen_kernel.generation.type_mapping_registry`` can import from
here without a boundary violation.
"""

from __future__ import annotations

from enum import StrEnum


class MappingRequirement(StrEnum):
    """Tier governing how strictly a canonical type's mapping is required.

    CORE_REQUIRED: must be globally mapped for every selected language.
        All builtin scalar types default to this tier. A language claiming
        support must provide a mapping for every CORE_REQUIRED type or the
        completeness gate will block generation.

    USED_REQUIRED: must be mapped only if the application actually uses it.
        Extension-declared scalars default to this tier. If an application
        uses an extension type and the generator has no mapping, generation
        must fail for that application but not for applications that don't
        use the type.

    EXPERIMENTAL: fails when used without a mapping; never blocks otherwise.
        Types under active development that are not yet supported by all
        generators. A generator may omit EXPERIMENTAL types from its map
        unless an application uses one of them.
    """

    CORE_REQUIRED = "core_required"
    USED_REQUIRED = "used_required"
    EXPERIMENTAL = "experimental"
