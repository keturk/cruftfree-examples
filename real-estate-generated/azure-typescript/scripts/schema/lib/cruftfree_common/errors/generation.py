"""Code generation errors."""

from cruftfree_common.errors.base import CruftFreeError


class GenerationError(CruftFreeError):
    """Raised when code generation fails."""

    pass


class CodeGenerationError(GenerationError):
    """Raised when generated code is invalid."""

    pass


class ResourceGenerationError(CodeGenerationError):
    """Raised when a specific resource generation fails.

    Attributes:
        resource_type: Type of resource being generated
        resource_name: Name of the resource being generated
    """

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        resource_name: str | None = None,
    ) -> None:
        """Initialize ResourceGenerationError."""
        super().__init__(message)
        self.resource_type = resource_type
        self.resource_name = resource_name


class TokenModelGenerationError(CodeGenerationError):
    """Raised when token model generation fails."""

    pass


class SecretsGenerationError(CodeGenerationError):
    """Raised when secrets generation fails."""

    pass


class DependenciesGenerationError(CodeGenerationError):
    """Raised when dependencies generation fails."""

    pass


class CodeValidationError(CodeGenerationError):
    """Raised when generated code fails validation.

    Attributes:
        file_path: Path to the file that failed validation
        line_number: Line number where the error occurred
        errors: List of validation error messages
    """

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
        line_number: int | None = None,
        errors: list[str] | None = None,
    ) -> None:
        """Initialize CodeValidationError."""
        self.file_path = file_path
        self.line_number = line_number
        self.errors = errors if errors is not None else []
        primary = (
            message
            + (f" (file: {file_path})" if file_path else "")
            + (f" (line: {line_number})" if line_number is not None else "")
        )
        formatted_parts: list[str] = [primary]
        if self.errors:
            formatted_parts.append("\n".join(self.errors))
        formatted = "\n".join(formatted_parts)
        super().__init__(formatted)
        self.message = message
