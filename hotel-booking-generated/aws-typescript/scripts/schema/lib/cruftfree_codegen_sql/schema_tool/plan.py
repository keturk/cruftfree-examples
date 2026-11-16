"""``schema.py plan <block> --catalog F --expand F --contract F [--approved]``: what a deploy would do.

The command reads ``L`` from the catalog file ``schema-read <block>`` printed
(:func:`~cruftfree_codegen_sql.schema_tool.live_catalog.read_live_catalog`), plans it against the
block's ``D`` with the convergence planner (``converge``), writes each phase's SQL to its file,
``--expand`` (applied before the new release starts,
while the previous release still serves) and ``--contract`` (applied once the new release is
healthy), each with its statement map ``<file>.statements.json`` beside it, and prints the plan.
It changes nothing: no database is reached.

``--approved`` is the one source of approval: without it a change that needs approval is
refused, printed with the SQL it runs once approved and kept out of both SQL files; with it the
change is planned, in the contract phase. A change no forward DDL realizes is refused either
way. Every file is created, never overwritten, readable by its owner alone; an existing path
among the four is refused before any of them is written. A phase that applies nothing has an
empty SQL file and a map of no statement.

Exit status: 0 the plan applies every change; 1 a change is refused (needs approval, or never
applied); 2 a usage error or a block the tool holds no documents for; 4 the catalog file or a
plan file is refused; 5 the planner cannot plan the catalog against ``D``.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from cruftfree_codegen_kernel.sql_facts.convergence import (
    ConvergencePlan,
    PlanPhase,
    converge,
)
from cruftfree_codegen_kernel.sql_facts.errors import DialectFeatureError
from cruftfree_codegen_kernel.sql_facts.plan_statement_map import (
    PLAN_FILE_ENCODING,
    sql_file_bytes,
    statement_map_document,
    statement_map_path,
)
from cruftfree_common.errors.generation import GenerationError
from cruftfree_rdbms_schema.change_policy import ConvergencePhase

from cruftfree_codegen_sql.schema_tool.live_catalog import (
    CatalogFileRefused,
    LiveCatalog,
    read_live_catalog,
)
from cruftfree_codegen_sql.schema_tool.read_batch import (
    ReadOutputRefused,
    UnknownBlockError,
)
from cruftfree_codegen_sql.schema_tool.tool_files import print_output

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from cruftfree_rdbms_schema.change_policy import ConvergenceOutcome

#: The command's name in ``schema.py``'s command table.
COMMAND_NAME: Final[str] = "plan"

#: Exit status of a plan that refuses a change: one needing approval, or one never applied.
REFUSED_EXIT: Final[int] = 1

#: Exit status of a run whose catalog file or a plan file is refused.
INPUT_REFUSED_EXIT: Final[int] = 4

#: Exit status of a run whose catalog the planner cannot plan against ``D``.
PLAN_FAILED_EXIT: Final[int] = 5

#: Every plan file's permissions: read and written by its owner alone.
PLAN_FILE_MODE: Final[int] = 0o600

#: The mark of an applied change that is validated over the rows the catalog holds.
RISKY_MARK: Final[str] = (
    " [risky: validated over the rows when applied; may refuse writes the running release makes]"
)

_LINE_BREAK: Final[str] = "\n"
_INDENT: Final[str] = "  "


@dataclass(frozen=True)
class _PhaseText:
    """How the plan's output names a phase, and when the phase is applied."""

    name: str
    when: str


#: Each phase as the output names it; every :class:`ConvergencePhase` has one.
PHASE_TEXT: Final[Mapping[ConvergencePhase, _PhaseText]] = {
    ConvergencePhase.EXPAND: _PhaseText(
        "Expand",
        "applied before the new release starts, while the previous release still serves",
    ),
    ConvergencePhase.CONTRACT: _PhaseText("Contract", "applied after the new release is healthy"),
}


class PlanFileRefused(ValueError):
    """A plan file cannot be created: the path exists, repeats another, or is refused."""


@dataclass(frozen=True)
class PlanFile:
    """One file the plan writes: a phase's SQL or its statement map, as its exact bytes.

    Attributes:
        path: Where the file is created.
        content: Its bytes, written as they are.
    """

    path: Path
    content: bytes


def plan_block(live: LiveCatalog, approved: bool) -> ConvergencePlan:
    """The plan that brings *live*'s ``L`` to its block's ``D``, with the switch *approved*.

    The fingerprint guard re-reads the block's catalog queries, bound to ``D``'s schema.

    Raises:
        ValueError: The read is not at ``D``'s schema, or a change is malformed.
        GenerationError: The dialect declares no session lock, ``L`` lacks an object a change
            removes, or a change cannot be rendered.
        DialectFeatureError: The dialect cannot spell a guard or a change's statement.
    """
    documents = live.documents
    return converge(
        live.live,
        documents.desired,
        approved,
        live.read.digest,
        dialect=documents.dialect,
        catalog_queries=documents.catalog_queries,
    )


def plan_files(plan: ConvergencePlan, expand: Path, contract: Path) -> tuple[PlanFile, ...]:
    """The four files *plan* is written as: each phase's SQL at its path, then its statement map."""
    files: list[PlanFile] = []
    for phase, path in ((plan.expand, expand), (plan.contract, contract)):
        files.append(PlanFile(path, sql_file_bytes(phase)))
        files.append(
            PlanFile(
                statement_map_path(path),
                statement_map_document(phase).encode(PLAN_FILE_ENCODING),
            )
        )
    return tuple(files)


def _owner_only(path: str, flags: int) -> int:
    """Open *path* with *flags*, creating it readable and writable by its owner alone."""
    return os.open(path, flags, PLAN_FILE_MODE)


def _same_file_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def _require_distinct(files: Sequence[PlanFile]) -> None:
    """Refuse *files* when two of them name one path: the second would overwrite the first."""
    seen: dict[str, Path] = {}
    for planned in files:
        key = _same_file_key(planned.path)
        if key in seen:
            raise PlanFileRefused(
                f"The plan files {seen[key]} and {planned.path} are one path. Give the expand and "
                "the contract file paths that differ, neither one the other's statement map."
            )
        seen[key] = planned.path


def _require_absent(files: Sequence[PlanFile]) -> None:
    """Refuse *files* when any path exists, naming every one, before a file is written."""
    existing = [str(planned.path) for planned in files if os.path.lexists(planned.path)]
    if existing:
        raise PlanFileRefused(
            f"The plan file(s) {', '.join(existing)} already exist. The plan never overwrites a "
            "file: give paths that do not exist yet."
        )


def _create(planned: PlanFile, created: list[Path]) -> None:
    """Create *planned*'s file holding its bytes; record it in *created* once it exists."""
    try:
        with open(planned.path, "xb", opener=_owner_only) as handle:
            created.append(planned.path)
            handle.write(planned.content)
    except FileExistsError as error:
        raise PlanFileRefused(
            f"The plan file {planned.path} already exists. The plan never overwrites a file: "
            "give a path that does not exist yet."
        ) from error
    except OSError as error:
        raise PlanFileRefused(
            f"The plan file {planned.path} could not be created or written ({error})."
        ) from error


def _remove(created: Sequence[Path]) -> list[str]:
    """Remove each of *created*; the ones that could not be removed, each with its cause."""
    left: list[str] = []
    for path in reversed(created):
        try:
            path.unlink()
        except OSError as error:
            left.append(f"{path} ({error})")
    return left


def write_plan_files(files: Sequence[PlanFile]) -> None:
    """Create every one of *files*, or none: never overwrite a file, never leave a part behind.

    Every path is checked first, so an existing one is refused before any file is written; a
    file that appears or fails after that check removes the files this call created.

    Raises:
        PlanFileRefused: Two paths are one, a path exists, or a file cannot be created or
            written; the message names it.
    """
    _require_distinct(files)
    _require_absent(files)
    created: list[Path] = []
    try:
        for planned in files:
            _create(planned, created)
    except PlanFileRefused as error:
        left = _remove(created)
        if left:
            raise PlanFileRefused(
                f"{error} The plan files it created could not all be removed: {', '.join(left)}."
            ) from error
        raise


def _outcome_line(outcome: ConvergenceOutcome, risky: bool) -> str:
    """One planned change as the plan prints it: its kind and diagnostic, marked when risky."""
    mark = RISKY_MARK if risky else ""
    return f"{_INDENT}- {outcome.change.kind.value}: {outcome.diagnostic}{mark}"


def _indented(text: str) -> str:
    return _LINE_BREAK.join(f"{_INDENT}{line}" for line in text.split(_LINE_BREAK))


def _phase_changes(phase: PlanPhase, risky: tuple[ConvergenceOutcome, ...]) -> list[str]:
    """*phase*'s heading, saying when it is applied, then each of its changes."""
    text = PHASE_TEXT[phase.phase]
    return [
        f"{text.name}, {text.when}: {len(phase.applied)} change(s).",
        *(_outcome_line(outcome, outcome in risky) for outcome in phase.applied),
    ]


def _phase_sql(phase: PlanPhase, path: Path) -> list[str]:
    """Where *phase*'s SQL and statement map were written, then the SQL."""
    name = PHASE_TEXT[phase.phase].name
    statement_map = statement_map_path(path)
    if not phase.statements:
        return [f"{name} SQL written to {path}: none, nothing applies (statement map {statement_map})."]
    heading = f"{name} SQL written to {path} ({len(phase.lines)} line(s); statement map {statement_map}):"
    return [heading, phase.sql.removesuffix(_LINE_BREAK)]


def render_plan(block: str, plan: ConvergencePlan, expand: Path, contract: Path) -> str:
    """*plan* of *block* as the command prints it, ended by a line break.

    The applied changes under their phase's heading, expand then contract (a risky one marked),
    each refused change with the SQL it runs once approved, each never-applied change with its
    reason and fix, then each phase's SQL and the path it was written to, *expand* and
    *contract*.
    """
    risky = plan.risky
    lines = [
        (
            f"Plan of block '{block}' (rdbms_id {plan.block}; catalog fingerprint "
            f"{plan.fingerprint}; approved: {'yes' if plan.approved else 'no'})."
        ),
        f"Applied: {len(plan.applied)} change(s).",
        *_phase_changes(plan.expand, risky),
        *_phase_changes(plan.contract, risky),
        f"Refused until the deploy runs with --approved: {len(plan.refused)} change(s).",
        *(_indented(refused.message) for refused in plan.refused),
        f"Never applied: {len(plan.never_applied)} change(s).",
        *(_outcome_line(outcome, False) for outcome in plan.never_applied),
        *_phase_sql(plan.expand, expand),
        *_phase_sql(plan.contract, contract),
    ]
    return "".join(f"{line}{_LINE_BREAK}" for line in lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"schema.py {COMMAND_NAME}",
        description=(
            "Print what a deploy would do to an RDBMS block's schema, from a verified read of its "
            "catalog, and write the SQL it would apply before and after the new release starts. "
            "Changes nothing."
        ),
    )
    parser.add_argument("block", help="The block key, as named under desired/ and facts/.")
    parser.add_argument(
        "--catalog", required=True, help="The file holding the document 'schema-read <block>' printed."
    )
    parser.add_argument(
        "--expand",
        required=True,
        help=(
            "The file to create with the SQL applied before the new release starts; it and its "
            "statement map must not exist."
        ),
    )
    parser.add_argument(
        "--contract",
        required=True,
        help=(
            "The file to create with the SQL applied once the new release is healthy; it and its "
            "statement map must not exist."
        ),
    )
    parser.add_argument(
        "--approved",
        action="store_true",
        help="Plan the changes that need approval instead of refusing them.",
    )
    return parser


def _refusal(block: str, plan: ConvergencePlan) -> str | None:
    """Why *plan* of *block* exits :data:`REFUSED_EXIT`, or ``None`` when it refuses nothing.

    The counts, then each refused change and each never-applied change on its own line, kind
    and diagnostic: the diagnostic names the object, so whoever reads only standard error sees
    what an approved deploy would drop and what no deploy applies.
    """
    if not (plan.refused or plan.never_applied):
        return None
    lines = [
        (
            f"block '{block}': {len(plan.refused)} change(s) refused until the deploy runs with "
            f"--approved, {len(plan.never_applied)} change(s) never applied."
        ),
        *(_outcome_line(refused.outcome, False) for refused in plan.refused),
        *(_outcome_line(outcome, False) for outcome in plan.never_applied),
    ]
    return _LINE_BREAK.join(lines)


def run(argv: Sequence[str], tool_dir: Path) -> int:
    """Plan *argv*'s block from its catalog file, write the plan files and print the plan.

    A block *tool_dir* holds no documents for exits 2 (argparse's usage exit), naming the
    known blocks. A refusal is printed on standard error, naming its cause.
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
        plan = plan_block(live, bool(arguments.approved))
    except (GenerationError, DialectFeatureError, ValueError) as error:
        print(
            f"schema.py {COMMAND_NAME}: block '{block}' cannot be planned from its catalog file: "
            f"{error}",
            file=sys.stderr,
        )
        return PLAN_FAILED_EXIT
    expand = Path(arguments.expand)
    contract = Path(arguments.contract)
    try:
        write_plan_files(plan_files(plan, expand, contract))
    except PlanFileRefused as error:
        print(f"schema.py {COMMAND_NAME}: {error}", file=sys.stderr)
        return INPUT_REFUSED_EXIT
    print_output(render_plan(block, plan, expand, contract))
    refusal = _refusal(block, plan)
    if refusal is not None:
        print(f"schema.py {COMMAND_NAME}: {refusal}", file=sys.stderr)
        return REFUSED_EXIT
    return 0
