param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Script,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ScriptArgs
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot

function Test-NewTryPython {
    param([string]$Exe)

    if (-not $Exe) {
        return $null
    }

    if (-not (Test-Path -LiteralPath $Exe)) {
        return $null
    }

    $probe = @"
import sys
import pandas as pd
import numpy as np
import scipy
print(sys.executable)
print(sys.version.split()[0])
print(pd.__version__)
print(np.__version__)
print(scipy.__version__)
print(pd.to_datetime(['2025-01-01 00:00:00.123456']).dtype)
"@

    try {
        $out = & $Exe -c $probe 2>$null
    } catch {
        Write-Host "[NewTRY] Runtime inaccessible: $Exe"
        return $null
    }

    if ($LASTEXITCODE -ne 0) {
        return $null
    }

    $dtype = ($out | Select-Object -Skip 5 -First 1)
    if ($dtype -ne "datetime64[ns]") {
        Write-Host "[NewTRY] Runtime rejete: $Exe | to_datetime dtype: $dtype"
        return $null
    }

    return [PSCustomObject]@{
        Exe = $Exe
        Resolved = ($out | Select-Object -First 1)
        PythonVersion = ($out | Select-Object -Skip 1 -First 1)
        PandasVersion = ($out | Select-Object -Skip 2 -First 1)
        NumpyVersion = ($out | Select-Object -Skip 3 -First 1)
        ScipyVersion = ($out | Select-Object -Skip 4 -First 1)
        DatetimeDtype = $dtype
    }
}

function Resolve-NewTryScript {
    param([string]$Value)

    $candidates = New-Object System.Collections.Generic.List[string]

    if ([System.IO.Path]::IsPathRooted($Value)) {
        $candidates.Add($Value)
    } else {
        $candidates.Add((Join-Path (Get-Location) $Value))
        $candidates.Add((Join-Path $ProjectRoot $Value))
        $candidates.Add((Join-Path (Join-Path $ProjectRoot "scripts") $Value))
        $candidates.Add((Join-Path (Join-Path $ProjectRoot "tests") $Value))
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    throw "Script introuvable: $Value"
}

$candidates = New-Object System.Collections.Generic.List[string]

if ($env:NEWTRY_PYTHON) {
    $candidates.Add($env:NEWTRY_PYTHON)
}

$candidates.Add("C:\SierraChart\tools\newtry_python\Scripts\python.exe")
$candidates.Add("C:\SierraChart\tools\python313\python.exe")
$candidates.Add("C:\Users\emman\AppData\Local\Programs\Python\Python313\python.exe")

$runtime = $null
foreach ($candidate in $candidates) {
    $runtime = Test-NewTryPython -Exe $candidate
    if ($runtime) {
        break
    }
}

if (-not $runtime) {
    throw "Aucun runtime NewTRY conforme trouve. Definir NEWTRY_PYTHON vers un Python avec pandas/numpy/scipy et pd.to_datetime(...).dtype == datetime64[ns]."
}

$scriptPath = Resolve-NewTryScript -Value $Script

Write-Host "[NewTRY] Python: $($runtime.Resolved) | version: $($runtime.PythonVersion)"
Write-Host "[NewTRY] pandas: $($runtime.PandasVersion) | numpy: $($runtime.NumpyVersion) | scipy: $($runtime.ScipyVersion) | to_datetime dtype: $($runtime.DatetimeDtype)"
Write-Host "[NewTRY] Script: $scriptPath"

if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$ProjectRoot;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $ProjectRoot
}

& $runtime.Exe $scriptPath @ScriptArgs
exit $LASTEXITCODE
