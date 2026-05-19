param(
    [string]$BaseUrl = "http://127.0.0.1:8001"
)

$ErrorActionPreference = "Stop"

function Test-Endpoint {
    param(
        [string]$Method,
        [string]$Path
    )

    $uri = "$BaseUrl$Path"
    try {
        if ($Method -eq "GET") {
            $null = Invoke-RestMethod -Uri $uri -Method Get -TimeoutSec 30
        } else {
            throw "Unsupported method: $Method"
        }
        Write-Host "[PASS] $Method $Path"
    } catch {
        Write-Host "[FAIL] $Method $Path :: $($_.Exception.Message)"
        throw
    }
}

Write-Host "Running FastAPI smoke checks against $BaseUrl"
Test-Endpoint -Method GET -Path "/api/health"
Test-Endpoint -Method GET -Path "/api/diagnostic/questions"
Test-Endpoint -Method GET -Path "/api/toeic/import-status"
Test-Endpoint -Method GET -Path "/api/toeic/summary"
Write-Host "Smoke checks completed."
