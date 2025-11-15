# PowerShell helper to activate the project virtual environment.
# Usage: .\activate_venv.ps1
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $repoRoot '.venv'
if (-not (Test-Path $venvPath)) {
    Write-Error "Virtual environment not found at $venvPath"
    return
}
$activateScript = Join-Path $venvPath 'Scripts\Activate.ps1'
if (-not (Test-Path $activateScript)) {
    Write-Error "Activation script missing: $activateScript"
    return
}
. $activateScript
