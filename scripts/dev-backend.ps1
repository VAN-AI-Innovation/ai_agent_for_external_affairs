$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$venvPython = Join-Path $rootDir ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    Write-Host "[backend] .venv not found. Falling back to system python."
    $python = "python"
}

if (-not (Test-Path (Join-Path $rootDir ".env"))) {
    Write-Host "[backend] .env not found. Copy .env.example to .env if you need custom settings."
}

Set-Location $backendDir
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
