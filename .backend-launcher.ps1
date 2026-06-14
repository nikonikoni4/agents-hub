$Host.UI.RawUI.WindowTitle = "Agents Hub Backend (port 99999)"
Set-Location "D:\desktop\软件开发\agents-hub\.claude\worktrees\task-33-front-improve"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  后端服务器" -ForegroundColor Cyan
Write-Host "  端口: 99999" -ForegroundColor Yellow
Write-Host "  健康检查: http://localhost:99999/health" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
python -m uvicorn agents_hub.api.app:app --host 0.0.0.0 --port 99999
Write-Host ""
Write-Host "后端已停止，按任意键关闭..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
