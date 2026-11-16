"""Column facts the schema runtime reads: the rendered column record and the auto-increment base types."""

from __future__ import annotations

from dataclasses import dataclass

from cruftfree_common.utils.sql_text import sql_line_comment_lines


@dataclass(frozen=True)
class ColumnDefinition:
    """SQL column definition for template rendering."""

    name: str
    sql_type: str
    nullable: bool
    default: str | None
    auto_increment: bool = False
    #: The column's database comment -- the field's PUBLISHED DSL
    #: documentation only, never an unmarked internal note (Decision 39 D2,
    #: ``cruftfree_common.documentation.database_comment_text``). ``None`` for an
    #: undocumented column, which emits no comment at all. An implicit column
    #: (a relationship's foreign key) has no DSL declaration to document and
    #: therefore never carries one.
    comment: str | None = None
    #: The field's SOURCE-channel (``//``) note, rendered as ``--`` lines above
    #: the column in the emitted DDL -- the source-commentary channel, which
    #: reaches the generated file and never the database catalog. A comment run
    #: is exactly one channel, so at most one of ``comment``/``source_note`` is
    #: ever set.
    source_note: str | None = None

    @property
    def source_note_lines(self) -> tuple[str, ...]:
        """``--``-prefixed lines for :attr:`source_note`, one per physical line.

        Every line carries its own marker, so an embedded newline can never
        leave the remainder of the note uncommented. Empty for a column with
        no source-channel note, which then renders byte-identically to before
        this channel existed.
        """
        return sql_line_comment_lines(self.source_note)


AUTO_INCREMENT_BASE_TYPES = frozenset({"SMALLINT", "INTEGER", "INT", "BIGINT"})
