---
version: 1.0
created_at: 2026-06-15
updated_at: 2026-06-15
last_updated: 新增：CodexParser 并发竞态导致 session_id 串台
abstract: CodexParser 共享实例的 _thread_id 被并发 agent 互相覆盖，导致不同 agent 的 main_session 被设置为同一个 thread_id，resume 时找不到 thread 而持续失败
---

## CodexParser 并发竞态导致 session_id 串台

- updated_at: 2026-06-15
- path: docs/history-bugs/2026-06-15-codex-parser-thread-id-race-condition.md

### Bug 简述

多个 Codex agent 并发执行时，共享的 CodexParser 实例的 _thread_id 被互相覆盖，导致不同 agent 的 AgentResult.session_id 被错误设置为同一个 thread_id。该 thread_id 只存在于最后一个完成的 agent 的 Codex 存储中，其他 agent 用它去 resume 时找不到 thread，抛出 CLIExecutionError: thread/resume failed: no rollout found，且因 main_session 持久化不会被清除而反复失败。

### 复用场景

- 任何使用带内部状态的解析器（parser）处理并发流式输出的场景
- 共享单例对象在 asyncio 并发协程间存在可变字段时
- CLI 流式输出解析器需要在事件间缓存上下文信息的场景

### 代码位置

| 文件 | 行号 | 问题 |
|------|------|------|
| agents_hub/agent_bridge/bridge.py | 42-45 | _parsers 字典中 CodexParser 是所有 Codex agent 共享的单例 |
| agents_hub/agent_bridge/parsers/codex.py | 20-21 | _thread_id 是实例级可变状态 |
| agents_hub/agent_bridge/parsers/codex.py | 39-41 | thread.started 事件写入 _thread_id，无隔离 |
| agents_hub/agent_bridge/parsers/codex.py | 50, 95 | session_id fallback 读取 self._thread_id，读到被覆盖的值 |

### 发生原因

1. **Parser 共享单例 + 可变状态**：AgentBridge.__init__() 创建一个 CodexParser() 实例存入 _parsers 字典，所有 Codex agent 共用。CodexParser 内部维护 _thread_id 字段用于从 thread.started 事件缓存 thread_id。

2. **并发执行时序交错**：_initialize_new_members() 使用 asyncio.gather() 并发初始化多个 agent，每个 agent 的 codex exec 子进程交错输出事件：

   T1: agent_A 的 thread.started -> parser._thread_id = AAA
   T2: agent_B 的 thread.started -> parser._thread_id = BBB（覆盖 AAA）
   T3: agent_A 的 item.completed -> session_id = BBB（错误！读到 agent_B 的 thread_id）

3. **session_id 错误传播**：bridge.execute() 中 result_session_id 从事件的 session_id 字段获取，事件的 session_id 由 parser 的 _thread_id fallback 填充。错误的 session_id 写入 AgentResult，再通过 update_agent_session() 持久化到 agent_member.json 的 main_session。

4. **无恢复机制**：main_session 只在为空时设置，一旦被错误值覆盖，后续调用始终用错误的 thread_id 去 resume，且 bridge.py 没有 resume 失败时的 fallback 逻辑。

### 最佳方案

**核心修复**：消除 parser 的共享可变状态。

**方案 A（推荐）：每次 execute_stream 调用创建独立 parser**

```python
# bridge.py - execute_stream()
async def execute_stream(self, prompt, config, session_id=None, ...):
    executor = self._executors[config.platform]
    # 每次调用创建独立 parser，避免并发状态污染
    parser = self._create_parser(config.platform)
    ...
```

```python
def _create_parser(self, platform: AgentPlatform):
    """每次调用创建独立 parser 实例"""
    if platform == AgentPlatform.CLAUDE:
        return ClaudeParser()
    elif platform == AgentPlatform.CODEX:
        return CodexParser()
    elif platform == AgentPlatform.OPENCODE:
        return OpenCodeParser()
```

**方案 B：在 parser 内部消除可变状态**

将 _thread_id 改为事件级局部变量，通过返回值传递而非实例缓存。

**方案 C（兜底）：添加 resume 失败 fallback**

在 bridge.execute_stream() 中捕获 CLIExecutionError，当有 session_id 时自动不带 session_id 重试新建会话。

**建议**：方案 A 修复根因，方案 C 作为防御性兜底。两者都实施最稳妥。
