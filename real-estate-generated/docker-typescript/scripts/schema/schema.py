"""The schema tool: reads, plans and applies an RDBMS block's schema with the standard library alone.

Generated projects carry this script as ``scripts/schema/schema.py``, with every CruftFree module
it runs written under ``lib/`` beside it and each block's facts under ``desired/`` and
``facts/``. It runs on a machine with no CruftFree installed: ``lib/`` goes first on
``sys.path``, the runtime modules are imported from there, and a module that resolves
anywhere else stops the run.

Usage: ``python schema.py <command> [arguments]``.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import ModuleType

#: The directory holding this script and each block's documents (``desired/``, ``facts/``).
TOOL_DIR = Path(__file__).resolve().parent

#: The directory holding the carried CruftFree modules: the first ``sys.path`` entry of a run.
LIB_DIR = TOOL_DIR / "lib"

#: Exit status of a run whose command line names no known command.
USAGE_EXIT = 2

#: Exit status of a run whose runtime modules do not load from ``lib/``.
RUNTIME_EXIT = 3

#: A command: its arguments in, the process exit status out.
Command = Callable[[Sequence[str]], int]


def _read_batch(arguments: Sequence[str]) -> int:
    """``read-batch <block> [--places]``: the input of one consistent read of the block's catalog.

    Imported when the command runs, after :func:`import_runtime` loaded it from ``lib/``.
    """
    from cruftfree_codegen_sql.schema_tool import read_batch

    return read_batch.run(arguments, TOOL_DIR)


def _read_verify(arguments: Sequence[str]) -> int:
    """``read-verify <block> --stdout F --stderr F --exit F``: a client run's files, checked.

    Imported when the command runs, after :func:`import_runtime` loaded it from ``lib/``.
    """
    from cruftfree_codegen_sql.schema_tool import read_verify

    return read_verify.run(arguments, TOOL_DIR)


def _plan(arguments: Sequence[str]) -> int:
    """``plan <block> --catalog F --expand F --contract F [--approved]``: what a deploy would do.

    Imported when the command runs, after :func:`import_runtime` loaded it from ``lib/``.
    """
    from cruftfree_codegen_sql.schema_tool import plan

    return plan.run(arguments, TOOL_DIR)


def _plan_compare(arguments: Sequence[str]) -> int:
    """``plan-compare <block> --planned-contract F --expand F --contract F``: a re-plan checked.

    Imported when the command runs, after :func:`import_runtime` loaded it from ``lib/``.
    """
    from cruftfree_codegen_sql.schema_tool import plan_compare

    return plan_compare.run(arguments, TOOL_DIR)


def _verify(arguments: Sequence[str]) -> int:
    """``verify <block> --catalog F``: whether the block's catalog holds its declared schema.

    Imported when the command runs, after :func:`import_runtime` loaded it from ``lib/``.
    """
    from cruftfree_codegen_sql.schema_tool import verify_schema

    return verify_schema.run(arguments, TOOL_DIR)


def _apply_batch(arguments: Sequence[str]) -> int:
    """``apply-batch <block> --sql F``: the input of one apply of a plan file to the block.

    Imported when the command runs, after :func:`import_runtime` loaded it from ``lib/``.
    """
    from cruftfree_codegen_sql.schema_tool import apply

    return apply.run_batch(arguments, TOOL_DIR)


def _apply_verify(arguments: Sequence[str]) -> int:
    """``apply-verify <block> --sql F --stdout F --stderr F --exit F``: an apply's client run, checked.

    Imported when the command runs, after :func:`import_runtime` loaded it from ``lib/``.
    """
    from cruftfree_codegen_sql.schema_tool import apply

    return apply.run_verify(arguments, TOOL_DIR)


#: The tool's commands, by the name a command line gives.
COMMANDS: dict[str, Command] = {
    "read-batch": _read_batch,
    "read-verify": _read_verify,
    "plan": _plan,
    "plan-compare": _plan_compare,
    "verify": _verify,
    "apply-batch": _apply_batch,
    "apply-verify": _apply_verify,
}


def import_runtime() -> tuple[ModuleType, ...]:
    """Import the modules the tool runs on: the schema runtime set, the planner, the block's facts and the commands.

    The engines' readers and SQL dialects are reached through their tables
    (``reflector_registry``, ``dialect_table``), which import every registered engine's
    module, so no plugin is discovered.
    """
    from cruftfree_codegen_kernel.sql_facts import convergence as convergence_plan
    from cruftfree_codegen_kernel.sql_facts import plan_statement_map, revision
    from cruftfree_codegen_kernel.sql_facts.dialects import dialect_table
    from cruftfree_rdbms_schema import (
        block_facts,
        canonicalize,
        catalog_reader,
        change_policy,
        convergence,
        schema_snapshot,
        snapshot_diff,
    )
    from cruftfree_rdbms_schema.sql_lowering import (
        builtins_table,
        dialect_rows,
        lowered,
        render,
    )

    from cruftfree_codegen_sql.dialects import reflector_registry
    from cruftfree_codegen_sql.schema_tool import (
        apply,
        plan,
        plan_compare,
        read_batch,
        read_verify,
        verify_schema,
    )

    return (
        reflector_registry,
        catalog_reader,
        dialect_table,
        lowered,
        dialect_rows,
        render,
        builtins_table,
        canonicalize,
        snapshot_diff,
        change_policy,
        convergence,
        revision,
        convergence_plan,
        plan_statement_map,
        schema_snapshot,
        block_facts,
        read_batch,
        read_verify,
        plan,
        plan_compare,
        verify_schema,
        apply,
    )


def modules_outside_lib(modules: Sequence[ModuleType], lib_dir: Path) -> list[str]:
    """The names of *modules* whose source file is not under *lib_dir*, sorted."""
    return sorted(
        module.__name__
        for module in modules
        if module.__file__ is None or not Path(module.__file__).resolve().is_relative_to(lib_dir)
    )


def dispatch(argv: Sequence[str], commands: Mapping[str, Command]) -> int:
    """Run the command of *commands* that ``argv[0]`` names with the rest of *argv*.

    A missing or unknown command exits with :data:`USAGE_EXIT`, naming the known commands.
    """
    known = ", ".join(sorted(commands)) or "none"
    if not argv:
        print(f"schema.py: no command given. Known commands: {known}.", file=sys.stderr)
        return USAGE_EXIT
    command = commands.get(argv[0])
    if command is None:
        print(f"schema.py: unknown command {argv[0]!r}. Known commands: {known}.", file=sys.stderr)
        return USAGE_EXIT
    return command(argv[1:])


def main(argv: Sequence[str]) -> int:
    """Load the runtime from :data:`LIB_DIR`, then run the command *argv* names.

    The runtime is loaded first, so a run with a missing module, or one resolving outside
    ``lib/``, fails with :data:`RUNTIME_EXIT` before any command runs.
    """
    outside = modules_outside_lib(import_runtime(), LIB_DIR)
    if outside:
        print(
            f"schema.py: the runtime modules {', '.join(outside)} did not load from {LIB_DIR}. "
            f"The tool runs only on the modules generated beside it: regenerate the project, "
            f"and run the script with no other CruftFree on the module path.",
            file=sys.stderr,
        )
        return RUNTIME_EXIT
    return dispatch(argv, COMMANDS)


if __name__ == "__main__":
    sys.path.insert(0, str(LIB_DIR))
    raise SystemExit(main(sys.argv[1:]))
