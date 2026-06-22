# AgentCall 生命周期审查报告

**审查时间**: 2026-06-14  
**审查范围**: AgentCall 从创建到销毁的完整生命周期  
**审查目标**: 发现状态转换遗漏、闭环机制缺陷、内存泄漏风险

---

## 1. 创建流程分析

### 1.1 创建入口

AgentCall 通过 `AgentCallManager.create_call()` 创建，调用来源：

| 调用位置 | 场景 | 参数来源 |
|---------|------|---------|
| `mcp/server.py::call_agent` | Manager 派活给 Worker | MCP 工具调用 |
| `mcp/server.py::complete_task` | Worker 完成任务后通知调用方（Agent） | MCP 工具调用 |
| `group_chat.py::_cleanup_agent_queue` | Agent 停止时主动失败未完成调用 | 系统自动 |
| `base_agent.py::_fallback_close_task` | 兜底闭环，回复调用方（Agent） | 系统自动 |
| `group_chat.py::send_message_to_agent` | 前端用户发消息给 Agent | API 调用 |

### 1.2 初始化状态

```python
call = AgentCall(
    send_from=send_from,
    send_to=send_to,
    content=content,
    message_type=message_type,  # TASK 或 NOTIFICATION
    status=CallStatus.PENDING,   # 初始状态
    timeout_seconds=timeout_seconds,
    business_task_id=business_task_id,
)
```

**关键字段**:
- `call_id`: UUID 前 8 位，全局唯一
- `status`: 初始为 `PENDING`
- `has_agent_response`: 初始为 `False`（TASK 消息需通过 complete_task 闭环）
- `created_at`: 创建时间（用于超时判断）

### 1.3 持久化机制

创建后**立即持久化**到 `<group_chat_id>/agent_calls.jsonl`：
```python
self._persist_call(call)  # 追加模式，每次状态变更都追加一条记录
```

---

## 2. 状态转换完整链路

### 2.1 状态定义

```python
class CallStatus(Enum):
    PENDING = "pending"      # 已创建，等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    TIMEOUT = "timeout"      # 执行超时
```

### 2.2 状态转换图

```
PENDING ──→ RUNNING ──→ COMPLETED
   │            │            
   │            ├──→ FAILED
   │            │
   └────────────┴──→ TIMEOUT (清理循环检测)
```

**正常流程**:
1. **创建时**: `PENDING`
2. **执行前**: `base_agent.py::_process_message()` 调用 `update_status(call_id, RUNNING)`
3. **执行完成**: 
   - NOTIFICATION: `base_agent.py::_process_message()` 调用 `update_status(call_id, COMPLETED)`
   - TASK: 需要 `complete_task` MCP 工具调用 `mark_agent_response()` 设置 `COMPLETED`

**异常流程**:
1. **执行失败**: `base_agent.py::_process_message()` catch 异常，调用 `update_status(call_id, FAILED)` + `set_error()`
2. **超时**: 清理循环 `_check_timeouts()` 检测到超时，调用 `update_status(call_id, TIMEOUT)`

### 2.3 状态转换触发点详解

#### 触发点 1: PENDING → RUNNING
- **位置**: `agents_hub/core/agent/base_agent.py:223`
- **时机**: Agent 从队列取出消息，开始执行前
- **代码**:
  ```python
  self.agent_call_manager.update_status(msg.call_id, CallStatus.RUNNING)
  ```

#### 触发点 2a: RUNNING → COMPLETED (NOTIFICATION)
- **位置**: `agents_hub/core/agent/base_agent.py:256`
- **时机**: NOTIFICATION 消息执行完成后（不需要 complete_task）
- **代码**:
  ```python
  if msg.message_type != MessageType.TASK:
      self.agent_call_manager.update_status(msg.call_id, CallStatus.COMPLETED)
  ```

#### 触发点 2b: RUNNING → COMPLETED (TASK)
- **位置**: `agents_hub/mcp/server.py::complete_task:660`
- **时机**: Agent 通过 MCP 工具 `complete_task` 显式闭环
- **代码**:
  ```python
  group_chat.agent_call_manager.mark_agent_response(
      call_id=call_id,
      content=safe_content,
      success=True,  # 或 False
  )
  ```

#### 触发点 3: RUNNING → FAILED
- **位置**: `agents_hub/core/agent/base_agent.py:279`
- **时机**: 执行过程中抛出异常
- **代码**:
  ```python
  self.agent_call_manager.update_status(msg.call_id, CallStatus.FAILED)
  self.agent_call_manager.set_error(msg.call_id, str(e), exc=e)
  ```

#### 触发点 4: PENDING/RUNNING → TIMEOUT
- **位置**: `agents_hub/core/communication/agent_call_manager.py:362`
- **时机**: 清理循环定期检测超时
- **代码**:
  ```python
  if call.is_timeout():
      self.update_status(call_id, CallStatus.TIMEOUT)
  ```

---

## 3. 闭环机制详解

### 3.1 NOTIFICATION 消息闭环

**特征**: 单向通知，不需要接收方回复

**闭环时机**: 执行完成后自动 COMPLETED

**代码路径**:
```python
// agents_hub/core/agent/base_agent.py:255-256
if msg.message_type != MessageType.TASK:
    self.agent_call_manager.update_status(msg.call_id, CallStatus.COMPLETED)
```

**完整流程**:
```
create_call(NOTIFICATION) → PENDING → 投递到队列
  → Agent 取出 → RUNNING → 执行完成 → COMPLETED
```

### 3.2 TASK 消息闭环

**特征**: 需要接收方显式回复（通过 `complete_task` MCP 工具）

**闭环方式**:
1. **显式闭环**（推荐）: Agent 调用 `complete_task` MCP 工具
2. **兜底闭环**（备用）: `_fallback_close_task()` 自动补齐

#### 3.2.1 显式闭环流程

```
A call_agent(B)
  → create_call(TASK) → PENDING
  → 投递到 B 队列
  → B 取出 → RUNNING → 执行
  → B 调用 complete_task(call_id, content)
  → mark_agent_response() → COMPLETED + has_agent_response=True
  → 如果 A 是 Agent: 创建 NOTIFICATION call 通知 A
  → 如果 A 是 user: 写入群聊历史，前端轮询拉取
```

**关键代码**: `agents_hub/mcp/server.py::complete_task:660-664`
```python
group_chat.agent_call_manager.mark_agent_response(
    call_id=call_id,
    content=safe_content,
    success=success,  # True=COMPLETED, False=FAILED
)
```

#### 3.2.2 兜底闭环流程

**触发条件**:
```python
// agents_hub/core/agent/base_agent.py:536-543
if (result and result.text and call 
    and call.message_type == MessageType.TASK
    and not call.has_agent_response):
    # 执行兜底闭环
```

**触发时机**: `base_agent.py::run()` 主循环，每次消息处理完成后（第 647 行）

**兜底动作**:
1. 调用 `mark_agent_response(call_id, content, success=True)`
2. 如果调用方是 Agent: 创建 NOTIFICATION 通知调用方
3. 如果调用方是 user: 写入群聊历史

**风险**: 
- ⚠️ 如果 Agent 既调用了 `complete_task` 又被兜底闭环，会导致**双重通知**
- ✅ 当前通过 `has_agent_response` 标志防重，**理论上安全**

### 3.3 user 调用 vs Agent 调用的差异

| 调用方 | TASK 完成后行为 | 数据流向 |
|--------|---------------|---------|
| **user** | 写入群聊历史 `group_chat_context.add_message()` | 前端轮询 `/messages` 拉取 |
| **Agent** | 创建 NOTIFICATION call 通知调用方 | 投递到调用方队列 |

**判断逻辑**: `config.is_user_name(call.send_from)`

---

## 4. 清理机制评估

### 4.1 清理任务启动状态

**问题**: `start_cleanup()` 方法存在，但**未被调用**

**证据**:
```bash
$ grep -r "start_cleanup" agents_hub/
agents_hub/core/communication/agent_call_manager.py:434:    def start_cleanup(self):
agents_hub/core/communication/agent_call_manager.py:444:    async def stop_cleanup(self):
agents_hub/core/orchestration/group_chat.py:905:        await self.agent_call_manager.stop_cleanup()
```

**结论**: 
- ✅ `stop_cleanup()` 在 `GroupChat.cleanup()` 中被调用
- ❌ `start_cleanup()` **从未被调用**，清理循环**未启动**

### 4.2 清理循环设计

**清理间隔**: 60 秒（默认）

**清理任务**:
1. **检查超时**: `_check_timeouts()` → 将超时 call 标记为 TIMEOUT
2. **删除过期**: `_cleanup_deletable_calls()` → 删除可删除的 call

**删除策略** (`agent_call.py::can_be_deleted`):

| 状态 | 消息类型 | 保留时间 | 删除条件 |
|------|---------|---------|---------|
| PENDING/RUNNING | 任意 | 永久 | ❌ 不删除 |
| COMPLETED | NOTIFICATION | 5 分钟 | ✅ 可删除 |
| COMPLETED | TASK | 1 小时 | ✅ 可删除 |
| FAILED/TIMEOUT | 任意 | 24 小时 | ✅ 可删除 |
| 任意 | 任意（有 business_task_id） | 永久 | ❌ 不删除 |

### 4.3 持久化压缩机制

**触发时机**: 删除记录后调用 `_compact_persistence()`

**压缩逻辑**:
```python
# 重写整个 agent_calls.jsonl，只保留内存中的 call
with open(temp_path, "w") as f:
    for call in self._calls.values():
        f.write(json.dumps(data) + "\n")
temp_path.replace(self._persistence_path)
```

**作用**: 防止 jsonl 文件无限增长

---

## 5. 发现的问题

### 🔴 问题 1: 清理循环未启动（严重）

**问题描述**: `start_cleanup()` 从未被调用，导致：
1. 超时检测不生效（TIMEOUT 状态永远不会出现）
2. 过期 call 永远不会被删除
3. 内存无限增长，最终 OOM

**影响范围**: 所有长时间运行的 GroupChat

**代码位置**: `agents_hub/core/orchestration/group_chat.py`

**建议修复**:
```python
# 在 GroupChat.__init__() 或 start()/load() 后调用
self.agent_call_manager.start_cleanup()
```

**严重程度**: 🔴 严重（导致内存泄漏）

---

### 🟡 问题 2: 兜底闭环可能导致双重通知（中等）

**问题描述**: 
- Agent 调用 `complete_task` 后，`_fallback_close_task()` 仍会检查并尝试闭环
- 虽然有 `has_agent_response` 防重，但逻辑复杂，容易出错

**影响范围**: 所有 TASK 类型消息

**代码位置**: 
- `agents_hub/core/agent/base_agent.py:647`
- `agents_hub/mcp/server.py::complete_task:660`

**建议修复**:
1. **短期**: 保持现状，依赖 `has_agent_response` 防重
2. **长期**: 移除兜底闭环，强制要求 Agent 显式调用 `complete_task`

**严重程度**: 🟡 中等（已有防重机制，但增加维护成本）

---

### 🟡 问题 3: Agent 停止时未完成 call 的处理不够优雅（中等）

**问题描述**: 
`_cleanup_agent_queue()` 会将所有 PENDING/RUNNING call 标记为 FAILED，
但这些 call 可能只是因为 Agent 主动停止，而非执行失败。

**影响范围**: Agent 停止流程

**代码位置**: `agents_hub/core/orchestration/group_chat.py:549-590`

**建议改进**:
- 引入新状态 `CANCELLED`，区分"主动取消"和"执行失败"
- 或在 `error` 字段中标注停止原因

**严重程度**: 🟡 中等（语义不够清晰，但不影响功能）

---

### 🟢 问题 4: 持久化文件可能无限增长（较低）

**问题描述**: 
虽然有 `_compact_persistence()` 压缩机制，但因为清理循环未启动，
压缩永远不会被触发，`agent_calls.jsonl` 会无限追加。

**影响范围**: 磁盘空间占用

**代码位置**: `agents_hub/core/communication/agent_call_manager.py:386`

**建议修复**: 启动清理循环（修复问题 1）

**严重程度**: 🟢 较低（磁盘空间通常充足，且可手动清理）

---

### 🟢 问题 5: NOTIFICATION 消息的保留时间过短（较低）

**问题描述**: 
NOTIFICATION 完成后 5 分钟即删除，可能导致前端轮询时消息已被删除。

**影响范围**: 前端展示

**代码位置**: `agents_hub/core/communication/agent_call.py:92`

**建议改进**: 
- 将 NOTIFICATION 保留时间延长至 30 分钟
- 或前端改为 WebSocket 推送，不依赖轮询

**严重程度**: 🟢 较低（5 分钟足够大部分场景）

---

## 6. 数据流图

### 6.1 创建到销毁的完整流程

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 创建阶段                                                       │
├─────────────────────────────────────────────────────────────────┤
│ MCP Tool (call_agent) / API (send_message)                      │
│   ↓                                                              │
│ AgentCallManager.create_call()                                  │
│   ↓                                                              │
│ AgentCall(status=PENDING, has_agent_response=False)             │
│   ↓                                                              │
│ _persist_call() → agent_calls.jsonl (追加)                      │
│   ↓                                                              │
│ _index_call() → _calls_by_receiver[send_to].append(call_id)    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 2. 执行阶段                                                       │
├─────────────────────────────────────────────────────────────────┤
│ MessageRouter.send_message() → Agent.message_queue              │
│   ↓                                                              │
│ Agent.run() 取出消息                                             │
│   ↓                                                              │
│ update_status(RUNNING) → _persist_call()                        │
│   ↓                                                              │
│ _process_message() 执行 CLI                                      │
│   ↓                                                              │
│ ├─ NOTIFICATION: update_status(COMPLETED)                       │
│ └─ TASK: 等待 complete_task MCP 工具                            │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 3. 闭环阶段 (TASK only)                                          │
├─────────────────────────────────────────────────────────────────┤
│ MCP Tool (complete_task) / _fallback_close_task()               │
│   ↓                                                              │
│ mark_agent_response(success=True/False)                         │
│   ↓                                                              │
│ status=COMPLETED/FAILED, has_agent_response=True                │
│   ↓                                                              │
│ _persist_call()                                                 │
│   ↓                                                              │
│ ├─ user 调用: add_message() → 群聊历史                          │
│ └─ Agent 调用: create_call(NOTIFICATION) → 通知调用方           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ 4. 清理阶段 (❌ 当前未启动)                                       │
├─────────────────────────────────────────────────────────────────┤
│ [MISSING] start_cleanup() 从未被调用                             │
│   ↓                                                              │
│ _cleanup_loop() (每 60 秒)                                       │
│   ↓                                                              │
│ ├─ _check_timeouts(): PENDING/RUNNING → TIMEOUT                 │
│ └─ _cleanup_deletable_calls(): 删除过期 call                     │
│       ↓                                                          │
│       _unindex_call() → 从 _calls 和 _calls_by_receiver 移除     │
│       ↓                                                          │
│       _compact_persistence() → 重写 jsonl 文件                   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 状态转换与方法调用映射

| 方法 | 作用 | 状态变化 | 副作用 |
|------|------|---------|--------|
| `create_call()` | 创建 call | → PENDING | 持久化、索引 |
| `update_status()` | 更新状态 | 任意 → 任意 | 持久化、设置时间戳 |
| `mark_agent_response()` | TASK 闭环 | → COMPLETED/FAILED | 持久化、设置 has_agent_response |
| `set_result()` | 设置结果 | → COMPLETED | 持久化 |
| `set_error()` | 设置错误 | → FAILED | 持久化 |
| `_check_timeouts()` | 超时检测 | → TIMEOUT | 通过 update_status() |
| `_cleanup_deletable_calls()` | 删除过期 | 从内存删除 | 触发压缩 |

---

## 7. 改进建议

### 7.1 立即修复（严重问题）

1. **启动清理循环**:
   ```python
   # agents_hub/core/orchestration/group_chat.py::start() 第 126 行后
   self.agent_call_manager.start_cleanup()
   ```

2. **在 load() 中也启动清理循环**:
   ```python
   # agents_hub/core/orchestration/group_chat.py::load() 第 149 行后
   self.agent_call_manager.start_cleanup()
   ```

### 7.2 中期优化（降低复杂度）

1. **移除兜底闭环**，强制要求 Agent 显式调用 `complete_task`
   - 优点: 逻辑清晰，责任明确
   - 缺点: MCP 断连会导致 call 悬空

2. **引入 CANCELLED 状态**，区分主动停止和执行失败
   - 修改 `CallStatus` 枚举
   - 修改 `_cleanup_agent_queue()` 逻辑

### 7.3 长期改进（架构层面）

1. **清理策略可配置化**: 将保留时间配置移到 config 或群聊元数据
2. **监控指标**: 增加 call 数量、清理频率的 metrics
3. **前端推送**: 使用 WebSocket 替代轮询，降低对 call 保留时间的依赖

---

## 8. 总结

### 8.1 核心发现

1. **清理循环未启动** → 内存泄漏、超时不生效
2. 闭环机制设计合理，但兜底闭环增加复杂度
3. 状态转换链路清晰，覆盖大部分异常情况
4. 持久化和索引机制完善

### 8.2 风险评估

| 风险项 | 当前状态 | 影响 | 优先级 |
|--------|---------|------|--------|
| 内存泄漏 | 🔴 存在 | 长时间运行必崩溃 | P0 |
| 超时不生效 | 🔴 存在 | TIMEOUT 状态永远不出现 | P0 |
| 双重通知 | 🟡 已防重 | 增加维护成本 | P2 |
| 持久化文件增长 | 🟢 可接受 | 磁盘占用缓慢增长 | P3 |

### 8.3 修复优先级

1. **P0**: 启动清理循环（2 行代码修复）
2. **P1**: 验证清理循环生效（增加单元测试）
3. **P2**: 考虑移除兜底闭环（需评估 MCP 稳定性）
4. **P3**: 引入 CANCELLED 状态（架构优化）

---

**审查人**: Claude Opus 4.7  
**审查方法**: 代码静态分析 + 数据流追踪  
**置信度**: 高（已覆盖所有关键路径）

