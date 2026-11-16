"""Base type classes for the CruftFree type system.

CruftFreeType is the abstract root. ScalarType represents builtin scalar types
with identity and metadata only — NO target-language knowledge.
TypeConstraints holds named constraint semantics from type parameters.
TypeMappingBase is the shared base for generator-specific mapping dataclasses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from cruftfree_common.types.mapping_requirement import MappingRequirement


@dataclass(frozen=True)
class CruftFreeType(ABC):
    """Abstract base for all CruftFree types.

    All types are frozen dataclasses — immutable after construction.
    """

    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name for error messages and debugging."""
        ...

    def is_optional(self) -> bool:
        """Whether this type is optional (nullable)."""
        return False

    def unwrap(self) -> CruftFreeType:
        """Strip OptionalType wrapper if present, returning the inner type."""
        return self


@dataclass(frozen=True)
class ScalarType(CruftFreeType):
    """A builtin scalar type. Identity and metadata only — no language mappings.

    ScalarType instances are registered in TypeRegistry and represent
    primitive types (String, Integer), domain types (UUID, Email),
    and temporal types (DateTime, Date).
    """

    canonical_name: str
    category: str  # "primitive" | "domain" | "temporal"
    supports_sizing: bool = False
    aliases: frozenset[str] = frozenset()
    implicit_validation: str | None = None  # "email", "url", "uuid", etc.
    zero_value: str | None = (
        None  # Minimal valid raw value, language-agnostic (e.g., "0", "x")
    )
    sample_values: tuple[
        str, ...
    ] = ()  # Language-agnostic raw test values from builtin definitions
    # The tier is a property of the canonical type, not of any one language's mapping.
    # Decision rationale: requirement level is intrinsic to the type definition (is it
    # part of the core language contract?) and must be visible to the completeness gate
    # regardless of which generator is consulted. Storing it on TypeMappingBase would
    # require every generator to repeat the same value and would hide the tier from the
    # registry when no mapping exists yet.
    mapping_requirement: MappingRequirement = MappingRequirement.CORE_REQUIRED

    def __deepcopy__(self, memo: dict[int, object]) -> ScalarType:
        """A deep copy is this object: a frozen scalar holds only immutable values."""
        return self

    def display_name(self) -> str:
        return self.canonical_name


@dataclass(frozen=True)
class TypeConstraints:
    """Named constraint semantics derived from type parameters.

    The parser translates positional DSL syntax to named constraints:
      String(20)      → TypeConstraints(max_length=20)
      String(5, 20)   → TypeConstraints(min_length=5, max_length=20)
      Decimal(10, 2)  → TypeConstraints(precision=10, scale=2)
      Text(1000)      → TypeConstraints(max_length=1000)
    """

    min_length: int | None = None
    max_length: int | None = None
    precision: int | None = None
    scale: int | None = None


@dataclass(frozen=True)
class TypeMappingBase:
    """Base for generator-specific type mapping dataclasses.

    Generators extend this with target-specific fields.
    Provides just enough for shared tooling (docs, introspection).
    """

    type_name: str  # target language type: "str", "string", "TEXT"
    import_stmt: str | None = None  # import needed, or None
