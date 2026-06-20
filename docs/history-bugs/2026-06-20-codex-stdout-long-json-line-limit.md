---
version: 1.0
created_at: 2026-06-20
updated_at: 2026-06-20
last_updated: 创建 Codex stdout 超长单行 JSON 导致 LimitOverrunError 的 Bug 记录
abstract: 记录 Codex CLI --json 输出超长单行 JSON 时，asyncio 按行/分隔符读取 API 触发 LimitOverrunError，导致 Agent run 异常退出的问题、复现方式和修复方案。
---

# Codex stdout 超长单行 JSON 导致 LimitOverrunError

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 Bug 记录 |

## Bug 简述

Codex Agent 执行过程中，`codex exec --json` stdout 输出包含超长单行 JSON，`CodexExecutor.execute()` 使用 `process.stdout.readuntil(b"\n")` 读取时触发 `asyncio.exceptions.LimitOverrunError`，导致 Agent 的 `run()` 任务异常退出。

典型日志：

```text
Agent 'codex' 执行失败: Separator is not found, and chunk exceed the limit
asyncio.exceptions.LimitOverrunError: Separator is not found, and chunk exceed the limit
```

## 复用场景

该经验适用于所有“外部 CLI 以 JSONL / 行协议输出，但单行可能很大”的读取场景：

- Codex / Claude / OpenCode 等 Agent CLI stdout 读取。
- 命令执行结果被聚合到单个 JSON 字段的流式协议。
- 使用 `asyncio.StreamReader.readline()`、`async for line in stdout`、`readuntil(separator=b"\n")` 的地方。

关键判断：如果协议按行分隔，但单行长度不受系统控制，不要使用 asyncio 的按行或按分隔符 API 作为底层读取方式。

## 代码位置

问题位置：

- `agents_hub/agent_bridge/executors/codex.py`
  - `CodexExecutor.execute()`
  - 原实现使用 `process.stdout.readuntil(separator=b"\n")`

上游传播链路：

```text
Agent._process_message()
  -> AgentBridge.execute()
  -> AgentBridge.execute_stream()
  -> CodexExecutor.execute()
  -> process.stdout.readuntil(b"\n")
```

相关数据字段：

- `agents_hub/agent_bridge/parsers/codex.py`
  - `CodexParser._parse_item_completed()`
  - `command_execution.aggregated_output`

`aggregated_output` 可能包含完整命令输出，导致单个 JSONL 事件超过 asyncio StreamReader 默认 limit。

## 发生原因

根因是读取策略错误。

Codex `--json` 输出虽然是 JSONL，每个事件以换行分隔，但每一行 JSON 的大小不固定。特别是 `item.completed` + `command_execution` 事件会把命令输出聚合到 `aggregated_output` 字段，单行可能超过 asyncio StreamReader 的默认扫描限制。

之前的修复只把：

```python
async for line in process.stdout:
```

换成：

```python
await process.stdout.readuntil(separator=b"\n")
```

但这没有绕开限制。`async for line in stdout`、`readline()` 和 `readuntil(b"\n")` 都需要在 StreamReader 的 limit 内找到换行符，否则会抛 `LimitOverrunError`。

因此，当问题是“单行本身太长”时，不能用另一个按行 API 修复。

## 最佳方案

使用固定大小 chunk 读取 stdout，并在业务层维护 buffer 手动按 `\n` 切分：

```python
buffer = ""
while True:
    chunk = await process.stdout.read(256 * 1024)
    if not chunk:
        break

    buffer += chunk.decode("utf-8", errors="ignore")
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        decoded = line.strip()
        if decoded:
            yield decoded

if buffer.strip():
    yield buffer.strip()
```

这个方案保留了上层“每次 yield 一行 JSON 字符串”的契约，同时不依赖 asyncio 按行/分隔符 API 的单行限制。

## 复现与验证

新增复现测试：

- `tests/utils/agent_bridge/executors/test_codex_executor.py`
  - `test_execute_streams_json_line_longer_than_asyncio_separator_limit`

测试方式：

1. 使用真实 `asyncio.StreamReader` 模拟 Codex stdout。
2. 注入一条超过默认行限制的单行 JSON。
3. 修复前稳定复现 `LimitOverrunError`。
4. 修复后验证 `CodexExecutor.execute()` 能完整 yield 该 JSON 行。

验证命令：

```bash
python -m pytest tests\utils\agent_bridge\executors\test_codex_executor.py -k long --tb=short
python -m pytest tests\utils\agent_bridge\executors\test_codex_executor.py --tb=short
```
