param(
    [string]$PythonVersion = "3.12",
    [int]$Port = 0,
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Get-EnvValue([string]$Name, [string]$Default = "") {
    $envPath = Join-Path $root ".env"
    if (-not (Test-Path $envPath)) {
        return $Default
    }
    foreach ($rawLine in Get-Content $envPath) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            continue
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        if ($key -ne $Name) {
            continue
        }
        $value = $parts[1].Trim()
        if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        return $value
    }
    return $Default
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & powershell -ExecutionPolicy Bypass -File ".\scripts\check_environment.ps1" -PythonVersion $PythonVersion
    throw "Local virtual environment '.venv' is missing. Create it first with 'py -$PythonVersion -m venv .venv'."
}

if (-not (Test-Path ".env")) {
    throw ".env is missing. Copy .env.example to .env and fill in the required values first."
}

$resolvedHost = Get-EnvValue "APP_HOST" "0.0.0.0"
$resolvedPort = if ($Port -gt 0) { $Port } else { [int](Get-EnvValue "APP_PORT" "8000") }
$env:APP_HOST = $resolvedHost
$env:APP_PORT = "$resolvedPort"

$arguments = @("-m", "uvicorn", "app.main:app", "--host", $resolvedHost, "--port", "$resolvedPort")
if (-not $NoReload) {
    $arguments += "--reload"
}

& ".\.venv\Scripts\python.exe" @arguments
