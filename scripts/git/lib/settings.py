"""Per-machine settings of the git scripts: host names, model names and tool paths.

These belong to one person's machines, never to the public repository. They are read from
``scripts/git/git-scripts.local.env``, a file git ignores; ``git-scripts.example.env`` next to it, which
is committed, shows every key with a placeholder. A real environment variable of the same name
overrides the file, and a command-line argument overrides both.

The file is ``KEY=value`` lines; blank lines and lines starting with ``#`` are skipped, and one pair of
quotes around a value is removed. A key that is not listed in ``KEYS`` is an error, so a misspelled
name cannot silently leave a setting unset.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final

FILE_NAME: Final = "git-scripts.local.env"
EXAMPLE_NAME: Final = "git-scripts.example.env"
#: Names a different settings file; used by the self-test so it never reads the real one.
FILE_ENV: Final = "CRUFTFREE_EXAMPLES_SETTINGS_FILE"

HOSTS: Final = "CRUFTFREE_LOCAL_LLM_HOSTS"
MODELS: Final = "CRUFTFREE_LOCAL_LLM_MODELS"
CLAUDE_EXE: Final = "CRUFTFREE_CLAUDE_EXE"
BLOCKED_TEXT: Final = "CRUFTFREE_EXAMPLES_BLOCKED_TEXT"
KEYS: Final = (HOSTS, MODELS, CLAUDE_EXE, BLOCKED_TEXT)
#: Host names that every machine has and that generated code legitimately contains.
LOOPBACK: Final = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0"})


class SettingsError(ValueError):
    """The settings file cannot be used."""


def settings_path() -> Path:
    """The settings file: ``CRUFTFREE_EXAMPLES_SETTINGS_FILE`` if set, else the one beside the scripts."""
    named = os.environ.get(FILE_ENV, "").strip()
    return Path(named) if named else Path(__file__).resolve().parents[1] / FILE_NAME


def parse(text: str, origin: str) -> dict[str, str]:
    """The ``KEY=value`` pairs of *text*.

    Raises:
        SettingsError: on a line that is not ``KEY=value`` or a key not in ``KEYS``.
    """
    found: dict[str, str] = {}
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or key not in KEYS:
            raise SettingsError(f"{origin}:{number}: expected KEY=value with KEY one of {', '.join(KEYS)}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        found[key] = value
    return found


def from_file() -> dict[str, str]:
    """The pairs in the settings file; empty when the file does not exist."""
    path = settings_path()
    if not path.is_file():
        return {}
    return parse(path.read_text(encoding="utf-8"), path.name)


def value(key: str) -> str:
    """The setting *key*: the environment variable, else the settings file, else the empty string."""
    return os.environ.get(key, "").strip() or from_file().get(key, "").strip()


def host_names(hosts: str) -> list[str]:
    """The host part (no port, no brackets) of each entry of a comma separated host list, loopback excluded."""
    names: list[str] = []
    for entry in (part.strip() for part in hosts.split(",")):
        if not entry:
            continue
        name = entry[1:].split("]", 1)[0] if entry.startswith("[") else entry.rsplit(":", 1)[0] if entry.count(":") == 1 else entry
        if name and name.lower() not in LOOPBACK:
            names.append(name)
    return names
