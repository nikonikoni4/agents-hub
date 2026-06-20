---
version: 1.0
created_at: 2026-06-20
updated_at: 2026-06-20
last_updated: 创建 Codex 进程 wait() 阻塞导致任务无法闭环的 Bug 记录
abstract: 记录 Codex CLI 进程 stdout 关闭后，process.wait() 永久阻塞，导致 Agent 任务无法完成、消息无法闭环的问题。此 bug 出现频率较高，需要特别关注。
severity: 高（导致任务永久卡住，无法闭环）
frequency: 较高（已多次出现）
---

# Codex 进程 wait() 阻塞导致任务无法闭环

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 Bug 记录 |

## Bug 简述

Codex CLI 进程的 stdout 关闭后（读到 EOF），`await process.wait()` 永久阻塞，导致：
1. `CodexExecutor.execute()` 无法完成
2. `AgentBridge.execute()` 的 `async for` 循环无法结束
3. `base_agent._process_message()` 无法返回
4. Agent Call 一直处于 `running` 状态，无法闭环
5. 消息无法显示在群聊中

**此 bug 出现频率较高，已多次发生，需要特别关注。**

## 典型案例

**Case ID**: be304726  
**发生时间**: 2026-06-20 18:04:49 - 19:02（超过40分钟）  
**Agent**: codex  
**进程 PID**: 40712  
**Session**: 019ee47a-9ef6-7062-bf2d-ec9b9861583f

### 时间线

| 时间 | 事件 | 日志位置 |
|------|------|----------|
| 18:04:49 | 任务创建并发送给 codex | agent_calls.log:216-217 |
| 18:04:49 | Codex CLI 进程启动 (PID 40712) | agents_hub.log:codex.py:84 |
| 18:04:49 - 18:18:19 | 持续读取 stdout（共 229 行） | agents_hub.log:codex.py:96 |
| 18:18:19 | Stdout 关闭（读到 EOF） | agents_hub.log:codex.py:104 |
| 18:18:19 | 开始执行 `await process.wait()` | agents_hub.log:codex.py:132 |
| 18:18:19 - ? | **永久阻塞，无后续日志** | - |
| 18:21:04 | Manager 第1次检查状态（still running） | agents_hub.log:server.py:435 |
| 18:41:00 | Manager 第2次检查状态（still running） | agents_hub.log:server.py:435 |
| 19:00:58 | Manager 第3次检查状态（still running） | agents_hub.log:server.py:435 |

### 关键日志

**应该打印但没有打印的日志**：

```python
# codex.py:138 - 永远没有打印
logger.debug("[CodexExecutor] 进程已退出: pid=%s, session_id=%s, returncode=%s")

# base_agent.py:1059 - 永远没有打印
logger.debug("Agent %s 开始处理消息: call_id=%s, send_from=%s, message_type=%s")

# base_agent.py:359 - 永远没有打印
logger.debug("执行完成: agent=%s, call_id=%s, result_len=%d")

# base_agent.py:365 - 永远没有打印
logger.info("Agent %s 完成消息处理: call_id=%s, send_from=%s, result_text=%s")
```

**最后打印的日志**：

```
2026-06-20 18:18:19,557 [agents_hub.agent_bridge.executors.codex] DEBUG codex.py:132 - 
[CodexExecutor] 等待进程退出: pid=40712, session_id=019ee47a-9ef6-7062-bf2d-ec9b9861583f
```

之后再也没有任何相关日志。

## 复用场景

该问题影响所有使用 `asyncio.create_subprocess_exec` + `await process.wait()` 的场景：

- **所有 Agent CLI 执行**：
  - `codex.py` ✅ 已发现
  - `claude.py` ⚠️ 有风险
  - `opencode.py` ⚠️ 有风险
  - `docker_base.py` ⚠️ 有风险
  - `container.py` ⚠️ 有风险

关键特征：
- Stdout 通过 `process.stdout.read()` 读取
- 读到 EOF 后直接执行 `await process.wait()`
- **没有超时控制**

## 代码位置

### 问题位置

**agents_hub/agent_bridge/executors/codex.py:136**

```python
# 等待进程结束并检查返回码
logger.debug(
    "[CodexExecutor] 等待进程退出: pid=%s, session_id=%s",
    process.pid,
    session_id,
)
await process.wait()  # ← 这里永久阻塞！
logger.debug(
    "[CodexExecutor] 进程已退出: pid=%s, session_id=%s, returncode=%s",
    process.pid,
    session_id,
    process.returncode,
)
```

### 上游传播链路

```
base_agent._run_loop()
  -> base_agent._process_message()  (line 1066)
  -> AgentBridge.execute()  (line 338)
  -> AgentBridge.execute_stream()  (line 295)
  -> async for raw_line in executor.execute()  (line 157)
  -> CodexExecutor.execute()
  -> await process.wait()  (line 136) ← 阻塞在这里
```

整个调用链都被阻塞，无法返回。

## 发生原因

### 根因

**Windows 平台上 asyncio 进程管理的问题**：

1. Codex CLI 进程关闭了 stdout（可能是正常结束，也可能是异常）
2. `process.stdout.read()` 读到 EOF，跳出循环
3. 执行 `await process.wait()` 时，进程可能：
   - 处于僵尸状态（zombie process）
   - 有子进程未关闭
   - 有文件句柄/资源未释放
   - Windows 的 ProactorEventLoop 没有正确捕获进程退出信号
4. `process.wait()` 永久阻塞，等待进程退出信号
5. 即使进程后来退出了（PID 40712 现在不存在），asyncio 也没有收到通知

### 为什么会发生？

可能的原因：
1. **Codex CLI 有子进程**：主进程退出，但子进程还在运行
2. **Windows 进程管理问题**：Windows 上的进程句柄管理与 Unix 不同
3. **asyncio ProactorEventLoop bug**：Windows 上的 asyncio 进程管理有已知问题
4. **资源泄漏**：进程持有的资源（文件、socket）未释放

### 为什么 stdout 关闭不代表进程退出？

- Stdout 是一个管道，进程可以主动关闭
- 关闭 stdout 后，进程可能继续运行（清理资源、等待子进程等）
- 正常情况下，进程会很快退出
- **异常情况下，进程可能卡住，永远不退出**

## 解决方案

### 方案1：添加超时控制（推荐）

```python
# agents_hub/agent_bridge/executors/codex.py:136
logger.debug(
    "[CodexExecutor] 等待进程退出: pid=%s, session_id=%s",
    process.pid,
    session_id,
)

try:
    await asyncio.wait_for(process.wait(), timeout=30)
    logger.debug(
        "[CodexExecutor] 进程已退出: pid=%s, session_id=%s, returncode=%s",
        process.pid,
        session_id,
        process.returncode,
    )
except asyncio.TimeoutError:
    logger.warning(
        "[CodexExecutor] 进程等待超时(%ds)，强制终止: pid=%s, session_id=%s. "
        "可能原因：进程僵尸、子进程未关闭、资源未释放。stdout 已完整读取，继续执行。",
        30,
        process.pid,
        session_id,
    )
    try:
        process.kill()
        # 不等待 kill 完成，避免再次阻塞
    except Exception as e:
        logger.debug("[CodexExecutor] 强制终止进程失败: %s", e)
    # 不抛出异常，因为 stdout 已经完整读取，CLI 执行成功
```

**关键设计决策**：
- **不抛出异常**：因为 stdout 已经完整读取（读到 EOF），CLI 实际上已经成功执行完成
- **只记录警告**：超时是进程清理阶段的问题，不应该影响任务状态
- **强制 kill**：尝试清理僵尸进程，但不等待 kill 完成（避免再次阻塞）
- **继续执行**：任务正常闭环，Agent 状态不会变为 error

### 方案2：不等待进程退出（不推荐）

```python
# 删除 await process.wait() 这一行
# 让进程在后台自行退出
# 风险：无法获取退出码，无法检测执行失败
```

### 影响范围

需要修复的文件：
- ✅ `agents_hub/agent_bridge/executors/codex.py:136`
- ✅ `agents_hub/agent_bridge/executors/claude.py:类似位置`
- ✅ `agents_hub/agent_bridge/executors/opencode.py:类似位置`
- ✅ `agents_hub/agent_bridge/executors/docker_base.py:类似位置`
- ✅ `agents_hub/agent_bridge/docker/container.py:类似位置`

## 验证方式

### 验证修复

1. 运行相同的任务（Slice 7 MCP 工具开发）
2. 观察是否能正常完成或超时报错
3. 检查日志中是否有"进程已退出"或"进程等待超时"

### 测试用例

暂无自动化测试（难以稳定复现进程僵尸状态）

## 临时解决方案

如果遇到此问题：

1. **重启 Agent**：
   ```python
   # 通过 MCP 或 API 重启 codex agent
   ```

2. **强制 kill 进程**：
   ```bash
   # Windows
   taskkill /F /PID 40712
   
   # Linux/Mac
   kill -9 40712
   ```

3. **手动标记任务失败**：
   ```python
   # 修改 agent_calls.jsonl，将状态改为 failed
   ```

## 相关 Bug

- `2026-06-05-windows-asyncio-subprocess-notimplementederror.md`: Windows asyncio 子进程问题
- `2026-06-20-codex-stdout-long-json-line-limit.md`: Codex stdout 超长行问题

## 经验教训

1. **永远不要无限等待**：所有 `await` 操作都应该有超时控制
2. **进程管理的复杂性**：stdout 关闭 ≠ 进程退出
3. **Windows asyncio 的特殊性**：Windows 平台的进程管理与 Unix 不同
4. **高频 bug 需要优先修复**：此问题已多次出现，影响用户体验
5. **日志的重要性**：通过日志可以准确定位阻塞点
6. **Try-finally 不等于异常处理**：没有 except 的 finally 不会捕获异常，只会在退出时执行清理

## 注意事项

⚠️ **此 bug 出现频率较高，已多次发生**：
- 需要优先修复
- 修复后需要在所有 executor 中统一应用
- 需要在代码审查中检查是否有类似的无限等待问题
