"""``schema.py read-verify <block>``: what a catalog read's client run printed, checked.

A deploy script runs the input ``read-batch <block>`` prints under the engine's stock client
on its platform's channel, and hands the three files that run left to this command: the
client's standard output, its standard error and its exit status. The script never inspects
or edits them. The command refuses a non-zero exit status, naming the statement the client
stopped at (a guard's error names the guard and the block), and any standard output but one
row whose length and SHA-256 equal the server's (:func:`read_batch.verify_read_output`). A
verified read prints the composed catalog document on standard output as its UTF-8 bytes, ended
by a line break, and nothing else.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from cruftfree_codegen_sql.schema_tool.read_batch import (
    ReadOutputRefused,
    UnknownBlockError,
    build_read_batch,
    name_failed_statement,
    verify_read_output,
)
from cruftfree_codegen_sql.schema_tool.tool_files import print_output

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cruftfree_codegen_sql.schema_tool.read_batch import ReadBatch

#: The command's name in ``schema.py``'s command table.
COMMAND_NAME: Final[str] = "read-verify"

#: Exit status of a run whose client failed, or whose files are not a verified read.
REFUSED_EXIT: Final[int] = 1

#: The exit status a successful client run leaves.
_CLIENT_SUCCESS: Final[int] = 0

#: Ends the exit status file's one line and the printed document.
_LINE_BREAK: Final[str] = "\n"

#: The encoding the client prints in, and the server's digest is computed over.
_OUTPUT_ENCODING: Final[str] = "utf-8"


class ReadFilesRefused(ValueError):
    """A file a client run left is missing, unreadable, or not what the client writes."""


def read_run_file(path: Path, what: str) -> bytes:
    """The bytes of *path*, the run's *what* file, refused naming it when it cannot be read."""
    try:
        return path.read_bytes()
    except OSError as error:
        raise ReadFilesRefused(
            f"The client run's {what} file {path} could not be read ({error}). The channel "
            "did not bring back every file of the run."
        ) from error


def read_exit_status(path: Path) -> int:
    """The exit status the client run left in *path*: one decimal number, optionally ended by a line break.

    Raises:
        ReadFilesRefused: The file is missing, or holds anything but the one number.
    """
    raw = read_run_file(path, "exit status")
    text = raw.decode("ascii", errors="replace").removesuffix(_LINE_BREAK)
    if not (raw.isascii() and text.isdigit()):
        raise ReadFilesRefused(
            f"The client run's exit status file {path} holds {raw[:40]!r}; expected one "
            "decimal exit status, optionally ended by a line break. The file was cut or altered "
            "in transfer."
        )
    return int(text)


def decode_output(raw: bytes, path: Path) -> str:
    """The client's standard output *raw*, read from *path*, decoded as the server's digest was computed.

    The bytes are decoded without newline translation, so a changed line ending is a changed
    document that :func:`verify_read_output` refuses.

    Raises:
        ReadFilesRefused: *raw* is not valid UTF-8.
    """
    try:
        return raw.decode(_OUTPUT_ENCODING)
    except UnicodeDecodeError as error:
        raise ReadFilesRefused(
            f"The client run's standard output file {path} is not {_OUTPUT_ENCODING} ({error}): "
            "the output was altered in transfer."
        ) from error


def verified_document(batch: ReadBatch, stdout: Path, stderr: Path, exit_status: Path) -> str:
    """The catalog document *batch*'s client run printed, from the three files it left.

    Every file is read before any is judged, so a run the channel did not bring back whole
    is refused whatever its exit status. The standard error is never verified, only quoted
    in the refusal of a failed run: a byte that is not UTF-8 is shown as the replacement
    character rather than hiding the client's error. The standard output of a failed run is
    never decoded, so its bytes cannot hide the statement the run stopped at.

    Raises:
        ReadFilesRefused: A file is missing or not what the client writes.
        ReadOutputRefused: The client exited non-zero (the message names the statement it
            stopped at and its exit status), or its output is not one verified row.
    """
    status = read_exit_status(exit_status)
    error = read_run_file(stderr, "standard error").decode(_OUTPUT_ENCODING, errors="replace")
    output = read_run_file(stdout, "standard output")
    if status != _CLIENT_SUCCESS:
        raise ReadOutputRefused(f"{name_failed_statement(error, batch)} (client exit status {status})")
    return verify_read_output(decode_output(output, stdout), batch).document


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"schema.py {COMMAND_NAME}",
        description=(
            "Check the files a client run of read-batch's input left, and print the verified "
            "catalog document."
        ),
    )
    parser.add_argument("block", help="The block key the read was of, as named under desired/ and facts/.")
    parser.add_argument("--stdout", required=True, help="The file holding the client's standard output.")
    parser.add_argument("--stderr", required=True, help="The file holding the client's standard error.")
    parser.add_argument("--exit", required=True, help="The file holding the client's exit status.")
    return parser


def run(argv: Sequence[str], tool_dir: Path) -> int:
    """Print the verified document of *argv*'s block's client run, or refuse it on standard error.

    A block *tool_dir* holds no documents for exits 2 (argparse's usage exit), naming the
    known blocks; a failed client run or files that are not a verified read exit
    :data:`REFUSED_EXIT`, naming why.
    """
    parser = _parser()
    arguments = parser.parse_args(list(argv))
    try:
        batch = build_read_batch(tool_dir, str(arguments.block))
    except UnknownBlockError as error:
        parser.error(str(error))
    try:
        document = verified_document(
            batch, Path(arguments.stdout), Path(arguments.stderr), Path(arguments.exit)
        )
    except (ReadFilesRefused, ReadOutputRefused) as error:
        print(f"schema.py {COMMAND_NAME}: {error}", file=sys.stderr)
        return REFUSED_EXIT
    print_output(f"{document}{_LINE_BREAK}")
    return 0
