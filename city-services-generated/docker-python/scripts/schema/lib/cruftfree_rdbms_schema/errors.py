"""Error types of the declared-schema model."""

from __future__ import annotations


class SchemaError(Exception):
    """Base error for declared-schema failures."""


class SchemaMismatchError(SchemaError):
    """A database does not hold the declared schema ``D``.

    Raised by :func:`cruftfree_rdbms_schema.convergence.require_same_schema`, the one check
    of whether two snapshots describe the same schema. It fails closed: each difference
    the change differ classifies is named, and a difference it does not classify is
    still a refusal, naming the differ as the defect.

    Attributes:
        block_name: The RDBMS block the two snapshots describe.
        differences: One line per difference, in render order; a single line saying the
            differ does not classify the difference when it reported none.
    """

    def __init__(self, block_name: str, differences: tuple[str, ...]) -> None:
        self.block_name = block_name
        self.differences = differences
        difference_lines = "\n".join(f"  - {line}" for line in differences)
        super().__init__(
            f"The schema of RDBMS block '{block_name}' is not the declared schema: "
            "expected the two snapshots to describe the same tables, columns, indexes, "
            "foreign keys, checks, enum types and schema placement, found:\n"
            f"{difference_lines}\n"
            "Bring the database to the declared schema (deploy it again), or change "
            "the DSL so it declares what the database holds."
        )
