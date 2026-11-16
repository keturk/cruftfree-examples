"""``schema.py plan-compare <block> --planned-contract F --expand F --contract F``: a re-plan checked.

A deploy plans each block, applies the expand SQL, then reads the catalog again and plans it with
the same arguments into fresh files. Once the expand is applied, the re-plan must hold exactly the
contract changes the first plan held: its expand file applies no change, and its contract file
applies the same changes as the first plan's contract file. Any other change, or a missing one,
means the catalog moved under the deploy or the expand did not do what it planned, and the deploy
stops before a service starts.

The three files are the ones ``schema.py plan`` wrote: ``--planned-contract`` the first plan's
contract file, ``--expand`` and ``--contract`` the re-plan's. A non-empty file must be one of the
block's plan files (``checked_plan_file``, as ``apply-batch`` checks it), and every file's statement
map must describe exactly its bytes (``load_statement_map``). Changes are compared through the
statement maps, as the multiset of ``(change kind, owner)`` over the statements that render a change:
the guards, the begin and commit, the schema prelude and the catalog statement are not changes, and
the fingerprint guard legitimately differs, since the re-plan carries the second read's fingerprint.

Exit status: 0 the re-plan holds exactly the planned contract changes, printing nothing; 1 it does
not, each extra and each missing change named with the block on standard error; 2 a usage error or
a block the tool holds no documents for, as ``read-batch``; 4 a file or its statement map is missing
or refused, naming the file.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from cruftfree_codegen_kernel.sql_facts.plan_statement_map import (
    StatementMapError,
    load_statement_map,
    statement_map_path,
)

from cruftfree_codegen_sql.schema_tool.apply import (
    ApplyFileRefused,
    checked_plan_file,
    read_plan_bytes,
)
from cruftfree_codegen_sql.schema_tool.read_batch import UnknownBlockError, block_documents

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cruftfree_codegen_kernel.sql_facts.plan_statement_map import StatementMap

    from cruftfree_codegen_sql.schema_tool.read_batch import BlockDocuments

#: The command's name in ``schema.py``'s command table.
COMMAND_NAME: Final[str] = "plan-compare"

#: Exit status of a re-plan that does not hold exactly the planned contract changes.
DIFFERENCE_EXIT: Final[int] = 1

#: Exit status of a run whose plan file or statement map is missing or refused.
INPUT_REFUSED_EXIT: Final[int] = 4

_LINE_BREAK: Final[str] = "\n"
_INDENT: Final[str] = "  "


@dataclass(frozen=True, order=True)
class PlannedChange:
    """One statement of a plan file that renders a change, as its statement map names it.

    Attributes:
        change_kind: The kind of the change it renders (``ChangeKind`` value).
        owner: The change as a failed apply names it: its kind, the object and the block.
    """

    change_kind: str
    owner: str


def planned_changes(statements: StatementMap) -> Counter[PlannedChange]:
    """Every statement of *statements* that renders a change, counted by kind and owner."""
    return Counter(
        PlannedChange(change_kind=statement.change_kind, owner=statement.owner)
        for statement in statements.statements
        if statement.change_kind is not None
    )


def plan_file_changes(path: Path, documents: BlockDocuments) -> Counter[PlannedChange]:
    """The changes *path*, one of *documents*' block's plan files, applies.

    An empty file applies nothing, and its statement map must map no statement.

    Raises:
        ApplyFileRefused: The file or its statement map is missing or unreadable, a non-empty file
            is not one of the block's plan files, or the map does not describe its bytes.
    """
    block = documents.block
    sql = read_plan_bytes(path, "SQL file", block)
    if sql:
        return planned_changes(checked_plan_file(path, sql, documents).statements)
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
    return planned_changes(statements)


def _listed(changes: Counter[PlannedChange]) -> list[str]:
    """Each of *changes* on its own indented line, with its count when it repeats."""
    return [
        f"{_INDENT}- {change.owner}" + (f" ({count} statements)" if count > 1 else "")
        for change, count in sorted(changes.items())
    ]


def compare_replan(
    block: str,
    planned_contract: Counter[PlannedChange],
    replanned_expand: Counter[PlannedChange],
    replanned_contract: Counter[PlannedChange],
) -> str | None:
    """Why the re-plan of *block* is not exactly the planned contract, or ``None`` when it is.

    The re-planned expand must apply nothing, and the re-planned contract must apply the planned
    contract's changes, each as many times.
    """
    lines: list[str] = []
    if replanned_expand:
        lines.append("The re-plan's expand applies changes the applied expand should have made:")
        lines.extend(_listed(replanned_expand))
    extra = replanned_contract - planned_contract
    if extra:
        lines.append("The re-plan's contract applies changes the planned contract does not:")
        lines.extend(_listed(extra))
    missing = planned_contract - replanned_contract
    if missing:
        lines.append("The re-plan's contract lacks changes the planned contract applies:")
        lines.extend(_listed(missing))
    if not lines:
        return None
    heading = (
        f"block '{block}': after its expand was applied, the catalog does not plan to exactly the "
        "planned contract changes, so the deploy stops before the new release starts. Read the "
        "catalog for what changed since the first read, then run the deploy again: it reads and "
        "plans anew."
    )
    return _LINE_BREAK.join((heading, *lines))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"schema.py {COMMAND_NAME}",
        description=(
            "Check that a block's re-plan, made after its expand SQL was applied, holds exactly the "
            "contract changes of its first plan: no expand change, no contract change more or less. "
            "Prints nothing when it does."
        ),
    )
    parser.add_argument("block", help="The block key, as named under desired/ and facts/.")
    parser.add_argument(
        "--planned-contract",
        required=True,
        help="The contract file the first 'schema.py plan' of the deploy wrote; its map beside it.",
    )
    parser.add_argument(
        "--expand",
        required=True,
        help="The expand file the re-plan wrote after the expand was applied; its map beside it.",
    )
    parser.add_argument(
        "--contract",
        required=True,
        help="The contract file the re-plan wrote after the expand was applied; its map beside it.",
    )
    return parser


def run(argv: Sequence[str], tool_dir: Path) -> int:
    """Compare *argv*'s re-plan files with its planned contract file; print nothing when they agree.

    A block *tool_dir* holds no documents for exits 2 (argparse's usage exit), naming the known
    blocks. A refused file exits :data:`INPUT_REFUSED_EXIT` and a difference
    :data:`DIFFERENCE_EXIT`, each named on standard error.
    """
    parser = _parser()
    arguments = parser.parse_args(list(argv))
    block = str(arguments.block)
    try:
        documents = block_documents(tool_dir, block)
    except UnknownBlockError as error:
        parser.error(str(error))
    try:
        planned = plan_file_changes(Path(arguments.planned_contract), documents)
        expand = plan_file_changes(Path(arguments.expand), documents)
        contract = plan_file_changes(Path(arguments.contract), documents)
    except ApplyFileRefused as error:
        print(f"schema.py {COMMAND_NAME}: {error}", file=sys.stderr)
        return INPUT_REFUSED_EXIT
    difference = compare_replan(block, planned, expand, contract)
    if difference is not None:
        print(f"schema.py {COMMAND_NAME}: {difference}", file=sys.stderr)
        return DIFFERENCE_EXIT
    return 0
