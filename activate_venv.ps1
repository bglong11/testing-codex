# PowerShell helper to activate the project virtual environment.
# Usage: .\activate_venv.ps1
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $repoRoot '.venv'
if (-not (Test-Path $venvPath)) {
    Write-Error "Virtual environment not found at $venvPath"
    return
}

$candidateScripts = @(
    "$venvPath\Scripts\Activate.ps1",
    "$venvPath\bin\Activate.ps1"
)

$activateScript = $candidateScripts | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $activateScript) {
    Write-Error "Activation script missing (expected Scripts\\Activate.ps1 or bin/Activate.ps1)"
    return
}

. $activateScript
