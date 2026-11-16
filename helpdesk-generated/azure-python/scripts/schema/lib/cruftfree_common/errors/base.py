"""Base error class for all CruftFree errors."""

from cruftfree_common.errors.location import SourceLocation


class CruftFreeError(Exception):
    """Base exception for all CruftFree errors.

    All CruftFree-specific exceptions inherit from this class, allowing
    callers to catch all CruftFree errors with a single except clause.

    This follows the fail-fast philosophy: errors should be caught at
    generation time with helpful messages, not silently ignored.

    Attributes:
        message: The error message
        source_location: Optional source code location where error occurred
        suggestions: Optional list of helpful suggestions
    """

    def __init__(
        self,
        message: str,
        *,
        source_location: SourceLocation | None = None,
        suggestions: list[str] | None = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Error message
            source_location: Optional source code location
            suggestions: Optional list of suggestions
        """
        self.message = message
        self.source_location = source_location
        self.suggestions = suggestions or []
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with context.

        Returns:
            Formatted error message including location and suggestions
        """
        msg = self.message

        if self.source_location:
            msg += f"\n  at {self.source_location}"

        if self.suggestions:
            msg += "\n  Suggestions:"
            for suggestion in self.suggestions:
                msg += f"\n    - {suggestion}"

        return msg
