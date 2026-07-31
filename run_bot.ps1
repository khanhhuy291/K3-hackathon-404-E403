# Chạy Discord Bot listener
# Usage: .\run_bot.ps1
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"   # bắt buộc trên Windows: code có emoji + tiếng Việt trong print()
# -u: tắt buffer stdout. Không có nó, khi ghi log ra file (`.\run_bot.ps1 > bot.log`)
# mọi print() của bot bị giữ trong buffer, nhìn log tưởng bot không nhận được tin nào.
& "$root\.venv\Scripts\python.exe" -u "$root\codebase\python\discord_bot.py"
