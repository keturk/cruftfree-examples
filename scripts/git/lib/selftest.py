"""Checks of the git scripts, run in a scratch repository with a bare remote and a stand-in Ollama server.

Nothing here touches this repository or the network beyond the loopback interface: the scratch repositories
live in a temporary folder, and the stand-in server answers the three Ollama endpoints the scripts use.
The Claude CLI is never started.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Final

import commit_and_push
import llm
import pull
import settings as machine
from common import EXIT_ERROR, EXIT_OK, EXIT_STOPPED, forbidden_paths, git, personal_strings

REPLY_TEXT: Final = "<think>planning</think>Add demo specs\n\n- adds demo/spec.cfree"
MODEL_NAME: Final = "stand-in-model"
IDENTITY: Final = ("self-test", "self-test@example.invalid")


class StandInOllama(BaseHTTPRequestHandler):
    """Answers /api/ps, /api/tags and /api/chat like an Ollama server holding one resident model."""

    def _send(self, body: dict[str, object]) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802 - the name http.server dispatches on
        self._send({"models": [{"name": MODEL_NAME}]})

    def do_POST(self) -> None:  # noqa: N802
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self._send({"message": {"role": "assistant", "content": REPLY_TEXT}})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Stay quiet."""


@contextlib.contextmanager
def stand_in_server() -> Iterator[str]:
    """``host:port`` of a running stand-in server."""
    server = HTTPServer(("127.0.0.1", 0), StandInOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def setup_clone(remote: Path, target: Path) -> Path:
    """A clone of *remote* at *target* with a commit identity."""
    git(target.parent, "clone", "-q", str(remote), str(target))
    git(target, "config", "user.name", IDENTITY[0])
    git(target, "config", "user.email", IDENTITY[1])
    return target


def write(repo: Path, relative: str, text: str) -> Path:
    """Write *text* to *relative* in *repo*."""
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run_quietly(call: Callable[[], int]) -> tuple[int, str]:
    """The exit code and the printed output of *call*."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = call()
    return code, buffer.getvalue()


def publish_args(repo: Path, *extra: str) -> list[str]:
    return ["--repo", str(repo), *extra]


def head_subject(repo: Path) -> str:
    return git(repo, "log", "-1", "--format=%s").stdout.strip()


class Report:
    """Collects the checks and prints one line each."""

    def __init__(self) -> None:
        self.failed = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + ("" if ok else f"  [{detail}]"))
        self.failed += 0 if ok else 1


def text_checks(report: Report) -> None:
    """Pure functions: message cleaning and the forbidden-path table."""
    long_reply = "x" * 90
    cases = {
        "reasoning block removed": (REPLY_TEXT, "Add demo specs\n\n- adds demo/spec.cfree"),
        "fence and signature removed": ("```\nFix the build\n```\nCo-Authored-By: Someone <a@b.c>", "Fix the build"),
        "quotes removed": ('"Add a page"', "Add a page"),
        "subject cropped to 72": (long_reply, "x" * 69 + "..."),
    }
    for name, (reply, expected) in cases.items():
        report.check(f"clean_message: {name}", llm.clean_message(reply) == expected, llm.clean_message(reply))
    try:
        llm.clean_message("<think>only thinking</think>")
        report.check("clean_message: empty reply refused", False, "no error")
    except llm.LlmUnavailable:
        report.check("clean_message: empty reply refused", True)
    os.environ[llm.CLAUDE_EXE_ENV] = str(Path(tempfile.gettempdir()) / "no-such-claude-binary")
    try:
        report.check("a named but missing Claude binary is not replaced by PATH", llm._claude_exe() is None)
    finally:
        del os.environ[llm.CLAUDE_EXE_ENV]
    paths = {
        "scripts/git/git-scripts.local.env": True, "scripts/git/git-scripts.example.env": False,
        "x/.env": True, "x/.env.example": True, "a-generated/docker-python/secrets/k": True,
        "a-generated/aws-python/.cruftfree/snapshots/s.json": True, "a/node_modules/m.js": True,
        "a-generated/docker-python/config/resolved/client-contract.test.json": True,
        "a-generated/docker-python/config/generated/client-contract.test.json": False,
        "x/android/local.properties": True, "a/ui.cfree": False, "a-generated/aws-python/infra/main.yaml": False,
        "a/environment.md": False,
    }
    for path, refused in paths.items():
        report.check(f"forbidden_paths: {path}", bool(forbidden_paths([path])) == refused)


def settings_checks(report: Report, settings_file: Path) -> None:
    """The per-machine settings file: parsing, precedence and the host names it adds to the blocked text."""
    parsed = machine.parse('# note\n\nCRUFTFREE_LOCAL_LLM_HOSTS = "gpu-box:11434"\nCRUFTFREE_LOCAL_LLM_MODELS=m1,m2\n', "t")
    report.check("settings: comments skipped, quotes removed", parsed == {
        machine.HOSTS: "gpu-box:11434", machine.MODELS: "m1,m2"}, str(parsed))
    for bad in ("CRUFTFREE_LOCAL_LLM_HOST=x\n", "no separator\n"):
        try:
            machine.parse(bad, "t")
            report.check(f"settings: refused {bad.strip()!r}", False, "no error")
        except machine.SettingsError:
            report.check(f"settings: refused {bad.strip()!r}", True)
    report.check("settings: no file means no values", machine.value(machine.HOSTS) == "")
    settings_file.write_text(f"{machine.HOSTS}=192.0.2.55:11434,[2001:db8::7]:11434,localhost\n", encoding="utf-8")
    try:
        report.check("settings: the file supplies a value", machine.value(machine.HOSTS).startswith("192.0.2.55"))
        os.environ[machine.HOSTS] = "from-environment"
        try:
            report.check("settings: the environment overrides the file", machine.value(machine.HOSTS) == "from-environment")
        finally:
            del os.environ[machine.HOSTS]
        chosen = llm.settings_from("auto")
        report.check("settings: hosts come from the file", chosen.hosts[0] == "192.0.2.55:11434", str(chosen.hosts))
        report.check("settings: an argument beats the file", llm.settings_from("auto", "arg-host").hosts == ("arg-host",))
        names = machine.host_names(machine.value(machine.HOSTS))
        report.check("settings: host names without ports or loopback", names == ["192.0.2.55", "2001:db8::7"], str(names))
        blocked = personal_strings(Path(tempfile.gettempdir()))
        report.check("settings: the configured hosts are blocked text", "192.0.2.55" in blocked and "localhost" not in blocked)
    finally:
        settings_file.unlink()


def refusal_checks(report: Report, repo: Path, settings_file: Path) -> None:
    """A path, a blocked text and a token shape each stop the run with nothing committed."""
    before = git(repo, "rev-parse", "HEAD").stdout.strip()
    code, out = run_quietly(lambda: commit_and_push.main(publish_args(repo, "--message", "x", "--no-push")))
    report.check("a clean tree has nothing to commit", code == EXIT_OK and "Nothing to commit" in out, out)
    secret = ("demo/.env", "A=1\n")
    leak_env = {"CRUFTFREE_EXAMPLES_BLOCKED_TEXT": "private-host-name"}
    trials = {
        "a .env file": (secret, {}),
        "blocked text": (("demo/notes.md", "see private-host-name\n"), leak_env),
        "a token shape": (("demo/t.md", "key " + "AKIA" + "A" * 16 + "\n"), {}),
        "a Google API key shape": (("demo/g.md", "key " + "AIza" + "x" * 35 + "\n"), {}),
        "a private key outside tests": (("demo/k.pem", "-----BEGIN " + "RSA PRIVATE KEY-----\n"), {}),
    }
    trials["a host from the settings file"] = (("demo/hosts.md", "model server 192.0.2.55 here\n"), {})
    for name, ((relative, text), env) in trials.items():
        path = write(repo, relative, text)
        if name == "a host from the settings file":
            settings_file.write_text(f"{machine.HOSTS}=192.0.2.55:11434\n", encoding="utf-8")
        os.environ.update(env)
        code, out = run_quietly(lambda: commit_and_push.main(publish_args(repo, "--message", "x", "--no-push")))
        for key in env:
            del os.environ[key]
        path.unlink()
        settings_file.unlink(missing_ok=True)
        report.check(f"refused: {name}", code == EXIT_STOPPED and "Refused" in out, out)
    report.check("refusals committed nothing", git(repo, "rev-parse", "HEAD").stdout.strip() == before)


def publish_checks(report: Report, remote: Path, repo: Path, server: str) -> None:
    """Message sources, commit and push."""
    write(repo, "demo/spec.cfree", "service demo.Service {}\n")
    code, out = run_quietly(
        lambda: commit_and_push.main(publish_args(repo, "--message-source", "local", "--local-hosts", "127.0.0.1:9", "--dry-run"))
    )
    report.check("a forced local source with no host fails", code == EXIT_STOPPED and "no commit message" in out, out)
    original = llm._claude_exe
    llm._claude_exe = lambda: None
    try:
        code, out = run_quietly(
            lambda: commit_and_push.main(publish_args(repo, "--local-hosts", "127.0.0.1:9", "--dry-run"))
        )
    finally:
        llm._claude_exe = original
    report.check("auto with no model falls back to a counted message", code == EXIT_OK and "Update examples: 1 files in demo" in out, out)
    code, out = run_quietly(lambda: commit_and_push.main(publish_args(repo, "--local-hosts", server, "--no-push")))
    report.check("the local model writes the message", code == EXIT_OK and head_subject(repo) == "Add demo specs", out)
    code, out = run_quietly(lambda: commit_and_push.main(publish_args(repo)))
    pushed = git(remote, "log", "-1", "--format=%s").stdout.strip() == "Add demo specs"
    report.check("an unpushed commit is pushed", code == EXIT_OK and pushed, out)


def pull_checks(report: Report, remote: Path, other: Path, repo: Path, server: str) -> None:
    """Fast-forward with a summary, divergence and rebase."""
    code, out = run_quietly(lambda: pull.main(publish_args(other, "--local-hosts", server)))
    report.check("a pull fast-forwards", code == EXIT_OK and "Updated" in out, out)
    report.check("the pull is summarized by the local model", "summary by local model" in out and "- adds demo/spec.cfree" in out, out)
    code, out = run_quietly(lambda: pull.main(publish_args(other)))
    report.check("a second pull is up to date", code == EXIT_OK and "Up to date" in out, out)
    write(repo, "demo/more.cfree", "x\n")
    run_quietly(lambda: commit_and_push.main(publish_args(repo, "--message", "Add more")))
    write(other, "demo/local.cfree", "y\n")
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "Local work")
    code, out = run_quietly(lambda: pull.main(publish_args(other, "--no-summary")))
    report.check("a diverged branch stops", code == EXIT_STOPPED and "Diverged" in out, out)
    code, out = run_quietly(lambda: pull.main(publish_args(other, "--rebase", "--no-summary")))
    report.check("--rebase replays the local commit", code == EXIT_OK and head_subject(other) == "Local work", out)


def run_self_test() -> int:
    """Run every check; the exit code is 0 when all pass. The real settings file is never read."""
    with tempfile.TemporaryDirectory(prefix="examples-git-selftest-") as scratch:
        settings_file = Path(scratch) / "settings.env"
        names = (machine.FILE_ENV, *machine.KEYS)
        saved = {name: os.environ.pop(name) for name in names if name in os.environ}
        os.environ[machine.FILE_ENV] = str(settings_file)
        try:
            return _run_checks(Path(scratch), settings_file)
        finally:
            os.environ.pop(machine.FILE_ENV, None)
            os.environ.update(saved)


def _run_checks(root: Path, settings_file: Path) -> int:
    report = Report()
    print("Pure checks:")
    text_checks(report)
    print("Settings file:")
    settings_checks(report, settings_file)
    with stand_in_server() as server:
        remote = root / "remote.git"
        git(root, "init", "-q", "--bare", "-b", "main", str(remote))
        repo = setup_clone(remote, root / "a")
        write(repo, "README.md", "scratch\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "Initial commit")
        git(repo, "push", "-q", "-u", "origin", "main")
        other = setup_clone(remote, root / "b")
        print("Commit and push:")
        refusal_checks(report, repo, settings_file)
        publish_checks(report, remote, repo, server)
        print("Pull:")
        pull_checks(report, remote, other, repo, server)
    print(f"{'All checks passed.' if report.failed == 0 else str(report.failed) + ' check(s) failed.'}")
    return EXIT_OK if report.failed == 0 else EXIT_ERROR
