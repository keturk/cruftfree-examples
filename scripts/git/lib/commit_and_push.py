"""Commit every change in this repository and push it.

The commit message is written by a local model, with Claude Sonnet 5.5 (the Claude Code CLI) as the
fallback; see ``llm.py``. Before anything is staged the working tree is checked (``common.py``): a
path or text that must not be published stops the run with nothing committed, and there is no
switch that skips the checks.

Exit codes: 0 done (or nothing to do), 1 stopped by a check, a rejected push or a failed message
source, 2 git could not run or the repository is not in a state to commit.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Final

import llm
from common import (
    EXIT_ERROR,
    EXIT_OK,
    EXIT_STOPPED,
    Changes,
    GitError,
    ahead_behind,
    current_branch,
    default_repo,
    forbidden_paths,
    git,
    leaks,
    personal_strings,
    report_refusal,
    upstream_of,
    working_changes,
)

GENERATED_SUFFIX: Final = "-generated"
DOC_PATHSPECS: Final = ("*.cfree", "*.ccfg", "*.cseed", "*.md", ":!*-generated/**", ":!scripts/**")
MAX_DIFF_CHARS: Final = 6000
MAX_GROUPS: Final = 60
MAX_FOLDERS_IN_SUBJECT: Final = 3

SYSTEM_PROMPT: Final = (
    "You write git commit messages for a repository of CruftFree example specifications and the code "
    "generated from them. Reply with the commit message only. First line: a summary of at most 72 "
    "characters in the imperative mood. Then, only if it helps, a blank line and up to five short lines "
    "starting with a hyphen. No quotes, no code fences, no signature."
)


def group_of(path: str) -> str:
    """The folder a path is reported under: a spec folder, or a generated folder with its platform."""
    parts = path.split("/")
    if parts[0].endswith(GENERATED_SUFFIX) and len(parts) > 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


def change_counts(changes: Changes) -> dict[str, Counter[str]]:
    """Per folder, how many paths were added, modified and deleted."""
    counts: dict[str, Counter[str]] = {}
    for kind, paths in (("added", changes.added), ("modified", changes.modified), ("deleted", changes.deleted)):
        for path in paths:
            counts.setdefault(group_of(path), Counter())[kind] += 1
    return counts


def deterministic_message(changes: Changes) -> str:
    """A message built from the counts alone, used when no model is asked or none answers."""
    folders = sorted({path.split("/")[0] for path in changes.everything})
    if len(folders) <= MAX_FOLDERS_IN_SUBJECT:
        shown = ", ".join(folders)
    else:
        shown = f"{', '.join(folders[:MAX_FOLDERS_IN_SUBJECT])} and {len(folders) - MAX_FOLDERS_IN_SUBJECT} more"
    return f"Update examples: {len(changes.everything)} files in {shown}"


def build_prompt(repo: Path, changes: Changes) -> str:
    """What the model is told: the counts per folder and an excerpt of the spec and document changes."""
    lines = ["Changed files per folder:"]
    for group, counter in sorted(change_counts(changes).items())[:MAX_GROUPS]:
        detail = ", ".join(f"{n} {kind}" for kind, n in sorted(counter.items()))
        lines.append(f"  {group}: {detail}")
    diff = git(repo, "diff", "HEAD", "--unified=1", "--no-color", "--", *DOC_PATHSPECS, check=False)
    if diff.code == 0 and diff.stdout.strip():
        lines += ["", "Excerpt of the changes to specs and documents:", diff.stdout[:MAX_DIFF_CHARS]]
    new_specs = [p for p in changes.added if p.endswith((".cfree", ".ccfg", ".cseed")) and GENERATED_SUFFIX not in p]
    if new_specs:
        lines += ["", "New spec files: " + ", ".join(new_specs[:30])]
    return "\n".join(lines)


def commit_message(repo: Path, changes: Changes, args: argparse.Namespace) -> str:
    """The message to commit with: the given one, a model's, or (source auto only) a counted one.

    Raises:
        llm.LlmUnavailable: when a forced source (local or claude) produced nothing.
    """
    if args.message:
        return str(args.message)
    settings = llm.settings_from(
        args.message_source, args.local_hosts, args.local_model, args.claude_model, args.claude_timeout_ms
    )
    try:
        label, reply = llm.ask(SYSTEM_PROMPT, build_prompt(repo, changes), settings, print)
        message = llm.clean_message(reply)
        print(f"Message written by {label}.")
        return message
    except llm.LlmUnavailable as exc:
        if args.message_source != llm.SOURCE_AUTO:
            raise
        print(f"No model produced a message ({exc}). Using a counted message instead.")
        return deterministic_message(changes)


def publish(repo: Path, args: argparse.Namespace) -> int:
    """Check, commit and push *repo*; the exit code."""
    branch = current_branch(repo)
    changes = working_changes(repo)
    upstream = upstream_of(repo)
    ahead = ahead_behind(repo)[0] if upstream else 0
    if not changes.everything and upstream is not None and ahead == 0:
        print(f"Nothing to commit and nothing to push on '{branch}'.")
        return EXIT_OK

    message = ""
    if changes.everything:
        bad = forbidden_paths(changes.present)
        if bad:
            report_refusal("these paths must never be published:", bad)
            return EXIT_STOPPED
        found = leaks(repo, personal_strings(repo))
        if found:
            report_refusal("the repository holds data that must not be published:", found)
            return EXIT_STOPPED
        message = commit_message(repo, changes, args)
        print(f"Branch '{branch}': {len(changes.present)} files added or changed, {len(changes.deleted)} deleted.")
        print("Message:\n" + "\n".join(f"  {line}" for line in message.splitlines()))
    if args.dry_run:
        print("Dry run: nothing committed, nothing pushed.")
        return EXIT_OK
    if changes.everything:
        git(repo, "add", "-A")
        git(repo, "commit", "-F", "-", input_text=message + "\n")
        print("Committed.")
    if args.no_push:
        print("Not pushed (--no-push).")
        return EXIT_OK
    push_args = ["push"] if upstream else ["push", "-u", "origin", branch]
    pushed = git(repo, *push_args, check=False)
    for line in (pushed.stdout + pushed.stderr).splitlines():
        print(line)
    if pushed.code != 0:
        print("The push was rejected. Run scripts/git/pull.ps1, then run this script again.")
        return EXIT_STOPPED
    print(f"Pushed '{branch}'.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """The command line."""
    parser = argparse.ArgumentParser(description="Commit every change in this repository and push it.")
    parser.add_argument("--message", default="", help="the commit message; default: written by a model")
    parser.add_argument("--dry-run", action="store_true", help="run the checks and show the message; change nothing")
    parser.add_argument("--no-push", action="store_true", help="commit, but do not push")
    parser.add_argument("--message-source", choices=llm.SOURCES, default=llm.SOURCE_AUTO)
    parser.add_argument("--local-hosts", default="", help=f"hosts to search for Ollama; default: ${llm.HOSTS_ENV}, then localhost")
    parser.add_argument("--local-model", default="", help="ask this model on each host instead of the preferred ones")
    parser.add_argument("--claude-model", default=llm.DEFAULT_CLAUDE_MODEL)
    parser.add_argument("--claude-timeout-ms", type=int, default=llm.DEFAULT_CLAUDE_TIMEOUT_MS)
    parser.add_argument("--repo", default="", help=argparse.SUPPRESS)
    parser.add_argument("--self-test", action="store_true", help="run the script's own checks in a scratch repository")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = build_parser().parse_args(argv)
    if args.self_test:
        from selftest import run_self_test

        return run_self_test()
    repo = Path(args.repo).resolve() if args.repo else default_repo()
    try:
        return publish(repo, args)
    except GitError as exc:
        print(f"Error: {exc}")
        return EXIT_ERROR
    except llm.LlmUnavailable as exc:
        print(f"Error: no commit message could be written: {exc}")
        return EXIT_STOPPED


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.exit(main())
