# Loom 一键启动：Hub WebSocket 服务 + 前端 Vite
# 用法：powershell -ExecutionPolicy Bypass -File scripts/start.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

Write-Host "==> 启动 Loom Hub (WS :8765)" -ForegroundColor Cyan
$hub = Start-Process -FilePath "python" `
  -ArgumentList "scripts/run_hub_server.py" `
  -WorkingDirectory $root `
  -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 1

Write-Host "==> 启动 Loom Shell 前端 (Vite :5173)" -ForegroundColor Cyan
$vite = Start-Process -FilePath "npm" `
  -ArgumentList "run","dev" `
  -WorkingDirectory $root `
  -PassThru -WindowStyle Minimized

Write-Host ""
Write-Host "  Hub   : http://127.0.0.1:8765/ws  (health: /health)" -ForegroundColor Green
Write-Host "  Shell : http://localhost:5173/" -ForegroundColor Green
Write-Host ""
Write-Host "按 Ctrl+C 停止（会尝试结束子进程 Hub=$($hub.Id) Vite=$($vite.Id)）"

try {
  Wait-Process -Id $hub.Id, $vite.Id -ErrorAction SilentlyContinue
} finally {
  foreach ($p in @($hub, $vite)) {
    if ($p -and -not $p.HasExited) {
      Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
  }
  Write-Host "已停止。"
}
