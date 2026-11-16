"""Source location models for error reporting."""

from dataclasses import dataclass
from pathlib import Path


# @canonical(common/errors/source-location): Frozen file path plus 1-based line and column for diagnostics
# @rule: line and column are 1-based when set
@dataclass(frozen=True)
class SourceLocation:
    """Source code location for error reporting.

    Attributes:
        file_path: Path to the source file (optional)
        line: Line number (1-based, optional)
        column: Column number (1-based, optional)
    """

    file_path: Path | None
    line: int | None
    column: int | None

    def __deepcopy__(self, memo: dict[int, object]) -> "SourceLocation":
        """A deep copy is this object: a frozen location holds only immutable values."""
        return self

    def __str__(self) -> str:
        """Format location as string.

        Returns:
            Formatted location string (e.g., "file.cfree:42:10" or "line 42")
        """
        parts = []
        if self.file_path:
            parts.append(str(self.file_path))
        if self.line is not None:
            parts.append(str(self.line))
            if self.column is not None:
                parts.append(str(self.column))
        if not parts:
            return "unknown location"
        if not self.file_path and self.line is not None:
            if self.column is not None:
                return f"line {self.line}:{self.column}"
            return f"line {self.line}"
        return ":".join(parts)
