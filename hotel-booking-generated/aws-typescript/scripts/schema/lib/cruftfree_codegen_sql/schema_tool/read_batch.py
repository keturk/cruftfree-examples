"""``schema.py read-batch <block>``: the input of one consistent read of a block's catalog.

The command prints everything a stock client needs to read the block's catalog in one state,
one statement after another: the client's opening, the block's lock taken under a guard, the
running server's version checked against the engine's minimum under a guard, the session's
search path set to the places the queries read (so the names the catalog prints are spelled
the same whatever path the connecting role defaults to), a read-only snapshot transaction
around the one statement composing every catalog query of the block's engine, its commit,
and the lock released under a guard. Every statement comes from the block's SQL dialect and
every query from its engine's catalog reader. The composed statement holds no place: the
places travel as one client argument, which ``read-batch <block> --places`` prints; the
search path names them as quoted identifiers.

:func:`verify_read_output` checks what the client printed against the length and SHA-256 the
server computed over the same document, and :func:`name_failed_statement` names the statement
a failed run stopped at, from the input line the client's error names.
:func:`read_catalog_document` reads back the document a verified read printed, as the commands
planning from a read take it, through the same check of its members.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from cruftfree_codegen_kernel.sql_facts.dialects.dialect_table import sql_dialect
from cruftfree_rdbms_schema.block_facts import decode_block_facts
from cruftfree_rdbms_schema.schema_snapshot import deserialize_snapshot

from cruftfree_codegen_sql.dialects.reflector_registry import get_reflector
from cruftfree_codegen_sql.schema_tool.tool_files import (
    BLOCK_DOCUMENT_SUFFIX,
    DESIRED_DIR_NAME,
    FACTS_DIR_NAME,
    block_document_name,
    print_output,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from cruftfree_codegen_kernel.sql_facts.dialects.base import SQLDialect
    from cruftfree_codegen_kernel.sql_facts.dialects.catalog_read import CatalogClient
    from cruftfree_rdbms_schema._snapshot_models import RdbmsSchemaSnapshot
    from cruftfree_rdbms_schema.block_facts import BlockFacts
    from cruftfree_rdbms_schema.catalog_reader import CatalogQuery, CatalogReader

#: The command's name in ``schema.py``'s command table.
COMMAND_NAME: Final[str] = "read-batch"

#: The fields the server prints after the document: its length, then its SHA-256.
_TRAILING_FIELDS: Final[int] = 2

#: Ends every input line and the one row the read prints.
_LINE_BREAK: Final[str] = "\n"

#: The encoding the server's digest is computed over (``convert_to(doc, 'UTF8')``).
_DOCUMENT_ENCODING: Final[str] = "utf-8"

_OPENING_STATEMENT: Final[str] = "the client's opening"
_BEGIN_STATEMENT: Final[str] = "the begin of the read-only transaction"
_DOCUMENT_STATEMENT: Final[str] = "the composed catalog statement"
_COMMIT_STATEMENT: Final[str] = "the commit of the read-only transaction"


class UnknownBlockError(ValueError):
    """A block key the schema tool holds no documents for."""


class ReadOutputRefused(ValueError):
    """What a catalog read printed is not one verified document of the read's queries."""


@dataclass(frozen=True)
class ReadBatch:
    """The input of one consistent catalog read of a block, and what checks its run.

    Attributes:
        block: The block key the read is of.
        lines: The input, one element per line, in the order the client runs it.
        line_statements: Per input line, in the same order, the statement it belongs to;
            a statement spanning several lines names each of them.
        query_names: The composed statement's members, in the order its document holds them.
        places: The places the queries read, bound as the composed statement's parameter.
        client: The stock client that runs the input.
    """

    block: str
    lines: tuple[str, ...]
    line_statements: tuple[str, ...]
    query_names: tuple[str, ...]
    places: tuple[str, ...]
    client: CatalogClient

    @property
    def text(self) -> str:
        """The input as the client reads it: every line, each ended by a line break."""
        return "".join(f"{line}{_LINE_BREAK}" for line in self.lines)

    @property
    def places_option(self) -> tuple[str, str]:
        """The two client arguments that set the places variable to :attr:`places`."""
        return self.client.places_option(self.places)

    def statement_at(self, line: int) -> str | None:
        """The statement input line *line* (numbered from 1) belongs to, or ``None`` past the input."""
        if 1 <= line <= len(self.line_statements):
            return self.line_statements[line - 1]
        return None


@dataclass(frozen=True)
class VerifiedRead:
    """The document a catalog read printed, checked against the server's length and digest.

    Attributes:
        document: The composed statement's document, as the server built it.
        digest: Its SHA-256, hex: the catalog fingerprint of the read.
        documents: Each query's document, keyed by query name, as ``parse_catalog`` reads them.
    """

    document: str
    digest: str
    documents: Mapping[str, str]


def lock_guard(block: str) -> str:
    """The error the lock guard raises when another session holds *block*'s lock."""
    return (
        f"The catalog of block '{block}' is being read or changed by another session, "
        "which holds the block's lock. The read did not start; run it again once that "
        "session has finished."
    )


def server_guard(block: str, engine: str, minimum: int) -> str:
    """The error the server guard raises when the running server is older than *minimum*.

    The server appends its running version's text, so the message ends naming it.
    """
    return (
        f"The catalog of block '{block}' is read only from a {engine} server whose version "
        f"number is {minimum} or later, the oldest that holds every object kind the read "
        "reads. The read did not start; this server's version is "
    )


def release_guard(block: str) -> str:
    """The error the release guard raises when the reading session did not hold *block*'s lock."""
    return (
        f"The read of block '{block}' did not hold the block's lock when it released it, "
        "so it is not known to be consistent. Run the read again."
    )


def known_blocks(tool_dir: Path) -> frozenset[str]:
    """The block keys *tool_dir* holds a desired snapshot for, under ``desired/``."""
    return frozenset(
        path.name.removesuffix(BLOCK_DOCUMENT_SUFFIX)
        for path in (tool_dir / DESIRED_DIR_NAME).iterdir()
        if path.is_file() and path.name.endswith(BLOCK_DOCUMENT_SUFFIX)
    )


def _statement_lines(statement: str, sql: str) -> list[tuple[str, str]]:
    """Every line of *sql*, each paired with the *statement* it belongs to."""
    return [(line, statement) for line in sql.split(_LINE_BREAK)]


@dataclass(frozen=True)
class BlockDocuments:
    """A block's documents as the schema tool holds them, and what they name.

    Attributes:
        block: The block key.
        desired: ``D``, the block's schema snapshot, from ``desired/<block>.json``.
        facts: The block's engine facts, from ``facts/<block>.json``.
    """

    block: str
    desired: RdbmsSchemaSnapshot
    facts: BlockFacts

    @property
    def dialect(self) -> SQLDialect:
        """The block's SQL dialect, by the DDL dialect its facts name."""
        return sql_dialect(self.facts.ddl_dialect)

    @property
    def reader(self) -> CatalogReader:
        """The catalog reader of the block's engine."""
        return get_reflector(self.facts.engine)

    @property
    def catalog_queries(self) -> tuple[CatalogQuery, ...]:
        """Every catalog query of the block's engine, bound to the schema ``D`` places it in."""
        return self.reader.catalog_queries(self.desired.schema_name)


def block_documents(tool_dir: Path, block: str) -> BlockDocuments:
    """*block*'s desired snapshot and facts, from the documents in *tool_dir*.

    Raises:
        UnknownBlockError: *block* is not a block key *tool_dir* holds documents for; the
            message names the known keys. *block* is only ever compared with them, never
            joined into a path before it matched one.
        ValueError: The desired snapshot does not decode.
        GenerationError: The facts document does not decode.
    """
    known = known_blocks(tool_dir)
    if block not in known:
        raise UnknownBlockError(
            f"No RDBMS block '{block}' in {tool_dir}. Known blocks: "
            f"{', '.join(sorted(known)) or 'none'}. Give one of them, as the generator "
            f"named its documents under '{DESIRED_DIR_NAME}/'."
        )
    name = block_document_name(block)
    return BlockDocuments(
        block=block,
        desired=deserialize_snapshot((tool_dir / DESIRED_DIR_NAME / name).read_text(encoding="utf-8")),
        facts=decode_block_facts((tool_dir / FACTS_DIR_NAME / name).read_text(encoding="utf-8")),
    )


def build_read_batch(tool_dir: Path, block: str) -> ReadBatch:
    """The input of one consistent read of *block*'s catalog, from the documents in *tool_dir*.

    Raises:
        UnknownBlockError: *block* is not a block key *tool_dir* holds documents for.
        ValueError: A document does not decode, the engine has no catalog reader, or the
            queries do not compose (``catalog_read_queries``).
        GenerationError: The facts document does not decode.
        DialectFeatureError: The block's dialect spells no consistent catalog read.
    """
    return read_batch_of(block_documents(tool_dir, block))


def read_batch_of(documents: BlockDocuments) -> ReadBatch:
    """The input of one consistent read of the catalog of *documents*' block.

    The block's schema and ``rdbms_id`` come from its desired snapshot, its engine, DDL
    dialect and minimum server version from its facts. The lock is the block's session
    lock, keyed by its ``rdbms_id``; the server guard refuses a server older than the
    minimum, naming its running version; the search path is the queries' places, as an
    apply's frame sets it, so the document's digest is the one the apply's fingerprint
    guard recomputes; the queries are every catalog query of the engine's reader, bound to
    the block's schema.

    Raises:
        ValueError: The engine has no catalog reader, or the queries do not compose
            (``catalog_read_queries``).
        DialectFeatureError: The block's dialect spells no consistent catalog read.
    """
    block = documents.block
    snapshot = documents.desired
    facts = documents.facts
    dialect = documents.dialect
    client = dialect.catalog_client()
    queries = documents.catalog_queries
    lock = dialect.session_lock_sql(str(snapshot.rdbms_id))
    server = dialect.server_version_sql()
    minimum = facts.minimum_server_version
    document_sql = dialect.catalog_document_sql(queries)
    numbered = [
        (client.opening, _OPENING_STATEMENT),
        *_statement_lines(
            f"the lock guard of block '{block}'",
            dialect.abort_unless_sql(lock.try_acquire_condition, lock_guard(block)),
        ),
        *_statement_lines(
            f"the server guard of block '{block}'",
            dialect.abort_unless_sql(
                server.at_least(minimum),
                server_guard(block, facts.engine, minimum),
                reported=server.text,
            ),
        ),
        *_statement_lines(
            f"the search path of block '{block}'", dialect.catalog_search_path_sql(queries)
        ),
        *_statement_lines(_BEGIN_STATEMENT, dialect.catalog_read_begin_sql()),
        *_statement_lines(_DOCUMENT_STATEMENT, document_sql),
        *_statement_lines(_COMMIT_STATEMENT, dialect.catalog_read_commit_sql()),
        *_statement_lines(
            f"the release guard of block '{block}'",
            dialect.abort_unless_sql(lock.release_condition, release_guard(block)),
        ),
    ]
    return ReadBatch(
        block=block,
        lines=tuple(line for line, _ in numbered),
        line_statements=tuple(statement for _, statement in numbered),
        query_names=tuple(sorted(query.name for query in queries)),
        places=queries[0].places,
        client=client,
    )


def _unique_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """A JSON object's members, refusing a member name given twice."""
    names = [name for name, _ in pairs]
    repeated = sorted({name for name in names if names.count(name) > 1})
    if repeated:
        raise ReadOutputRefused(
            f"The catalog document names the member(s) {repeated} more than once. Each "
            "query is one member of the document; the output is not the read's."
        )
    return dict(pairs)


def _document_members(document: str) -> dict[str, object]:
    """The members of the composed document, in the order it holds them."""
    try:
        parsed: object = json.loads(document, object_pairs_hook=_unique_members)
    except json.JSONDecodeError as error:
        raise ReadOutputRefused(
            f"The catalog document is not JSON ({error}): it is not a document the composed "
            "statement prints."
        ) from error
    if not isinstance(parsed, dict):
        raise ReadOutputRefused(
            f"The catalog document is a JSON {type(parsed).__name__}, not an object of "
            "one member per query."
        )
    return parsed


def verify_read_output(stdout: str, batch: ReadBatch) -> VerifiedRead:
    """The document the client printed for *batch*, refused unless it is exactly what the server sent.

    The read prints one row, ended by a line break: the document, then its length and its
    SHA-256 as the server computed them in the same statement, separated by the client's
    field separator. The document may itself hold line breaks and separators, so the two
    trailing fields are split from the right. The length and digest are recomputed over
    the document and must both equal the server's, and the document's members must be
    exactly the read's query names in order: a cut, an altered character or a second row
    is refused.

    Raises:
        ReadOutputRefused: Any of these differs; the message names what.
    """
    if not stdout.endswith(_LINE_BREAK):
        raise ReadOutputRefused(
            f"The catalog read of block '{batch.block}' printed {len(stdout)} characters "
            "with no line break at the end: the output was cut. Expected one row ended "
            "by a line break."
        )
    fields = stdout.removesuffix(_LINE_BREAK).rsplit(batch.client.field_separator, _TRAILING_FIELDS)
    if len(fields) != _TRAILING_FIELDS + 1:
        raise ReadOutputRefused(
            f"The catalog read of block '{batch.block}' printed a row of {len(fields)} "
            f"field(s); expected the document, its length and its SHA-256, separated by "
            f"{batch.client.field_separator!r}."
        )
    document, length_field, digest = fields
    if not (length_field.isascii() and length_field.isdigit()) or int(length_field) != len(document):
        raise ReadOutputRefused(
            f"The catalog document of block '{batch.block}' is {len(document)} characters, "
            f"but the server counted {length_field!r}: the output was cut, altered, or holds "
            "more than the one row the read prints."
        )
    recomputed = hashlib.sha256(document.encode(_DOCUMENT_ENCODING)).hexdigest()
    if recomputed != digest:
        raise ReadOutputRefused(
            f"The catalog document of block '{batch.block}' hashes to {recomputed}, but the "
            f"server's SHA-256 is {digest!r}: the output was altered in transfer."
        )
    return _verified_read(document, digest, batch)


def read_catalog_document(text: str, batch: ReadBatch) -> VerifiedRead:
    """The document a verified read of *batch*'s block printed, read back from *text*.

    A verified read (``read-verify``, ``schema-read``) prints the composed document ended by
    one line break, and nothing else; *text* is refused unless it is exactly that, so a cut
    file, a second line break or a line ending translated to ``\\r\\n`` is refused. The
    document's members must be exactly the read's query names in order, checked as a client
    run's are (:func:`verify_read_output`). Its SHA-256 is recomputed as the read's
    fingerprint, which a plan's fingerprint guard checks against the server again.

    Raises:
        ReadOutputRefused: *text* is not one document of the read's queries ended by one
            line break; the message names what.
    """
    if not text.endswith(_LINE_BREAK):
        raise ReadOutputRefused(
            f"The catalog document of block '{batch.block}' is {len(text)} characters with no "
            "line break at the end: the file was cut. Expected the document a verified read "
            "printed, ended by one line break."
        )
    document = text.removesuffix(_LINE_BREAK)
    if document.endswith(("\n", "\r")):
        raise ReadOutputRefused(
            f"The catalog document of block '{batch.block}' ends with more than one line "
            "break, or with a line ending translated to '\\r\\n': it is not the document a "
            "verified read printed. Hand over the read's output byte for byte."
        )
    digest = hashlib.sha256(document.encode(_DOCUMENT_ENCODING)).hexdigest()
    return _verified_read(document, digest, batch)


def _verified_read(document: str, digest: str, batch: ReadBatch) -> VerifiedRead:
    """*document* with its *digest*, refused unless its members are exactly *batch*'s query names in order."""
    members = _document_members(document)
    if tuple(members) != batch.query_names:
        raise ReadOutputRefused(
            f"The catalog document of block '{batch.block}' holds the members "
            f"{list(members)}; expected exactly the read's queries {list(batch.query_names)}, "
            "in that order."
        )
    return VerifiedRead(
        document=document,
        digest=digest,
        documents={name: json.dumps(value) for name, value in members.items()},
    )


def name_failed_statement(stderr: str, batch: ReadBatch) -> str:
    """A message naming the statement of *batch* a failed client run stopped at.

    The statement is found by the input line the client's first error names
    (``CatalogClient.failed_line``); a failure before any input line ran (the client
    could not connect) is named as such. The client's own error text follows.
    """
    reported = stderr.strip() or "the client printed no error"
    line = batch.client.failed_line(stderr)
    if line is None:
        return (
            f"The catalog read of block '{batch.block}' failed before any input line ran: "
            f"{reported}"
        )
    statement = batch.statement_at(line)
    if statement is None:
        return (
            f"The catalog read of block '{batch.block}' failed at input line {line}, past "
            f"the {len(batch.lines)} lines of its input: {reported}"
        )
    return (
        f"The catalog read of block '{batch.block}' stopped at {statement} "
        f"(input line {line}): {reported}"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"schema.py {COMMAND_NAME}",
        description=(
            "Print the input a stock client runs to read an RDBMS block's catalog in one "
            "consistent state, under the block's lock."
        ),
    )
    parser.add_argument("block", help="The block key, as named under desired/ and facts/.")
    parser.add_argument(
        "--places",
        action="store_true",
        help=(
            "Print the client arguments that set the places variable, one per line, instead "
            "of the input."
        ),
    )
    return parser


def run(argv: Sequence[str], tool_dir: Path) -> int:
    """Print *argv*'s block's read input, or with ``--places`` its places arguments, one per line.

    The output is the text's UTF-8 bytes, nothing translated (``print_output``). A block
    *tool_dir* holds no documents for exits 2 (argparse's usage exit), naming the known blocks.
    """
    parser = _parser()
    arguments = parser.parse_args(list(argv))
    try:
        batch = build_read_batch(tool_dir, str(arguments.block))
    except UnknownBlockError as error:
        parser.error(str(error))
    if arguments.places:
        print_output("".join(f"{argument}{_LINE_BREAK}" for argument in batch.places_option))
    else:
        print_output(batch.text)
    return 0
