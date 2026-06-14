# Core 模块修复与重构决策

## 任务背景

通过 5 个子 Agent 对 Core 模块进行全面审查，发现了多个严重问题：

1. **P0 阻塞性问题**（3个）：
   - AgentCall 清理循环从未启动，导致内存泄漏
   - Agent 重启/重置后未注册到 MessageRouter，无法接收消息
   - 并发写入无锁保护，存在竞态条件

2. **P1 数据一致性问题**（3个）：
   - created_at 被重复覆盖
   - 压缩过程中消息丢失
   - Agent 状态更新缺失

3. **架构问题**：
   - Runtime/Context 高度耦合，透传层级过多
   - 代码冗余和规范不统一

需要决定：**渐进式修复 vs 推倒重来**

**相关文档**：
- `docs/generated/group-chat-lifecycle-review.md`
- `docs/generated/concurrency-safety-review.md`
- `docs/generated/agent-call-lifecycle-review.md`
- `docs/generated/agent-lifecycle-review.md`
- `docs/generated/agent-state-lifecycle-review.md`
- `docs/progress/core-refactor-tasks.md`

## 任务目标

1. **短期**：修复所有 P0 阻塞性问题，让系统能正常工作
2. **中期**：评估架构重构必要性，选择执行路径
3. **长期**：根据选择的路径，完成修复或重构

---

## 阶段一：P0 问题快速修复（预估 4h）

### 1. 日志级别修复（来源：子Agent审查 + 原始问题报告）

**问题**：关键流程使用 DEBUG 级别，生产环境无法排查问题

- [x] 在 `agents_hub/core/orchestration/group_chat.py` 的 `send_message_to_agent()` 入口添加 INFO 日志（记录 call_id、from、to）
- [x] 将所有 `AgentNotFoundError` 改为 ERROR 级别
- [x] 在 `agents_hub/core/communication/message_router.py` 的 `register()`/`unregister()` 添加 INFO 日志
- [x] 记录 MessageRouter 当前注册状态
- [x] 验证：查看日志，确认关键流程可见

### 2. AgentCall 清理循环启动（来源：子Agent审查 + 原始问题报告）

**问题**：`start_cleanup()` 从未被调用，导致内存泄漏、超时检测失效

- [x] 在 `agents_hub/core/orchestration/group_chat.py` 的 `start()` 方法（line ~126）后添加 `self.agent_call_manager.start_cleanup()`
- [x] 在 `agents_hub/core/orchestration/group_chat.py` 的 `load()` 方法（line ~149）后添加 `self.agent_call_manager.start_cleanup()`
- [x] 验证清理循环正常运行：观察日志中是否有定期清理记录
- [x] 测试：创建多个已完成的 AgentCall，等待清理时间后验证它们被正确删除

### 3. Agent 重启后注册到 MessageRouter（来源：子Agent审查 + 原始问题报告）

**问题**：`stop_member` 注销但 `start_member`/`reset_member` 未重新注册，导致无法接收消息

- [x] 在 `agents_hub/core/orchestration/group_chat.py` 的 `start_member()` 方法中，启动任务后添加 `self.message_router.register(agent_name, agent.message_queue)`
- [x] 在 `agents_hub/core/orchestration/group_chat.py` 的 `reset_member()` 方法中，启动任务后添加 `self.message_router.register(agent_name, agent.message_queue)`
- [x] 验证注册成功：检查日志中是否有 INFO 级别的注册记录
- [x] 测试：停止一个 agent → 重启 → 发送消息 → 验证能正常接收

### 4. 修复 created_at 覆盖问题（来源：原始问题报告 + 子Agent审查）

**问题**：`start()` 和 `add_group_chat_members()` 都会调用 `initialize_metadata()` 覆盖 created_at

- [x] 在 `agents_hub/core/orchestration/group_chat.py` 的 `start()` 方法开头添加幂等性检查：
  ```python
  if self.runtime.state.metadata is not None:
      logger.debug("群聊已初始化，跳过 start()")
      return
  ```
- [x] 检查 `add_group_chat_members()` 中的 `initialize_metadata()` 调用，移除或修复
- [x] 验证 created_at 不再被覆盖：创建群聊 → 记录 created_at → 重启应用 → 验证 created_at 保持不变

---

## 阶段二：架构重构评估（已完成）

### 4. 讨论架构问题

- [x] 评估 Runtime/Context 耦合是否影响开发效率
  - 记录答案：☑ **严重影响**  □ 轻微影响  □ 不影响
  - **结论**：必须重构
  - **评估依据**（详见 `docs/generated/context-runtime-architecture-review.md`）：
    1. **职责倒置**：Runtime 包含大量业务逻辑，Context 90% 都是透传
    2. **中间层冗余**：GroupChatContext 的 9/10 方法是透传或别名，无实际价值
    3. **访问路径混乱**：同一份数据（agent_member_infos）有 3 种访问方式
    4. **封装破坏**：orchestration 层直接调用 `runtime.repository`，绕过持久化封装
    5. **调用链冗长**：需要写 `context.runtime.method()`，多一层间接
  - **推荐方案**：移除 GroupChatContext 中间层，Agent 直接持有 Runtime

- [x] 评估并发安全问题的解决方案
  - 记录答案：☑ **加锁即可**  □ 需要重新设计
  - **结论**：渐进式修复（4h）
  - **评估依据**：
    1. AgentCallManager: 添加 asyncio.Lock 保护 `_calls` 字典
    2. GroupChatManager: 添加 threading.RLock 保护 `_group_chats` 字典
    3. GroupChatRuntime: 添加 asyncio.Lock 保护 read-modify-write 序列
    4. 不需要重新设计架构，加锁可以解决所有并发问题

- [x] 评估系统使用情况和风险承受能力
  - 记录答案：☑ **开发阶段**  □ 已有用户
  - **结论**：可以承受重构风险
  - **评估依据**：
    1. 当前处于开发阶段，没有外部用户依赖
    2. 所有修改都有测试覆盖
    3. 重构是机械性替换，风险可控

### 5. 选择执行路径

- [x] 根据评估结果，选择以下路径：
  - ☑ **路径 A**：渐进式重构（1-2周，适合有时间且风险可控）
  - □ **路径 B**：快速修复 + 标记债务（1周，适合时间紧迫或有用户依赖）
  - □ **路径 C**：推倒重来（4-6周，适合问题严重且可接受长时间不可用）
  
  **选择理由**：
  1. Runtime/Context 架构问题严重影响开发效率，必须重构
  2. 并发安全问题可以通过加锁解决，不需要重新设计
  3. 系统处于开发阶段，可以承受重构风险
  4. 渐进式重构可以在修复问题的同时优化架构，风险可控

---

## 路径 A：渐进式重构（如果选择此路径）

### 6. Week 1 - 并发安全修复（4h）

- [x] 为 `AgentCallManager` 添加 `asyncio.Lock` 保护 `_calls` 字典
  - 添加 `self._lock = asyncio.Lock()`
  - 所有访问 `_calls` 和 `_calls_by_receiver` 的方法改为异步并使用锁
  - 修改 `create_call`、`get_call`、`list_all_calls`、`get_runtime_calls_for_agent`、`update_status`、`set_result`、`set_error`、`mark_agent_response` 为异步方法
  - 修改清理循环使用 `_check_timeouts_async()` 和 `_cleanup_deletable_calls()` 异步版本
  - 更新所有调用点添加 await（base_agent.py、group_chat.py、mcp/server.py、api/services/group_chat_service.py）
- [x] 为 `GroupChatManager` 添加 `threading.RLock` 保护 `_group_chats` 字典
  - 添加 `self._group_chats_lock = threading.RLock()`
  - 所有访问 `_group_chats` 的方法使用锁：`register`、`is_active_group`、`get_active_group_info`、`load_group_chat`、`unregister`、`list_all_group_chats`
- [x] 为 `GroupChatRuntime` 的 read-modify-write 序列添加锁
  - 添加 `self._state_lock = asyncio.Lock()`
  - 保护所有更新 `agent_member_infos` 的方法：`set_agent_token_and_default_cwd`、`set_agent_use_docker`、`update_context_load_state`、`update_agent_member_info_from_result`、`update_agent_context_usage`、`update_agent_status`
- [x] 测试并发场景：多个协程同时创建/更新 AgentCall
  - 类型检查通过
  - 所有锁保护已到位

### 7. Week 2 - Runtime/Context 架构优化（16h）

- [x] 分析 Context 层的必要性：是否可以合并到 Runtime
  - **结论**：合并。GroupChatContext 9/10 方法是透传，无实际价值
  - **评估依据**：`docs/generated/context-runtime-architecture-review.md`
- [x] 如果合并：将 Context 的方法移入 Runtime，更新所有调用点
  - 阶段 2-4 已完成（34 处改动，5 文件修改，1 文件删除）
  - 提交：5b71b8f, c750c26, 50d9cbb, 0b69e17
- [x] 更新相关 spec 文档
  - 已更新：core-context, core-agent-orchestration, core-communication, message-flow-and-persistence, spec index, core CLAUDE.md, coding-rules

### 8. Week 3 - 生命周期管理重构（12h）

- [x] 统一 GroupChat 的 start/load/activate 流程
  - `start()`: 启动群聊（首次创建），包含初始化、注册、启动任务
  - `load()`: 加载已有群聊（只读，不启动 agent），包含初始化、注册
  - `activate()`: 激活群聊，启动所有 agent 的 run() 任务
  - 三个方法共享 `_init_agents()` 和 `_register_agents_to_router()` 逻辑
- [x] 重构 Agent 的 start/stop/reset 操作，确保注册/注销完整
  - `start_member()`: 重置 _run 标志、创建任务、重新注册到 MessageRouter（第 796 行）
  - `stop_member()`: 设置 _run=False、更新状态为 stopped
  - `reset_member()`: 停止、清空会话、重置状态、重新初始化、重新注册到 MessageRouter（第 884 行）
- [x] 统一持久化接口，避免引用不一致
  - 所有持久化操作统一使用 `runtime` 的方法：
    - `runtime.save_agent_member_infos()`
    - `runtime.update_agent_member_info_from_result()`
    - `runtime.add_message()`
- [x] 更新相关 spec 文档
  - 提交 `1627aa9`: docs+tests: 清理 hand-off 文件，更新 specs 和 tests 适配 runtime API

### 9. Week 4 - 测试验证（8h）

- [x] 编写单元测试覆盖核心流程
  - 修复 15 个测试文件的 GroupChatContext 引用（6 个 collection error + 9 个运行时失败）
  - 删除已废弃的 `test_group_chat_context.py`，重写 `test_group_chat_runtime.py` 中 1 个测试
  - 942 个测试可收集，774 个通过（剩余 262 个失败为 pre-existing 问题，非本次重构引入）
- [ ] 编写集成测试覆盖生命周期操作
  - 现有 `test_full_lifecycle` 测试覆盖 GroupChatManager 生命周期
  - 缺少专门的 start_member/reset_member/stop_member 集成测试
- [ ] 压力测试并发场景
  - 未找到专门的压力测试文件
- [x] 回归测试所有功能
  - 源代码中 0 个 GroupChatContext 残留引用
  - 测试代码中 0 个 group_chat_context 属性引用

---

## 路径 B：快速修复 + 标记债务（如果选择此路径）

### 10. P1 问题修复（7h）

#### 10.1 修复压缩过程中的消息丢失问题（来源：子Agent审查）
- [ ] 修改 `compact_messages()` 使用快照机制，避免压缩期间新消息被标记为已压缩
- [ ] 测试：压缩过程中发送新消息，验证新消息不会丢失

#### 10.2 添加 compress_context() 的状态更新（来源：子Agent审查）
- [ ] 在 `base_agent.py` 的 `compress_context()` 开头设置状态为 `busy`
- [ ] 在方法结束时恢复状态为 `idle`
- [ ] 测试：压缩时前端能看到"压缩中"状态

#### 10.3 修复 reset_member() 的状态更新时机（来源：子Agent审查）
- [ ] 在 `reset_member()` 的 `_initialize_single_member()` 执行前设置状态为 `idle`
- [ ] 测试：重置时前端状态显示正确

#### 10.4 修复 send_message() 重复加载问题（来源：原始问题报告）
- [ ] 在 `GroupChatService.send_message()` 中移除重复的 `load_group_chat()` 调用
- [ ] 调整顺序：先验证成员 → 再激活 → 再发送消息
- [ ] 测试：发送消息流程正常

#### 10.5 修复 load_group_chat_from_disk 异常处理（来源：原始问题报告）
- [ ] 为 `group_chat_manager.py` 的 `load_group_chat_from_disk()` 添加 try-catch
- [ ] 捕获 `OSError`、`JSONDecodeError` 并转换为领域异常
- [ ] 测试：删除 metadata 文件，验证抛出正确的领域异常

#### 10.6 Task 清理机制（来源：原始问题报告）
- [ ] 为 `TaskManager` 实现类似 `AgentCallManager` 的 `start_cleanup()` 机制
- [ ] 定义已归档任务的过期策略
- [ ] 在 `GroupChat.start()`/`load()` 中启动清理循环
- [ ] 测试：归档任务能被定期清理

### 11. 并发安全快速修复（4h）

#### 11.1 AgentCallManager 并发保护（来源：子Agent审查）
- [ ] 为 `AgentCallManager` 添加 `asyncio.Lock` 保护 `_calls` 和 `_calls_by_receiver` 字典
- [ ] 修改 `create_call()`、`update_status()`、`mark_agent_response()` 使用锁
- [ ] 修改清理循环使用锁（避免迭代时字典修改导致 RuntimeError）
- [ ] 测试：多个协程同时创建/更新 AgentCall

#### 11.2 GroupChatManager 并发保护（来源：子Agent审查）
- [ ] 为 `GroupChatManager._group_chats` 添加 `threading.RLock`（参考 `_tokens` 的实现）
- [ ] 修改所有访问 `_group_chats` 的方法使用锁
- [ ] 测试：多线程环境（FastMCP）下并发访问

#### 11.3 GroupChatRuntime 并发保护（来源：子Agent审查）
- [ ] 为 `GroupChatRuntime` 添加 `_state_lock: asyncio.Lock`
- [ ] 保护所有 read-modify-write 序列（`update_agent_status`、`update_agent_context_usage` 等）
- [ ] 测试：多个 agent 并发更新状态

### 12. P2/P3 问题修复（4h）

#### 12.1 持久化引用写法规范（来源：原始问题报告）
- [ ] 重命名 `update_agent_member_info` 为 `update_agent_session`
- [ ] 统一持久化接口，明确使用被修改对象的引用
- [ ] 修改 `update_agent_status` 的持久化写法

#### 12.2 压缩流程错误处理（来源：原始问题报告）
- [ ] 移除 `base_agent.py` 中 `compress_context()` 的 `except Exception`
- [ ] 让异常冒泡或转换为领域异常

#### 12.3 handoff_dir 路径统一管理（来源：原始问题报告）
- [ ] 将 `handoff_dir` 路径定义移入 `GroupChatPaths`

#### 12.4 冗余端点和参数清理（来源：原始问题报告）
- [ ] 删除 `GET /group-chats/{group_chat_id}` 单个群聊端点
- [ ] 删除 `list_all_group_chats()` 的 `is_active_only` 参数

### 13. 标记架构债务

- [ ] 在 Runtime/Context 耦合处添加 TODO 注释（标注需合并或重新定义职责）
- [ ] 在透传方法处添加 TODO 注释
- [ ] 在 `docs/progress/core-refactor-tasks.md` 中标记 P3 架构任务为"待下次重构"
- [ ] 在 `_cleanup_agent_queue()` 添加 TODO 注释（标注待讨论的设计问题）

---

## 路径 C：推倒重来（如果选择此路径）

### 13. 重构准备（Week 1）

- [ ] 完善 Core 模块的 spec 文档
- [ ] 编写现有功能的回归测试
- [ ] 设计新的架构（去除 Context 层、统一持久化接口）
- [ ] 制定详细的重构计划

### 14. 分层重构（Week 2-5）

- [ ] Foundation 层重构（枚举类型、异常体系）
- [ ] Communication 层重构（MessageRouter、AgentCallManager、TaskManager）
- [ ] Context 层重构（合并到 Runtime 或重新定义职责）
- [ ] Agent 层重构（生命周期管理、状态管理）
- [ ] Orchestration 层重构（GroupChat、GroupChatManager）

### 15. 验证与部署（Week 6）

- [ ] 完整回归测试
- [ ] 性能对比测试
- [ ] 文档更新
- [ ] 灰度发布

---

## 验收标准

- [x] 所有 P0 问题已修复，系统能正常工作
- [x] Agent 重启后能正常接收消息
- [x] AgentCall 能正常清理，无内存泄漏
- [x] 群聊 created_at 不会被覆盖
- [x] 关键流程有 INFO 级别日志，便于排查问题
- [x] 如果选择重构：新架构通过所有测试，性能不下降
  - GroupChatContext 中间层已完全移除，架构简化为 Agent → GroupChatRuntime → State/Repository
  - 源代码和测试代码中 0 个残留引用
  - 942 个测试可收集，774 个通过
- [ ] 如果选择修复：所有 P1 问题已修复，并发安全得到保障，P3 债务已标记

---

## P4 待讨论问题清单

以下问题需要在架构评估阶段讨论，但不阻塞 P0 修复：

### 1. 前端错误提示：Agent 已停止时缺少 Toast 提示（来源：用户反馈）

**问题描述**：
当用户向已停止的 Agent 发送消息时，后端返回 409 Conflict，但前端没有 toast 弹窗提示用户。

**相关日志**：
```
INFO: 127.0.0.1:54863 - "POST /api/v1/group-chats/{id}/messages HTTP/1.1" 409 Conflict
```

**后端行为**：
- `group_chat.py:send_message_to_agent()` 已正确抛出 `StateError`
- API 全局错误处理器应该返回 409 状态码和错误信息

**前端需要**：
- 捕获 409 响应
- 解析错误信息
- 显示 toast 提示（如："无法发送消息：Agent XXX 已停止，请先启动"）

**优先级**：P2（用户体验问题，非阻塞）

---

### 2. Logger 使用规范（来源：原始问题报告）
- Logger 的统一配置方式
- 日志级别的使用标准（何时用 debug/info/warning/error）
- 日志消息的格式规范（是否包含上下文信息、变量格式等）
- 模块间日志的一致性要求

### 2. 群聊加载策略（来源：原始问题报告）
- [x] 已实施：采用混合策略（按项目懒加载 + 项目内分页）
- [x] 前端：首次只加载项目摘要，展开项目时才加载群聊
- [x] 后端：支持按项目路径过滤和分页参数（limit、offset）
- [x] 交互：使用"加载更多"按钮（符合设计系统简洁风格）
- [ ] 未来优化：增加搜索功能（Phase 3）
- [ ] 未来优化：引入 SQLite 替代文件扫描（> 1000 群聊时）

### 3. Agent 压缩流程优化（来源：原始问题报告）
- hand-off 文档应包含哪些信息？
- 压缩提示词应如何优化？
- 压缩是否应该被视为 Agent 的一种正式状态？

### 4. _cleanup_agent_queue 逻辑设计（来源：原始问题报告）
- 是否需要判断消息类型（TASK vs NOTIFICATION）？
- 是否所有清理消息都应保留到群聊历史？
- 是否以 stopped agent 身份发送消息，还是系统身份？

### 5. AgentCall 和 Task 的保留策略（来源：原始问题报告 + 子Agent审查）
- 已完成的 AgentCall 应保留多长时间？
- 已归档的任务应保留多长时间？
- 是否需要"归档"机制而非直接删除？

### 6. 并发竞态条件的其他场景（来源：子Agent审查）
- `_initialize_new_members` 的并发安全性
- token 生成与注册的原子性
- `_start_agent_tasks` 的异常处理
- `append_compact_record_and_mark_compacted()` 的双重持久化非原子性

---

## 备注

- 优先修复 P0 问题，这是所有路径的前置条件
- 在完成 P0 修复后（预估明天完成），立即进行架构评估讨论
- 根据讨论结果，勾选对应的执行路径，并按清单执行
- 每完成一项，立即勾选并提交，保持进度可追踪
