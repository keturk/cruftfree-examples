# Git scripts

Two scripts keep this repository in step with its remote. Each is a thin PowerShell wrapper (`.ps1`) or
shell twin (`.sh`) around a Python module in [`lib/`](lib/) that uses only the standard library
(Python 3.11 or newer, and `git`).

| Script | What it does |
|---|---|
| `commit-and-push.ps1` / `.sh` | Checks the working tree, commits every change with a model-written message, pushes. |
| `pull.ps1` / `.sh` | Fetches, fast-forwards (or rebases with `-Rebase`), then summarizes what came in. |

```powershell
scripts/git/commit-and-push.ps1 -DryRun            # checks + the message, nothing changes
scripts/git/commit-and-push.ps1                    # commit and push
scripts/git/commit-and-push.ps1 -Message "Fix X"   # your own message, no model
scripts/git/pull.ps1
scripts/git/pull.ps1 -Rebase -NoSummary
```

```bash
scripts/git/commit-and-push.sh --dry-run
scripts/git/pull.sh --rebase
```

Both accept `-SelfTest` / `--self-test`: the script's own checks, run in a scratch repository with a bare
remote and a stand-in model server. Nothing in this repository is touched.

## Your machine's settings (first-time setup)

Host names, model names and tool paths belong to your machines, so they are not in this repository.
Copy the example and fill in your own values:

```powershell
Copy-Item scripts/git/git-scripts.example.env scripts/git/git-scripts.local.env
```

`git-scripts.local.env` is ignored by git, and the scripts refuse to commit it. Every line is optional;
with no file the scripts use `localhost` and the defaults below. A real environment variable of the same
name overrides the file, and a command-line argument overrides both.

| Setting | Meaning |
|---|---|
| `CRUFTFREE_LOCAL_LLM_HOSTS` | Where to look for Ollama: comma separated `host` or `host:port`. Also added to the text that may never be published. |
| `CRUFTFREE_LOCAL_LLM_MODELS` | Models to ask, in order of preference. |
| `CRUFTFREE_CLAUDE_EXE` | Full path of the Claude Code executable, when it is not found on `PATH`. |
| `CRUFTFREE_EXAMPLES_BLOCKED_TEXT` | More text that must never be published (project or host names). |

## Message and summary writers

The commit message (and the pull summary) comes from, in order:

1. **A local model** served by Ollama. Hosts: `-LocalHosts`, else the `CRUFTFREE_LOCAL_LLM_HOSTS` setting,
   else `localhost`. Models: `-LocalModel`, else the `CRUFTFREE_LOCAL_LLM_MODELS` setting, else
   `qwen3-coder:30b-ctx32k` then `qwen3.6:35b`; a model already loaded on a host is tried first.
2. **Claude Sonnet 5.5** through the Claude Code CLI (`-ClaudeModel`, default `claude-sonnet-5-5`). It runs
   as a plain text call: no tools, no project settings or hooks, a neutral working directory. If the CLI
   is not on `PATH`, or its shim is broken, set `CRUFTFREE_CLAUDE_EXE`.
3. For a commit only, if neither answers: a counted message (`Update examples: 12 files in a, b`).

`-MessageSource local` or `claude` uses only that writer and stops the run if it fails.

## What is refused

The checks run on the working tree before anything is staged. There is no switch that skips them: fix or
remove what they name, then run again. Exit code 1, nothing committed.

- Paths that must never be published: `.env` and `.env.*`, `secrets`, `snapshots`, `node_modules`, `.venv`,
  `.dart_tool`, `.git`, `ephemeral`, and Flutter's machine-local files (`local.properties`,
  `Generated.xcconfig`, `flutter_export_environment.sh`, `.flutter-plugins-dependencies`,
  `flutter_native_integration.env`).
- Text that identifies the person running the script: the home folder, the `git config user.email`
  address, the hosts named in `CRUFTFREE_LOCAL_LLM_HOSTS` (loopback excluded), and anything in
  `CRUFTFREE_EXAMPLES_BLOCKED_TEXT`. A refusal names `file:line` only, never the text.
- `git-scripts.local.env` itself.
- Credential shapes (AWS access keys, GitHub, Slack and OpenAI tokens) and private-key headers outside tests.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Done, or nothing to do |
| 1 | Stopped: a check refused, the push was rejected, a forced message writer failed, the pull diverged or hit a conflict |
| 2 | git or Python could not run |

`pull` never discards local work: a diverged branch stops unless `-Rebase` is given, and a conflict is left
for you to resolve.
