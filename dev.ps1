<#
.SYNOPSIS
    启动 Agents Hub 开发服务器（前端 + 后端）

.DESCRIPTION
    同时启动前端和后端开发服务器，支持自定义端口。

.PARAMETER BackendPort
    后端 API 端口，默认 8099

.PARAMETER FrontendPort
    前端开发服务器端口，默认 5173

.PARAMETER Mode
    Vite 启动模式，默认 development

.EXAMPLE
    # 使用默认端口启动
    .\dev.ps1

.EXAMPLE
    # 自定义端口启动
    .\dev.ps1 -BackendPort 8100 -FrontendPort 5174

.EXAMPLE
    # 使用分支配置（需要先创建 .env.branch-feature-a）
    .\dev.ps1 -Mode branch-feature-a
#>

param(
    [int]$BackendPort = 8099,
    [int]$FrontendPort = 5173,
    [string]$Mode = "development"
)

# 颜色输出函数
function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

# 显示启动信息
Write-Color "`n========================================" "Cyan"
Write-Color "  Agents Hub 开发服务器" "Cyan"
Write-Color "========================================`n" "Cyan"
Write-Color "后端端口: $BackendPort" "Yellow"
Write-Color "前端端口: $FrontendPort" "Yellow"
Write-Color "Vite 模式: $Mode`n" "Yellow"

# 处理前端环境配置
$envFile = "frontend/.env.local"
$envBackup = "frontend/.env.local.backup"

# 如果 .env.local 存在，先备份
if (Test-Path $envFile) {
    Copy-Item -Path $envFile -Destination $envBackup -Force
    Write-Color "已备份现有 .env.local" "Gray"
}

# 创建临时 .env.local 文件（优先级最高）
$envContent = @"
# 由 dev.ps1 自动生成
VITE_USE_MOCK=false
VITE_API_BASE_URL=/api/v1
VITE_DEV_PORT=$FrontendPort
VITE_API_PORT=$BackendPort
"@

# 如果使用非默认模式，读取对应 .env 文件的内容并合并
if ($Mode -ne "development") {
    $modeEnvFile = "frontend/.env.$Mode"
    if (Test-Path $modeEnvFile) {
        Write-Color "加载模式配置: $modeEnvFile" "Green"
        $modeContent = Get-Content -Path $modeEnvFile -Raw
        # 模式文件的配置优先
        $envContent = "$modeContent`n# 以下为端口覆盖`nVITE_DEV_PORT=$FrontendPort`nVITE_API_PORT=$BackendPort"
    } else {
        Write-Color "模式配置不存在，使用默认配置" "Yellow"
    }
}

# 写入 .env.local
$envContent | Out-File -FilePath $envFile -Encoding utf8
Write-Color "已写入环境配置: $envFile" "Gray"

# 启动后端（后台）
Write-Color "[1/2] 启动后端服务器..." "Green"
$backendJob = Start-Job -ScriptBlock {
    param($port, $workDir)
    Set-Location $workDir
    python -m uvicorn agents_hub.api.app:app --host 0.0.0.0 --port $port
} -ArgumentList $BackendPort, $PWD

# 等待后端启动
Start-Sleep -Seconds 3

# 检查后端是否启动成功
try {
    $response = Invoke-WebRequest -Uri "http://localhost:$BackendPort/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Color "后端启动成功: http://localhost:$BackendPort" "Green"
    }
} catch {
    Write-Color "后端启动中... (可能需要更多时间)" "Yellow"
}

# 启动前端
Write-Color "`n[2/2] 启动前端服务器..." "Green"

Write-Color "`n========================================" "Cyan"
Write-Color "  服务已启动" "Cyan"
Write-Color "========================================" "Cyan"
Write-Color "前端: http://localhost:$FrontendPort" "White"
Write-Color "后端: http://localhost:$BackendPort" "White"
Write-Color "健康检查: http://localhost:$BackendPort/health" "White"
Write-Color "`n按 Ctrl+C 停止所有服务`n" "Yellow"

# 启动前端（前台运行）
Set-Location frontend
& pnpm dev

# 清理：当前端退出时，停止后端并恢复配置
Write-Color "`n正在停止后端服务..." "Yellow"
Stop-Job -Job $backendJob
Remove-Job -Job $backendJob -Force

# 恢复或清理 .env.local
Set-Location ..
if (Test-Path $envBackup) {
    Move-Item -Path $envBackup -Destination $envFile -Force
    Write-Color "已恢复原始 .env.local" "Gray"
} else {
    Remove-Item -Path $envFile -Force -ErrorAction SilentlyContinue
    Write-Color "已清理临时 .env.local" "Gray"
}

Write-Color "已停止所有服务" "Green"
