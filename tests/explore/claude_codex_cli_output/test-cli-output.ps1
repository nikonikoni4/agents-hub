# Claude Code 和 Codex CLI 输出测试脚本
# 用于测试流式输出和非流式输出的内容差异

param(
    [string]$TestPrompt = "你的CLI工具，思考过程，它会在流式或非流式输出中显示吗？"
)

# 设置输出目录
$OutputDir = "$PSScriptRoot\outputs"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

# 确保输出目录存在
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CLI 输出测试 - $Timestamp" -ForegroundColor Cyan
Write-Host "测试提示词: $TestPrompt" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 测试 1: Claude Code 非流式输出
Write-Host "[1/4] 测试 Claude Code 非流式输出..." -ForegroundColor Yellow
$ClaudeNonStreamFile = "$OutputDir\claude_non_stream_$Timestamp.txt"
try {
    claude -p $TestPrompt 2>&1 | Out-File -FilePath $ClaudeNonStreamFile -Encoding UTF8
    Write-Host "  ✓ 输出已保存到: $ClaudeNonStreamFile" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 错误: $_" -ForegroundColor Red
}

# 测试 2: Claude Code 流式输出 (JSON)
Write-Host "`n[2/4] 测试 Claude Code 流式输出 (stream-json)..." -ForegroundColor Yellow
$ClaudeStreamFile = "$OutputDir\claude_stream_json_$Timestamp.txt"
try {
    claude -p --verbose --output-format=stream-json --include-partial-messages $TestPrompt 2>&1 | Out-File -FilePath $ClaudeStreamFile -Encoding UTF8
    Write-Host "  ✓ 输出已保存到: $ClaudeStreamFile" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 错误: $_" -ForegroundColor Red
}

# 测试 3: Codex 非流式输出
Write-Host "`n[3/4] 测试 Codex 非流式输出..." -ForegroundColor Yellow
$CodexNonStreamFile = "$OutputDir\codex_non_stream_$Timestamp.txt"
try {
    codex exec $TestPrompt 2>&1 | Out-File -FilePath $CodexNonStreamFile -Encoding UTF8
    Write-Host "  ✓ 输出已保存到: $CodexNonStreamFile" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 错误: $_" -ForegroundColor Red
}

# 测试 4: Codex 流式输出 (JSONL)
Write-Host "`n[4/4] 测试 Codex 流式输出 (JSONL)..." -ForegroundColor Yellow
$CodexStreamFile = "$OutputDir\codex_stream_jsonl_$Timestamp.txt"
try {
    codex exec --json $TestPrompt 2>&1 | Out-File -FilePath $CodexStreamFile -Encoding UTF8
    Write-Host "  ✓ 输出已保存到: $CodexStreamFile" -ForegroundColor Green
} catch {
    Write-Host "  ✗ 错误: $_" -ForegroundColor Red
}

# 生成测试报告
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "测试完成！" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n输出文件列表:" -ForegroundColor White
Get-ChildItem -Path $OutputDir -Filter "*_$Timestamp.txt" | ForEach-Object {
    $Size = [math]::Round($_.Length / 1KB, 2)
    Write-Host "  - $($_.Name) (${Size} KB)" -ForegroundColor Gray
}

Write-Host "`n提示: 使用以下命令查看输出文件:" -ForegroundColor Yellow
Write-Host "  Get-Content `"$OutputDir\<文件名>`"" -ForegroundColor Gray
