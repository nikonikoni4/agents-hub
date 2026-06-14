# Core 模块重构任务清单

**创建时间**: 2026-06-14  
**来源**: [Core 模块问题报告](../history-bugs/2026-06-14-core-module-issues.md) + [GroupChat activate 问题](../history-bugs/2026-06-13-group-chat-activate-missing-agent-registration.md)

---

## 🔴 P0 - 阻塞性问题（立即修复）

### Task 1: Agent 启动后未注册到 MessageRouter

**问题描述**:
- `stop_member()` 会调用 `message_router.unregister(agent_name)` 注销 agent
- 但 `start_member()` 中没有重新注册
- 导致 agent 重启后无法接收消息

**相关代码**:
- `agents_hub/core/orchestration/group_chat.py:738-749` - `start_member()`
- `agents_hub/core/orchestration/group_chat.py` - `stop_member()`

**修复方案**:
在 `start_member()` 中添加：
```python
self.message_router.register(agent_name, agent.message_queue)
```

**验证方法**:
1. 停止某个 agent
2. 重新启动该 agent
3. 发送消息给该 agent
4. 验证消息能正常送达

**优先级**: P0  
**预估工时**: 0.5h  
**状态**: 待处理

---

### Task 2: Agent 重置后未注册到 MessageRouter

**问题描述**:
- `reset_member()` 内部调用 `stop_member()`，会注销 agent
- 但重置后没有重新注册到 MessageRouter
- 与 Task 1 是同样的问题

**相关代码**:
- `agents_hub/core/orchestration/group_chat.py:790-818` - `reset_member()`

**修复方案**:
在 `reset_member()` 中，启动 agent 后添加：
```python
self.message_router.register(agent_name, agent.message_queue)
```

**验证方法**:
1. 重置某个 agent
2. 发送消息给该 agent
3. 验证消息能正常送达

**优先级**: P0  
**预估工时**: 0.5h  
**状态**: 待处理

---

### Task 3: 日志级别不规范导致问题无法排查

**问题描述**:
1. 关键流程（`send_message()`）使用 DEBUG 级别，生产环境无法排查
2. `AgentNotFoundError` 等致命错误也是 DEBUG 级别
3. MessageRouter 注册/注销缺少日志

**相关代码**:
- `agents_hub/core/communication/message_router.py` - `send_message()`
- `agents_hub/core/orchestration/group_chat.py` - `send_message_to_agent()`

**修复方案**:
1. `send_message_to_agent()` 入口添加 INFO 日志（记录 call_id、from、to）
2. 所有 `AgentNotFoundError` 改为 ERROR 级别
3. MessageRouter 的 `register()`/`unregister()` 添加 INFO 日志
4. 记录 MessageRouter 当前注册状态

**日志级别规范**:
- **INFO**: 关键流程入口/出口（消息投递、agent 启动/停止、GroupChat 生命周期）
- **ERROR**: 所有异常抛出前、关键操作失败
- **DEBUG**: 内部状态变化、详细参数

**优先级**: P0  
**预估工时**: 1h  
**状态**: 待处理

---

## 🟠 P1 - 数据一致性问题（本周修复）

### Task 4: initialize_metadata 幂等性缺陷

**问题描述**:
- `GroupChat.start()` 先 `load()` 加载已有 metadata
- 然后调用 `initialize_metadata()` 重新创建并保存
- `created_at` 没有传入，导致被 `datetime.now()` 覆盖

**相关代码**:
- `agents_hub/core/orchestration/group_chat.py:86-126` - `start()`
- `agents_hub/core/context/group_chat_runtime.py:234-260` - `initialize_metadata()`

**修复方案**:
1. 在 `start()` 开始处添加幂等性检查：
   ```python
   if self.runtime.state.metadata is not None:
       logger.debug("群聊已初始化，跳过 start()")
       return
   ```
2. 如果需要保留原逻辑，在调用 `initialize_metadata()` 时传入已加载的 `created_at`

**优先级**: P1  
**预估工时**: 1h  
**状态**: 待处理

---

### Task 5: load_group_chat_from_disk 缺少异常处理

**问题描述**:
- `load_group_chat_from_disk()` 直接操作文件 IO（json.load、open）
- 没有捕获 `OSError`、`JSONDecodeError` 等异常
- 违反编码规范：外部接口层必须捕获错误并转换为领域异常

**相关代码**:
- `agents_hub/core/orchestration/group_chat_manager.py:290-379`

**修复方案**:
添加 try-catch：
```python
try:
    with open(metadata_file, encoding="utf-8") as f:
        data = json.load(f)
except OSError as e:
    raise FileSystemError(f"无法读取 metadata 文件: {metadata_file}") from e
except json.JSONDecodeError as e:
    raise DataParseError(f"metadata 文件格式错误: {metadata_file}") from e
```

**优先级**: P1  
**预估工时**: 1h  
**状态**: 待处理

---

### Task 6: 用户发送消息时重复加载 + 顺序不当

**问题描述**:
1. `GroupChatService.send_message()` 先调用 `activate_group_chat()`（内部会 `load_group_chat`）
2. 然后又显式调用 `load_group_chat()`
3. 成员验证在激活之后，顺序不合理

**相关代码**:
- `agents_hub/api/services/group_chat_service.py` - `send_message()`

**修复方案**:
1. 移除显式的 `load_group_chat()` 调用，只保留 `activate()`
2. 调整顺序：
   - 先 load（不激活）
   - 验证成员身份
   - 再激活群聊
   - 再发送消息

**优先级**: P1  
**预估工时**: 1h  
**状态**: 待处理

---

## 🟡 P2 - 内存泄漏与清理机制（2周内修复）

### Task 7: Agent Call 清理机制失效

**问题描述**:
1. `start_cleanup` 没有被调用，内存中的 Agent Call 无法被清理
2. `can_be_deleted` 字段只在清理循环中使用，但清理循环未运行
3. `GET /group-chats/{id}/agent-calls` 加载所有历史记录，无分页

**相关代码**:
- `agents_hub/core/communication/agent_call_manager.py`
- `agents_hub/api/routes/group_chat.py` - `/agent-calls` 端点

**修复方案**:
1. 在 `GroupChat.start()` 或 `activate()` 中调用 `start_cleanup()`
2. 定义 Agent Call 过期策略（如：已完成的保留 24 小时）
3. API 端点添加分页参数（limit, offset）
4. 前端只加载最近的 N 条

**待讨论**:
- 已完成的 Agent Call 应保留多长时间？
- 是否需要"归档"机制？

**优先级**: P2  
**预估工时**: 3h  
**状态**: 待处理

---

### Task 8: Task 清理机制缺失

**问题描述**:
1. `TaskManager.__init__()` 调用 `_load_from_persistence()`，加载全部历史任务（包括已归档的）
2. TaskManager 没有任何清理方法
3. 已归档的任务永远不会被清理，内存占用持续增长

**相关代码**:
- `agents_hub/core/communication/task_manager.py:56` - `__init__()`
- `agents_hub/core/communication/task_manager.py:276-307` - `_load_from_persistence()`

**修复方案**:
1. 实现类似 `AgentCallManager.start_cleanup()` 的清理机制
2. 定义已归档任务的过期策略
3. API 端点添加分页

**待讨论**:
- 已归档任务应保留多长时间？
- 是否需要定期清理机制？

**优先级**: P2  
**预估工时**: 3h  
**状态**: 待处理

---

## 🟢 P3 - 架构优化与代码规范（重构时处理）

### Task 9: Runtime 与 Context 高度耦合

**问题描述**:
- Runtime 和 Context 之间存在高度耦合
- 每个 Runtime 的函数都需要经过 Context 透传调用
- 调用链冗长：`GroupChat → Context → Runtime → Repository`
- Context 层只是简单转发，没有增加业务价值

**相关代码**:
- `agents_hub/core/context/group_chat_context.py`
- `agents_hub/core/context/group_chat_runtime.py`

**待讨论**:
1. 是否移除 Context 层，让 GroupChat 直接调用 Runtime？
2. Context 是否应该承担更多业务逻辑，而非简单透传？
3. 如何平衡分层架构的清晰性与代码简洁性？

**优先级**: P3  
**预估工时**: 8h（含讨论和重构）  
**状态**: 待讨论

---

### Task 10: 持久化引用写法不规范

**问题描述**:
- `update_agent_member_info()` 修改 `agent_member_info`（单个对象）
- 但保存时用 `self.state.agent_member_infos`（整个字典）
- 虽然是同一引用，但写法不规范，容易误解

**相关代码**:
- `agents_hub/core/context/group_chat_runtime.py:397-423` - `update_agent_member_info_from_result()`
- `agents_hub/core/context/group_chat_runtime.py:453-470` - `update_agent_status()`

**修复方案**:
1. 统一接口设计，只提供一个 save 函数
2. 持久化时明确使用被修改对象的引用

**优先级**: P3  
**预估工时**: 2h  
**状态**: 待处理

---

### Task 11: 接口命名与职责不匹配

**问题描述**:
- 函数名 `update_agent_member_info` 暗示更新整个 member info
- 但实际职权仅限于更新 session_id（main_session/btw_session）

**相关代码**:
- `agents_hub/core/context/group_chat_runtime.py:397-423`

**修复方案**:
重命名为 `update_agent_session` 或 `update_agent_session_id`

**优先级**: P3  
**预估工时**: 0.5h  
**状态**: 待处理

---

### Task 12: 冗余端点

**问题描述**:
- `GET /group-chats` 返回所有群聊的完整信息
- `GET /group-chats/{group_chat_id}` 获取单个群聊详情是冗余的

**相关代码**:
- `agents_hub/api/routes/group_chat.py`

**修复方案**:
删除单个群聊端点，前端从 list 结果中筛选

**优先级**: P3  
**预估工时**: 0.5h  
**状态**: 待处理

---

### Task 13: is_active_only 参数无用

**问题描述**:
- `list_all_group_chats()` 的 `is_active_only` 参数前端未使用
- 属于遗留代码

**相关代码**:
- `agents_hub/core/orchestration/group_chat_manager.py:224`

**修复方案**:
删除该参数

**优先级**: P3  
**预估工时**: 0.5h  
**状态**: 待处理

---

### Task 14: handoff_dir 路径硬编码

**问题描述**:
- 留痕文件目录硬编码在代码中
- 应统一管理

**相关代码**:
- `agents_hub/core/agent/base_agent.py:351`

**修复方案**:
将路径定义移入 `GroupChatPaths`，统一管理

**优先级**: P3  
**预估工时**: 0.5h  
**状态**: 待处理

---

### Task 15: 压缩流程错误处理有问题

**问题描述**:
- 使用 `except Exception` 吞掉异常，违反编码规范
- 应转换为领域异常或让异常冒泡

**相关代码**:
- `agents_hub/core/agent/base_agent.py:348-366`

**修复方案**:
移除 `except Exception`，让异常冒泡，或转换为领域异常

**优先级**: P3  
**预估工时**: 0.5h  
**状态**: 待处理

---

## ⚪ P4 - 待讨论设计问题

### Task 16: 群聊加载策略设计

**问题描述**:
当群聊数量过多时，如何高效加载？

**方案 A：按活跃文件夹加载**
- 某个群聊最近活跃 → 加载该文件夹下的全部群聊
- 优点：保持项目维度的组织性
- 缺点：可能加载不相关的群聊

**方案 B：按前 N 个活跃群聊加载**
- 直接取最近活跃的前 20 个群聊
- 优点：精确控制加载数量
- 缺点：可能遗漏同一项目的其他群聊

**遗留问题**:
1. 不活跃的群聊如何获取？是否需要搜索/筛选功能？
2. 是否需要分页机制？

**优先级**: P4  
**状态**: 待讨论

---

### Task 17: Agent 压缩流程优化

**待讨论**:
1. hand-off 文档应包含哪些信息？
2. 压缩提示词（`COMPACT_CONTEXT_PROMPT`）应如何优化？
3. 压缩是否应该被视为 Agent 的一种正式状态？
   - 如果是：`stopped` 状态下也应该支持压缩
   - 如果不是：当前实现（只检查 busy）是合理的

**相关代码**:
- `agents_hub/core/agent/base_agent.py:333-366` - `compress_context()`

**优先级**: P4  
**状态**: 待讨论

---

### Task 18: _cleanup_agent_queue 逻辑重新设计

**问题描述**:
当前实现可能存在严重问题，需要仔细判断：

1. 没有判断消息类型是不是 `MessageType.TASK` 就直接 `mark_agent_response`
2. 按照惯例，所有发送消息都应该保留到群消息，所有群消息保存都应该使用回调函数通知前端更新
3. 该不该以 stop 的 agent 身份发送消息？
   - 如果简单一点，至少需要增加上系统标识

**相关代码**:
- `agents_hub/core/orchestration/group_chat.py` - `_cleanup_agent_queue()`

**优先级**: P4  
**状态**: 待讨论

---

### Task 19: Logger 使用规范制定

**问题描述**:
当前 core 模块中 logger 的使用方式不统一、不规范

**待讨论**:
1. Logger 的统一配置方式
2. 日志级别的使用标准（何时用 debug/info/warning/error）
3. 日志消息的格式规范（是否包含上下文信息、变量格式等）
4. 模块间日志的一致性要求

**优先级**: P4  
**状态**: 待讨论

---

## 执行计划

**第一阶段（本周）**:
- [ ] Task 1: Agent 启动后未注册（0.5h）
- [ ] Task 2: Agent 重置后未注册（0.5h）
- [ ] Task 3: 日志级别不规范（1h）
- [ ] Task 4: initialize_metadata 幂等性（1h）
- [ ] Task 5: load_group_chat_from_disk 异常处理（1h）
- [ ] Task 6: 重复加载 + 顺序不当（1h）

**第二阶段（2周内）**:
- [ ] Task 7: Agent Call 清理机制（3h）
- [ ] Task 8: Task 清理机制（3h）

**第三阶段（重构时）**:
- [ ] 讨论 P4 设计问题（Task 16-19）
- [ ] 执行 P3 架构优化（Task 9-15）

---

## 相关文档

- [Core 模块问题报告](../history-bugs/2026-06-14-core-module-issues.md)
- [GroupChat activate 问题](../history-bugs/2026-06-13-group-chat-activate-missing-agent-registration.md)
- [架构文档](../ARCHITECTURE.md)
- [Core Foundation Spec](../specs/2026-05-31-core-foundation.md)
- [Core Communication Spec](../specs/2026-05-31-core-communication.md)
- [Core Context Spec](../specs/2026-05-31-core-context.md)
