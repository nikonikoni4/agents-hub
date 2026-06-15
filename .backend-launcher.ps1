$Host.UI.RawUI.WindowTitle = "Agents Hub Backend (port 8100)"
Set-Location "D:\desktop\软件开发\agents-hub\.claude\worktrees\task-33-front-improve"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  后端服务器" -ForegroundColor Cyan
Write-Host "  端口: 8100" -ForegroundColor Yellow
Write-Host "  健康检查: http://localhost:8100/health" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
python -m uvicorn agents_hub.api.app:app --host 0.0.0.0 --port 8100
Write-Host ""
Write-Host "后端已停止，按任意键关闭..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
