<#
.SYNOPSIS
    Capture the UI screenshots of an example from its running local stack.

.DESCRIPTION
    Runs lib/capture.py. The pages come from <Domain>/screenshots.json; each site is opened in a fresh
    browser session, signed in through the stack's identity server when the manifest says so, and every
    page is saved as a 1280x800 WebP under <Domain>/screenshots/. Console errors, failed requests and
    HTTP errors from this machine are reported (exit 1); map tiles and other hosts are not judged.

    The stack must be running (scripts/deploy.ps1 of the generated docker-* tree). The sign-in user must
    exist and hold the roles the pages need; its password is read from $env:CRUFTFREE_SCREENSHOT_PASSWORD
    and never from the command line.

    Needs Python 3.11+ with playwright and pillow, and a Chromium:
        pip install playwright pillow ; playwright install chromium
    $env:CRUFTFREE_BROWSER_EXE names a browser executable to use instead.

    Exit codes: 0 captured cleanly, 1 captured with problems, 2 could not run. See scripts/screenshots/README.md.

.PARAMETER Domain
    The example's folder, for example blog-cms.

.PARAMETER Site
    Capture only this site of the manifest.

.PARAMETER User
    The sign-in user (an e-mail address). Default: $env:CRUFTFREE_SCREENSHOT_USER.

.PARAMETER Markdown
    Print the README gallery for the manifest and exit.

.PARAMETER UpdateReadme
    Write the gallery into <domain>/README.md (between its screenshots markers) and exit.

.PARAMETER SelfTest
    Run the script's own checks, then exit.
#>
[CmdletBinding()]
param(
    [string]$Domain = '',
    [string]$Site = '',
    [string]$User = '',
    [switch]$Markdown,
    [switch]$UpdateReadme,
    [switch]$SelfTest
)

$ErrorActionPreference = 'Stop'

function Find-Python {
    foreach ($candidate in @(@('python'), @('python3'), @('py', '-3'))) {
        $command = Get-Command $candidate[0] -ErrorAction SilentlyContinue
        if (-not $command) { continue }
        $extra = @($candidate | Select-Object -Skip 1)
        & $command.Source @extra -c 'import sys, playwright, PIL; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) { return , (@($command.Source) + $extra) }
    }
    return $null
}

$python = Find-Python
if (-not $python) {
    Write-Host 'Error: no Python 3.11+ with playwright and pillow was found (tried python, python3, py -3).'
    Write-Host 'Install them: pip install playwright pillow ; playwright install chromium'
    exit 2
}

$arguments = @((Join-Path $PSScriptRoot 'lib/capture.py'))
if ($Domain) { $arguments += @('--domain', $Domain) }
if ($Site) { $arguments += @('--site', $Site) }
if ($User) { $arguments += @('--user', $User) }
if ($Markdown) { $arguments += '--markdown' }
if ($UpdateReadme) { $arguments += '--update-readme' }
if ($SelfTest) { $arguments += '--self-test' }

$env:PYTHONIOENCODING = 'utf-8'
$extraPython = @($python | Select-Object -Skip 1)
& $python[0] @extraPython @arguments
exit $LASTEXITCODE
