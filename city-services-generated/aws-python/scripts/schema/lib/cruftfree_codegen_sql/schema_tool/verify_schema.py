"""``schema.py verify <block> --catalog F``: whether a block's catalog holds its declared schema.

The command reads ``L`` from the catalog file ``schema-read <block>`` printed
(:func:`~cruftfree_codegen_sql.schema_tool.live_catalog.read_live_catalog`), prepares it with the
convergence planner the plan runs (``converge`` with the switch off, exactly as a deploy
prepares it), and compares that
``L`` with the block's ``D`` through ``require_same_schema``, the one check of whether two
snapshots describe the same schema. It prints the verdict and changes nothing: no database is
reached and no file is written.

Exit status: 0 the block holds ``D``; 1 it differs, each difference printed; 2 a usage error or
a block the tool holds no documents for; 4 the catalog file is refused; 5 the planner cannot
prepare the catalog against ``D``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

from cruftfree_codegen_kernel.sql_facts.errors import DialectFeatureError
from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema.convergence import require_same_schema
from cruftfree_rdbms_schema.errors import SchemaMismatchError

from cruftfree_codegen_sql.schema_tool.live_catalog import (
    CatalogFileRefused,
    LiveCatalog,
    read_live_catalog,
)
from cruftfree_codegen_sql.schema_tool.plan import plan_block
from cruftfree_codegen_sql.schema_tool.read_batch import (
    ReadOutputRefused,
    UnknownBlockError,
)
from cruftfree_codegen_sql.schema_tool.tool_files import print_output

if TYPE_CHECKING:
    from collections.abc import Sequence

#: The command's name in ``schema.py``'s command table.
COMMAND_NAME: Final[str] = "verify"

#: Exit status of a block whose catalog differs from ``D``.
DIFFERS_EXIT: Final[int] = 1

#: Exit status of a run whose catalog file is refused.
INPUT_REFUSED_EXIT: Final[int] = 4

#: Exit status of a run whose catalog the planner cannot prepare against ``D``.
VERIFY_FAILED_EXIT: Final[int] = 5

_LINE_BREAK: Final[str] = "\n"
_INDENT: Final[str] = "  "


def verify_block(live: LiveCatalog) -> tuple[str, ...]:
    """The differences between *live*'s ``L`` and its block's ``D``; empty when the block holds ``D``.

    ``L`` is the one :func:`plan_block` prepares with the switch off (``ConvergencePlan.live``);
    nothing is filtered from it.

    Raises:
        ValueError: The read is not at ``D``'s schema, a change is malformed, or a column lists
            members its type does not declare.
        GenerationError: The dialect declares no session lock, or a change cannot be rendered.
        DialectFeatureError: The dialect cannot spell a guard or a change's statement.
    """
    plan = plan_block(live, approved=False)
    try:
        require_same_schema(plan.live, live.documents.desired)
    except SchemaMismatchError as mismatch:
        return mismatch.differences
    return ()


def render_verdict(block: str, live: LiveCatalog, differences: tuple[str, ...]) -> str:
    """The verdict on *block* as the command prints it, ended by a line break."""
    heading = (
        f"Verify of block '{block}' (rdbms_id {live.documents.desired.rdbms_id}; catalog "
        f"fingerprint {live.read.digest})."
    )
    if not differences:
        lines = [heading, "The block holds its declared schema."]
    else:
        lines = [
            heading,
            f"The block differs from its declared schema: {len(differences)} difference(s).",
            *(f"{_INDENT}- {difference}" for difference in differences),
        ]
    return "".join(f"{line}{_LINE_BREAK}" for line in lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"schema.py {COMMAND_NAME}",
        description=(
            "Say whether an RDBMS block's catalog, from a verified read of it, holds the block's "
            "declared schema. Changes nothing."
        ),
    )
    parser.add_argument(
        "block", help="The block key, as named under desired/ and facts/."
    )
    parser.add_argument(
        "--catalog",
        required=True,
        help="The file holding the document 'schema-read <block>' printed.",
    )
    return parser


def run(argv: Sequence[str], tool_dir: Path) -> int:
    """Compare *argv*'s block's catalog file with its ``D`` and print the verdict.

    A block *tool_dir* holds no documents for exits 2 (argparse's usage exit), naming the
    known blocks. A refusal or a difference is named on standard error.
    """
    parser = _parser()
    arguments = parser.parse_args(list(argv))
    block = str(arguments.block)
    try:
        live = read_live_catalog(tool_dir, block, Path(arguments.catalog))
    except UnknownBlockError as error:
        parser.error(str(error))
    except (CatalogFileRefused, ReadOutputRefused) as error:
        print(f"schema.py {COMMAND_NAME}: {error}", file=sys.stderr)
        return INPUT_REFUSED_EXIT
    try:
        differences = verify_block(live)
    except (GenerationError, DialectFeatureError, ValueError) as error:
        print(
            f"schema.py {COMMAND_NAME}: block '{block}' cannot be verified from its catalog file: "
            f"{error}",
            file=sys.stderr,
        )
        return VERIFY_FAILED_EXIT
    print_output(render_verdict(block, live, differences))
    if differences:
        print(
            f"schema.py {COMMAND_NAME}: block '{block}' differs from its declared schema in "
            f"{len(differences)} difference(s).",
            file=sys.stderr,
        )
        return DIFFERS_EXIT
    return 0
