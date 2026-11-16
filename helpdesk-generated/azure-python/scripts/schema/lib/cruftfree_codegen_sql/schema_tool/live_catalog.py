"""A block's live catalog ``L``, from the catalog file a verified read printed.

The commands that compare a block's catalog with its declared schema ``D`` (``plan``) take
the catalog as a file: the document ``schema-read <block>`` printed, ended by one line break.
That file crossed the operator's machine, so it is untrusted input. It is read as UTF-8 with no
newline translation, refused unless it is exactly one document of the block's read queries
(:func:`~cruftfree_codegen_sql.schema_tool.read_batch.read_catalog_document`, the same member check
a client run passes), and parsed by the block's engine reader into ``L``. Its SHA-256 is the
fingerprint a plan's guard recomputes on the server before any change runs, so a file edited
to differ from the catalog it claims to be stops the apply there.

``L`` is stamped with ``D``'s own identity (its ``rdbms_id``, service, container, block, schema
and revision): the catalog cannot supply them, and the plan compares the two as one block's.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from cruftfree_common.errors.generation import GenerationError

from cruftfree_codegen_sql.errors import SQLGeneratorError
from cruftfree_codegen_sql.schema_tool.read_batch import (
    BlockDocuments,
    ReadBatch,
    VerifiedRead,
    block_documents,
    read_batch_of,
    read_catalog_document,
)

if TYPE_CHECKING:
    from pathlib import Path

    from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot

#: The encoding a verified read prints its document in.
_DOCUMENT_ENCODING: Final[str] = "utf-8"


class CatalogFileRefused(ValueError):
    """The catalog file cannot be read, or its document is not one the block's reader parses."""


@dataclass(frozen=True)
class DesiredIdentity:
    """The source-side identity a reader stamps onto ``L``: ``D``'s own (``ReflectionIdentity``)."""

    rdbms_id: str
    service_name: str
    service_version: str | None
    container_name: str
    container_kind: str
    block_name: str
    schema_name: str | None

    @classmethod
    def of(cls, desired: RdbmsSchemaSnapshot) -> DesiredIdentity:
        """The identity *desired* (``D``) carries."""
        return cls(
            rdbms_id=desired.rdbms_id,
            service_name=desired.service.name,
            service_version=desired.service.version,
            container_name=desired.container.name,
            container_kind=desired.container.kind,
            block_name=desired.block.name,
            schema_name=desired.schema_name,
        )


@dataclass(frozen=True)
class LiveCatalog:
    """A block's documents, the read its catalog file holds, and ``L`` parsed from it.

    Attributes:
        documents: The block's ``D`` and facts.
        batch: The block's read, whose query names the file's document must hold.
        read: The file's document, its members by query and its fingerprint.
        live: ``L``, the block's engine reader over the document, stamped with ``D``'s identity.
    """

    documents: BlockDocuments
    batch: ReadBatch
    read: VerifiedRead
    live: RdbmsSchemaSnapshot


def _catalog_text(path: Path, block: str) -> str:
    """The text of the catalog file *path*, decoded as UTF-8 with no newline translation."""
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CatalogFileRefused(
            f"The catalog file {path} of block '{block}' could not be read ({error}). Give the "
            f"file 'schema-read {block}' printed."
        ) from error
    try:
        return raw.decode(_DOCUMENT_ENCODING)
    except UnicodeDecodeError as error:
        raise CatalogFileRefused(
            f"The catalog file {path} of block '{block}' is not {_DOCUMENT_ENCODING} ({error}): "
            "it was altered after the read printed it."
        ) from error


def read_live_catalog(tool_dir: Path, block: str, catalog: Path) -> LiveCatalog:
    """*block*'s documents in *tool_dir* and ``L`` from the catalog file *catalog*.

    Raises:
        UnknownBlockError: *block* is not a block key *tool_dir* holds documents for.
        CatalogFileRefused: The file cannot be read, is not UTF-8, or its document is one the
            block's reader refuses (naming the query or the object).
        ReadOutputRefused: The file is not one document of the block's read queries ended by
            one line break.
    """
    documents = block_documents(tool_dir, block)
    batch = read_batch_of(documents)
    read = read_catalog_document(_catalog_text(catalog, block), batch)
    try:
        live = documents.reader.parse_catalog(
            read.documents, DesiredIdentity.of(documents.desired)
        )
    except (SQLGeneratorError, GenerationError, ValueError) as error:
        raise CatalogFileRefused(
            f"The catalog file {catalog} of block '{block}' holds a document its "
            f"{documents.facts.engine} reader refuses: {error}"
        ) from error
    return LiveCatalog(documents=documents, batch=batch, read=read, live=live)
