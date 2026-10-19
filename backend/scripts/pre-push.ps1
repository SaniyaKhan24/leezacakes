param([switch]$SkipDependencyAudit)
$ErrorActionPreference = "Stop"
$backend = Split-Path -Parent $PSScriptRoot
$python = Join-Path $backend ".venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Missing backend/.venv. Follow README setup instructions."
    exit 1
}
$arguments = @((Join-Path $PSScriptRoot "checks.py"))
if ($SkipDependencyAudit) { $arguments += "--skip-dependency-audit" }
& $python @arguments
exit $LASTEXITCODE
