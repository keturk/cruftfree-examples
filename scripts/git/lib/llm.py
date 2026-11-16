"""Text from a local Ollama model, with the Claude Code CLI as the fallback.

Used by the git scripts to write a commit message and to summarize what a pull brought in.

Local models are looked for on the hosts named by ``--local-hosts`` or the setting
``CRUFTFREE_LOCAL_LLM_HOSTS`` (comma separated, ``host`` or ``host:port``; default ``localhost``),
which comes from the environment or the git-ignored settings file (``settings.py``).
Host names belong to the machine, not to this repository, so none is written here. On each
reachable host a model already in memory is used first; when none is resident, the first of the
preferred models (``CRUFTFREE_LOCAL_LLM_MODELS``, comma separated) that the host has installed is
asked, which loads it. A model that fails to answer hands over to the next one. When no local
model answers, the Claude Code CLI is run with Claude Sonnet 5.5 as a pure text call: no tools,
no project settings, no hooks, and a neutral working directory.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import settings as machine

SOURCE_AUTO: Final = "auto"
SOURCE_LOCAL: Final = "local"
SOURCE_CLAUDE: Final = "claude"
SOURCES: Final = (SOURCE_AUTO, SOURCE_LOCAL, SOURCE_CLAUDE)

HOSTS_ENV: Final = machine.HOSTS
MODELS_ENV: Final = machine.MODELS
CLAUDE_EXE_ENV: Final = machine.CLAUDE_EXE
DEFAULT_HOSTS: Final = ("localhost",)
DEFAULT_MODELS: Final = ("qwen3-coder:30b-ctx32k", "qwen3.6:35b")
OLLAMA_PORT: Final = 11434
DEFAULT_CLAUDE_MODEL: Final = "claude-sonnet-5-5"

REACHABLE_TIMEOUT_S: Final = 3
LOCAL_TIMEOUT_S: Final = 180
DEFAULT_CLAUDE_TIMEOUT_MS: Final = 300000
MS_PER_S: Final = 1000
KEEP_ALIVE: Final = "10m"
CONTEXT_TOKENS: Final = 16384
TEMPERATURE: Final = 0.2

SUBJECT_LIMIT: Final = 72
THINK_BLOCK: Final = re.compile(r"<think>.*?</think>", re.DOTALL)
THINK_CLOSE: Final = "</think>"
FENCE_LINE: Final = re.compile(r"^\s*```\w*\s*$")
#: A model sometimes signs its work; the commit author is the person running the script.
ATTRIBUTION_LINES: Final = (
    re.compile(r"^\s*co-authored-by:.*$", re.IGNORECASE),
    re.compile(r"^\s*(?:\W*\s*)?generated (?:with|by) .*$", re.IGNORECASE),
)
BATCH_SHIM_SUFFIXES: Final = frozenset({".bat", ".cmd"})
CMD_METACHARACTERS: Final = frozenset('&|<>^%!"()\r\n')


class LlmUnavailable(RuntimeError):
    """No backend produced text."""


@dataclass(frozen=True)
class LlmSettings:
    """Which backends to try, and with what."""

    source: str
    hosts: tuple[str, ...]
    models: tuple[str, ...]
    local_model: str
    claude_model: str
    claude_timeout_ms: int


def _split(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in text.split(",") if part.strip())


def settings_from(
    source: str,
    local_hosts: str = "",
    local_model: str = "",
    claude_model: str = DEFAULT_CLAUDE_MODEL,
    claude_timeout_ms: int = DEFAULT_CLAUDE_TIMEOUT_MS,
) -> LlmSettings:
    """The settings of a run: the arguments, then the environment and the settings file, then the defaults."""
    hosts = _split(local_hosts) or _split(machine.value(HOSTS_ENV)) or DEFAULT_HOSTS
    models = _split(machine.value(MODELS_ENV)) or DEFAULT_MODELS
    return LlmSettings(source, hosts, models, local_model, claude_model, claude_timeout_ms)


def strip_reasoning(text: str) -> str:
    """*text* without a reasoning block a thinking model put in front of its answer."""
    without = THINK_BLOCK.sub("", text)
    if THINK_CLOSE in without:
        without = without.split(THINK_CLOSE, 1)[1]
    return without.strip()


def clean_message(text: str) -> str:
    """A commit message from a model's reply.

    Reasoning blocks, code fences, quotes around the whole reply and signature lines are removed,
    and the subject line is cut to ``SUBJECT_LIMIT`` characters.

    Raises:
        LlmUnavailable: when nothing is left.
    """
    kept = [
        line.rstrip()
        for line in strip_reasoning(text).splitlines()
        if not FENCE_LINE.match(line) and not any(p.match(line) for p in ATTRIBUTION_LINES)
    ]
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1].strip():
        kept.pop()
    if not kept:
        raise LlmUnavailable("The model returned no message.")
    subject = kept[0].strip().strip("\"'`")
    if len(subject) > SUBJECT_LIMIT:
        subject = subject[: SUBJECT_LIMIT - 3].rstrip() + "..."
    return "\n".join([subject, *kept[1:]])


def clean_summary(text: str) -> str:
    """A summary from a model's reply, without reasoning blocks, fences or signature lines."""
    kept = [
        line.rstrip()
        for line in strip_reasoning(text).splitlines()
        if not FENCE_LINE.match(line) and not any(p.match(line) for p in ATTRIBUTION_LINES)
    ]
    summary = "\n".join(kept).strip()
    if not summary:
        raise LlmUnavailable("The model returned no summary.")
    return summary


def _base_url(host: str) -> str:
    return f"http://{host}" if ":" in host else f"http://{host}:{OLLAMA_PORT}"


def _fetch_json(url: str, timeout_s: int) -> dict[str, object]:
    with urllib.request.urlopen(url, timeout=timeout_s) as response:  # noqa: S310 - an http URL built from a host name
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{url} answered {type(data).__name__}, not an object")
    return data


def _post_json(url: str, body: dict[str, object], timeout_s: int) -> dict[str, object]:
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:  # noqa: S310
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{url} answered {type(data).__name__}, not an object")
    return data


def _names(listing: dict[str, object]) -> list[str]:
    models = listing.get("models")
    if not isinstance(models, list):
        return []
    return [str(m["name"]) for m in models if isinstance(m, dict) and "name" in m]


def _same_model(installed: str, wanted: str) -> bool:
    return installed == wanted or installed == f"{wanted}:latest"


def local_candidates(settings: LlmSettings, report: Callable[[str], None]) -> list[tuple[str, str]]:
    """``(base url, model)`` pairs to ask, best first: resident models, then installed preferred ones."""
    resident: list[tuple[str, str]] = []
    to_load: list[tuple[str, str]] = []
    for host in settings.hosts:
        base = _base_url(host)
        try:
            loaded = [n for n in _names(_fetch_json(f"{base}/api/ps", REACHABLE_TIMEOUT_S)) if "embed" not in n]
            installed = _names(_fetch_json(f"{base}/api/tags", REACHABLE_TIMEOUT_S))
        except (OSError, ValueError, urllib.error.URLError) as exc:
            report(f"  {host}: not reachable ({exc})")
            continue
        wanted = (settings.local_model,) if settings.local_model else settings.models
        if settings.local_model:
            resident += [(base, n) for n in loaded if _same_model(n, settings.local_model)]
        else:
            resident += [(base, n) for n in loaded]
        if not loaded or settings.local_model:
            match = next((n for w in wanted for n in installed if _same_model(n, w)), None)
            if match is not None and (base, match) not in resident:
                to_load.append((base, match))
        report(f"  {host}: {len(loaded)} model(s) in memory, {len(installed)} installed")
    return resident + to_load


def ask_local(
    system: str, prompt: str, settings: LlmSettings, report: Callable[[str], None]
) -> tuple[str, str]:
    """``(label, text)`` of the first answer from a local model.

    Raises:
        LlmUnavailable: when no host is reachable or no model answers.
    """
    candidates = local_candidates(settings, report)
    if not candidates:
        raise LlmUnavailable("No local model host is reachable with a usable model.")
    for base, model in candidates:
        body: dict[str, object] = {
            "model": model,
            "stream": False,
            "think": False,
            "keep_alive": KEEP_ALIVE,
            "options": {"temperature": TEMPERATURE, "num_ctx": CONTEXT_TOKENS},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        try:
            reply = _post_json(f"{base}/api/chat", body, LOCAL_TIMEOUT_S)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            report(f"  {model} on {base}: no answer ({exc})")
            continue
        message = reply.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and strip_reasoning(content):
            return f"local model {model}", strip_reasoning(content)
        report(f"  {model} on {base}: empty answer")
    raise LlmUnavailable("No local model answered.")


def _claude_exe() -> str | None:
    """The Claude CLI: the file named by the ``CRUFTFREE_CLAUDE_EXE`` setting, else the first one on PATH."""
    named = machine.value(CLAUDE_EXE_ENV)
    if named:
        return named if Path(named).is_file() else None
    for name in ("claude.cmd", "claude.exe", "claude"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _require_batch_safe(command: list[str]) -> None:
    """Refuse an argument ``cmd.exe`` would parse when the CLI is a Windows batch shim."""
    if Path(command[0]).suffix.lower() not in BATCH_SHIM_SUFFIXES:
        return
    unsafe = [a for a in command[1:] if CMD_METACHARACTERS & set(a)]
    if unsafe:
        raise LlmUnavailable(f"claude is a batch shim and these arguments hold characters cmd.exe parses: {unsafe}")


def ask_claude(system: str, prompt: str, settings: LlmSettings) -> str:
    """Claude's answer to *prompt*, as a pure text call.

    The prompt goes to stdin, so a long change summary cannot overflow the command line. The call
    gets no tools, none of the project's settings, hooks or skills, and a neutral working directory.

    Raises:
        LlmUnavailable: when the CLI is missing, times out, fails or returns no text.
    """
    exe = _claude_exe()
    if exe is None:
        raise LlmUnavailable(
            f"The claude CLI was not found (set {CLAUDE_EXE_ENV} to its path, or install it: "
            "npm install -g @anthropic-ai/claude-code)"
        )
    with tempfile.TemporaryDirectory(prefix="examples-git-") as neutral:
        settings_file = Path(neutral) / "settings.json"
        settings_file.write_text(json.dumps({"includeCoAuthoredBy": False}), encoding="utf-8")
        command = [
            exe, "-p", "--model", settings.claude_model, "--output-format", "json", "--tools", "",
            "--safe-mode", "--no-session-persistence", "--settings", str(settings_file), "--system-prompt", system,
        ]
        _require_batch_safe(command)
        try:
            done = subprocess.run(
                command, input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                cwd=neutral, env={**os.environ, "NO_COLOR": "1"}, timeout=max(1.0, settings.claude_timeout_ms / MS_PER_S),
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise LlmUnavailable(f"The claude CLI timed out after {settings.claude_timeout_ms} ms.") from exc
    if done.returncode != 0:
        raise LlmUnavailable(f"The claude CLI exited {done.returncode}: {(done.stderr or done.stdout).strip()[:300]}")
    try:
        data = json.loads(done.stdout)
    except json.JSONDecodeError as exc:
        raise LlmUnavailable(f"The claude CLI returned non-JSON output: {exc}") from exc
    result = data.get("result") if isinstance(data, dict) else None
    if not isinstance(result, str) or not result.strip():
        raise LlmUnavailable("The claude CLI returned no text.")
    return result


def ask(system: str, prompt: str, settings: LlmSettings, report: Callable[[str], None]) -> tuple[str, str]:
    """``(label of the backend, text)`` from the local models, then Claude, as the source allows.

    Raises:
        LlmUnavailable: when every allowed backend failed; the message names each failure.
    """
    failures: list[str] = []
    if settings.source in (SOURCE_AUTO, SOURCE_LOCAL):
        report("Looking for a local model:")
        try:
            return ask_local(system, prompt, settings, report)
        except LlmUnavailable as exc:
            failures.append(f"local: {exc}")
            report(f"  {exc}")
    if settings.source in (SOURCE_AUTO, SOURCE_CLAUDE):
        report(f"Asking the claude CLI ({settings.claude_model}):")
        try:
            return f"claude {settings.claude_model}", ask_claude(system, prompt, settings)
        except LlmUnavailable as exc:
            failures.append(f"claude: {exc}")
            report(f"  {exc}")
    raise LlmUnavailable("; ".join(failures))
