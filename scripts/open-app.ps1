$ErrorActionPreference = "Stop"

$url = "http://127.0.0.1:5173"
Write-Host "Opening $url"
python -m webbrowser $url
