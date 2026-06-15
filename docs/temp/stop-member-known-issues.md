# Stop Member 功能已知问题

## 创建时间
2026-06-13

## 问题描述

当用户调用 `stop_member()` 停止一个正在运行的 agent 时，会立即 cancel 该 agent 的 asyncio.Task（协程），但**不会停止该 agent 正在运行的 CLI 子进程**（如 Claude CLI、Codex CLI 等）。

### 具体表现

1. **协程被 cancel**：agent.run() 循环被中断，不再处理新消息
2. **子进程继续运行**：如果 agent 正在调用 LLM CLI（通过 `asyncio.create_subprocess_exec` 创建），该子进程会变成孤儿进程继续执行
3. **消息队列被清空**：待处理的消息被正确闭环
4. **状态正确更新**：agent 状态被设置为 "stopped"

### 影响范围

- **CLI 调用中的 agent**：Stop 时如果 agent 正在等待 CLI 响应（如调用 `claude` 命令执行任务），CLI 进程不会被终止
- **资源占用**：孤儿进程会继续占用 CPU、内存、API 配额等资源，直到任务自然完成
- **无功能影响**：由于 CLI 使用会话管理，孤儿进程完成后结果会保存到会话中，Start 后可以继续工作

### 不受影响的场景

- Agent 空闲时（没有正在执行的 CLI 调用）
- Docker 模式（容器可以整体停止）
- Agent 正在执行内部逻辑（非 CLI 调用）

---

## 根本原因

### 架构层级

```
Agent.run() (协程)
  └─> Agent._process_message() (协程)
      └─> bridge.execute_stream() (协程)
          └─> executor.execute_stream() (协程)
              └─> asyncio.create_subprocess_exec() (子进程)
```

### 问题点

1. **process 引用未保存**：子进程的引用只在 executor 的局部变量中，没有传递到上层
2. **无清理机制**：当协程被 cancel 时，没有 finally 块或 cleanup 逻辑来终止子进程
3. **无进程追踪**：Agent 层不知道当前是否有正在运行的子进程

### 代码位置

**子进程创建**：
- `agents_hub/agent_bridge/executors/claude.py:47` - Claude CLI
- `agents_hub/agent_bridge/executors/codex.py:63` - Codex CLI
- `agents_hub/agent_bridge/executors/opencode.py:46` - OpenCode CLI
- `agents_hub/agent_bridge/docker/container.py:47` - Docker exec

**协程取消**：
- `agents_hub/core/orchestration/group_chat.py:595` - `stop_member()` 中的 `task.cancel()`

---

## 解决方案（待实现）

### 方案 1：在 Executor 中追踪进程（推荐）

**修改点**：
1. 在 `ClaudeExecutor` 等类中添加 `_current_process` 属性
2. 在 `execute_stream()` 开始时保存进程引用
3. 添加 `stop()` 方法终止进程
4. 在 Agent 层调用 `executor.stop()` 后再 cancel 协程

**优点**：
- 精确控制子进程生命周期
- 不影响其他功能
- 可以逐步迁移各个 executor

**缺点**：
- 需要改造 agent_bridge 层
- 需要确保线程安全（process 引用的访问）

---

### 方案 2：使用进程组

**修改点**：
1. 创建子进程时使用 `start_new_session=True`（Unix）或 `creationflags=CREATE_NEW_PROCESS_GROUP`（Windows）
2. Stop 时通过进程组 ID 杀掉整个进程组

**示例**：
```python
# Unix
process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    start_new_session=True,  # 创建新进程组
)

# Stop 时
os.killpg(os.getpgid(process.pid), signal.SIGTERM)
```

**优点**：
- 可以杀掉所有子孙进程（CLI 可能创建的子进程）
- 实现相对简单

**缺点**：
- 平台差异（Unix vs Windows）
- 可能误杀无关进程（如果进程组被复用）

---

### 方案 3：在 Agent 层添加进程管理

**修改点**：
1. 在 `Agent` 类中添加 `_running_processes: list[asyncio.subprocess.Process]`
2. Bridge 层返回 process 引用给 Agent
3. Stop 时遍历并终止所有进程

**优点**：
- Agent 层有完全控制权
- 可以实现更复杂的策略（如优雅关闭）

**缺点**：
- 需要改造 bridge 接口
- 破坏层级封装

---

### 方案 4：依赖 CLI 自身管理（当前方案）

**说明**：
- 不做任何修改，依赖 CLI 的会话管理
- 孤儿进程执行完毕后，结果保存到会话中
- Start 后可以正常恢复

**优点**：
- 无需修改代码
- 利用现有的会话机制

**缺点**：
- 资源浪费（孤儿进程继续运行）
- 用户体验不佳（以为停止了，实际还在跑）
- API 配额浪费

---

## 临时解决方案

在修复之前，用户可以：

1. **使用 Reset 而非 Stop**：Reset 会清空会话，下次不会恢复孤儿进程的结果
2. **手动杀进程**：
   - Windows: `taskkill /F /IM claude.exe`
   - Unix: `pkill -f "claude "`
3. **检查进程**：
   ```bash
   # Windows
   tasklist | findstr claude
   
   # Unix
   ps aux | grep claude
   ```

---

## 测试计划

### 验证孤儿进程是否存在

1. 启动群聊，向 agent 发送一个长时间任务（如 "帮我分析整个代码仓库"）
2. 在任务执行过程中点击 Stop
3. 检查进程列表，确认 CLI 进程是否还在运行
4. 观察该进程何时自然结束

### 验证功能影响

1. Stop 后立即 Start，检查是否能正常工作
2. Stop 后 Reset，检查是否能清空状态
3. 多次 Stop/Start，检查是否有累积的孤儿进程

---

## 优先级建议

**P1（高优先级）**：
- 如果孤儿进程导致严重的资源泄漏或 API 配额浪费
- 如果用户频繁使用 Stop 功能

**P2（中优先级）**：
- 如果孤儿进程会自然结束，只是浪费少量资源
- 如果用户更多使用 Reset 而非 Stop

**P3（低优先级）**：
- 如果用户很少使用 Stop 功能
- 如果 CLI 任务通常很快完成

---

## 相关文档

- 实现计划：`D:\数据文档\claude_yunyi\plans\crystalline-plotting-hippo.md`
- Stop 实现：`agents_hub/core/orchestration/group_chat.py:562`
- Executor 实现：`agents_hub/agent_bridge/executors/`

---

## 更新记录

- 2026-06-13：创建文档，记录已知问题和解决方案
