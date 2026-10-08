param(
    [ValidateRange(1024,65535)][int]$BackendPort = 8001,
    [ValidateRange(1024,65535)][int]$FrontendPort = 5173,
    [switch]$CheckOnly,
    [switch]$SmokeTest
)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Runner = Join-Path $Root 'run_pilot_windows.ps1'
$PythonPath = Join-Path $Root '.venv/Scripts/python.exe'
if ($BackendPort -eq $FrontendPort) {throw 'Backend dan frontend perlu port berbeda.'}
if (-not (Test-Path -LiteralPath $PythonPath)) {throw 'Environment .venv belum tersedia. Buat .venv dan install research/requirements-json-pilot.txt serta backend/requirements.txt.'}
if (-not (Test-Path -LiteralPath (Join-Path $Root 'frontend/node_modules'))) {throw 'Jalankan npm --prefix frontend install dahulu.'}
$null = Get-Command npm.cmd -ErrorAction Stop
& $PythonPath -c 'import fastapi, uvicorn'
if ($LASTEXITCODE -ne 0) {throw 'Dependensi backend belum lengkap di .venv.'}
$Busy = @(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.LocalPort -in @($BackendPort,$FrontendPort)})
if ($Busy.Count) {throw "Port sudah digunakan: $($Busy.LocalPort -join ', '). Hentikan server lama dahulu."}
if ($CheckOnly) {Write-Host 'Konfigurasi demo siap.'; return}
$Jobs = @()
try {
    foreach ($Mode in @('Backend','Frontend')) {
        $Jobs += Start-Job -ArgumentList $Runner,$Mode,$PythonPath,$BackendPort,$FrontendPort -ScriptBlock {
            param($RunPath,$RunMode,$Python,$ApiPort,$WebPort)
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $RunPath -Mode $RunMode -PythonPath $Python -Dataset valid_baseline_v1 -BackendPort $ApiPort -FrontendPort $WebPort 2>&1 | ForEach-Object { $_.ToString() }
            if ($LASTEXITCODE -ne 0) {throw "$RunMode berhenti dengan exit code $LASTEXITCODE"}
        }
    }
    Write-Host 'Menyiapkan SIGNAL...' -ForegroundColor Cyan
    $Deadline = (Get-Date).AddSeconds(60)
    $Ready = $false
    do {
        if (@($Jobs | Where-Object {$_.State -ne 'Running'}).Count) {throw 'Server berhenti saat startup.'}
        try {
            $Api = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2
            $Web = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort" -TimeoutSec 2
            $Ready = $Api.StatusCode -eq 200 -and $Web.StatusCode -eq 200
        } catch { $Ready = $false }
        if (-not $Ready) {Start-Sleep -Milliseconds 500}
    } while (-not $Ready -and (Get-Date) -lt $Deadline)
    if (-not $Ready) {throw 'Server belum siap dalam 60 detik.'}
    Write-Host "SIGNAL siap: http://127.0.0.1:$FrontendPort" -ForegroundColor Green
    Write-Host 'Biarkan terminal ini terbuka. Tekan Ctrl+C untuk menghentikan kedua server.'
    if ($SmokeTest) {return}
    while ($true) {
        foreach ($Job in $Jobs) {
            Receive-Job -Job $Job -ErrorAction Continue
            if ($Job.State -ne 'Running') {throw 'Salah satu server berhenti.'}
        }
        Start-Sleep -Seconds 1
    }
} finally {
    foreach ($Job in $Jobs) {
        Stop-Job -Job $Job -ErrorAction SilentlyContinue
        Receive-Job -Job $Job -ErrorAction Continue
        Remove-Job -Job $Job -Force -ErrorAction SilentlyContinue
    }
    Write-Host 'Server SIGNAL dihentikan.'
}
