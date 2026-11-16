<#
.SYNOPSIS
    Pull the latest cruftfree-examples changes into this clone.

.DESCRIPTION
    Runs lib/pull.py. Fast-forward only unless -Rebase is given; local work is never discarded. After an
    update a local model (Ollama), with Claude Sonnet 5.5 as the fallback, summarizes what came in; the
    summary is a convenience, and the pull still counts as done when no model answers.

    Exit codes: 0 up to date or updated, 1 stopped (local changes in the way, a diverged branch or a
    conflict), 2 git or Python could not run. See scripts/git/README.md.

.PARAMETER Rebase
    When the branch has diverged, replay the local commits on top of the remote ones.

.PARAMETER NoSummary
    Do not ask a model to summarize what came in.

.PARAMETER MessageSource
    auto (default): a local model first, then Claude.  local: only a local model.  claude: only Claude.

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
    [switch]$Rebase,
    [switch]$NoSummary,
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

$arguments = @((Join-Path $PSScriptRoot 'lib/pull.py'))
if ($Rebase) { $arguments += '--rebase' }
if ($NoSummary) { $arguments += '--no-summary' }
$arguments += @('--message-source', $MessageSource, '--claude-model', $ClaudeModel, '--claude-timeout-ms', $ClaudeTimeoutMs)
if ($LocalHosts) { $arguments += @('--local-hosts', $LocalHosts) }
if ($LocalModel) { $arguments += @('--local-model', $LocalModel) }
if ($SelfTest) { $arguments += '--self-test' }

$env:PYTHONIOENCODING = 'utf-8'
$extraPython = @($python | Select-Object -Skip 1)
& $python[0] @extraPython @arguments
exit $LASTEXITCODE
