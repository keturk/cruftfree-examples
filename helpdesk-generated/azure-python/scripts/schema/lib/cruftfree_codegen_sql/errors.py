"""SQL generator-specific errors.

The errors the shared SQL dialect facts raise (``TypeMappingError``,
``DialectNotFoundError``, ``DialectFeatureError``) live beside those facts in
``cruftfree_codegen_kernel.sql_facts.errors``.

All errors are explicit; no silent fallbacks.
"""

from __future__ import annotations

from cruftfree_common.errors.configuration import (
    ConfigurationError as CommonConfigurationError,
)


class SQLGeneratorError(Exception):
    """Base exception for cruftfree-codegen-sql."""

    pass


class ConfigurationError(CommonConfigurationError, SQLGeneratorError):
    """Raised when generator configuration is invalid (e.g. unsupported dialect).

    Inherits rich error attributes (config_key, config_file, suggestion) from
    the canonical ConfigurationError and satisfies ``except SQLGeneratorError``.
    """

    pass
