"""Plugin-related error classes."""

from cruftfree_common.errors.base import CruftFreeError


class PluginError(CruftFreeError):
    """Base exception for all plugin-related errors."""

    pass


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin cannot be found."""

    pass


class ExtensionNotFoundError(PluginNotFoundError):
    """Raised when a domain extension is declared but not installed.

    The message names the ``cruftfree.extensions`` entry-point group the
    extension must be registered under and ends with
    :data:`cruftfree_common.constants.FRAMEWORK_INSTALL_SENTENCE`. Callers may
    catch ``PluginNotFoundError`` to handle this together with other missing
    plugins.
    """


class ExtensionNotSupportedError(PluginError):
    """Raised when a language generator has no type mappings for a declared extension."""

    pass


class TypeConflictError(PluginError):
    """Raised when an extension defines a scalar type name that collides with core or another extension."""

    pass


class CustomScalarNameTakenError(TypeConflictError):
    """A custom scalar is declared under the name of a builtin or extension-loaded type.

    Attributes:
        name: The declared scalar name.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"Cannot register custom scalar '{name}': the name conflicts with a builtin or "
            f"extension-loaded type. Expected: a scalar name no registered type uses. "
            f"Fix: choose a distinct name."
        )


class CustomScalarRedeclaredError(TypeConflictError):
    """A custom scalar name is registered again with a different base type.

    Attributes:
        name: The scalar name as declared the second time.
        registered_as: The spelling the name was first registered under.
        registered_base: The display name of the first registration's base type.
        requested_base: The display name of the base type declared the second time.
    """

    def __init__(self, name: str, registered_as: str, registered_base: str, requested_base: str) -> None:
        self.name = name
        self.registered_as = registered_as
        self.registered_base = registered_base
        self.requested_base = requested_base
        super().__init__(
            f"Custom scalar '{name}' is already registered (as '{registered_as}') with the base "
            f"type {registered_base}, not the requested {requested_base}. Expected: one base type "
            f"per scalar name, compared case-insensitively. Fix: rename one of the scalars, or "
            f"give both the same base type."
        )


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""

    pass


class PluginGenerationError(PluginError):
    """Raised when plugin generation fails."""

    pass
