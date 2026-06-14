# Core 模块问题报告

---

## 零、全局问题

### 问题：Logger 使用不规范

#### 问题描述

当前 core 模块中 logger 的使用方式不统一、不规范，需要制定明确的使用规范。

#### 待讨论

1. Logger 的统一配置方式
2. 日志级别的使用标准（何时用 debug/info/warning/error）
3. 日志消息的格式规范（是否包含上下文信息、变量格式等）
4. 模块间日志的一致性要求

#### 解决方法

待讨论

---

## 一、架构性问题

### 问题：Runtime 与 Context 高度耦合，透传层级过多

#### 问题描述

Runtime 和 Context 之间存在高度耦合，每个 Runtime 的函数都需要经过 Context 透传调用。这是为了快速编码而遗留的架构问题，导致：
1. 调用链冗长：`GroupChat → Context → Runtime → Repository`
2. 职责边界模糊：Context 层只是简单转发，没有增加业务价值
3. 维护成本高：修改 Runtime 接口需要同步修改 Context

#### 相关代码示例

```python
# group_chat_context.py - Context 只是简单透传
async def update_agent_member_info(self, agent_result):
    await self.runtime.update_agent_member_info_from_result(agent_result)

async def add_message(self, agent_result):
    await self.runtime.add_message(agent_result)
```

#### 影响范围

- `GroupChatContext` 的大部分方法都是 `Runtime` 的简单包装
- 调用方需要通过 `group_chat_context` 访问 `runtime` 的功能
- 增加了代码理解和调试的复杂度

#### 建议方向

待讨论：
1. 是否移除 Context 层，让 GroupChat 直接调用 Runtime？
2. Context 是否应该承担更多业务逻辑，而非简单透传？
3. 如何平衡分层架构的清晰性与代码简洁性？

---

## 二、群聊创建生命周期

### 关键函数调用链

```
GroupChatManager.create_group_chat()
    └─> GroupChat.start()
        ├─> group_chat_context.load()  [line:106]
        │   └─> runtime.load()  [line:54]
        │       ├─> repository.load_group_chat_session()  → 群聊消息历史
        │       ├─> repository.load_agent_member_infos()  → 成员session信息(session_id, token, 上下文标志位)
        │       ├─> repository.load_compact_history()      → 压缩历史
        │       └─> repository.load_group_metadata()       → 群聊元数据
        │
        ├─> runtime.initialize_metadata()  [line:109]
        │   └─> 创建新的 GroupMetadata 并保存
        │
        ├─> _init_agents()  [line:115]
        ├─> _generate_and_register_tokens()  [line:118]
        ├─> _initialize_new_members()  [line:121]
        └─> _start_agent_tasks()  [line:124]
```

---

### 问题 1：initialize_metadata 幂等性缺陷与 created_at 覆盖

### 问题描述

在 `GroupChat.start()` 方法中，第 106 行先调用 `load()` 加载已有数据（包括 metadata），然后第 109 行调用 `initialize_metadata()` 重新创建并保存 metadata。

问题：
1. **幂等性问题**：如果 metadata 已存在，`initialize_metadata` 会覆盖它
2. **created_at 被覆盖**：`initialize_metadata` 没有传入 `created_at` 参数，默认使用 `datetime.now()`，导致原创建时间丢失
3. **缺少防御性编程**：`start()` 作为初次创建方法，没有防止被重复调用的机制

### 相关代码

```python
# group_chat.py:86-126
async def start(self):
    # 1. 加载上下文数据（会加载已有 metadata）
    await self.group_chat_context.load()

    # 2. 初始化并保存群聊元数据（问题：会覆盖已有的 metadata）
    await self.runtime.initialize_metadata(
        group_chat_name=self.group_chat_name,
        group_type=self.group_type,
    )
    # ...

# group_chat_runtime.py:234-260
async def initialize_metadata(
    self,
    group_chat_name: str,
    group_type: GroupChatType,
    created_at: datetime | None = None,  # 可选参数，但 start() 没传
) -> GroupMetadata:
    metadata = GroupMetadata(
        group_chat_id=self.group_chat_id,
        group_chat_name=group_chat_name,
        project_path=self.project_path,
        created_at=created_at or datetime.now(),  # 没传则用当前时间，覆盖原值
        group_type=group_type.value,
    )
    self.state.metadata = metadata
    await self._persist(lambda: self.repository.save_group_metadata(metadata))
    return metadata
```

### 验证结果

**确认存在**：
- `start()` 方法没有检查是否已经初始化过
- `initialize_metadata` 的 `created_at` 参数在 `start()` 中未传入
- 已有的 `created_at` 会被 `datetime.now()` 覆盖

### 建议修复

1. 在 `start()` 开始处添加幂等性检查
2. 如果 metadata 已存在，保留原 `created_at` 或在调用时传入

---

### 问题 2：update_agent_member_info 接口设计问题

### 问题描述

`update_agent_member_info` 方法只更新 session_id，但：
1. 函数命名暗示更新整个 member info，实际只更新 session
2. 持久化调用存在引用不一致的写法

### 相关代码

```python
# group_chat_context.py:64-75
async def update_agent_member_info(self, agent_result):
    """根据 AgentResult 更新 agent session id 并保存"""
    await self.runtime.update_agent_member_info_from_result(agent_result)

# group_chat_runtime.py:397-423
async def update_agent_member_info_from_result(self, agent_result) -> AgentMemberInfo:
    agent_member_info = self.get_or_create_agent_member_info(agent_result.agent_name)

    if not agent_member_info.main_session:
        agent_member_info.main_session = agent_result.session_id
    elif (
        agent_result.session_id != agent_member_info.main_session
        and agent_result.session_id not in agent_member_info.btw_session
    ):
        agent_member_info.btw_session.append(agent_result.session_id)

    # 问题：这里保存的是 self.state.agent_member_infos（整个字典）
    # 而上面修改的是 agent_member_info（单个对象）
    # 虽然它们是同一引用，但写法不规范
    await self._persist(
        lambda: self.repository.save_agent_member(self.state.agent_member_infos)
    )
    return agent_member_info
```

### 验证结果

**确认存在**：
- **职权与函数名称不匹配**：函数名 `update_agent_member_info` 暗示更新整个 member info，但实际职权仅限于更新 session_id（main_session/btw_session）
- **建议更名**：应改为 `update_agent_session` 或 `update_agent_session_id`，准确反映其职责
- **持久化引用不规范**：`agent_member_info` 和 `self.state.agent_member_infos` 在运行时是同一对象引用，但代码写法上存在歧义

### 建议修复

1. 函数重命名为 `update_agent_session`，明确职权范围
2. 统一接口设计，只提供一个 save 函数
3. 持久化时明确使用被修改对象的引用

---

---

## 三、群聊列表加载

### 关键函数调用链

```
GET /group-chats                    → list_all_group_chats()  [GroupChatManager]
GET /group-chats/{group_chat_id}    → 直接读取 metadata 文件（冗余）

list_all_group_chats() [group_chat_manager.py:224]
    └─> 扫描 teams/*/*/group_metadata.json
        └─> GroupMetadata.from_dict(data)
```

### 问题 1：冗余端点

#### 问题描述

存在两个端点：
- `GET /group-chats` - 列出所有群聊
- `GET /group-chats/{group_chat_id}` - 获取单个群聊详情

但 `list_all_group_chats()` 已经返回了所有群聊的完整信息，单个群聊端点是冗余的。

#### 验证结果

**确认存在**：单个群聊端点可以删除，前端可从 list 结果中筛选

---

### 问题 2：is_active_only 参数无用

#### 问题描述

`list_all_group_chats()` 的 `is_active_only` 参数前端未使用，属于遗留代码。

#### 验证结果

**确认存在**：该参数应删除

---

### 问题 3：群聊加载策略设计问题（待讨论）

#### 问题描述

当群聊数量过多时，如何高效加载是一个设计问题。当前方案存在两个待选策略：

**方案 A：按活跃文件夹加载**
- 某个群聊最近活跃 → 加载该文件夹下的全部群聊
- 优点：保持项目维度的组织性
- 缺点：可能加载不相关的群聊

**方案 B：按前 N 个活跃群聊加载**
- 直接取最近活跃的前 20 个群聊
- 优点：精确控制加载数量
- 缺点：可能遗漏同一项目的其他群聊

#### 遗留问题

1. 不活跃的群聊如何获取？是否需要搜索/筛选功能？
2. 是否需要分页机制？

#### 注意

当前实现直接扫描文件系统，没有通过 `group_chat_manager` 加载，这是正确的设计（避免内存占用）。

---

## 四、群聊详情加载（前端点击某个群聊时）

### 前端请求统计

点击一个群聊，最少发 **5 个 HTTP 请求 + 1 个 WebSocket 连接**：

```
GET /group-chats/{id}/messages?limit=30
GET /group-chats/{id}/members
GET /roles
GET /group-chats/{id}/pinned-messages
WS  /ws/{id}
```

如果右侧栏打开，额外 **2 个**：

```
GET /group-chats/{id}/agent-calls
GET /group-chats/{id}/tasks
```

---

### 关键函数调用链

```
GET /group-chats/{id}/messages
    └─> GroupChatManager.load_group_chat(group_chat_id)
        ├─> 优先从内存获取 [line:109]
        └─> 内存未命中 → load_group_chat_from_disk() [line:290]
            ├─> group_chat_paths.find_project_path_by_group_chat_id()
            ├─> json.load(metadata_file)
            ├─> json.load(agent_member_file)
            ├─> GroupChat.__init__()
            ├─> group_chat.load()  [不启动 agent，正确设计]
            └─> self.register(group_chat_id, group_chat)
```

### 问题：load_group_chat_from_disk 缺少 try-catch

#### 问题描述

`load_group_chat_from_disk()` 方法直接操作外部文件接口（json.load、open），但没有对这些外部接口进行错误捕获。

根据项目编码规范：
> 外部接口层（文件 IO、网络请求、数据库操作）必须捕获对应错误并转换为领域异常

#### 相关代码

```python
# group_chat_manager.py:290-379
async def load_group_chat_from_disk(self, group_chat_id, base_path=None):
    # 1. 查找 project_path
    project_path = group_chat_paths.find_project_path_by_group_chat_id(...)
    
    # 2. 读取 metadata - 没有 try-catch
    with open(metadata_file, encoding="utf-8") as f:
        data = json.load(f)
    
    # 3. 读取 agent_member - 没有 try-catch
    with open(agent_member_file, encoding="utf-8") as f:
        session_data = json.load(f)
```

#### 验证结果

**确认存在**：
- 文件读取操作没有捕获 `OSError`、`JSONDecodeError` 等异常
- 应转换为 `FileSystemError` 或其他领域异常

#### 建议修复

添加 try-catch，捕获外部接口异常并转换为领域异常

---

### 问题：Agent Call 加载与清理机制失效

#### 问题描述

`GET /group-chats/{id}/agent-calls` 端点存在严重的加载和清理问题：

1. **加载所有 Agent Call**：`_load_from_persistence` 会加载全部历史记录，无分页/过滤
2. **清理机制未启动**：`start_cleanup` 没有被调用，内存中的 Agent Call 无法被清理
3. **`can_be_deleted` 字段失效**：该字段只在清理循环中使用，但清理循环未运行

#### 影响

- Agent Call 数量增长后，内存占用持续增加
- 已完成的 Agent Call 永远不会被清理
- 前端加载时传输大量无用数据

#### 待讨论

1. Agent Call 的完整生命周期问题（从 Agent Call 角度解决）
2. 已完成的 Agent Call 应保留多长时间？
3. 是否需要分页加载机制？

---

### 问题：Task 加载与清理机制缺失

#### 问题描述

`GET /group-chats/{id}/tasks` 端点存在与 Agent Call 类似的问题：

1. **加载所有历史任务**：`_load_from_persistence` 在 `__init__` 中被调用，加载全部历史任务列表（包括已归档的）
2. **无清理机制**：TaskManager 没有任何清理方法（类似 AgentCallManager 的 `start_cleanup`）
3. **无过期策略**：已归档的任务永远不会被清理，内存占用持续增长

#### 相关代码

```python
# task_manager.py:56
def __init__(self, group_chat_id: str, project_path: str):
    ...
    # 加载历史任务列表 - 无过滤，加载全部
    self._load_from_persistence()

# task_manager.py:276-307
def _load_from_persistence(self):
    """从持久化文件加载历史任务列表"""
    # 加载所有 TaskList，包括已 ARCHIVED 的
    for list_id, data in task_list_records.items():
        task_list = TaskList.from_dict(data)
        self._task_lists[list_id] = task_list  # 全部加载到内存
```

#### 验证结果

**确认存在**：
- 已归档任务会一直驻留内存
- 没有任何清理/过期机制
- 与 Agent Call 问题同源

#### 待讨论

1. 已归档任务应保留多长时间？
2. 是否需要定期清理机制？

---

## 六、Agent.run 正常处理流程与状态变化

### Agent 状态定义

| 状态 | 含义 |
|------|------|
| `idle` | 空闲，等待消息 |
| `busy` | 处理 MAIN 会话（群聊消息） |
| `chatting` | 处理 BTW 会话（单聊） |
| `stopped` | 已停止（特殊状态） |

### AgentCall 状态定义

| 状态 | 含义 |
|------|------|
| `PENDING` | 已创建，等待处理 |
| `RUNNING` | Agent 正在执行 CLI |
| `COMPLETED` | 任务完成 |
| `FAILED` | 任务失败 |
| `TIMEOUT` | 超时 |

### 正常处理流程（不包括压缩/暂停/重启/重置）

```
1. Agent 空闲 (idle)
        │
        ▼
2. 消息到达 + 创建 AgentCall (PENDING)
        │
        ▼
3. agent.run() 获取消息
   ├─ BTW 会话 → _sync_status("chatting")
   └─ MAIN 会话 → _sync_status("busy")
        │
        ▼
4. _process_message()
   ├─ update_status(call_id, RUNNING)  # AgentCall: PENDING → RUNNING
   ├─ 执行 CLI (execute/btw_execute)
   │
   ├─ 非 TASK 任务：
   │   └─ update_status(call_id, COMPLETED)  # 直接闭环
   │
   └─ TASK 任务（A→B 闭环）：
       ├─ Agent 发送的 TASK (manager→worker)：
       │   ├─ complete_task MCP 工具：
       │   │   └─ mark_agent_response(call_id, content, success)
       │   │       ├─ success=True → COMPLETED
       │   │       └─ success=False → FAILED
       │   │       同时创建通知 Call 给发送者（B→A 闭环）
       │   │
       │   └─ 兜底 _fallback_close_task()（CLI 结束后）：
       │       └─ mark_agent_response + 创建通知 Call
       │
       └─ CLI 调用失败：
           └─ update_status(call_id, FAILED)
        │
        ▼
5. _sync_status("idle")  # finally 块中
```

### 关键代码位置

```python
# base_agent.py:586-663 - agent.run()
async def run(self):
    while self._run:
        msg = await self.message_queue.get()
        status = "chatting" if msg.session_type == SessionType.BTW else "busy"
        await self._sync_status(status)
        try:
            result = await self._process_message(msg, prompt)
        finally:
            await self._sync_status("idle")

# base_agent.py:197-286 - _process_message()
async def _process_message(self, msg, prompt):
    self.agent_call_manager.update_status(msg.call_id, CallStatus.RUNNING)
    result = await self.execute(...)  # 或 btw_execute
    if msg.message_type != MessageType.TASK:
        self.agent_call_manager.update_status(msg.call_id, CallStatus.COMPLETED)
    return result

# base_agent.py:533-584 - _fallback_close_task()
async def _fallback_close_task(self, msg, result):
    self.agent_call_manager.mark_agent_response(call_id, content, success=True)
    # 创建通知 Call 给发送者
```

---

### 问题：update_agent_status 持久化引用问题

#### 问题描述

与问题 2（update_agent_member_info）相同的持久化引用问题：

```python
# group_chat_runtime.py:453-470
async def update_agent_status(self, agent_name: str, status: str) -> AgentMemberInfo:
    agent_member_info = self.get_or_create_agent_member_info(agent_name)
    agent_member_info.status = status  # 修改单个对象
    await self._persist(
        lambda: self.repository.save_agent_member(self.state.agent_member_infos)  # 保存整个字典
    )
```

#### 验证结果

**确认存在**：与 `update_agent_member_info` 相同的写法问题

---

## 十、Agent 重置流程（reset_member）

### 关键函数调用链

```
reset_member(agent_name)
    ├─> _find_agent(agent_name)
    ├─> stop_member(agent_name)  # 内部会 unregister
    │   └─> message_router.unregister(agent_name)  # 注销
    ├─> 清空 main_session 和 btw_sessions
    ├─> 清空消息队列
    ├─> update_agent_context_usage(0)
    ├─> _initialize_single_member(agent)  # 打招呼
    ├─> asyncio.create_task(agent.run())  # 创建新任务
    └─> runtime.update_agent_status("idle")
    
    ⚠️ 缺少：重新注册到 message_router
```

### 问题：重置后未重新注册（阻塞性问题）

#### 问题描述

与 `start_member` 相同的问题：`stop_member` 中注销了 agent，但 `reset_member` 中没有重新注册。

#### 相关代码

```python
# group_chat.py:790-792
# 2. 如果正在运行，先停止
agent_member_info = self.runtime.state.agent_member_infos.get(agent_name)
if agent_member_info and agent_member_info.status != "stopped":
    await self.stop_member(agent_name)  # 内部会 unregister

# group_chat.py:812-818
# 7. 自动启动
agent._run = True
if self.manager and agent_name == self.manager.name:
    self.manager_task = asyncio.create_task(agent.run())
else:
    new_task = asyncio.create_task(agent.run())
    self.worker_tasks[agent_name] = new_task

# ⚠️ 缺少：self.message_router.register(agent_name, agent.message_queue)
```

#### 验证结果

**确认存在**：与 `start_member` 相同的阻塞性问题

---

## 九、Agent 启动流程（start_member）

### 关键函数调用链

```
start_member(agent_name)
    ├─> _find_agent(agent_name)  # 查找 agent
    ├─> 验证状态为 "stopped"
    ├─> agent._run = True  # 重置运行标志
    ├─> asyncio.create_task(agent.run())  # 创建新任务
    └─> runtime.update_agent_status("idle")
    
    ⚠️ 缺少：重新注册到 message_router
```

### 问题：重启后未重新注册（阻塞性问题）

#### 问题描述

`stop_member` 中会调用 `message_router.unregister(agent_name)` 注销 agent，但 `start_member` 中没有重新注册。

这导致 agent 重启后无法接收消息，是一个阻塞性问题。

#### 相关代码

```python
# group_chat.py:738-749
# 3. 重置 _run 标志
agent._run = True

# 4. 创建新任务
if self.manager and agent_name == self.manager.name:
    self.manager_task = asyncio.create_task(agent.run())
else:
    new_task = asyncio.create_task(agent.run())
    self.worker_tasks[agent_name] = new_task

# 5. 更新状态为 "idle"
await self.runtime.update_agent_status(agent_name, "idle")

# ⚠️ 缺少：self.message_router.register(agent_name, agent.message_queue)
```

#### 验证结果

**确认存在**：`stop_member` 中有 `unregister`，但 `start_member` 中没有对应的 `register`

#### 建议修复

在 `start_member` 中添加 `message_router.register(agent_name, agent.message_queue)`

---

## 八、Agent 停止流程（_cleanup_agent_queue）

### 关键函数调用链

```
stop_member(agent_name)
    ├─> runtime.update_agent_status("stopped")
    ├─> _stop_agent_process(agent)  # 终止 CLI 进程
    ├─> agent.stop()  # 发送停止信号
    ├─> 取消 asyncio.Task
    ├─> _cleanup_agent_queue(agent_name)
    │   ├─> get_runtime_calls_for_agent(agent_name)  # 获取 PENDING/RUNNING 的 call
    │   ├─> 对每个 call：
    │   │   ├─> mark_agent_response(call_id, content, success=False)
    │   │   ├─> 调用方不是 user：
    │   │   │   └─> create_call + send_message (NOTIFICATION)
    │   │   └─> 调用方是 user：
    │   │       └─> add_message(result)
    │   └─> 清空消息队列
    └─> message_router.unregister(agent_name)
```

### 问题：_cleanup_agent_queue 需要仔细判断（待讨论）

#### 问题描述

这里有大问题，需要后续仔细判断。以下问题不一定准确：

1. **没有判断消息类型是不是 Message.TASK 就直接 mark_agent_response**

2. **按照惯例，所有发送消息都应该保留到群消息，所有群消息保存都应该使用回调函数通知前端更新**

3. **该不该以 stop 的 agent 身份发送消息？**
   - 当前不确定状态
   - 如果简单一点，至少需要增加上系统标识

---

## 七、Agent 压缩流程

### 关键函数调用链

```
agent.compress_context()
    ├─> 忙碌校验（只检查 busy 状态）
    ├─> execute(COMPACT_CONTEXT_PROMPT)  # 发送压缩 prompt
    ├─> 提取摘要
    ├─> 写入留痕文件（hand-off docs）
    ├─> 清空 main_session
    ├─> execute(summary)  # 用摘要新建 session
    ├─> 更新 main_session
    ├─> update_agent_context_usage(0)  # 重置 context_usage
    └─> add_system_message()  # 写入系统消息
```

### 问题 1：hand-off 文档和压缩提示词需要重构

#### 问题描述

当前的 hand-off 文档格式和压缩提示词（`COMPACT_CONTEXT_PROMPT`）需要重构，以提高可读性和实用性。

#### 待讨论

1. hand-off 文档应包含哪些信息？
2. 压缩提示词应如何优化？

---

### 问题 2：压缩状态的架构考虑（待讨论）

#### 问题描述

当前压缩只检查 `busy` 状态，没有考虑 `stopped` 状态。

架构问题：压缩是否应该被视为 Agent 的一种正式状态？
- 如果是：`stopped` 状态下也应该支持压缩
- 如果不是：当前实现（只检查 busy）是合理的

#### 相关代码

```python
# base_agent.py:333-335
agent_member_info = self.group_chat_context.agent_member_info.get(self.name)
if agent_member_info and agent_member_info.status == "busy":
    raise AgentBusyError(self.name)
```

#### 待讨论

压缩是否应该被视为 Agent 的正式状态？

---

### 问题 3：handoff_dir 路径应写入 GroupChatPaths

#### 问题描述

留痕文件目录硬编码在代码中，应统一管理。

#### 相关代码

```python
# base_agent.py:351
handoff_dir = Path(self.agent_cwd) / "docs" / "hand-off"
```

#### 建议修复

将路径定义移入 `GroupChatPaths`，统一管理。

---

### 问题 4：错误处理有问题

#### 问题描述

压缩流程中的错误处理不符合项目编码规范。

#### 相关代码

```python
# base_agent.py:348-366
try:
    ...
    handoff_file.write_text(handoff_content, encoding="utf-8")
except Exception as e:
    self.logger.warning("留痕文件写入失败: %s", str(e))  # 只 warning，吞掉异常
```

#### 验证结果

**确认存在**：
- 使用 `except Exception` 吞掉异常，违反编码规范
- 应转换为领域异常或让异常冒泡

---

## 五、用户发送消息（前端 → Agent）

### 关键函数调用链

```
POST /group-chats/{id}/messages
    └─> GroupChatService.send_message()
        ├─> _resolve_send_to(content, members)  # 解析目标 agent
        ├─> group_chat_manager.activate_group_chat(group_chat_id)  # 第1次加载（内部调用 load_group_chat）
        ├─> 校验 send_to 是群聊成员
        ├─> group_chat_manager.load_group_chat(group_chat_id)  # 第2次加载（重复！）
        ├─> agent_call_manager.create_call(...)  # 创建 AgentCall
        └─> group_chat.send_message_to_agent(message)
```

### send_message_to_agent 详细链路（关键代码）

```
send_message_to_agent(message)
    ├─> self.activate()  # 第2次加载（activate 内部会调用 load_group_chat）
    ├─> 检查目标 agent 状态（stopped 则抛异常）
    ├─> self.message_router.send_message(message)  # 投递消息到队列
    ├─> self._find_agent(message.send_from)  # 获取发送方 agent
    ├─> render_for_chat()  # 格式化消息（添加 @前缀）
    ├─> 构造 AgentResult（text, timestamp, agent_name, platform, role_type）
    └─> self.group_chat_context.add_message(sender_result)  # 保存消息
        └─> runtime.add_message()
            └─> repository.save_group_chat_session()  # 持久化
```

### 问题：重复加载与顺序问题

#### 问题描述

1. **重复加载**：`activate()` 内部已经调用过 `load_group_chat()`，但 service 层又显式调用一次，造成重复
2. **执行顺序不当**：当前先激活群聊，再验证是否是群成员。应该先验证成员身份，再激活

#### 相关代码

```python
# group_chat_service.py (推测)
async def send_message(self, group_chat_id, message):
    group_chat = await group_chat_manager.load_group_chat(group_chat_id)  # 第1次
    await group_chat.activate()  # 第2次（activate 内部会调用 load_group_chat）
    # ... 验证成员 ...
    await group_chat.send_message_to_agent(message)
```

#### 验证结果

**确认存在**：
- `load_group_chat` 被调用两次（一次显式，一次在 activate 内部）
- 成员验证在激活之后，顺序不合理

#### 建议修复

1. 移除显式的 `load_group_chat` 调用，只使用 `activate()`
2. 调整顺序：先验证成员身份 → 再激活群聊 → 再发送消息

---

### 待排查问题（用户未详细描述）

- [ ] `_initialize_new_members` 的并发安全性
- [ ] token 生成与注册的原子性
- [ ] `_start_agent_tasks` 的异常处理
