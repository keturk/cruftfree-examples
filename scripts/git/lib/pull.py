"""Pull the latest changes into this clone, and say in a few lines what came in.

Fast-forward only unless ``--rebase`` is given; local work is never discarded. After an update a local
model, or Claude Sonnet 5.5 as the fallback (``llm.py``), summarizes the incoming commits. The summary
is a convenience: when no model answers, the pull is still reported as done.

Exit codes: 0 up to date or updated, 1 stopped (local changes in the way, a diverged branch or a
conflict), 2 git could not run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

import llm
from common import EXIT_ERROR, EXIT_OK, EXIT_STOPPED, GitError, ahead_behind, current_branch, default_repo, git, upstream_of

MAX_LOG_CHARS: Final = 8000

SYSTEM_PROMPT: Final = (
    "You summarize the changes a git pull brought into a repository of CruftFree example specifications "
    "and the code generated from them. Reply with at most six short lines, each starting with a hyphen, "
    "naming what changed and where. No introduction, no code fences, no signature."
)


def incoming_log(repo: Path, old: str, new: str) -> str:
    """The commits between two revisions, with the files each touched, cut to ``MAX_LOG_CHARS``."""
    log = git(repo, "log", "--no-merges", "--stat=100", "--format=commit %h %s", f"{old}..{new}", check=False)
    return log.stdout[:MAX_LOG_CHARS]


def summarize(repo: Path, old: str, new: str, args: argparse.Namespace) -> None:
    """Print a model's summary of the commits from *old* to *new*; say so when none answers."""
    settings = llm.settings_from(
        args.message_source, args.local_hosts, args.local_model, args.claude_model, args.claude_timeout_ms
    )
    try:
        label, reply = llm.ask(SYSTEM_PROMPT, incoming_log(repo, old, new), settings, print)
        print(f"What came in (summary by {label}):")
        print(llm.clean_summary(reply))
    except llm.LlmUnavailable as exc:
        print(f"No summary: {exc}")


def pull(repo: Path, args: argparse.Namespace) -> int:
    """Pull *repo*; the exit code."""
    branch = current_branch(repo)
    upstream = upstream_of(repo)
    if upstream is None:
        print(f"Branch '{branch}' has no upstream yet, so there is nothing to pull. Push it first with commit-and-push.")
        return EXIT_OK
    git(repo, "fetch")
    ahead, behind = ahead_behind(repo)
    print(f"Branch '{branch}' vs {upstream}: {ahead} ahead, {behind} behind.")
    if behind == 0:
        print("Up to date.")
        return EXIT_OK
    if ahead > 0 and not args.rebase:
        print(f"Diverged: {ahead} local commits and {behind} remote commits. Run again with --rebase to replay yours on top.")
        return EXIT_STOPPED
    old = git(repo, "rev-parse", "HEAD").stdout.strip()
    pulled = git(repo, "pull", "--rebase" if args.rebase else "--ff-only", check=False)
    for line in (pulled.stdout + pulled.stderr).splitlines():
        print(line)
    if pulled.code != 0:
        print("Stopped: nothing was discarded. Commit or move your local changes, or resolve the conflict, then run again.")
        return EXIT_STOPPED
    print(f"Updated '{branch}'.")
    if not args.no_summary:
        summarize(repo, old, git(repo, "rev-parse", "HEAD").stdout.strip(), args)
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """The command line."""
    parser = argparse.ArgumentParser(description="Pull the latest changes into this clone.")
    parser.add_argument("--rebase", action="store_true", help="when the branch has diverged, replay local commits on top")
    parser.add_argument("--no-summary", action="store_true", help="do not ask a model to summarize what came in")
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
        return pull(repo, args)
    except GitError as exc:
        print(f"Error: {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    sys.exit(main())
