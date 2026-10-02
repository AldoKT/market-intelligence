$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Payload = Join-Path $Root "payloads\latest_2026-09-29"

Write-Host ""
Write-Host "=== Starting SIGNAL Latest Historical Snapshot ===" -ForegroundColor Magenta
Write-Host "Snapshot: 2026-09-29"
Write-Host "No Sectors API calls are made."
Write-Host ""

if (-not (Test-Path $Backend)) { throw "Backend folder not found: $Backend" }
if (-not (Test-Path $Frontend)) { throw "Frontend folder not found: $Frontend" }
if (-not (Test-Path $Payload)) { throw "Demo payload folder not found: $Payload" }

$backendCommand = "Set-Location -LiteralPath '$Backend'; `$env:SIGNAL_PAYLOAD_DIR='$Payload'; `$env:SIGNAL_CORS_ORIGINS='http://localhost:5173,http://127.0.0.1:5173'; python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
$frontendCommand = "Set-Location -LiteralPath '$Frontend'; npm run dev"

$backendArgs = @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand)
$frontendArgs = @("-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand)

Start-Process -FilePath "powershell.exe" -ArgumentList $backendArgs
Start-Sleep -Seconds 2
Start-Process -FilePath "powershell.exe" -ArgumentList $frontendArgs

Write-Host ""
Write-Host "Backend API docs: http://127.0.0.1:8000/docs" -ForegroundColor Cyan
Write-Host "Frontend:         http://127.0.0.1:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Keep both PowerShell windows open while using SIGNAL."
