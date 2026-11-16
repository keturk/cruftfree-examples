"""``schema.py apply-batch`` and ``schema.py apply-verify``: one plan file's apply, and its run checked.

A deploy applies each SQL file ``plan`` wrote under the engine's stock client, on the channel
its platform reads the catalog through, as the block's owner login. ``apply-batch <block> --sql F``
prints the client's input: its opening, then the file byte for byte. It refuses a file that is
not one of the block's plan files, so no DDL runs unguarded: the file must open with the block's
lock guard, then the catalog search path the read set, then the fingerprint guard of the read
it was planned from (re-rendered for the fingerprint the file holds and compared exactly), then
the apply's begin, and end with the
apply's commit, the composed catalog statement and the release guard, each exactly as the
planner renders them (``apply_frame``). A file whose statement map
(``<file>.statements.json``) is missing or describes other bytes is refused too, before the
client runs: a failed apply could not name its statement. An empty file applies nothing, and
the command prints nothing.

``apply-verify <block> --sql F --stdout F --stderr F --exit F`` checks the three files that client
run left, as ``read-verify`` checks a read's. A non-zero exit status is refused naming the block,
the statement the client stopped at and the change it renders (through the statement map), and
whether the schema is as it was. A zero exit status hands the standard output to the read's own
check (``verify_read_output``): the catalog the apply left, printed by the composed catalog
statement with the server's length and digest, inside the apply's session and under the block's
lock. A verified apply prints that catalog's document, ended by a line break, and nothing else,
exactly as ``read-verify`` prints a read's: a deploy plans and verifies the block from it
without reading the catalog again.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from cruftfree_codegen_kernel.sql_facts.convergence import apply_frame
from cruftfree_codegen_kernel.sql_facts.dialects.dialect_statements import (
    session_lock_for,
)
from cruftfree_codegen_kernel.sql_facts.plan_statement_map import (
    PLAN_FILE_ENCODING,
    StatementMapError,
    load_statement_map,
    statement_map_path,
)

from cruftfree_codegen_sql.schema_tool.read_batch import (
    ReadOutputRefused,
    UnknownBlockError,
    block_documents,
    read_batch_of,
    verify_read_output,
)
from cruftfree_codegen_sql.schema_tool.read_verify import (
    ReadFilesRefused,
    decode_output,
    read_exit_status,
    read_run_file,
)
from cruftfree_codegen_sql.schema_tool.tool_files import print_output

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cruftfree_codegen_kernel.sql_facts.convergence import ApplyFrame
    from cruftfree_codegen_kernel.sql_facts.plan_statement_map import StatementMap

    from cruftfree_codegen_sql.schema_tool.read_batch import BlockDocuments

#: The name of the command printing a plan file's apply input, in ``schema.py``'s command table.
BATCH_COMMAND_NAME: Final[str] = "apply-batch"

#: The name of the command checking an apply's client run, in ``schema.py``'s command table.
VERIFY_COMMAND_NAME: Final[str] = "apply-verify"

#: Exit status of an ``apply-batch`` run whose SQL file or statement map is refused.
INPUT_REFUSED_EXIT: Final[int] = 4

#: Exit status of an ``apply-verify`` run whose apply failed, or whose files are not a verified apply.
REFUSED_EXIT: Final[int] = 1

#: The exit status a successful client run leaves.
_CLIENT_SUCCESS: Final[int] = 0

#: Ends every line of a plan file, of the input and of the printed fingerprint.
_LINE_BREAK: Final[str] = "\n"

#: A catalog fingerprint as a plan file's fingerprint guard holds it: 64 lowercase hex digits.
_FINGERPRINT: Final[re.Pattern[str]] = re.compile(
    r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])"
)


class ApplyFileRefused(ValueError):
    """A SQL file or its statement map that is not one of the block's plan files as ``plan`` wrote it."""


@dataclass(frozen=True)
class PlanFileLayout:
    """Where a block's plan file holds its guards, by line numbered from 1.

    Attributes:
        fingerprint: The fingerprint of the read the file was planned from, as its guard checks it.
        first_change: The first line after the guards and the apply's begin: no change of the
            file runs before it.
        last_committed: The last line of the apply's commit: a failure up to it rolls back every
            change of the file.
        lines: How many lines the file holds.
    """

    fingerprint: str
    first_change: int
    last_committed: int
    lines: int


@dataclass(frozen=True)
class PlanFile:
    """A block's plan file as an apply runs it.

    Attributes:
        path: Where the file lies.
        sql: Its bytes, which the client receives after its opening.
        layout: Where its guards lie.
        statements: Its statement map, which describes exactly *sql*.
        commits: The last line of each of the file's commits, in order: one per transaction.
            A file adding an enum label its dialect makes usable only once committed commits
            the label additions first, so a later failure leaves them committed.
    """

    path: Path
    sql: bytes
    layout: PlanFileLayout
    statements: StatementMap
    commits: tuple[int, ...]


@dataclass(frozen=True)
class ApplyRun:
    """The three files an apply's client run left, read before any of them is judged.

    Attributes:
        status: The client's exit status.
        stdout: Its standard output, as the bytes it printed.
        stderr: Its standard error, a byte that is not UTF-8 shown as the replacement character.
        stdout_path: Where the standard output was read from.
    """

    status: int
    stdout: bytes
    stderr: str
    stdout_path: Path


def _statements_text(*statements: str) -> str:
    """*statements* as a plan file holds them: each followed by a line break."""
    return "".join(f"{statement}{_LINE_BREAK}" for statement in statements)


def _line_count(text: str) -> int:
    return text.count(_LINE_BREAK)


def read_plan_bytes(path: Path, what: str, block: str) -> bytes:
    """The bytes of *path*, *block*'s plan *what*, refused naming it when it cannot be read.

    Raises:
        ApplyFileRefused: The file is missing or unreadable.
    """
    try:
        return path.read_bytes()
    except OSError as error:
        raise ApplyFileRefused(
            f"The {what} {path} of block '{block}' could not be read ({error}). Give the SQL file "
            "'schema.py plan' wrote for the block, with its statement map beside it."
        ) from error


def _decoded(sql: bytes, path: Path, block: str) -> str:
    """*sql* as text, refused unless it is UTF-8 ended by a line break, as ``plan`` writes it."""
    try:
        text = sql.decode(PLAN_FILE_ENCODING)
    except UnicodeDecodeError as error:
        raise ApplyFileRefused(
            f"The SQL file {path} of block '{block}' is not {PLAN_FILE_ENCODING} ({error}): it is "
            "not a file 'schema.py plan' wrote."
        ) from error
    if not text.endswith(_LINE_BREAK):
        raise ApplyFileRefused(
            f"The SQL file {path} of block '{block}' does not end with a line break: the file was "
            "cut. Give the file 'schema.py plan' wrote, byte for byte."
        )
    return text


def _require_closing(text: str, where: str, frame: ApplyFrame, commit: str) -> None:
    """Refuse *text* unless it ends with the apply's commit, the catalog statement and the release guard."""
    catalog, release = (statement.sql for statement in frame.closing)
    endings = (
        (_statements_text(release), "does not end with the block's release guard"),
        (
            _statements_text(catalog, release),
            "does not run the composed catalog statement just before its release guard",
        ),
        (
            _statements_text(commit, catalog, release),
            "does not commit its changes just before the composed catalog statement",
        ),
    )
    for ending, cause in endings:
        if not text.endswith(ending):
            raise ApplyFileRefused(
                f"{where} {cause}: it is not one of the block's plan files. Apply only a file "
                "'schema.py plan' wrote for this block, unaltered."
            )


def plan_file_layout(
    text: str, path: Path, documents: BlockDocuments
) -> PlanFileLayout:
    """Where the guards of *text*, one of *documents*' block's plan files, lie.

    The guards are re-rendered from the block's documents as the planner renders them
    (``apply_frame``): the lock guard keyed by the block's ``rdbms_id``, the catalog search
    path, and the fingerprint guard for each fingerprint *text* holds, compared exactly, so a
    file of another block, a file with a statement before its guards and an altered guard are
    refused.

    Raises:
        ApplyFileRefused: *text* does not open with the lock guard, the search path, the
            fingerprint guard of a fingerprint it holds and the apply's begin, does not end
            with the apply's commit,
            the catalog statement and the release guard, or holds no change between them.
    """
    block = documents.block
    where = f"The SQL file {path} of block '{block}'"
    rdbms_id = documents.desired.rdbms_id
    dialect = documents.dialect
    lock = session_lock_for(dialect, rdbms_id)
    frames = {
        fingerprint: apply_frame(
            rdbms_id, fingerprint, lock, dialect, documents.catalog_queries
        )
        for fingerprint in dict.fromkeys(_FINGERPRINT.findall(text))
    }
    if not frames:
        raise ApplyFileRefused(
            f"{where} holds no catalog fingerprint, so it does not open with a fingerprint guard: "
            "it is not one of the block's plan files. Apply only a file 'schema.py plan' wrote."
        )
    any_frame = next(iter(frames.values()))
    lock_text = _statements_text(any_frame.opening[0].sql)
    if not text.startswith(lock_text):
        raise ApplyFileRefused(
            f"{where} does not open with the block's lock guard: it is another block's plan file, "
            "or one altered. Apply only a file 'schema.py plan' wrote for this block, unaltered."
        )
    commit = dialect.apply_commit_sql()
    _require_closing(text, where, any_frame, commit)
    after_commit = _statements_text(*(statement.sql for statement in any_frame.closing))
    closing = _statements_text(commit) + after_commit
    begin = _statements_text(dialect.apply_begin_sql())
    for fingerprint, frame in frames.items():
        opening = (
            _statements_text(*(statement.sql for statement in frame.opening)) + begin
        )
        if not text.startswith(opening):
            continue
        if len(opening) + len(closing) >= len(text):
            raise ApplyFileRefused(
                f"{where} holds no change between its guards and its commit: 'schema.py plan' "
                "writes an empty file for a phase that applies nothing."
            )
        return PlanFileLayout(
            fingerprint=fingerprint,
            first_change=_line_count(opening) + 1,
            last_committed=_line_count(text) - _line_count(after_commit),
            lines=_line_count(text),
        )
    raise ApplyFileRefused(
        f"{where} does not follow its lock guard with the block's search path, fingerprint "
        "guard and the apply's begin: a statement precedes the guard, or the guard was altered. "
        "Apply only a "
        "file 'schema.py plan' wrote for this block, unaltered."
    )


def checked_plan_file(path: Path, sql: bytes, documents: BlockDocuments) -> PlanFile:
    """*sql*, read from *path*, as one of *documents*' block's plan files, with its statement map.

    Raises:
        ApplyFileRefused: *sql* is not one of the block's plan files (:func:`plan_file_layout`),
            or its statement map is missing or does not describe exactly *sql*.
    """
    block = documents.block
    layout = plan_file_layout(_decoded(sql, path, block), path, documents)
    map_path = statement_map_path(path)
    document = read_plan_bytes(map_path, "statement map", block)
    try:
        statements = load_statement_map(document, sql)
    except StatementMapError as error:
        raise ApplyFileRefused(
            f"The statement map {map_path} of block '{block}' does not describe the SQL file "
            f"{path} ({error}). Give the SQL file and the map 'schema.py plan' wrote beside it, "
            "both unaltered."
        ) from error
    commits = _commit_lines(
        _decoded(sql, path, block), statements, documents.dialect.apply_commit_sql()
    )
    return PlanFile(
        path=path, sql=sql, layout=layout, statements=statements, commits=commits
    )


def _commit_lines(text: str, statements: StatementMap, commit: str) -> tuple[int, ...]:
    """The last line of each statement of *statements* that is the apply's *commit*, in order.

    A commit belongs to no change, and its lines hold exactly the dialect's commit.
    """
    lines = text.split(_LINE_BREAK)
    return tuple(
        statement.last_line
        for statement in statements.statements
        if statement.change_kind is None
        and _LINE_BREAK.join(lines[statement.first_line - 1 : statement.last_line])
        == commit
    )


def _consequence(line: int, plan_file: PlanFile) -> str:
    """What a failure at *line* of *plan_file* left of the schema."""
    layout = plan_file.layout
    if line < layout.first_change:
        return (
            "No change ran and the schema is as it was. Run the deploy again: it reads the "
            "catalog and plans from it anew."
        )
    committed = [commit for commit in plan_file.commits if commit < line]
    if line <= layout.last_committed and committed:
        return (
            f"The file's enum label additions, up to line {committed[-1]}, were committed in a "
            "transaction of their own, since a new label is usable only once committed; the "
            "transaction holding this line rolled back, so no other change of the file took "
            "effect. The next deploy plans again from the catalog, which holds the labels."
        )
    if line <= layout.last_committed:
        return (
            "The transaction rolled back, so no change of the file took effect and the schema "
            "is as it was; the next deploy plans again from the unchanged catalog."
        )
    return (
        "The file's changes were committed before it, but the catalog the apply left was not "
        "verified; read the catalog again before planning."
    )


def name_failed_apply(
    stderr: str, plan_file: PlanFile, documents: BlockDocuments
) -> str:
    """A message naming the block, the statement a failed apply of *plan_file* stopped at and its change.

    The client's input is its opening, then the file, so the input line its first error names
    (``CatalogClient.failed_line``) is the file's line after the opening's lines; the statement
    map names the statement that line belongs to and the change it renders. The client's own
    error text follows.
    """
    block = documents.block
    client = documents.dialect.catalog_client()
    reported = stderr.strip()
    line = client.failed_line(stderr)
    if not reported and line is None:
        return (
            f"The apply of block '{block}' ended without an error naming a statement of "
            f"{plan_file.path}: the client printed no error and may have been stopped at its time "
            "limit. The file's changes run in one transaction, or in two when it adds enum "
            "labels, and each took effect together or not at all; read the catalog again "
            "before planning."
        )
    opening = _line_count(client.opening) + 1
    if line is None or line <= opening:
        return (
            f"The apply of block '{block}' failed before any statement of {plan_file.path} ran; "
            f"the schema is as it was: {reported}"
        )
    file_line = line - opening
    statement = plan_file.statements.statement_at(file_line)
    if statement is None:
        return (
            f"The apply of block '{block}' failed at input line {line}, past the "
            f"{plan_file.layout.lines} lines of {plan_file.path}: {reported}"
        )
    change = (
        "" if statement.change_kind is None else f", a {statement.change_kind} change"
    )
    return (
        f"The apply of block '{block}' stopped at {statement.owner}{change} (line {file_line} "
        f"of {plan_file.path}, input line {line}). {_consequence(file_line, plan_file)} "
        f"Client error: {reported}"
    )


def read_apply_run(stdout: Path, stderr: Path, exit_status: Path) -> ApplyRun:
    """The three files an apply's client run left, every one read before any is judged.

    Raises:
        ReadFilesRefused: A file is missing, or the exit status file holds anything but one number.
    """
    status = read_exit_status(exit_status)
    error = read_run_file(stderr, "standard error").decode(
        PLAN_FILE_ENCODING, errors="replace"
    )
    output = read_run_file(stdout, "standard output")
    return ApplyRun(status=status, stdout=output, stderr=error, stdout_path=stdout)


def verified_apply(
    run: ApplyRun, plan_file: PlanFile, documents: BlockDocuments
) -> str:
    """The document of the catalog *run*, an apply of *plan_file*, left: its verified output's document.

    The standard output of a failed run is never decoded, so its bytes cannot hide the
    statement the run stopped at.

    Raises:
        ReadOutputRefused: The client exited non-zero (the message names the block, the
            statement and its change, and the exit status), or its output is not the catalog
            statement's one verified row.
        ReadFilesRefused: The standard output is not UTF-8.
    """
    if run.status != _CLIENT_SUCCESS:
        raise ReadOutputRefused(
            f"{name_failed_apply(run.stderr, plan_file, documents)} (client exit status {run.status})"
        )
    output = decode_output(run.stdout, run.stdout_path)
    try:
        return verify_read_output(output, read_batch_of(documents)).document
    except ReadOutputRefused as error:
        raise ReadOutputRefused(
            f"The apply of block '{documents.block}' exited 0, so its changes were committed, but "
            f"its output is not the catalog statement's verified row: {error}"
        ) from error


def _documents(
    parser: argparse.ArgumentParser, tool_dir: Path, block: str
) -> BlockDocuments:
    """*block*'s documents; a block *tool_dir* holds none for exits 2 naming the known blocks."""
    try:
        return block_documents(tool_dir, block)
    except UnknownBlockError as error:
        parser.error(str(error))


def _block_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "block", help="The block key, as named under desired/ and facts/."
    )
    parser.add_argument(
        "--sql",
        required=True,
        help="A SQL file 'schema.py plan' wrote for the block; its statement map lies beside it.",
    )


def _batch_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"schema.py {BATCH_COMMAND_NAME}",
        description=(
            "Print the input a stock client runs to apply a plan file to an RDBMS block: the "
            "client's opening, then the file. Prints nothing for an empty file."
        ),
    )
    _block_argument(parser)
    return parser


def _verify_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"schema.py {VERIFY_COMMAND_NAME}",
        description=(
            "Check the files a client run of apply-batch's input left, and print the verified "
            "document of the catalog the apply left."
        ),
    )
    _block_argument(parser)
    parser.add_argument(
        "--stdout", required=True, help="The file holding the client's standard output."
    )
    parser.add_argument(
        "--stderr", required=True, help="The file holding the client's standard error."
    )
    parser.add_argument(
        "--exit", required=True, help="The file holding the client's exit status."
    )
    return parser


def run_batch(argv: Sequence[str], tool_dir: Path) -> int:
    """Print the apply input of *argv*'s plan file, or refuse the file on standard error.

    The output is the client's opening and the file's bytes, nothing translated
    (``print_output``). An empty file prints nothing and exits 0. A block *tool_dir* holds no
    documents for exits 2 (argparse's usage exit); a refused file exits :data:`INPUT_REFUSED_EXIT`.
    """
    parser = _batch_parser()
    arguments = parser.parse_args(list(argv))
    documents = _documents(parser, tool_dir, str(arguments.block))
    path = Path(arguments.sql)
    try:
        sql = read_plan_bytes(path, "SQL file", documents.block)
        if not sql:
            return 0
        checked_plan_file(path, sql, documents)
    except ApplyFileRefused as error:
        print(f"schema.py {BATCH_COMMAND_NAME}: {error}", file=sys.stderr)
        return INPUT_REFUSED_EXIT
    opening = documents.dialect.catalog_client().opening
    print_output(f"{opening}{_LINE_BREAK}{sql.decode(PLAN_FILE_ENCODING)}")
    return 0


def run_verify(argv: Sequence[str], tool_dir: Path) -> int:
    """Print the document of the catalog *argv*'s apply left, or refuse its files on standard error.

    The document goes to standard output as its UTF-8 bytes, ended by a line break, as
    ``read-verify`` prints a read's (``print_output``).

    The run's three files are read first, then the plan file and its statement map. A block
    *tool_dir* holds no documents for exits 2 (argparse's usage exit); a failed apply, an empty
    or refused plan file, and files that are not a verified apply exit :data:`REFUSED_EXIT`,
    naming why.
    """
    parser = _verify_parser()
    arguments = parser.parse_args(list(argv))
    documents = _documents(parser, tool_dir, str(arguments.block))
    path = Path(arguments.sql)
    try:
        run = read_apply_run(
            Path(arguments.stdout), Path(arguments.stderr), Path(arguments.exit)
        )
        sql = read_plan_bytes(path, "SQL file", documents.block)
        if not sql:
            raise ApplyFileRefused(
                f"The SQL file {path} of block '{documents.block}' is empty: it applies nothing, "
                "so no client runs it and there is no run to verify."
            )
        document = verified_apply(
            run, checked_plan_file(path, sql, documents), documents
        )
    except (ApplyFileRefused, ReadFilesRefused, ReadOutputRefused) as error:
        print(f"schema.py {VERIFY_COMMAND_NAME}: {error}", file=sys.stderr)
        return REFUSED_EXIT
    print_output(f"{document}{_LINE_BREAK}")
    return 0
