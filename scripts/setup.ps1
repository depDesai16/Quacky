$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    $PythonCmd = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $PythonCmd) {
    throw "Python was not found on PATH."
}

if ($PythonCmd.Name -eq "py") {
    & py -3 scripts/dev.py setup --python py
} else {
    & python scripts/dev.py setup --python python
}
