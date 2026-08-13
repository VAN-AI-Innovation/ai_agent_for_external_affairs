$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$frontendDir = Join-Path $rootDir "frontend"

Set-Location $frontendDir
npm run dev -- --host 127.0.0.1 --port 5173
