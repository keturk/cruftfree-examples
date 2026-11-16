"""Errors raised by the SQL dialect facts.

These three classes are raised only by the type map, the column derivation and the
dialects in this subpackage. The SQL generator's own error hierarchy
(``SQLGeneratorError`` and its subclasses) stays in the SQL generator package.

All errors are explicit; no silent fallbacks.
"""

from __future__ import annotations

from cruftfree_common.errors.codegen import TypeMappingError as CodegenTypeMappingError


class TypeMappingError(CodegenTypeMappingError):
    """Raised when a CruftFree type has no SQL mapping for the dialect."""


class DialectNotFoundError(Exception):
    """Raised when the requested SQL dialect is not registered."""


class DialectFeatureError(Exception):
    """Raised when a requested feature is not supported by the dialect."""
