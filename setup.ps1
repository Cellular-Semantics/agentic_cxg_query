#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

$MinPython = '3.10'
$MaxPython = '3.13'

function Info([string]$Message) { Write-Host "[INFO]  $Message" -ForegroundColor Blue }
function Ok([string]$Message) { Write-Host "[OK]    $Message" -ForegroundColor Green }
function Warn([string]$Message) { Write-Host "[WARN]  $Message" -ForegroundColor Yellow }
function Fail([string]$Message) { Write-Host "[FAIL]  $Message" -ForegroundColor Red; exit 1 }

function Get-PythonVersion {
    param(
        [Parameter(Mandatory = $true)][string]$Command,
        [string[]]$BaseArgs = @()
    )

    try {
        $version = & $Command @BaseArgs -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if (-not $version) { return $null }
        return $version.Trim()
    } catch {
        return $null
    }
}

function Test-PythonVersionInRange {
    param([Parameter(Mandatory = $true)][string]$Version)

    try {
        $v = [Version]::Parse("$Version.0")
        $minV = [Version]::Parse("$MinPython.0")
        $maxV = [Version]::Parse("$MaxPython.0")
        return ($v -ge $minV -and $v -lt $maxV)
    } catch {
        return $false
    }
}

function Sync-FileIfDifferent {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (Test-Path $Destination) {
        $srcHash = (Get-FileHash -Algorithm SHA256 -Path $Source).Hash
        $dstHash = (Get-FileHash -Algorithm SHA256 -Path $Destination).Hash
        if ($srcHash -eq $dstHash) {
            return $false
        }
    }

    $destParent = Split-Path -Parent $Destination
    if (-not (Test-Path $destParent)) {
        New-Item -ItemType Directory -Path $destParent -Force | Out-Null
    }

    Copy-Item -Path $Source -Destination $Destination -Force
    return $true
}

function Sync-MirrorDirectory {
    param(
        [Parameter(Mandatory = $true)][string]$SourceDir,
        [Parameter(Mandatory = $true)][string]$DestinationDir
    )

    New-Item -ItemType Directory -Path $DestinationDir -Force | Out-Null

    if (Get-Command robocopy -ErrorAction SilentlyContinue) {
        robocopy $SourceDir $DestinationDir /MIR /NFL /NDL /NJH /NJS /NP /R:1 /W:1 | Out-Null
        $code = $LASTEXITCODE
        if ($code -gt 7) {
            throw "robocopy failed with exit code $code"
        }
        return
    }

    # Fallback if robocopy is unavailable.
    if (Test-Path $DestinationDir) {
        Get-ChildItem -Path $DestinationDir -Recurse -Force | Remove-Item -Recurse -Force
    }
    Copy-Item -Path (Join-Path $SourceDir '*') -Destination $DestinationDir -Recurse -Force
}

# ---- Check Python -----------------------------------------------------------

$candidates = @(
    @{ Command = 'py'; Args = @('-3.12') },
    @{ Command = 'py'; Args = @('-3.11') },
    @{ Command = 'py'; Args = @('-3.10') },
    @{ Command = 'python3.12'; Args = @() },
    @{ Command = 'python3.11'; Args = @() },
    @{ Command = 'python3.10'; Args = @() },
    @{ Command = 'python'; Args = @() },
    @{ Command = 'python3'; Args = @() }
)

$PythonCommand = $null
$PythonArgs = @()
$PyVersion = $null

foreach ($candidate in $candidates) {
    if (-not (Get-Command $candidate.Command -ErrorAction SilentlyContinue)) {
        continue
    }

    $version = Get-PythonVersion -Command $candidate.Command -BaseArgs $candidate.Args
    if (-not $version) {
        continue
    }

    if (Test-PythonVersionInRange -Version $version) {
        $PythonCommand = $candidate.Command
        $PythonArgs = $candidate.Args
        $PyVersion = $version
        break
    }
}

if (-not $PythonCommand) {
    Fail "No compatible Python found. Install Python >=$MinPython and <$MaxPython (python 3.10, 3.11, or 3.12)."
}

Info "Found $PythonCommand $PyVersion"
Ok "Python version OK (>=$MinPython, <$MaxPython)"

# ---- Create venv ------------------------------------------------------------

if (-not (Test-Path '.venv')) {
    Info 'Creating virtual environment...'
    & $PythonCommand @PythonArgs -m venv .venv
    Ok 'Virtual environment created'
} else {
    Info 'Virtual environment already exists'
}

$VenvPython = Join-Path '.venv' 'Scripts/python.exe'
if (-not (Test-Path $VenvPython)) {
    Fail "Expected venv interpreter not found at $VenvPython"
}

# ---- Install ----------------------------------------------------------------

Info 'Installing dependencies (editable)...'
& $VenvPython -m pip install --upgrade pip -q
& $VenvPython -m pip install -e '.[dev]' -q
Ok 'Dependencies installed'

# ---- Verify imports ---------------------------------------------------------

Info 'Verifying imports...'
& $VenvPython -c @"
from cxg_query_enhancer import enhance
from gene_resolver import resolve_genes, build_var_value_filter
print('  cxg_query_enhancer.enhance ......... OK')
print('  gene_resolver.resolve_genes ........ OK')
print('  gene_resolver.build_var_value_filter OK')
"@
Ok 'All imports verified'

# ---- Refresh census field lookups ------------------------------------------

Info 'Refreshing census field lookups...'
& $VenvPython 'src/refresh_census_fields.py'
Ok 'Census field lookups refreshed'

# ---- Check OLS4 MCP ---------------------------------------------------------

Info 'Checking OLS4 MCP connectivity...'
try {
    $response = Invoke-WebRequest -Uri 'http://www.ebi.ac.uk/ols4/api/mcp' -Method Head -TimeoutSec 10 -MaximumRedirection 3 -SkipHttpErrorCheck
    $statusCode = [int]$response.StatusCode
    if ($statusCode -eq 200 -or $statusCode -eq 405) {
        Ok "OLS4 MCP reachable (HTTP $statusCode)"
    } else {
        Warn "OLS4 MCP returned HTTP $statusCode (may still work via MCP protocol)"
    }
} catch {
    Warn 'Could not check OLS4 MCP connectivity (network issue?)'
}

# ---- Refresh obsolete-stage lookups ----------------------------------------

Info 'Refreshing obsolete developmental-stage lookups from Ubergraph...'
if ((Get-Command bash -ErrorAction SilentlyContinue) -and (Test-Path './data/refresh_obsolete_stages.sh')) {
    try {
        bash ./data/refresh_obsolete_stages.sh
        if ($LASTEXITCODE -eq 0) {
            Ok 'Obsolete-stage lookups refreshed'
        } else {
            Warn 'Could not refresh obsolete-stage lookups (network issue?). Using cached files.'
        }
    } catch {
        Warn 'Could not refresh obsolete-stage lookups (network issue?). Using cached files.'
    }
} else {
    Warn 'Skipping obsolete-stage refresh (bash not available on this system). Using cached files.'
}

# ---- Sync shared config (.claude -> .codex) --------------------------------

Info 'Syncing shared configs from .claude to .codex...'

# Agents
$agentsSrcDir = '.claude/agents'
$agentsDestDir = '.codex/agents'
if (Test-Path $agentsSrcDir) {
    New-Item -ItemType Directory -Path $agentsDestDir -Force | Out-Null
    Get-ChildItem -Path $agentsSrcDir -Filter '*.md' -File | ForEach-Object {
        $dest = Join-Path $agentsDestDir $_.Name
        if (Sync-FileIfDifferent -Source $_.FullName -Destination $dest) {
            Ok "  Synced agents/$($_.Name)"
        }
    }
}

# Skills (mirror entire skill directories)
$skillsSrcRoot = '.claude/skills'
$skillsDestRoot = '.codex/skills'
if (Test-Path $skillsSrcRoot) {
    New-Item -ItemType Directory -Path $skillsDestRoot -Force | Out-Null
    Get-ChildItem -Path $skillsSrcRoot -Directory | ForEach-Object {
        $destDir = Join-Path $skillsDestRoot $_.Name
        Sync-MirrorDirectory -SourceDir $_.FullName -DestinationDir $destDir
        Ok "  Synced skills/$($_.Name)/"
    }
}

# AGENTS.md <- CLAUDE.md
if (Test-Path 'CLAUDE.md') {
    if (Sync-FileIfDifferent -Source 'CLAUDE.md' -Destination 'AGENTS.md') {
        Ok '  Synced AGENTS.md'
    }
}

# ---- Done -------------------------------------------------------------------

Write-Host ''
Ok 'Setup complete!'
Write-Host ''
Info 'Activate the environment:'
Write-Host '  .\.venv\Scripts\Activate.ps1'
Write-Host ''
Info 'Usage with Claude Code:'
Write-Host '  claude'
Write-Host '  /cxg-query female T cells in lung tissue'
Write-Host ''
Info 'Run tests:'
Write-Host '  make test'
