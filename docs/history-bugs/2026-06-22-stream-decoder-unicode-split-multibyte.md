---
version: 1.0
created_at: 2026-06-22
updated_at: 2026-06-22
last_updated: 创建 CLI stdout 流式解码跨块多字节字符截断的 Bug 记录
abstract: 记录 Claude/OpenCode Executor 使用固定 chunk 读取 stdout 时，多字节 UTF-8 字符被截断在块边界导致 UnicodeDecodeError 的问题和修复方案。
---

# CLI stdout 流式解码跨块多字节字符截断导致 UnicodeDecodeError

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 Bug 记录 |

## Bug 简述

Claude/OpenCode Agent 执行过程中，`ClaudeExecutor.execute()` / `OpenCodeExecutor.execute()` 使用 `process.stdout.read(256 * 1024)` 按固定字节数读取 stdout，然后直接 `chunk.decode("utf-8")` 解码。当一个多字节 UTF-8 字符（如中文占 3 字节）恰好被截断在块边界时，`decode()` 抛出 `UnicodeDecodeError`，导致 Agent 的 `run()` 任务异常退出。

典型日志：

```text
UnicodeDecodeError: 'utf-8' codec can't decode bytes in position 131070-131071: unexpected end of data
```

位置 131070-131071 说明一个 3 字节 UTF-8 字符的前 1 字节落在上一个块末尾，后 2 字节在下一个块开头。

## 复用场景

该经验适用于所有"按固定字节数读取流式数据并解码"的场景：

- 从 subprocess stdout/stderr 按 chunk 读取并解码。
- 网络流按 chunk 接收并解码。
- 任何使用 `chunk.decode("utf-8")` 且 chunk 大小不保证对齐字符边界的地方。

关键判断：如果数据包含多字节字符（如 CJK 文本），固定大小 chunk 读取不能直接 `decode()`，必须处理跨块截断。

## 代码位置

问题位置：

- `agents_hub/agent_bridge/executors/claude.py`
  - `ClaudeExecutor.execute()` 第 94 行
  - `buffer += chunk.decode("utf-8")`
- `agents_hub/agent_bridge/executors/opencode.py`
  - `OpenCodeExecutor.execute()` 第 75 行
  - `buffer += chunk.decode("utf-8")`

上游传播链路：

```text
Agent._process_message()
  -> AgentBridge.execute()
  -> AgentBridge.execute_stream()
  -> ClaudeExecutor.execute() / OpenCodeExecutor.execute()
  -> process.stdout.read(256 * 1024)
  -> chunk.decode("utf-8")  ← 这里崩溃
```

## 发生原因

根因是解码策略错误。

`process.stdout.read(256 * 1024)` 按固定 256KB 字节数读取，不感知 UTF-8 字符边界。UTF-8 是变长编码：

- ASCII 字符：1 字节
- 中文等 CJK 字符：3 字节
- Emoji 等：4 字节

当一个 3 字节字符恰好跨越块边界（前 1 字节在当前块末尾，后 2 字节在下一块开头），`chunk.decode("utf-8")` 无法解码不完整的字节序列，抛出 `UnicodeDecodeError`。

此前的 Codex 超长行 bug（`2026-06-20-codex-stdout-long-json-line-limit.md`）修复时，从按行读取改为按 chunk 读取，但引入了这个新问题——解决了行长度限制，却忽略了多字节字符截断。

## 最佳方案

使用 `codecs.getincrementaldecoder("utf-8")()` 增量解码器替代 `chunk.decode("utf-8")`：

```python
import codecs

decoder = codecs.getincrementaldecoder("utf-8")()
buffer = ""
while True:
    chunk = await process.stdout.read(256 * 1024)
    if not chunk:
        break
    buffer += decoder.decode(chunk)
    # ... 按 \n 切分处理 ...

# EOF 时 flush 出剩余字节
buffer += decoder.decode(b"", final=True)
```

增量解码器在每次 `decode(chunk)` 时，如果块末尾有不完整的多字节序列，会暂存这些字节。下次调用时自动与新块拼接，确保不会在多字节字符中间断开。`decode(b"", final=True)` 在流结束时 flush 出所有剩余字节。

### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| `chunk.decode("utf-8")` | 简单 | 跨块截断会崩溃 |
| `chunk.decode("utf-8", errors="ignore")` | 简单，不崩溃 | 丢失截断的字符，数据损坏 |
| `codecs.getincrementaldecoder` | 正确处理跨块字符 | 略复杂 |

**结论**：`codecs.getincrementaldecoder` 是唯一不丢数据的方案。

## 验证方式

修复已在以下文件中应用：

- `agents_hub/agent_bridge/executors/claude.py`：第 79 行创建 decoder，第 96 行使用 `decoder.decode(chunk)`，第 104 行 EOF flush
- `agents_hub/agent_bridge/executors/opencode.py`：第 71 行创建 decoder，第 76 行使用 `decoder.decode(chunk)`，第 87 行 EOF flush

验证：发送包含大量中文文本的任务给 Claude/OpenCode Agent，确认不再出现 `UnicodeDecodeError`。

## 经验教训

1. **chunk 读取 ≠ 安全解码**：按固定字节数读取解决了行长度限制问题，但引入了多字节字符截断问题。两个 bug 是同一代码位置的连续修复。
2. **流式解码必须用增量解码器**：只要数据可能包含多字节字符，`chunk.decode()` 就不安全。`codecs.getincrementaldecoder` 是标准库提供的正确方案。
3. **关注字节边界**：在处理二进制/文本混合流时，任何按固定字节数切分的操作都需要考虑编码的字符边界。
