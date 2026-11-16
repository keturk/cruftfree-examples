"""CruftFree type system -- unified type hierarchy, registry, and definitions.

This package is the single source of truth for:
- CruftFreeType hierarchy (ScalarType, ConstrainedType, CollectionType, etc.) -- cruftfree_common.types.base / .compound / .ref
- TypeRegistry (builtin lookup, name resolution) -- cruftfree_common.types.registry
- TypeConstraints (named constraint semantics) -- cruftfree_common.types.base
- TypeMappingBase (shared base for generator mapping dataclasses) -- cruftfree_common.types.base
- Type definitions (primitive, domain, temporal) -- cruftfree_common.types.parser
"""
