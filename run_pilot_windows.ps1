param(
    [ValidateSet("Validate", "Backend", "Frontend")][string]$Mode = "Validate",
    [string]$PythonPath = "",
    [string]$DependencyPath = "",
    [ValidateSet("pilot_v2","expanded_v2","valid_baseline_v1")][string]$Dataset = "valid_baseline_v1",
    [ValidateRange(1024,65535)][int]$BackendPort = 8001,
    [ValidateRange(1024,65535)][int]$FrontendPort = 5173
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Payloads = Join-Path $Root "payloads/$Dataset"
if (-not (Test-Path -LiteralPath (Join-Path $Payloads "manifest.json"))) { throw "Pilot payloads not found." }
$OriginalLocation = Get-Location
$PreviousPythonPath = $env:PYTHONPATH
$PreviousBrokers = $env:SIGNAL_BROKER_DIR
$PreviousPayloads = $env:SIGNAL_PAYLOAD_DIR
$PreviousCors = $env:SIGNAL_CORS_ORIGINS
$PreviousApi = $env:VITE_API_BASE_URL
try {
    if ($Mode -eq "Frontend") {
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
        Set-Location (Join-Path $Root "frontend")
        & (Get-Command npm.cmd -ErrorAction Stop).Source run dev -- --port $FrontendPort --strictPort
    } else {
        if (-not $PythonPath) {
            $VirtualPython = Join-Path $Root ".venv/Scripts/python.exe"
            $PythonPath = if (Test-Path -LiteralPath $VirtualPython) {$VirtualPython} else {(Get-Command python -ErrorAction Stop).Source}
        }
        $ImportPaths = @($Root, (Join-Path $Root "backend"))
        if ($DependencyPath) {$ImportPaths += $DependencyPath}
        if ($PreviousPythonPath) {$ImportPaths += $PreviousPythonPath}
        $env:PYTHONPATH = $ImportPaths -join [IO.Path]::PathSeparator
        Set-Location $Root
        if ($Mode -eq "Validate") {
            $Report = Join-Path $Root "research/data/rework_phase1_v2/raw/json_pilot/reproducibility_report.json"
            if ($Dataset -eq "valid_baseline_v1") { & $PythonPath -m research.signal_validate_valid_history } elseif ($Dataset -eq "expanded_v2") { & $PythonPath -m research.signal_validate_expansion } else { & $PythonPath -m research.signal_validate_json_pilot --report $Report }
        } else {
            $env:SIGNAL_PAYLOAD_DIR = $Payloads
            if ($Dataset -eq "valid_baseline_v1") {$env:SIGNAL_BROKER_DIR = Join-Path $Root "research/data/rework_phase1_v2/raw/valid_baseline_history/broker_views"}
            elseif ($Dataset -eq "expanded_v2") {$env:SIGNAL_BROKER_DIR = Join-Path $Root "research/data/rework_phase1_v2/raw/expansion_2026/broker_views"}
            $env:SIGNAL_CORS_ORIGINS = "http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort"
            & $PythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort
        }
    }
    if ($LASTEXITCODE -ne 0) {throw "Pilot command stopped with exit code $LASTEXITCODE."}
} finally {
    Set-Location $OriginalLocation
    $env:PYTHONPATH = $PreviousPythonPath
    $env:SIGNAL_BROKER_DIR = $PreviousBrokers
    $env:SIGNAL_PAYLOAD_DIR = $PreviousPayloads
    $env:SIGNAL_CORS_ORIGINS = $PreviousCors
    $env:VITE_API_BASE_URL = $PreviousApi
}
