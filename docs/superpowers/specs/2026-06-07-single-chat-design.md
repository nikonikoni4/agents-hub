# Single Chat 单聊通道设计

## 概述

单聊通道是用户与单个 Agent 直接对话的通道，不依赖群聊的编排逻辑（MessageRouter、AgentCallManager、Manager/Worker）。

### 核心理念

- **解析器 + 透传层**：agents-hub 负责解析平台 session 文件和透传消息
- **数据权威源**：消息内容由底层平台（Claude Code/Codex）管理
- **轻量级架构**：直接调用 agent_bridge.execute_stream()，无需消息队列

## 数据模型

### 异常类

```python
# agents_hub/core/foundation/exceptions.py

from agents_hub.exceptions import ResourceNotFoundError

class SessionFileNotFoundError(ResourceNotFoundError):
    """Session 文件不存在"""
    def __init__(self, session_id: str, platform: str, work_root: str):
        super().__init__(
            message=f"Session 文件不存在: {session_id} ({platform})",
            error_code="SESSION_FILE_NOT_FOUND",
            details={"session_id": session_id, "platform": platform, "work_root": work_root},
        )
```

### SessionMessage

单聊消息类型（从平台 session 文件解析）：

```python
class SessionMessage(BaseModel):
    id: str                                    # 消息唯一标识（前端需要）
    role: Literal["user", "assistant", "system", "tool"]  # 角色
    content: str                               # 消息内容
    timestamp: str                             # 时间戳
    model: str | None = None                   # 使用的模型
    token_usage: dict | None = None            # Token 使用情况
```

### SingleChatIndex

单聊索引结构（持久化到 `local_data/single_chats/index.json`）：

```python
class SingleChatIndex(BaseModel):
    single_chat_id: str                        # 单聊唯一标识
    single_chat_name: str                      # 单聊名称
    type: Literal["new", "fork", "continue_group_chat"]  # 创建类型
    agent_name: str                            # Agent 名称
    platform: AgentPlatform                    # 平台类型（claude/codex）
    session_id: str | None = None              # 平台 session ID（首次对话后更新）
    session_path: str | None = None            # 平台 session 文件路径
    group_chat_id: str | None = None           # 来源群聊 ID（可选）
    cwd: str                                   # 工作目录
    created_at: str                            # 创建时间
    last_active_at: str                        # 最后活跃时间
```

## 内存缓存策略

采用 **LRU 淘汰策略**，保留最近活跃的 15 个单聊：

```python
class SingleChatManager:
    def __init__(self):
        self._index: dict[str, SingleChatIndex] = {}  # 从文件加载
        self._cache: OrderedDict[str, SingleChatCache] = OrderedDict()
        self._max_cached = 15  # LRU 缓存上限

class SingleChatCache:
    single_chat_id: str
    messages: list[SessionMessage]  # 从平台 session 文件解析
    last_access_time: datetime
```

**缓存策略**：
- 缓存命中：移到最后（标记为最近使用）
- 缓存未命中：从平台文件加载，加入缓存
- 缓存满了：淘汰最久未使用的

## 三种创建方式

### A. 新建空白会话

```python
# API: POST /single-chats
{
  "type": "new",
  "single_chat_name": "讨论新功能",
  "agent_name": "architect",
  "cwd": "/path/to/project"  # 必填
}

# 后端逻辑
1. 创建索引记录（session_id 初始为空）
2. 持久化到 index.json
3. 返回 single_chat_id
4. 首次发送消息时，CLI 返回 session_id → 更新索引
```

### B. Fork 群聊 Agent 会话

```python
# API: POST /single-chats
{
  "type": "fork",
  "single_chat_name": "基于架构讨论的分支",
  "group_chat_id": "group-uuid-1",
  "agent_name": "architect"
}

# 后端逻辑
1. 加载群聊：group_chat = await group_chat_manager.load_group_chat(group_chat_id)
2. 检查 Agent 空闲状态：
   agent_stats = group_chat.list_agent_stat()
   if agent_stats[agent_name].status != "idle":
       raise AgentBusyError(agent_name, agent_stats[agent_name].status)
3. 获取 session 和 cwd：
   main_session = group_chat.runtime.get_agent_session(agent_name)
   cwd = group_chat.runtime.get_agent_cwd(agent_name)
4. 调用 agent_bridge.execute(fork_from=main_session, ...)
5. CLI 返回新 session_id → 保存到索引
```

### C. 继续群聊 Agent 会话（私聊/BTW）

```python
# API: POST /single-chats
{
  "type": "continue_group_chat",
  "single_chat_name": "与 architect 私聊",
  "group_chat_id": "group-uuid-1",
  "agent_name": "architect"
}

# 后端逻辑
1. 加载群聊，获取 main_session 和 cwd
2. 检查 Agent 空闲状态（同 B）
3. 直接使用 main_session（不 fork）
4. 后续消息：agent_bridge.execute(session_id=main_session, ...)
5. 消息不进入群聊历史（纯私聊）
```

**场景说明**：用户在群聊中安排工作，需要私下与某个 Agent 补充细节时使用。

**Agent 状态检查**：
- `list_agent_stat()` 返回所有 Agent 的状态
- 只有 `idle` 状态的 Agent 才能 fork 或 continue
- 如果 Agent 正在处理任务（`busy`），返回错误提示用户稍后重试

## Session 路径解析

**关键点**：使用 `RoleConfig.work_root` 作为配置路径，按平台类型指定搜索目录。

```python
def resolve_session_path(session_id: str, role_config: RoleConfig) -> Path:
    """
    根据 session_id 和角色配置解析 session 文件路径
    
    Args:
        session_id: 平台 session ID
        role_config: 角色配置，包含 work_root（Claude/Codex 的配置目录）
    
    Returns:
        session 文件路径
    
    Raises:
        SessionFileNotFoundError: 文件不存在
    """
    work_root = Path(role_config.work_root)
    
    if not work_root.exists():
        raise SessionFileNotFoundError(session_id, role_config.platform.value, str(work_root))
    
    # 按平台指定搜索目录
    if role_config.platform == AgentPlatform.CLAUDE:
        # Claude: 搜索 work_root/projects/ 目录
        search_dir = work_root / "projects"
    elif role_config.platform == AgentPlatform.CODEX:
        # Codex: 搜索 work_root/sessions/ 目录
        search_dir = work_root / "sessions"
    else:
        raise SessionFileNotFoundError(session_id, role_config.platform.value, str(work_root))
    
    if not search_dir.exists():
        raise SessionFileNotFoundError(session_id, role_config.platform.value, str(search_dir))
    
    # 递归搜索包含 session_id 的 .jsonl 文件
    for f in search_dir.rglob(f"*{session_id}*.jsonl"):
        return f
    
    raise SessionFileNotFoundError(session_id, role_config.platform.value, str(search_dir))
```

**为什么使用 RoleConfig.work_root**：
- 不同角色可能使用不同的配置目录
- 支持自定义 work_root 的 Agent
- 避免硬编码路径

**平台搜索路径**：
- **Claude**: `work_root/projects/` 目录
- **Codex**: `work_root/sessions/` 目录

**搜索逻辑**（参考 `scripts/find_session.py`）：
- 使用 `rglob` 递归搜索
- 文件名包含 session_id 的 `.jsonl` 文件

## 消息发送流程

单聊采用**流式接口**（与群聊的异步队列模式不同）：

```python
# API: POST /single-chats/{single_chat_id}/messages/stream
# 返回: Server-Sent Events (SSE) 流

async def send_message_stream(
    single_chat_id: str,
    message: MessageCreate,
):
    # 1. 加载单聊配置
    single_chat = await single_chat_manager.get_or_load(single_chat_id)
    
    # 2. 获取 Role 配置
    role = role_manager.get_role(single_chat.agent_name)
    
    # 3. 流式执行
    async def event_generator():
        async for event in agent_bridge.execute_stream(
            prompt=message.content,
            config=role.get_role_config(),
            session_id=single_chat.session_id,
            cwd=single_chat.cwd,
        ):
            yield f"data: {event.model_dump_json()}\n\n"
            
            # 缓存到内存（只缓存最终消息）
            if event.type == AgentEventType.MESSAGE:
                single_chat.add_message_to_cache(event)
        
        # 4. 如果是首次对话，更新 session_id
        if not single_chat.session_id and event.session_id:
            await single_chat_manager.update_session_id(
                single_chat_id, 
                event.session_id
            )
    
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream"
    )
```

**与群聊的对比**：

| 特性 | 群聊 | 单聊 |
|------|------|------|
| 消息投递 | 放入 message_queue | 直接执行 |
| 响应方式 | WebSocket 广播 | SSE 流式返回 |
| 等待时长 | 立即返回 200 | 保持连接直到完成 |
| 路由逻辑 | MessageRouter | 无需路由 |

## 消息历史加载

```python
# API: GET /single-chats/{single_chat_id}/messages

async def get_messages(single_chat_id: str):
    # 1. 尝试从内存缓存加载
    single_chat = single_chat_manager.get_from_cache(single_chat_id)
    if single_chat and single_chat.messages:
        return single_chat.messages
    
    # 2. 缓存未命中 → 从平台文件加载
    index = await single_chat_manager.get_index(single_chat_id)
    
    if not index.session_path:
        # 未发送过消息，返回空
        return []
    
    # 3. 解析平台 session 文件
    messages = await parse_session_file(
        session_path=index.session_path,
        platform=index.platform
    )
    
    # 4. 缓存到内存（LRU）
    await single_chat_manager.cache_messages(single_chat_id, messages)
    
    return messages
```

## 模块划分

```
agents_hub/
├── api/
│   ├── routes/
│   │   └── single_chat.py          # 单聊 API 端点
│   ├── services/
│   │   └── single_chat_service.py  # 单聊业务逻辑
│   └── schemas/
│       └── single_chat.py          # 单聊数据模型
│
├── utils/
│   └── session_parser.py           # Session 文件解析器
```

## agent_bridge 扩展

需要为 agent_bridge 增加 fork 支持：

```python
# agents_hub/agent_bridge/bridge.py

class AgentBridge:
    async def execute_stream(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,  # 新增：要 fork 的 session ID
    ) -> AsyncIterator[StreamEvent]:
        """流式执行 Agent 调用"""
        executor = self._executors[config.platform]
        
        raw_stream = executor.execute(
            prompt, 
            config, 
            session_id, 
            cwd,
            fork_from=fork_from
        )
        
        async for event in raw_stream:
            yield event
```

**Claude Executor 修改**：

```python
def _build_command(self, prompt, config, session_id, fork_from):
    cmd = [CLAUDE_COMMAND, "--print", "--verbose", ...]
    
    if fork_from:
        # Fork: --fork-session --resume <fork_from>
        cmd.extend(["--fork-session", "--resume", fork_from])
    elif session_id:
        # 继续: --resume <session_id>
        cmd.extend(["--resume", session_id])
    
    cmd.append(prompt)
    return cmd
```

**Codex Executor 修改**：

```python
def _build_command(self, prompt, config, session_id, fork_from):
    if fork_from:
        # codex fork <fork_from> <prompt>
        cmd = [CODEX_COMMAND, "fork", fork_from, prompt]
    elif session_id:
        # codex resume <session_id> <prompt>
        cmd = [CODEX_COMMAND, "resume", session_id, prompt]
    else:
        # codex <prompt>
        cmd = [CODEX_COMMAND, prompt]
    
    return cmd
```

## 测试策略

### 测试前置准备

```python
@pytest.fixture
async def test_role():
    """创建测试用 Role"""
    role_manager = RoleManager()
    role = await role_manager.create_role(
        name="test_agent",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.WORKER,
        description="测试用 Agent",
        work_root=str(Path.home() / ".claude"),
    )
    yield role
    await role_manager.delete_role("test_agent")

@pytest.fixture
async def test_group_chat(test_role):
    """创建测试用群聊"""
    group_chat = GroupChat(
        team_members_name=["test_agent"],
        group_type=GroupChatType.MANAGER_ORCHESTRATE,
        project_path=str(Path("/tmp/test_project")),
    )
    await group_chat.start()
    group_chat_manager.register(group_chat.group_chat_id, group_chat)
    yield group_chat
    await group_chat.cleanup()
    group_chat_manager.unregister(group_chat.group_chat_id)
```

### CLI Fork 命令测试

```python
@pytest.mark.integration
async def test_claude_fork_command(test_role):
    """测试 Claude CLI fork 功能"""
    role_config = test_role.get_role_config()
    
    # 1. 创建基础 session
    base_events = []
    async for event in agent_bridge.execute_stream(
        prompt="Hello, this is a test",
        config=role_config,
        cwd=str(Path.cwd()),
    ):
        base_events.append(event)
    
    base_session_id = extract_session_id(base_events)
    assert base_session_id is not None
    
    # 2. Fork 该 session
    fork_events = []
    async for event in agent_bridge.execute_stream(
        prompt="Continue discussion",
        config=role_config,
        fork_from=base_session_id,
    ):
        fork_events.append(event)
    
    new_session_id = extract_session_id(fork_events)
    
    # 3. 验证
    assert new_session_id != base_session_id
    assert new_session_id is not None
    
    # 4. 验证文件存在
    new_path = resolve_session_path(new_session_id, AgentPlatform.CLAUDE)
    assert new_path.exists()
    
    # 5. 验证消息历史
    messages = parse_session_file(str(new_path), AgentPlatform.CLAUDE)
    assert len(messages) > 0
```

### 端到端测试

```python
@pytest.mark.e2e
async def test_fork_from_group_chat(test_group_chat, test_role):
    """端到端：从群聊 fork 到单聊"""
    service = SingleChatService()
    
    # 1. 群聊中发送消息
    await test_group_chat.send_message_to_agent(
        agent_name="test_agent",
        content="讨论架构设计",
        send_from="user",
    )
    await asyncio.sleep(2)
    
    # 2. 获取 Agent 的 main_session
    main_session = test_group_chat.runtime.get_agent_session("test_agent")
    assert main_session is not None
    
    # 3. Fork 到单聊
    single_chat_id = await service.create_single_chat(
        single_chat_name="Fork 测试",
        type="fork",
        group_chat_id=test_group_chat.group_chat_id,
        agent_name="test_agent",
    )
    
    # 4. 在单聊中发送消息
    events = []
    async for event in service.send_message_stream(
        single_chat_id=single_chat_id,
        content="继续讨论",
    ):
        events.append(event)
    
    # 5. 验证
    assert len(events) > 0
    
    # 6. 加载历史
    messages = await service.get_messages(single_chat_id)
    assert len(messages) > 1
```

### Session 文件解析测试

```python
@pytest.mark.integration
async def test_parse_real_claude_session(test_role):
    """测试解析真实的 Claude session 文件"""
    events = []
    async for event in agent_bridge.execute_stream(
        prompt="Test message",
        config=test_role.get_role_config(),
    ):
        events.append(event)
    
    session_id = extract_session_id(events)
    session_path = resolve_session_path(session_id, AgentPlatform.CLAUDE)
    messages = parse_session_file(str(session_path), AgentPlatform.CLAUDE)
    
    assert len(messages) > 0
    assert all(m.id for m in messages)
    assert all(m.role in ["user", "assistant", "system"] for m in messages)
    assert all(m.content for m in messages)
```

### LRU 缓存测试

```python
async def test_lru_cache_eviction():
    """测试 LRU 缓存淘汰机制"""
    manager = SingleChatManager(max_cached=3)
    
    # 加载 5 个单聊
    for i in range(5):
        await manager.get_or_load(f"chat-{i}")
    
    # 验证：只保留最后 3 个
    assert len(manager._cache) == 3
    assert "chat-0" not in manager._cache
    assert "chat-4" in manager._cache
```

## 设计决策

### 为什么不在 core/ 层实现？

1. 单聊无需编排逻辑（无 MessageRouter、AgentCallManager）
2. 直接调用 agent_bridge.execute_stream()
3. 数据管理简单（索引 + LRU 缓存）
4. 符合简单性原则

### 为什么使用流式接口而非消息队列？

1. 群聊需要异步队列处理多个 Agent 的并发
2. 单聊是点对点通信，无需队列
3. 流式接口提供更好的用户体验（实时看到 Agent 思考过程）

### 为什么不持久化消息内容？

1. 符合 SSOT 原则：平台 session 文件是权威源
2. 避免数据冗余和同步问题
3. 减少 agents-hub 的存储负担
