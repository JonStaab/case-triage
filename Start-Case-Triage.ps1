$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$savedKey = [Environment]::GetEnvironmentVariable('OPENAI_API_KEY', 'User')
if ($savedKey) { $env:OPENAI_API_KEY = $savedKey }
Remove-Variable savedKey
$pythonCommand = 'python'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')) {
    $pythonCommand = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
} elseif (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'venv\Scripts\python.exe')) {
    $pythonCommand = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
}
try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8766/health' -TimeoutSec 2
    if ($health.status -eq 'ok') {
        Write-Host 'Case Triage is already running. Opening the app.'
        Start-Process 'http://127.0.0.1:8766/'
        exit 0
    }
} catch { }
if (-not $env:OPENAI_API_KEY) {
    Write-Host 'No saved API key found. The app will work, but AI summaries will be unavailable.' -ForegroundColor Yellow
}
Write-Host 'Starting Case Triage at http://127.0.0.1:8766/'
Write-Host 'Keep this window open while using the app. Press Ctrl+C to stop.'
& $pythonCommand -m uvicorn Case_Management:app --host 127.0.0.1 --port 8766 --workers 1
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Startup failed. Review the error above.' -ForegroundColor Red
    Read-Host 'Press Enter to close'
}
