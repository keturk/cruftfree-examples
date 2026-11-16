<#
.SYNOPSIS
    Commit every change in the cruftfree-examples repository and push it.

.DESCRIPTION
    Runs lib/commit_and_push.py. The commit message is written by a local model (Ollama), with
    Claude Sonnet 5.5 as the fallback; a message given with -Message is used as is. The working tree
    is checked first: paths that must not be published (.env files, secrets, snapshots, node_modules,
    virtual environments, Flutter machine-local files) and personal data or credentials stop the run
    with nothing committed. There is no switch that skips the checks.

    Exit codes: 0 done or nothing to do, 1 stopped by a check or a rejected push, 2 git or Python
    could not run. See scripts/git/README.md.

.PARAMETER Message
    The commit message. Default: written by a model.

.PARAMETER DryRun
    Run the checks and show the message; commit and push nothing.

.PARAMETER NoPush
    Commit, but do not push.

.PARAMETER MessageSource
    auto (default): a local model first, then Claude; if neither answers, a counted message.
    local: only a local model.  claude: only Claude.  A forced source that fails stops the run.

.PARAMETER LocalHosts
    Comma separated hosts to search for Ollama, host or host:port. Default: $env:CRUFTFREE_LOCAL_LLM_HOSTS, then localhost.

.PARAMETER LocalModel
    Ask this model on each host instead of the preferred ones ($env:CRUFTFREE_LOCAL_LLM_MODELS).

.PARAMETER ClaudeModel
    Model for the Claude fallback. Default: claude-sonnet-5-5.

.PARAMETER ClaudeTimeoutMs
    Time allowed for the Claude call. Default: 300000.

.PARAMETER SelfTest
    Run the script's own checks in a scratch repository, then exit.
#>
[CmdletBinding()]
param(
    [string]$Message = '',
    [switch]$DryRun,
    [switch]$NoPush,
    [ValidateSet('auto', 'local', 'claude')][string]$MessageSource = 'auto',
    [string]$LocalHosts = '',
    [string]$LocalModel = '',
    [string]$ClaudeModel = 'claude-sonnet-5-5',
    [int]$ClaudeTimeoutMs = 300000,
    [switch]$SelfTest
)

$ErrorActionPreference = 'Stop'

function Find-Python {
    foreach ($candidate in @(@('python'), @('python3'), @('py', '-3'))) {
        $command = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        $extra = @($candidate | Select-Object -Skip 1)
        & $command.Source @extra -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { return , (@($command.Source) + $extra) }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host 'Error: Python 3.11 or newer was not found (tried python, python3, py -3).'
    exit 2
}

$arguments = @((Join-Path $PSScriptRoot 'lib/commit_and_push.py'))
if ($Message) { $arguments += @('--message', $Message) }
if ($DryRun) { $arguments += '--dry-run' }
if ($NoPush) { $arguments += '--no-push' }
$arguments += @('--message-source', $MessageSource, '--claude-model', $ClaudeModel, '--claude-timeout-ms', $ClaudeTimeoutMs)
if ($LocalHosts) { $arguments += @('--local-hosts', $LocalHosts) }
if ($LocalModel) { $arguments += @('--local-model', $LocalModel) }
if ($SelfTest) { $arguments += '--self-test' }

$env:PYTHONIOENCODING = 'utf-8'
$extraPython = @($python | Select-Object -Skip 1)
& $python[0] @extraPython @arguments
exit $LASTEXITCODE
