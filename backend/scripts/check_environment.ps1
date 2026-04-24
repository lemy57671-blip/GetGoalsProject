param(
    [string]$PythonVersion = "3.12",
    [switch]$SkipImports
)

$ErrorActionPreference = "Stop"

function Write-Ok([string]$Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail([string]$Message) {
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Get-EnvValues([string]$Path) {
    $result = @{}
    if (-not (Test-Path $Path)) {
        return $result
    }
    foreach ($rawLine in Get-Content $Path) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $result[$key] = $value
    }
    return $result
}

function Get-PythonVersion([string]$PythonExecutable) {
    try {
        return (& $PythonExecutable -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')") 2>$null
    } catch {
        return $null
    }
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$selectedPython = $null
if (Test-Path ".venv\Scripts\python.exe") {
    $venvVersion = Get-PythonVersion ".venv\Scripts\python.exe"
    if ($venvVersion -eq $PythonVersion) {
        $selectedPython = ".venv\Scripts\python.exe"
        Write-Ok "Local virtual environment uses Python $PythonVersion."
    }
}

if (-not $selectedPython) {
    $pyList = & py -0p 2>$null
    if ($pyList) {
        foreach ($line in $pyList) {
            if ($line -match [regex]::Escape($PythonVersion)) {
                $selectedPython = $line
                break
            }
        }
    }
}

if (-not $selectedPython) {
    Write-Fail "Python $PythonVersion was not found via '.venv' or the Python launcher. Install Python 3.12 or 3.13 before booting FastAPI."
    if ($pyList) {
        Write-Host $pyList
    }
    exit 1
}

if ($selectedPython -ne ".venv\Scripts\python.exe") {
    Write-Ok "Python $PythonVersion is available."
}

$odbcDrivers = & powershell -NoProfile -Command "try { Get-ItemProperty 'HKLM:\SOFTWARE\ODBC\ODBCINST.INI\ODBC Drivers' -ErrorAction Stop | Format-List } catch { '' }" 2>$null
if ($odbcDrivers -and ($odbcDrivers | Out-String) -match "ODBC Driver 18 for SQL Server") {
    Write-Ok "ODBC Driver 18 for SQL Server is installed."
} else {
    Write-Warn "ODBC Driver 18 for SQL Server was not detected. SQL Server connections may fail."
}

$envExample = Join-Path $root ".env.example"
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Warn ".env is missing. Copy .env.example to .env before running FastAPI."
} else {
    Write-Ok ".env file exists."
    $envValues = Get-EnvValues $envFile
    foreach ($requiredKey in @("SQLSERVER_CONNECTION_STRING", "AUTH_JWT_KEY")) {
        if ([string]::IsNullOrWhiteSpace($envValues[$requiredKey])) {
            Write-Fail "$requiredKey is required in .env."
            exit 1
        }
    }

    $runtimeRoot = $envValues["FASTAPI_RUNTIME_ROOT"]
    if ([string]::IsNullOrWhiteSpace($runtimeRoot)) {
        $runtimeRoot = "runtime"
    }
    if ([System.IO.Path]::IsPathRooted($runtimeRoot)) {
        $runtimeBase = $runtimeRoot
    } else {
        $runtimeBase = Join-Path $root $runtimeRoot
    }

    $toeicRoot = $envValues["TOEIC_STATIC_ROOT"]
    if ([string]::IsNullOrWhiteSpace($toeicRoot)) {
        $toeicRoot = Join-Path $runtimeBase "static\\toeic"
    } elseif (-not [System.IO.Path]::IsPathRooted($toeicRoot)) {
        $toeicRoot = Join-Path $root $toeicRoot
    }

    $audioRoot = $envValues["AUDIO_STATIC_ROOT"]
    if ([string]::IsNullOrWhiteSpace($audioRoot)) {
        $audioRoot = Join-Path $runtimeBase "media\\audio"
    } elseif (-not [System.IO.Path]::IsPathRooted($audioRoot)) {
        $audioRoot = Join-Path $root $audioRoot
    }

    $imageRoot = $envValues["IMAGE_STATIC_ROOT"]
    if ([string]::IsNullOrWhiteSpace($imageRoot)) {
        $imageRoot = Join-Path $runtimeBase "media\\images"
    } elseif (-not [System.IO.Path]::IsPathRooted($imageRoot)) {
        $imageRoot = Join-Path $root $imageRoot
    }

    $roadmapRules = $envValues["ROADMAP_RULES_PATH"]
    if ([string]::IsNullOrWhiteSpace($roadmapRules)) {
        $roadmapRules = Join-Path $runtimeBase "config\\toeic_roadmap_rules.json"
    } elseif (-not [System.IO.Path]::IsPathRooted($roadmapRules)) {
        $roadmapRules = Join-Path $root $roadmapRules
    }

    foreach ($pathCheck in @(
        @{ Label = "TOEIC static root"; Path = $toeicRoot },
        @{ Label = "Audio static root"; Path = $audioRoot },
        @{ Label = "Image static root"; Path = $imageRoot }
    )) {
        if (Test-Path $pathCheck.Path) {
            Write-Ok "$($pathCheck.Label) exists at $($pathCheck.Path)"
        } else {
            Write-Warn "$($pathCheck.Label) is missing at $($pathCheck.Path). Restore the FastAPI runtime assets before booting."
        }
    }

    if (Test-Path $roadmapRules) {
        Write-Ok "Roadmap rules file exists at $roadmapRules"
    } else {
        Write-Warn "Roadmap rules file is missing at $roadmapRules."
    }
}

if (-not $SkipImports) {
    $importScript = "import fastapi, sqlalchemy, pydantic, httpx, jwt; print('imports-ok')"
    try {
        if ($selectedPython -eq ".venv\Scripts\python.exe") {
            $importResult = & ".\.venv\Scripts\python.exe" -c $importScript 2>&1
        } else {
            $importResult = & py "-$PythonVersion" -c $importScript 2>&1
        }
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Core Python packages import successfully."
        } else {
            Write-Warn "Core Python imports failed. Install requirements.txt in the Python $PythonVersion environment."
            Write-Host $importResult
        }
    } catch {
        Write-Warn "Core Python imports failed. Install requirements.txt in the Python $PythonVersion environment."
    }
}

Write-Host ""
Write-Host "Next step:"
Write-Host "  py -$PythonVersion -m venv .venv"
Write-Host "  .\\.venv\\Scripts\\Activate.ps1"
Write-Host "  pip install -r requirements.txt"
Write-Host "  .\\scripts\\run_local.ps1"
