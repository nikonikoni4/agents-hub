# Runtime 状态同步分析报告

## 调查目标

验证增量添加新 Agent 后，新 Agent 是否能正确访问所有 Runtime 状态，确保不存在状态不一致的风险。

---

## Runtime 状态架构

### 数据流向

```
GroupChat
  ├── runtime: GroupChatRuntime (状态 Facade)
  │     ├── state: GroupChatRuntimeState (内存状态)
  │     │     ├── group_chat_session: GroupChatSession (消息历史)
  │     │     ├── agent_member_infos: dict[str, AgentMemberInfo] (Agent 会话信息)
  │     │     ├── compact_history: list[dict] (压缩历史)
  │     │     └── metadata: GroupMetadata (群聊元数据)
  │     └── repository: GroupChatRepository (持久化层)
  │
  └── group_chat_context: GroupChatContext (业务逻辑层)
        └── runtime: GroupChatRuntime (持有引用，向后兼容)
```

### Agent 访问路径

```python
# Agent 构造函数接收 group_chat_context
Agent.__init__(
    group_chat_context: GroupChatContext,
    ...
)

# Agent 通过 group_chat_context 访问状态
self.group_chat_context.agent_member_info  # → runtime.state.agent_member_infos
self.group_chat_context.group_chat_session  # → runtime.state.group_chat_session
self.group_chat_context.get_project_path()  # → runtime.project_path

# AgentContext 也通过 group_chat_context 访问
self.agent_context = AgentContext(self.name, group_chat_context)
```

---

## 关键发现

### ✅ 状态共享是安全的

**核心机制**：所有 Agent 共享同一个 `GroupChatContext` 实例

```python
# group_chat.py: __init__
self.group_chat_context = GroupChatContext(self.runtime)  # 单例

# group_chat.py: _init_agents
self.manager = Manager(
    ...,
    self.group_chat_context,  # 所有 Agent 共享同一个实例
    ...
)
self.workers[role_name] = Worker(
    ...,
    self.group_chat_context,  # 同一个实例
    ...
)
```

**推论**：新 Agent 和旧 Agent 访问的是同一个 `GroupChatContext`，因此访问的是同一份 Runtime 状态。

---

## 状态访问点验证

### 1. Agent 会话信息 (agent_member_info)

**访问方式**：
```python
# base_agent.py:58-59
info = self.group_chat_context.agent_member_info.get(self.name)
return info.token if info else ""
```

**数据来源**：
```python
# group_chat_context.py:34-36
@property
def agent_member_info(self) -> dict[str, AgentMemberInfo]:
    return self.runtime.state.agent_member_infos  # 内存字典
```

**新 Agent 行为**：
- 首次访问时，`agent_member_info.get(self.name)` 返回 `None`
- Agent 执行后，通过 `update_agent_member_info()` 创建条目
- 使用 `get_or_create_agent_member_info()` 确保安全创建

**结论**：✅ 新 Agent 可以正确访问，首次为空，执行后自动创建

---

### 2. 消息历史 (group_chat_session)

**访问方式**：
```python
# agent_context.py:67-68
if self.group_chat_context.group_chat_session is None:
    raise StateError("GroupChatSession 未加载，请先调用 load()")
```

**数据来源**：
```python
# group_chat_context.py:30-31
@property
def group_chat_session(self) -> GroupChatSession | None:
    return self.runtime.state.group_chat_session
```

**新 Agent 行为**：
- 通过 `AgentContext.get_context()` 访问消息历史
- 读取 `session.messages[last_loaded_message_index:]` 增量加载
- 所有 Agent 看到的是同一份消息列表

**结论**：✅ 新 Agent 可以访问完整的消息历史

---

### 3. 压缩历史 (compact_history)

**访问方式**：
```python
# agent_context.py:59-60
compact_history = await self.group_chat_context.load_compact_history()
```

**数据来源**：
```python
# group_chat_context.py:79-86
async def load_compact_history(self) -> list[dict]:
    return await self.runtime.load_compact_history()

# group_chat_runtime.py:175-182
async def load_compact_history(self) -> list[dict]:
    return self.state.compact_history
```

**新 Agent 行为**：
- 通过 `AgentContext.get_context()` 访问压缩历史
- 读取 `compact_history[last_loaded_compact_index:]` 增量加载
- 新 Agent 的 `last_loaded_compact_index = 0`，会加载全部压缩历史

**结论**：✅ 新 Agent 可以访问完整的压缩历史

---

### 4. 项目路径 (project_path)

**访问方式**：
```python
# base_agent.py:149
group_chat_path = self.group_chat_context.get_project_path()
```

**数据来源**：
```python
# group_chat_context.py:38-39
def get_project_path(self) -> str:
    return self.runtime.project_path
```

**新 Agent 行为**：
- 直接读取 `runtime.project_path`（构造函数传入，不可变）
- 所有 Agent 访问的是同一个值

**结论**：✅ 新 Agent 可以访问正确的项目路径

---

### 5. 群聊元数据 (metadata)

**访问方式**：
```python
# group_chat_runtime.py:81
metadata = self.state.require_metadata()
```

**数据来源**：
```python
# group_chat_runtime_state.py
self.metadata: GroupMetadata | None = None
```

**新 Agent 行为**：
- 元数据在 `start()` 或 `load()` 时已经加载到 `runtime.state.metadata`
- 所有 Agent 访问的是同一份元数据

**结论**：✅ 新 Agent 可以访问群聊元数据

---

## 增量添加流程的状态同步

### 当前实现（有问题）

```python
# group_chat_service.py:752
await group_chat._init_agents()  # ❌ 重建所有 Agent
```

**问题**：
1. 重建所有 Agent 对象（包括旧成员）
2. 重新注册到 MessageRouter（覆盖旧队列）
3. 不启动任务（如果 `_activated=False`）

### 正确的增量添加流程

```python
# 伪代码
async def add_member(role_name: str):
    # 1. 创建新 Worker
    new_worker = Worker(
        role,
        self.group_chat_context,  # ✅ 共享同一个 context
        self.agent_call_manager,
        self.message_router,
        self.task_manager,
    )
    
    # 2. 注册到 MessageRouter
    self.message_router.register(role_name, new_worker.message_queue)
    
    # 3. 添加到 workers 字典
    self.workers[role_name] = new_worker
    
    # 4. 如果群聊已激活，启动任务
    if self._activated:
        new_task = asyncio.create_task(new_worker.run())
        self.worker_tasks.append(new_task)
    
    # 5. 更新 team_members_name
    self.team_members_name.append(role_name)
    
    # 6. 保存元数据
    await self.runtime.initialize_metadata(
        group_chat_name=self.group_chat_name,
        group_type=self.group_type,
    )
```

**状态同步点**：
1. ✅ 新 Worker 持有 `self.group_chat_context`，与旧 Agent 共享状态
2. ✅ `group_chat_context.runtime` 是同一个实例，内存状态一致
3. ✅ 新 Agent 首次执行时，会自动创建 `agent_member_info` 条目
4. ✅ 新 Agent 可以访问所有历史消息和压缩历史
5. ✅ 元数据更新后，所有 Agent 都能看到最新的 `team_members_name`

---

## 潜在风险点分析

### ❌ 风险 1：元数据更新时机

**问题**：
```python
# 添加成员后，team_members_name 更新了
self.team_members_name.append(role_name)

# 但 metadata 中的 team_members_name 需要重新保存
await self.runtime.initialize_metadata(...)
```

**现状**：
- `GroupMetadata` 不包含 `team_members_name` 字段
- `team_members_name` 只存在于 `GroupChat` 对象的内存中
- **没有持久化到 metadata.json**

**影响**：
- 如果群聊重启，`team_members_name` 不会丢失（从 `agent_member.json` 的 keys 推断）
- 但没有显式的持久化机制

**建议**：
- 在 `GroupMetadata` 中添加 `team_members: list[str]` 字段
- 添加成员后调用 `runtime.update_metadata_members(team_members_name)`

---

### ✅ 无风险：新 Agent 的 agent_member_info 创建

**机制**：
```python
# group_chat_runtime.py:152-164
def get_or_create_agent_member_info(self, agent_name: str) -> AgentMemberInfo:
    if agent_name not in self.state.agent_member_infos:
        self.state.agent_member_infos[agent_name] = AgentMemberInfo(cwd=self.project_path)
    return self.state.agent_member_infos[agent_name]
```

**触发时机**：
1. 新 Agent 首次执行后调用 `update_agent_member_info()`
2. 内部调用 `get_or_create_agent_member_info()` 自动创建
3. 默认 `cwd=project_path`，符合预期

**结论**：✅ 自动创建机制健壮，无需担心

---

### ✅ 无风险：新 Agent 的上下文加载

**机制**：
```python
# agent_context.py:50-56
agent_member_info = self.group_chat_context.agent_member_info.get(self.agent_name)
if not agent_member_info:
    last_loaded_compact_index = 0
    last_loaded_message_index = 0
else:
    last_loaded_compact_index = agent_member_info.context_state.last_loaded_compact_index
    last_loaded_message_index = agent_member_info.context_state.last_loaded_message_index
```

**新 Agent 行为**：
1. 首次调用 `get_context()` 时，`agent_member_info` 为 `None`
2. `last_loaded_*_index = 0`，会加载全部历史
3. 加载后更新 `context_state`，后续增量加载

**结论**：✅ 新 Agent 能正确加载全部历史上下文

---

## 最终结论

### ✅ 状态同步是正确的

**核心保证**：
1. **共享 GroupChatContext**：所有 Agent（新旧）访问同一个 `group_chat_context` 实例
2. **共享 Runtime State**：`runtime.state` 是单例内存状态，所有 Agent 看到的是同一份数据
3. **增量加载机制健壮**：新 Agent 首次执行时，从 `index=0` 加载全部历史
4. **自动创建机制**：`get_or_create_agent_member_info()` 确保新 Agent 条目正确创建

### ⚠️ 注意事项

**唯一需要关注的点**：
- **不要重建旧 Agent**（当前实现的问题）
- **增量添加新 Agent**（只创建新的，不动旧的）
- **确保 MessageRouter 注册不覆盖旧队列**（增量注册，不重新注册全部）

### 📋 实施建议

采用**方案 A（纯增量添加）**：

1. **只创建新 Agent 对象**
2. **只注册新 Agent 到 MessageRouter**
3. **如果已激活，启动新 Agent 的任务**
4. **更新 team_members_name 并持久化**
5. **新 Agent 首次执行时自动接入 Runtime 状态**

**关键代码点**：
```python
# ✅ 正确：共享 context
new_worker = Worker(..., self.group_chat_context, ...)

# ✅ 正确：增量注册
self.message_router.register(new_name, new_worker.message_queue)

# ✅ 正确：条件启动
if self._activated:
    new_task = asyncio.create_task(new_worker.run())
    self.worker_tasks.append(new_task)
```

---

## 测试验证清单

为确保实现正确，需要验证以下场景：

### 场景 1：空闲时添加成员
- [ ] 新成员能否接收消息
- [ ] 新成员的 `agent_member_info` 是否正确创建
- [ ] 新成员能否访问历史消息
- [ ] 新成员能否访问压缩历史

### 场景 2：有消息历史时添加成员
- [ ] 新成员首次执行时，上下文是否包含全部历史
- [ ] 新成员的 `last_loaded_compact_index` 和 `last_loaded_message_index` 是否从 0 开始
- [ ] 新成员执行后，状态是否正确更新

### 场景 3：已激活时添加成员
- [ ] 新成员的任务是否立即启动
- [ ] 旧成员的任务是否不受影响
- [ ] 旧成员的消息队列是否不受影响

### 场景 4：持久化验证
- [ ] 添加成员后，`agent_member.json` 是否包含新成员
- [ ] 群聊重启后，新成员是否仍在 `team_members_name` 中
- [ ] 新成员的 session 和 token 是否正确恢复

---

## 结论

**增量添加新 Agent 的方案是安全的，不会导致状态不一致**。

关键在于：
1. 不重建旧 Agent（避免当前实现的问题）
2. 新 Agent 共享 GroupChatContext（自动同步状态）
3. 新 Agent 首次执行时从头加载历史（增量加载机制）
4. Runtime 状态是单例（所有 Agent 访问同一份数据）

只要按照方案 A 实现，状态同步是完全正确的。
