# Agent Call 清理策略

## 概述

`AgentCallManager` 负责管理所有跨 Agent 的异步调用记录。为了避免内存无限增长，需要定期清理已完成的调用记录。同时，为了保证系统重启后的一致性，所有调用记录都会持久化到磁盘。

## 持久化机制

### 为什么需要持久化？

**一致性问题：**
```
场景：
1. Agent A 调用 call_agent，创建 call_id="abc123"
2. call_id 记录在 AgentCallManager 的内存中
3. 同时，这次 MCP tool call 也记录在 Agent A 的对话历史中（由 Claude/Codex 平台管理）
4. 程序重启
5. AgentCallManager 内存清空，call_id="abc123" 丢失
6. 但 Agent A 的对话历史还在，里面还有 call_id="abc123"
7. Agent A 继续对话时可能会引用这个 call_id，但查询时返回 None

问题：
AgentCallManager (内存)          Agent 对话历史 (持久化)
     ❌ 无数据                    ✅ 有 call_id="abc123"
                                      
                    不一致！
```

### 持久化实现

**文件路径：**
```
{data_path}/{project_path}/{group_chat_id}/agent_calls.jsonl
```

**文件格式（JSONL）：**
```jsonl
{"call_id": "abc123", "status": "pending", "created_at": "2026-05-31T10:00:00", ...}
{"call_id": "abc123", "status": "running", "started_at": "2026-05-31T10:00:05", ...}
{"call_id": "abc123", "status": "completed", "completed_at": "2026-05-31T10:01:00", ...}
{"call_id": "def456", "status": "pending", "created_at": "2026-05-31T10:02:00", ...}
```

**持久化时机：**
1. **创建时**：`create_call()` 立即追加到文件
2. **状态变更时**：`update_status()` 追加新记录
3. **完成时**：`set_result()` / `set_error()` 追加新记录
4. **清理时**：`_cleanup_deletable_calls()` 压缩文件，去除已删除的记录

**加载机制：**
- 启动时读取整个文件
- 同一个 call_id 可能有多条记录（状态变更历史）
- 加载时取最新记录（后面的覆盖前面的）

**压缩机制：**
- 每次清理删除记录后，重写持久化文件
- 只保留内存中的调用记录
- 避免文件无限增长

**注意事项：**
- `result` 字段不持久化（可能很大，且重启后无法恢复）
- 重启后加载的调用记录，`result` 为 `None`

## 删除策略

### 1. 不删除的情况

以下情况的 `AgentCall` **不会被删除**：

| 条件 | 原因 |
|------|------|
| 状态为 `PENDING` 或 `RUNNING` | 任务还在执行中 |
| `business_task_id` 不为 `None` | 有业务任务关联，需要长期追踪 |
| `completed_at` 为 `None` | 没有完成时间，无法判断保留时长 |

### 2. 可删除的情况

根据 **状态** 和 **消息类型** 决定保留时长：

| 状态 | 消息类型 | 保留时长 | 原因 |
|------|---------|---------|------|
| `COMPLETED` | `NOTIFICATION` | 5 分钟 | 不需要回复，完成后无后续交互 |
| `COMPLETED` | `TASK` | 1 小时 | 可能需要查询结果、调试 |
| `FAILED` | 任意 | 24 小时 | 需要调试、分析失败原因 |
| `TIMEOUT` | 任意 | 24 小时 | 需要调试、分析超时原因 |

### 3. 删除逻辑流程图

```
开始
  ↓
状态是 PENDING/RUNNING？ ──是→ 不删除
  ↓ 否
有 business_task_id？ ──是→ 不删除
  ↓ 否
completed_at 为空？ ──是→ 不删除
  ↓ 否
计算完成后经过的时间
  ↓
状态是 COMPLETED？
  ↓ 是
  消息类型是 NOTIFICATION？
    ↓ 是
    经过时间 > 5分钟？ ──是→ 删除
    ↓ 否
    不删除
  ↓ 否（TASK）
  经过时间 > 1小时？ ──是→ 删除
  ↓ 否
  不删除
  ↓ 否（FAILED/TIMEOUT）
经过时间 > 24小时？ ──是→ 删除
  ↓ 否
  不删除
```

## 实现细节

### AgentCall.can_be_deleted()

```python
def can_be_deleted(self, retention_config: dict[str, int] | None = None) -> bool:
    """
    判断是否可以删除
    
    Args:
        retention_config: 自定义保留时间配置（秒），格式：
            {
                "notification_completed": 300,  # NOTIFICATION 完成后保留 5 分钟
                "task_completed": 3600,         # TASK 完成后保留 1 小时
                "failed": 86400,                # 失败后保留 24 小时
            }
    
    Returns:
        bool: 是否可以删除
    """
```

### AgentCallManager 清理机制

`AgentCallManager` 启动后台清理任务，定期执行：

1. **超时检查**：调用 `AgentCall.is_timeout()` 检查超时，更新状态为 `TIMEOUT`
2. **清理删除**：调用 `AgentCall.can_be_deleted()` 判断并删除可删除的调用

#### 配置参数

```python
AgentCallManager(
    group_chat_id="xxx",
    project_path="xxx",
    cleanup_interval=60,  # 清理检查间隔（秒），默认 60 秒
    retention_config={     # 自定义保留时间配置（秒）
        "notification_completed": 300,   # 5 分钟
        "task_completed": 3600,          # 1 小时
        "failed": 86400,                 # 24 小时
    }
)
```

## 使用示例

### 1. 启动清理任务

```python
# 创建 AgentCallManager
manager = AgentCallManager(
    group_chat_id="chat_001",
    project_path="my_project"
)

# 启动后台清理任务
manager.start_cleanup()
```

### 2. 自定义保留时间

```python
# 自定义保留时间：NOTIFICATION 立即删除，TASK 保留 30 分钟
manager = AgentCallManager(
    group_chat_id="chat_001",
    project_path="my_project",
    cleanup_interval=30,  # 每 30 秒检查一次
    retention_config={
        "notification_completed": 0,      # 立即删除
        "task_completed": 1800,           # 30 分钟
        "failed": 3600,                   # 1 小时
    }
)
manager.start_cleanup()
```

### 3. 停止清理任务

```python
# 停止后台清理任务
await manager.stop_cleanup()
```

### 4. 查看统计信息

```python
# 获取当前调用统计
stats = manager.get_stats()
print(stats)
# 输出：
# {
#     "total": 10,
#     "by_status": {
#         "pending": 2,
#         "running": 3,
#         "completed": 4,
#         "failed": 1
#     },
#     "by_message_type": {
#         "task": 6,
#         "notification": 4
#     }
# }
```

## 注意事项

### 1. 业务任务关联

如果 `AgentCall` 有 `business_task_id`，则**不会被自动删除**。这类调用应该由业务任务管理器负责清理：

```python
# 创建有业务任务关联的调用
call = manager.create_call(
    send_from="agent_a",
    send_to="agent_b",
    content="执行任务",
    message_type=MessageType.TASK,
    business_task_id="task_123"  # 有业务任务关联
)

# 这个调用不会被自动删除，需要业务任务管理器手动删除
# 当业务任务完成后：
del manager._calls[call.call_id]
```

### 2. 持久化与重启

**持久化保证：**
- 所有调用记录都会持久化到 `agent_calls.jsonl`
- 系统重启后自动加载历史记录
- 保证 Agent 对话历史中的 call_id 仍然有效

**限制：**
- `result` 字段不持久化（可能很大，且无法序列化）
- 重启后加载的调用记录，`result` 为 `None`
- 如果 Agent 需要查询重启前的结果，会得到 `None`

**容错处理：**
```python
# 查询调用
call = manager.get_call(call_id)

if call is None:
    # 调用不存在（已被清理或数据丢失）
    logger.warning(f"调用 {call_id} 不存在")
elif call.result is None and call.status == CallStatus.COMPLETED:
    # 调用存在但结果为空（可能是重启后加载的）
    logger.warning(f"调用 {call_id} 的结果已丢失（系统重启）")
```

### 3. 性能考虑

- **清理间隔**：默认 60 秒，可根据调用频率调整
  - 高频场景（每秒数十个调用）：建议 30 秒
  - 低频场景（每分钟几个调用）：建议 120 秒

- **保留时间**：默认配置适合大多数场景，可根据需求调整
  - 调试阶段：建议延长保留时间（如 TASK 保留 24 小时）
  - 生产环境：建议使用默认配置

- **持久化性能**：
  - 追加写入，性能较好
  - 清理时压缩文件，避免文件无限增长
  - 启动时加载，文件越大加载越慢（建议定期清理历史文件）

## 未来优化

### 已实现
- ✅ **持久化机制**：所有调用记录持久化到 JSONL 文件
- ✅ **自动加载**：系统重启后自动加载历史记录
- ✅ **文件压缩**：清理时自动压缩持久化文件

### 待实现（TODO）

1. **历史查询优化**：
   - 当前问题：查询不到的 call_id 只返回 None
   - 优化方案：
     - 方案 A：从日志中解析历史调用信息（性能较差，仅用于调试）
     - 方案 B：增加归档文件，保留更长时间的历史记录
   - 优先级：低（大多数场景下 Agent 不需要查询很久以前的调用）

2. **call_id 长度优化**：
   - 当前：8 位 UUID（2^32 ≈ 42 亿种可能）
   - 问题：如果支持历史查询，碰撞概率增大
   - 优化方案：扩展到 16 位（2^64 种可能，碰撞概率极低）
   - 优先级：低（当前 8 位在内存中碰撞概率极低）

3. **分级存储**：
   - 热数据（运行中）：内存
   - 温数据（最近完成）：内存 + 持久化
   - 冷数据（历史记录）：归档文件或数据库

4. **智能清理**：
   - 根据内存使用情况动态调整保留时间
   - 优先删除 NOTIFICATION 类型的调用

5. **审计日志**：
   - 删除前将调用记录写入审计日志
   - 支持按时间范围查询历史调用

6. **监控告警**：
   - 监控调用堆积情况（pending/running 数量）
   - 监控超时率、失败率
   - 异常情况自动告警

7. **result 持久化**：
   - 当前 result 不持久化（可能很大，且无法序列化）
   - 优化方案：只持久化 result 的摘要或关键信息
   - 或者提供可选的完整持久化（需要自定义序列化）
