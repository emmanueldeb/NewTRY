$ErrorActionPreference = "Stop"

$RuntimeDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $RuntimeDir
$RunPython = Join-Path $RuntimeDir "run_python.cmd"

Write-Host "[NewTRY] check_runtime.py"
& $RunPython "scripts\check_runtime.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[NewTRY] check_time_units.py"
& $RunPython "scripts\check_time_units.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[NewTRY] check_durationus_semantics.py"
& $RunPython "scripts\check_durationus_semantics.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[NewTRY] tests/test_time_units.py"
& $RunPython "tests\test_time_units.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[NewTRY] Environment OK: $ProjectRoot"
exit 0
