# 快速对比输出文件的辅助脚本

param(
    [string]$Timestamp = ""
)

$OutputDir = "$PSScriptRoot\outputs"

# 如果没有指定时间戳，使用最新的
if ([string]::IsNullOrEmpty($Timestamp)) {
    $LatestFile = Get-ChildItem -Path $OutputDir -Filter "*.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -eq $LatestFile) {
        Write-Host "错误: 没有找到输出文件" -ForegroundColor Red
        exit 1
    }
    $Timestamp = $LatestFile.Name -replace '.*_(\d{8}_\d{6})\.txt$', '$1'
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "输出对比 - $Timestamp" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$Files = @(
    "claude_non_stream_$Timestamp.txt",
    "claude_stream_json_$Timestamp.txt",
    "codex_non_stream_$Timestamp.txt",
    "codex_stream_jsonl_$Timestamp.txt"
)

foreach ($File in $Files) {
    $FilePath = Join-Path $OutputDir $File
    if (Test-Path $FilePath) {
        $Size = [math]::Round((Get-Item $FilePath).Length / 1KB, 2)
        $LineCount = (Get-Content $FilePath).Count

        Write-Host "=== $File ===" -ForegroundColor Yellow
        Write-Host "大小: ${Size} KB | 行数: $LineCount" -ForegroundColor Gray
        Write-Host ""

        # 显示前 20 行
        Get-Content $FilePath -TotalCount 20 | ForEach-Object {
            Write-Host $_ -ForegroundColor White
        }

        if ($LineCount -gt 20) {
            Write-Host "`n... (省略 $($LineCount - 20) 行) ...`n" -ForegroundColor DarkGray
        }

        Write-Host "`n" -NoNewline
    } else {
        Write-Host "=== $File ===" -ForegroundColor Yellow
        Write-Host "文件不存在`n" -ForegroundColor Red
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "提示: 使用以下命令查看完整文件:" -ForegroundColor Yellow
Write-Host "  Get-Content `"$OutputDir\<文件名>`"" -ForegroundColor Gray
