"""What both git scripts share: running git, the repository root and the publication checks.

The checks decide what may enter this public repository. They run on the working tree before
anything is staged, and there is no way to skip them: a path or text that must not be published
is fixed or removed, then the script is run again.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import settings as machine

EXIT_OK: Final = 0
EXIT_STOPPED: Final = 1
EXIT_ERROR: Final = 2

#: Folders and files that are never published. A path with one of these as a segment is refused.
FORBIDDEN_SEGMENT: Final = re.compile(
    r"(^|/)(\.env|\.env\..*|secrets|snapshots|node_modules|\.venv|\.dart_tool|\.git|ephemeral)(/|$)"
)
#: Flutter's machine-local files, written with the paths of the machine that built the app.
FORBIDDEN_FILE: Final = re.compile(
    r"(^|/)(local\.properties|Generated\.xcconfig|flutter_export_environment\.sh"
    r"|\.flutter-plugins-dependencies|flutter_native_integration\.env"
    rf"|{re.escape(machine.FILE_NAME)})$"
)
#: The shape of a cloud, GitHub, Slack or OpenAI credential.
TOKEN_SHAPES: Final = r"AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{32,}"
PRIVATE_KEY_HEADER: Final = r"BEGIN [A-Z ]*PRIVATE KEY"
#: Extra text that must not be published (project names, host names), comma separated.
BLOCKED_TEXT_ENV: Final = machine.BLOCKED_TEXT
MIN_BLOCKED_LENGTH: Final = 4
GREP_NO_MATCH: Final = 1
MAX_REPORTED: Final = 20


class GitError(RuntimeError):
    """A git command failed in a way the caller did not expect."""


@dataclass(frozen=True)
class GitResult:
    """The outcome of one git command."""

    code: int
    stdout: str
    stderr: str

    @property
    def lines(self) -> list[str]:
        """The standard output as non-empty lines."""
        return [line for line in self.stdout.splitlines() if line]


def default_repo() -> Path:
    """The repository this script lives in: three folders above ``scripts/git/lib``."""
    return Path(__file__).resolve().parents[3]


def git(repo: Path, *args: str, check: bool = True, input_text: str | None = None) -> GitResult:
    """Run ``git -C <repo> <args>``.

    Raises:
        GitError: when *check* is true and git exits non-zero, or git cannot be started.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            input=input_text,
            check=False,
        )
    except OSError as exc:
        raise GitError(f"git could not be started: {exc}") from exc
    result = GitResult(done.returncode, done.stdout, done.stderr)
    if check and result.code != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GitError(f"git {' '.join(args)} failed (exit {result.code}): {detail}")
    return result


def nul_list(result: GitResult) -> list[str]:
    """The paths of a ``-z`` listing."""
    return sorted({path for path in result.stdout.split("\0") if path})


@dataclass(frozen=True)
class Changes:
    """The working tree's differences from HEAD, as git names the paths."""

    added: list[str]
    modified: list[str]
    deleted: list[str]

    @property
    def present(self) -> list[str]:
        """Every path that exists and is new or changed."""
        return sorted(set(self.added) | set(self.modified))

    @property
    def everything(self) -> list[str]:
        """Every path that differs, deleted ones included."""
        return sorted(set(self.present) | set(self.deleted))


def working_changes(repo: Path) -> Changes:
    """New (not ignored), modified and deleted paths of *repo*."""
    added = nul_list(git(repo, "ls-files", "-z", "--others", "--exclude-standard"))
    deleted = nul_list(git(repo, "ls-files", "-z", "--deleted"))
    modified = [p for p in nul_list(git(repo, "ls-files", "-z", "--modified")) if p not in set(deleted)]
    return Changes(added=added, modified=modified, deleted=deleted)


def current_branch(repo: Path) -> str:
    """The checked-out branch.

    Raises:
        GitError: on a detached HEAD.
    """
    name = git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if name == "HEAD":
        raise GitError("The repository is on a detached HEAD. Check out a branch first.")
    return name


def upstream_of(repo: Path) -> str | None:
    """The upstream of the current branch, or None when it has none."""
    result = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    return result.stdout.strip() if result.code == 0 else None


def ahead_behind(repo: Path) -> tuple[int, int]:
    """Commits the branch has that its upstream lacks, and the reverse."""
    counts = git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}").stdout.split()
    return int(counts[0]), int(counts[1])


def forbidden_paths(paths: Sequence[str]) -> list[str]:
    """The paths among *paths* that must never be published."""
    return [p for p in paths if FORBIDDEN_SEGMENT.search(p) or FORBIDDEN_FILE.search(p)]


def personal_strings(repo: Path) -> list[str]:
    """Text that identifies this machine's user.

    The home folder, the commit e-mail, the host names of the local model servers from the settings, and
    the extras in ``CRUFTFREE_EXAMPLES_BLOCKED_TEXT``.
    """
    found: set[str] = set(machine.host_names(machine.value(machine.HOSTS)))
    home = str(Path.home())
    for form in (home, home.replace("\\", "/")):
        if len(form) > MIN_BLOCKED_LENGTH:
            found.add(form)
    email = git(repo, "config", "user.email", check=False).stdout.strip()
    if "@" in email:
        found.add(email)
    for extra in machine.value(BLOCKED_TEXT_ENV).split(","):
        if len(extra.strip()) >= MIN_BLOCKED_LENGTH:
            found.add(extra.strip())
    return sorted(text for text in found if len(text) >= MIN_BLOCKED_LENGTH)


def _grep_hits(repo: Path, label: str, *grep_args: str) -> list[str]:
    """``label: file:line`` for each match of a ``git grep`` over the working tree; the text is not echoed."""
    result = git(repo, "grep", "--untracked", "-I", "-n", *grep_args, check=False)
    if result.code == GREP_NO_MATCH:
        return []
    if result.code != 0:
        raise GitError(f"git grep failed: {(result.stderr or result.stdout).strip()}")
    hits = []
    for line in result.lines:
        located = re.match(r"^(.+?):(\d+):", line)
        hits.append(f"{label}: {located.group(1)}:{located.group(2)}" if located else f"{label}: {line[:80]}")
    return hits


def leaks(repo: Path, blocked: Sequence[str]) -> list[str]:
    """Where the working tree holds personal data, a credential shape or a private key outside tests."""
    found: list[str] = []
    if blocked:
        fixed = [arg for text in blocked for arg in ("-e", text)]
        found += _grep_hits(repo, "personal data", "-F", *fixed)
    found += _grep_hits(repo, "token shape", "-E", TOKEN_SHAPES)
    found += _grep_hits(repo, "private key", "-E", PRIVATE_KEY_HEADER, "--", ":!**/tests/**", ":!**/test/**")
    return found


def report_refusal(title: str, items: Sequence[str]) -> None:
    """Print a refusal and the first of its items."""
    print(f"Refused: {title}")
    for item in items[:MAX_REPORTED]:
        print(f"  {item}")
    if len(items) > MAX_REPORTED:
        print(f"  ... and {len(items) - MAX_REPORTED} more")
