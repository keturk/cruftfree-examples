"""Exceptions for the code generation framework."""

from cruftfree_common.errors.base import CruftFreeError
from cruftfree_common.errors.generation import GenerationError


class TypeMappingError(GenerationError):
    """Raised when a CruftFree type has no mapping in the target language or dialect.

    Use with require_mapped_type() for consistent "Unmapped … Available: …" messages.
    """

    pass


class TemplateRenderError(Exception):
    """Raised when template loading or rendering fails.

    Attributes:
        message: Human-readable description
        template_name: Name of template (if applicable)
        cause: Original exception (if any)
    """

    def __init__(
        self,
        message: str,
        template_name: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.template_name = template_name
        self.cause = cause
        super().__init__(message)


class CodegenTranspilationError(CruftFreeError):
    """Raised when the transpiler encounters an unrecognized or invalid AST node."""

    pass


# Public name of the codegen-stage transpilation error.
TranspilationError = CodegenTranspilationError


class PipelineError(Exception):
    """Base error for pipeline failures."""

    def __init__(self, stage: str, message: str) -> None:
        self.stage = stage
        super().__init__(f"Pipeline failed at stage '{stage}': {message}")


def _make_stage_error(class_name: str, stage: str, docstring: str) -> type:
    """Create a pipeline stage error class that takes only message."""

    def __init__(self: PipelineError, message: str) -> None:
        PipelineError.__init__(self, stage, message)

    return type(
        class_name,
        (PipelineError,),
        {"__init__": __init__, "__doc__": docstring},
    )


ParseStageError = _make_stage_error("ParseStageError", "parse", "Parse stage failed.")

AnalysisStageError = _make_stage_error(
    "AnalysisStageError", "analyze", "Semantic analysis stage failed."
)

TargetCheckStageError = _make_stage_error(
    "TargetCheckStageError",
    "check_targets",
    "The run's backend language, client targets or platform cannot realize the source.",
)

SeedParseStageError = _make_stage_error(
    "SeedParseStageError",
    "discover_and_parse_seeds",
    "Seed discovery/parse stage failed.",
)


class GeneratorNotFoundError(PipelineError):
    """Requested generator is not installed."""

    def __init__(self, name: str, available: list[str]) -> None:
        available_str = ", ".join(sorted(available)) if available else "none"
        super().__init__(
            "discover",
            f"Generator '{name}' not found. Available: {available_str}",
        )
        self.name = name
        self.available = available


class GeneratorLoadError(PipelineError):
    """Generator entry point failed to load."""

    def __init__(self, name: str, cause: BaseException) -> None:
        super().__init__("discover", f"Generator '{name}' failed to load: {cause}")
        self.name = name
        self.cause = cause


class GenerationStageError(PipelineError):
    """A generator's generate() call failed."""

    def __init__(self, generator_name: str, message: str) -> None:
        super().__init__("generate", f"Generator '{generator_name}': {message}")
        self.generator_name = generator_name


WriteStageError = _make_stage_error(
    "WriteStageError", "write", "File writing stage failed."
)
