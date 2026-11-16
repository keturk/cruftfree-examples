"""Configuration-related errors."""

from pathlib import Path

from cruftfree_common.errors.base import CruftFreeError


class ConfigurationError(CruftFreeError):
    """Raised when configuration is invalid or missing.

    Attributes:
        config_key: Optional name of the configuration key that caused the error
        config_file: Optional path to the configuration file
        suggestion: Optional suggestion for fixing the error
    """

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        config_file: str | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Initialize ConfigurationError."""
        self.config_key = config_key
        self.config_file = config_file
        self.suggestion = suggestion

        error_parts: list[str] = []
        error_parts.append(message)

        if config_file:
            error_parts.append(f"  Config file: {config_file}")

        if config_key:
            error_parts.append(f"  Config key: {config_key}")

        if suggestion:
            error_parts.append(f"  Suggestion: {suggestion}")

        super().__init__("\n".join(error_parts))


class ProjectSettingsError(ConfigurationError):
    """Raised when a target's project settings are missing, unowned, or mistyped.

    Project settings are contributed by each registered language and platform
    plugin and validated at assembly; this error names the target, what was
    found, and the fix.
    """


class ConfigFileNotFoundError(CruftFreeError):
    """Raised when a configuration file cannot be found.

    Attributes:
        file_name: Name of the file that was searched for
        searched_paths: List of paths that were searched
    """

    def __init__(
        self,
        file_name: str,
        searched_paths: list[Path],
    ) -> None:
        """Initialize ConfigFileNotFoundError.

        Args:
            file_name: Name of the file that was searched for
            searched_paths: List of paths that were searched
        """
        self.file_name = file_name
        self.searched_paths = searched_paths

        paths_str = "\n  ".join(str(p) for p in searched_paths)
        message = (
            f"Configuration file '{file_name}' not found.\n"
            f"Searched locations:\n  {paths_str}\n"
            f"Run 'cruftfree init' to create a new project with configuration."
        )

        suggestions = [
            f"Check that '{file_name}' exists in one of the searched locations",
            "Run 'cruftfree init' to create a new project with configuration",
            "Verify you are in the correct project directory",
        ]

        super().__init__(message, suggestions=suggestions)


class ConfigDocumentSourceMissingError(ConfigurationError):
    """Raised when a config loader is reached through an Application with no config source.

    Every ``.ccfg`` is read through the ``ConfigDocumentSourceProtocol`` on
    ``Application.config_documents``; the ``attach_config_documents`` pipeline stage
    (directly after ``parse``) sets it. Reaching a loader without it is a wiring
    defect of the caller, never a missing file.
    """

    def __init__(self) -> None:
        """Initialize ConfigDocumentSourceMissingError."""
        super().__init__(
            "A .ccfg config document was requested through an Application that carries "
            "no config document source (Application.config_documents is None). Expected the "
            "'attach_config_documents' stage, which runs directly after 'parse', to "
            "attach one.",
            suggestion=(
                "Run the 'attach_config_documents' stage after parsing, or set "
                "app.config_documents to a ConfigDocumentSourceProtocol implementation "
                "(cruftfree_testing.config_documents.disk_config_documents() in tests)."
            ),
        )


class ConfigParseError(CruftFreeError):
    """Raised when YAML parsing fails.

    Attributes:
        file_path: Path to the file that failed to parse
        line: Optional line number where the error occurred
        column: Optional column number where the error occurred
        yaml_error: The underlying YAML error
    """

    def __init__(
        self,
        file_path: Path,
        yaml_error: Exception,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        """Initialize ConfigParseError.

        Args:
            file_path: Path to the file that failed to parse
            yaml_error: The underlying YAML error
            line: Optional line number where the error occurred
            column: Optional column number where the error occurred
        """
        self.file_path = file_path
        self.yaml_error = yaml_error
        self.line = line
        self.column = column

        location = ""
        if line is not None:
            location = f" at line {line}"
            if column is not None:
                location += f", column {column}"

        message = (
            f"Invalid YAML in configuration file '{file_path}'{location}.\n"
            f"Error: {yaml_error}\n"
            f"Check the syntax of your configuration file."
        )

        suggestions = [
            "Validate your YAML syntax using an online YAML validator",
            "Check for missing quotes, colons, or indentation errors",
            "Ensure all lists and dictionaries are properly formatted",
        ]

        super().__init__(message, suggestions=suggestions)


class PlatformConfigError(ConfigurationError):
    """Raised when platform config resolution fails.

    Provides actionable context: which deployment target was selected,
    which config field is missing (if applicable), what config model
    is expected, and a config snippet showing how to fix the issue.

    Attributes:
        deployment_target: The deployment target that failed resolution.
        missing_field: Optional name of the missing config field.
        expected_model: Optional name of the expected config model.
        yaml_example: Optional config snippet showing the fix.
    """

    def __init__(
        self,
        message: str,
        *,
        deployment_target: str,
        missing_field: str | None = None,
        expected_model: str | None = None,
        yaml_example: str | None = None,
    ) -> None:
        """Initialize PlatformConfigError.

        Args:
            message: Human-readable description of the resolution failure.
            deployment_target: The deployment target that failed resolution.
            missing_field: Optional name of the missing config field.
            expected_model: Optional name of the expected config model.
            yaml_example: Optional config snippet showing the fix.
        """
        self.deployment_target = deployment_target
        self.missing_field = missing_field
        self.expected_model = expected_model
        self.yaml_example = yaml_example

        parts: list[str] = [message]
        parts.append(f"  Deployment target: {deployment_target}")
        if missing_field:
            parts.append(f"  Missing field: {missing_field}")
        if expected_model:
            parts.append(f"  Expected config model: {expected_model}")
        if yaml_example:
            parts.append(f"  Example config:\n{yaml_example}")

        suggestion = (
            f"Add the required deployment configuration for '{deployment_target}' "
            f"in the referenced system .ccfg file."
        )

        super().__init__(
            "\n".join(parts),
            suggestion=suggestion,
        )


class ConfigValidationError(CruftFreeError):
    """Raised when configuration validation fails.

    Attributes:
        file_path: Path to the configuration file
        validation_errors: List of validation error details
    """

    def __init__(
        self,
        file_path: Path,
        validation_errors: list[str],
    ) -> None:
        """Initialize ConfigValidationError.

        Args:
            file_path: Path to the configuration file
            validation_errors: List of validation error details
        """
        self.file_path = file_path
        self.validation_errors = validation_errors

        errors_str = "\n  ".join(f"- {err}" for err in validation_errors)
        message = (
            f"Configuration validation failed for '{file_path}'.\n"
            f"Validation errors:\n  {errors_str}"
        )

        suggestions = [
            "Review the configuration schema documentation",
            "Check that all required fields are present",
            "Verify field types and constraints match the schema",
        ]

        super().__init__(message, suggestions=suggestions)
