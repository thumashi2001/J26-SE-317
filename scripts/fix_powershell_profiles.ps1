# PowerShell Setup Script to install permanent Application Control workarounds
# This script configures user profile scripts across Windows PowerShell and PowerShell Core
# so that python wrapper functions (uvicorn, pytest, etc.) are available in every PowerShell session.

$profileScriptContent = @'
# ==============================================================================
# AdaptiveLearnSE - PowerShell Profile
# Application Control (WDAC / AppLocker) Workaround for Python Virtual Environments
# Supersedes blocked .exe wrappers (uvicorn.exe, pytest.exe, etc.) with safe
# functions that invoke 'python -m <module>' using the active or local venv.
# ==============================================================================

function global:Invoke-PythonModuleSafe {
    param (
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$ModuleName,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ModuleArgs
    )

    # 1. Check if a virtual environment is active ($env:VIRTUAL_ENV)
    if ($env:VIRTUAL_ENV) {
        $venvPy = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
        if (Test-Path -LiteralPath $venvPy) {
            & $venvPy -m $ModuleName @ModuleArgs
            return
        }
    }

    # 2. Check local relative paths for .venv_c3 or .venv
    $candidatePaths = @(
        ".\.venv_c3\Scripts\python.exe",
        ".\.venv\Scripts\python.exe",
        "..\.venv_c3\Scripts\python.exe",
        "..\.venv\Scripts\python.exe",
        "..\..\.venv_c3\Scripts\python.exe",
        "..\..\.venv\Scripts\python.exe",
        "C:\Users\M S I\Desktop\Reserach\DEVELOPMENT\ADAPTIVE_LEARN_SE\ai-services\c3\.venv_c3\Scripts\python.exe",
        "C:\Users\M S I\Desktop\Reserach\DEVELOPMENT\.venv\Scripts\python.exe"
    )
    foreach ($cand in $candidatePaths) {
        if (Test-Path -LiteralPath $cand) {
            $resolvedPy = (Resolve-Path $cand).Path
            & $resolvedPy -m $ModuleName @ModuleArgs
            return
        }
    }

    # 3. Fallback to python in PATH
    python -m $ModuleName @ModuleArgs
}

# Define command functions so PowerShell resolves these BEFORE any .exe in PATH
function global:uvicorn  { Invoke-PythonModuleSafe "uvicorn"  @args }
function global:pytest   { Invoke-PythonModuleSafe "pytest"   @args }
function global:fastapi  { Invoke-PythonModuleSafe "fastapi"  @args }
function global:pip      { Invoke-PythonModuleSafe "pip"      @args }
function global:pip3     { Invoke-PythonModuleSafe "pip"      @args }
function global:httpx    { Invoke-PythonModuleSafe "httpx"    @args }
function global:black    { Invoke-PythonModuleSafe "black"    @args }
function global:flake8   { Invoke-PythonModuleSafe "flake8"   @args }
function global:ruff     { Invoke-PythonModuleSafe "ruff"     @args }
function global:mypy     { Invoke-PythonModuleSafe "mypy"     @args }
function global:coverage { Invoke-PythonModuleSafe "coverage" @args }
'@

$targetDirs = @(
    "C:\Users\M S I\OneDrive\Documents\WindowsPowerShell",
    "C:\Users\M S I\Documents\WindowsPowerShell",
    "C:\Users\M S I\OneDrive\Documents\PowerShell",
    "C:\Users\M S I\Documents\PowerShell"
)

foreach ($dir in $targetDirs) {
    if (-not (Test-Path -LiteralPath $dir)) {
        try {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            Write-Host "Created directory: $dir"
        } catch {
            Write-Warning "Could not create $dir - $_"
        }
    }
    if (Test-Path -LiteralPath $dir) {
        $profileFiles = @(
            (Join-Path $dir "profile.ps1"),
            (Join-Path $dir "Microsoft.PowerShell_profile.ps1"),
            (Join-Path $dir "Microsoft.VSCode_profile.ps1")
        )
        foreach ($pf in $profileFiles) {
            try {
                Set-Content -LiteralPath $pf -Value $profileScriptContent -Encoding UTF8
                Write-Host "Successfully installed profile: $pf"
            } catch {
                Write-Warning "Could not write to $pf - $_"
            }
        }
    }
}
