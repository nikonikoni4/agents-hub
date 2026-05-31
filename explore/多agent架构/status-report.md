# agents-hub 未完成功能状态报告

> 更新日期：2026-05-31
> 对照来源：`explore/多agent架构/team.py` 末尾的问题清单（问题 1-25）

---

## 总览

| 状态 | 数量 |
|------|------|
| ✅ 已完成 | 12 |
| ⚠️ 部分完成 | 4 |
| ❌ 未完成 | 11 |

**结论**：核心功能已可运行（Agent 消息处理、群聊启动/加载、消息路由、错误处理、上下文管理）。剩余工作主要集中在异步等待机制、编排模式扩展、运维清理和前端集成。

---

## 高优先级 — 必须实现才能运行

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 1 | Agent.run() 完整实现 | ✅ | `base_agent.py:123-153`，含消息处理、群聊写入、TASK 回复 |
| 2 | 启动 Agent.run() 任务 | ✅ | `group_chat.py` 的 `start()` 和 `load()` 都用 `create_task` 启动 |
| 3 | AgentCall.is_timeout() 空指针修复 | ✅ | `agent_call.py:61` 已有 `if self.timeout_seconds is None: return False` |
| 4 | call_agent() 异步执行机制 | ⚠️ | 返回 call_id，但 `need_response=True` 时无等待机制，调用者只能轮询 |
| 5 | 错误处理体系 | ✅ | `exceptions.py` 定义了完整错误类，MessageRouter/call_agent/Agent 都已使用 |

### 问题 4 详情：call_agent() 异步等待

当前 `call_agent()` 只是将消息放入队列就返回 call_id。当 `need_response=True` 时，调用者没有途径等待结果。

**可选方案**：
- A. 返回 call_id，调用者通过 `get_call_status()` 轮询
- B. 使用 `asyncio.Event` 或 `Future`，`need_response=True` 时阻塞等待
- C. 支持回调机制

---

## 中优先级 — 影响功能完整性

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 6 | GroupChat 消息添加与 WebSocket 推送 | ⚠️ | `add_message` 已有（`group_chat_context.py:40`），WebSocket 推送未实现 |
| 7 | AgentCallManager 日志和清理机制 | ❌ | 只有 TODO 注释，无 logger、无轮询清理、无超时检查 |
| 8 | GroupChatContext 并发安全 | ✅ | `group_chat_repository.py` 已用 `asyncio.Lock` 保护所有写操作 |
| 9 | compact_messages() 错误处理 | ✅ | 有 `CompactionError`、JSON 解析重试、LLM 调用异常捕获 |
| 10 | Manager 任务分配逻辑 | ❌ | `Manager` 类只有 `__init__`，无 `MANAGER_ORCHESTRATE` 模式的特殊逻辑 |
| 11 | SEQUENCE_EXECUTE 类型实现 | ❌ | 枚举已定义（`models.py:37`），但 `GroupChat` 未根据 `group_type` 分支处理 |

### 问题 7 详情：AgentCallManager 需要实现

`agent_call_manager.py:20-24` 中的 TODO：
1. Logger 集成 — 记录 call 的创建、状态变更、完成/失败
2. 轮询清理 — 定期检查已完成的 AgentCall，调用 `can_be_deleted()` 判断是否删除
3. 超时检查 — 定期调用 `is_timeout()` 将超时 call 标记为 TIMEOUT

### 问题 10 详情：Manager 缺少编排逻辑

当前 `Manager` 和 `Worker` 类（`manager.py`、`worker.py`）只有构造函数，没有特殊逻辑。

`MANAGER_ORCHESTRATE` 模式下 Manager 应该：
- 接收任务后动态决定分配给哪个 Worker
- 跟踪子任务进度
- 汇总结果返回给调用者

### 问题 11 详情：SEQUENCE_EXECUTE 未实现

`GroupChat` 接收 `group_type` 参数但从未使用。`SEQUENCE_EXECUTE` 模式下应该：
- 按预定义顺序依次调用 agent（流水线）
- 前一个 agent 的输出作为后一个 agent 的输入

---

## 低优先级 — 优化和完善

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 12 | WebSocketManager 实现 | ❌ | 无任何 WebSocket 相关代码 |
| 13 | 团队管理类（TeamManager） | ❌ | 只有 `Team` 数据模型（`team.py`），无管理类 |
| 14 | GroupChat 配置持久化 | ✅ | `load()` 方法从 `agent_session_id.json` 恢复（2026-05-31 实现） |
| 15 | 错误恢复机制（重试） | ❌ | `Agent._process_message` 有 try-except 但无重试逻辑 |
| 16 | 性能监控和统计 | ❌ | 无任何监控代码 |
| 17 | 测试用例 | ⚠️ | 有 19 个单元测试通过，但缺少集成测试和通信层测试 |
| 18 | 配置管理 | ❌ | `MAX_TOKEN`、`LOCAL_DATA_PATH` 等硬编码在 `constants.py` |
| 19 | 文档和使用示例 | ⚠️ | 有 docstring，缺少架构文档和使用示例 |

### 问题 12 详情：WebSocket 推送

前端需要实时接收消息更新。需要：
1. WebSocketManager 类 — 管理连接（按 group_chat_id）
2. 消息格式定义 — JSON schema
3. 集成到 `GroupChatContext.add_message()` 中

### 问题 15 详情：错误恢复

当前 `Agent._process_message()` 捕获异常后直接抛出 `AgentExecutionError`，没有重试。建议：
- 网络错误 / LLM API 限流：自动重试（指数退避，最多 3 次）
- 业务错误：不重试，直接返回错误信息
- 系统错误：记录日志，通知管理员

---

## 清理项 — 代码质量

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 20 | 调试代码清理 | ✅ | explore 文件中的调试代码已清理到独立文件 |
| 21 | AgentContext 实现 | ✅ | `agent_context.py` 已实现增量加载上下文 |
| 22 | MessageRouter 错误处理 | ✅ | 使用 `InvalidMessageError`/`AgentNotFoundError`/`MessageDeliveryError` |
| 23 | call_agent() 返回值设计 | ✅ | 成功返回 call_id，失败返回 `e.to_mcp_response()` |
| 24 | AgentCall.can_be_deleted() 逻辑 | ❌ | 始终返回 `False`，TODO 未解决 |
| 25 | main() 测试代码 | ❌ | explore 文件中的 main() 只初始化了 GroupChat，无消息流转测试 |

### 问题 24 详情：can_be_deleted() 删除策略

需要确认：
- NOTIFICATION 类型完成后立即删除？
- TASK 类型保留多久（如 1 小时）？
- 有 `business_task_id` 的是否保留更久？
- 是否需要持久化到磁盘？

---

## 建议的下一步

1. **AgentCallManager 轮询清理**（问题 7）— 防止 `_calls` 字典无限增长导致内存泄漏
2. **Manager 任务分配逻辑**（问题 10）— `MANAGER_ORCHESTRATE` 模式的核心能力
3. **SEQUENCE_EXECUTE 实现**（问题 11）— 另一种编排模式，与 Manager 模式互补
4. **call_agent() 异步等待**（问题 4）— 完善 `need_response=True` 的用户体验
5. **WebSocket 推送**（问题 12）— 前端实时更新的基础
