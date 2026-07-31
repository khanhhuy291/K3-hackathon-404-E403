# Chạy Python REST API backend (http://localhost:8000) cho Web Dashboard
# Usage: .\run_api.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
& "$root\.venv\Scripts\python.exe" -u "$root\codebase\python\main_api.py"
