# Claude Code 和 Codex CLI 输出测试

## 目的

测试 Claude Code 和 Codex 的流式输出和非流式输出，用于验证是否可以通过统一的类来管理输出。

## 测试脚本

### test-cli-output.ps1

主测试脚本，执行以下 4 个测试：

1. **Claude Code 非流式输出** - 使用 `-p` 参数
2. **Claude Code 流式输出** - 使用 `-p --verbose --output-format=stream-json --include-partial-messages`
3. **Codex 非流式输出** - 使用 `codex exec`
4. **Codex 流式输出** - 使用 `codex exec --json`

## 使用方法

### 基本用法

```powershell
# 使用默认提示词
.\test-cli-output.ps1

# 使用自定义提示词
.\test-cli-output.ps1 -TestPrompt "写一个 Hello World 程序"
```

### 输出文件

所有输出文件保存在 `outputs/` 目录下，文件名格式：

- `claude_non_stream_<时间戳>.txt` - Claude Code 非流式输出
- `claude_stream_json_<时间戳>.txt` - Claude Code 流式 JSON 输出
- `codex_non_stream_<时间戳>.txt` - Codex 非流式输出
- `codex_stream_jsonl_<时间戳>.txt` - Codex 流式 JSONL 输出

### 查看输出

```powershell
# 查看特定文件
Get-Content .\outputs\claude_non_stream_<时间戳>.txt

# 查看所有输出文件
Get-ChildItem .\outputs\*.txt | ForEach-Object { 
    Write-Host "`n=== $($_.Name) ===" -ForegroundColor Cyan
    Get-Content $_.FullName 
}
```

## 输出格式说明

### Claude Code

- **非流式** (`-p`): 纯文本输出，直接返回最终结果
- **流式** (`--verbose --output-format=stream-json`): JSON Lines 格式，每行一个 JSON 对象，包含事件类型和数据

### Codex

- **非流式** (`exec`): 纯文本输出，带有格式化的对话内容
- **流式** (`--json`): JSONL 格式，每行一个事件对象

## 分析要点

通过对比输出文件，可以分析：

1. **输出结构差异** - 流式和非流式的数据结构
2. **事件类型** - 不同 CLI 的事件命名和分类
3. **元数据** - 包含的额外信息（token 使用、时间戳等）
4. **统一接口可行性** - 是否可以抽象出统一的输出管理类
