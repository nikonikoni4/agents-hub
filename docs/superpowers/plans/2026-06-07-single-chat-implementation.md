# Single Chat 单聊通道实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现单聊通道，支持用户与单个 Agent 直接对话，支持新建、fork 群聊会话、继续群聊会话三种方式

**Architecture:** 单聊采用解析器+透传层架构，消息内容由平台 session 文件管理，agents-hub 负责索引管理和流式消息转发，实现位于 API 层（routes/services/schemas）

**Tech Stack:** Python, FastAPI, Pydantic, asyncio, SSE (Server-Sent Events)

---

## 文件结构

```
agents_hub/
├── api/
│   ├── routes/
│   │   └── single_chat.py          # 单聊 API 端点
│   ├── schemas/
│   │   └── single_chat.py          # 单聊数据模型
│   └── services/
│       └── single_chat_service.py  # 单聊业务逻辑
│
├── core/
│   └── foundation/
│       └── exceptions.py           # 新增 SessionFileNotFoundError
│
├── utils/
│   └── session_parser.py           # Session 文件解析器
│
├── agent_bridge/
│   ├── bridge.py                   # 修改：增加 fork_from 参数
│   └── executors/
│       ├── claude.py               # 修改：支持 fork 命令
│       └── codex.py                # 修改：支持 fork 命令
│
└── tests/
    ├── api/
    │   └── test_single_chat.py     # 单聊 API 测试
    ├── utils/
    │   └── test_session_parser.py  # Session 解析器测试
    └── agent_bridge/
        └── test_fork.py            # Fork 功能测试
```

---

## Task 1: 添加异常类

**Files:**
- Modify: `agents_hub/core/foundation/exceptions.py`

- [ ] **Step 1: 添加 SessionFileNotFoundError**

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

- [ ] **Step 2: 更新 __all__ 导出列表**

```python
# agents_hub/core/foundation/exceptions.py

__all__ = [
    # ... 现有导出 ...
    "SessionFileNotFoundError",
]
```

- [ ] **Step 3: Commit**

```bash
git add agents_hub/core/foundation/exceptions.py
git commit -m "feat: 添加 SessionFileNotFoundError 异常类"
```

---

## Task 2: 创建 Session 解析器

**Files:**
- Create: `agents_hub/utils/session_parser.py`
- Test: `tests/utils/test_session_parser.py`

- [ ] **Step 1: 创建解析器模块**

```python
# agents_hub/utils/session_parser.py

"""Session 文件解析器

解析 Claude Code 和 Codex 平台的 session 文件，返回统一格式的消息列表。
"""

import json
from pathlib import Path

from pydantic import BaseModel

from agents_hub.agent_bridge.models import AgentPlatform


class SessionMessage(BaseModel):
    """单聊消息类型"""
    id: str
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    timestamp: str
    model: str | None = None
    token_usage: dict | None = None


def load_jsonl(file_path: Path) -> list[dict]:
    """加载 JSONL 文件"""
    messages = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def parse_claude_session(messages: list[dict]) -> list[SessionMessage]:
    """解析 Claude Code session 文件"""
    result = []
    
    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")
        
        if msg_type == "user":
            content = msg.get("message", {}).get("content", "")
            if isinstance(content, str) and content:
                result.append(SessionMessage(
                    id=msg.get("uuid", ""),
                    role="user",
                    content=content,
                    timestamp=timestamp,
                ))
        
        elif msg_type == "assistant":
            inner = msg.get("message", {})
            content_blocks = inner.get("content", [])
            text_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            
            if text_parts:
                result.append(SessionMessage(
                    id=inner.get("id", msg.get("uuid", "")),
                    role="assistant",
                    content="\n".join(text_parts),
                    timestamp=timestamp,
                    model=inner.get("model"),
                ))
    
    return result


def parse_codex_session(messages: list[dict]) -> list[SessionMessage]:
    """解析 Codex session 文件"""
    result = []
    
    for msg in messages:
        msg_type = msg.get("type")
        timestamp = msg.get("timestamp", "")
        
        if msg_type == "response_item":
            payload = msg.get("payload", {})
            role = payload.get("role", "")
            texts = []
            for block in payload.get("content", []):
                bt = block.get("type", "")
                if bt in ("input_text", "output_text"):
                    texts.append(block.get("text", ""))
            
            if texts:
                result.append(SessionMessage(
                    id=payload.get("id", ""),
                    role=role,
                    content="\n".join(texts),
                    timestamp=timestamp,
                ))
    
    return result


def parse_session_file(file_path: Path, platform: AgentPlatform) -> list[SessionMessage]:
    """
    解析 session 文件，返回统一格式的消息列表
    
    Args:
        file_path: session 文件路径
        platform: 平台类型
    
    Returns:
        SessionMessage 列表
    """
    messages = load_jsonl(file_path)
    
    if platform == AgentPlatform.CLAUDE:
        return parse_claude_session(messages)
    elif platform == AgentPlatform.CODEX:
        return parse_codex_session(messages)
    else:
        raise ValueError(f"Unsupported platform: {platform}")
```

- [ ] **Step 2: 创建测试文件**

```python
# tests/utils/test_session_parser.py

"""Session 解析器测试"""

import json
import tempfile
from pathlib import Path

import pytest

from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.utils.session_parser import (
    SessionMessage,
    parse_session_file,
)


@pytest.fixture
def claude_session_file(tmp_path):
    """创建测试用 Claude session 文件"""
    data = [
        {"type": "user", "uuid": "msg-1", "timestamp": "2026-01-01T00:00:00Z", "message": {"content": "Hello"}},
        {"type": "assistant", "uuid": "msg-2", "timestamp": "2026-01-01T00:00:01Z", "message": {"id": "resp-1", "content": [{"type": "text", "text": "Hi there!"}], "model": "claude-3"}},
    ]
    file_path = tmp_path / "test_session.jsonl"
    with open(file_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return file_path


@pytest.fixture
def codex_session_file(tmp_path):
    """创建测试用 Codex session 文件"""
    data = [
        {"type": "response_item", "timestamp": "2026-01-01T00:00:00Z", "payload": {"id": "msg-1", "role": "user", "content": [{"type": "input_text", "text": "Hello"}]}},
        {"type": "response_item", "timestamp": "2026-01-01T00:00:01Z", "payload": {"id": "msg-2", "role": "assistant", "content": [{"type": "output_text", "text": "Hi there!"}]}},
    ]
    file_path = tmp_path / "test_session.jsonl"
    with open(file_path, "w") as f:
        for item in data:
            f.write(json.dumps(item) + "\n")
    return file_path


def test_parse_claude_session(claude_session_file):
    """测试解析 Claude session"""
    messages = parse_session_file(claude_session_file, AgentPlatform.CLAUDE)
    
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there!"
    assert messages[1].model == "claude-3"


def test_parse_codex_session(codex_session_file):
    """测试解析 Codex session"""
    messages = parse_session_file(codex_session_file, AgentPlatform.CODEX)
    
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Hello"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Hi there!"
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/utils/test_session_parser.py -v
```

- [ ] **Step 4: Commit**

```bash
git add agents_hub/utils/session_parser.py tests/utils/test_session_parser.py
git commit -m "feat: 添加 Session 文件解析器"
```

---

## Task 3: 创建单聊数据模型

**Files:**
- Create: `agents_hub/api/schemas/single_chat.py`

- [ ] **Step 1: 创建 Pydantic 模型**

```python
# agents_hub/api/schemas/single_chat.py

"""单聊数据模型"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from agents_hub.config.types import AgentPlatform


class SingleChatType(str, Enum):
    """单聊创建类型"""
    NEW = "new"
    FORK = "fork"
    CONTINUE_GROUP_CHAT = "continue_group_chat"


class SingleChatIndex(BaseModel):
    """单聊索引（持久化到文件）"""
    single_chat_id: str
    single_chat_name: str
    type: SingleChatType
    agent_name: str
    platform: AgentPlatform
    session_id: str | None = None
    session_path: str | None = None
    group_chat_id: str | None = None
    cwd: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_active_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CreateSingleChatRequest(BaseModel):
    """创建单聊请求"""
    type: SingleChatType
    single_chat_name: str
    agent_name: str
    group_chat_id: str | None = None
    cwd: str | None = None


class CreateSingleChatResponse(BaseModel):
    """创建单聊响应"""
    single_chat_id: str
    single_chat_name: str
    type: SingleChatType


class SingleChatResponse(BaseModel):
    """单聊详情响应"""
    single_chat_id: str
    single_chat_name: str
    type: SingleChatType
    agent_name: str
    platform: AgentPlatform
    session_id: str | None = None
    group_chat_id: str | None = None
    cwd: str
    created_at: str
    last_active_at: str


class SingleChatListResponse(BaseModel):
    """单聊列表响应"""
    single_chats: list[SingleChatResponse]


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str


class SessionMessageResponse(BaseModel):
    """Session 消息响应"""
    id: str
    role: str
    content: str
    timestamp: str
    model: str | None = None


class MessageHistoryResponse(BaseModel):
    """消息历史响应"""
    messages: list[SessionMessageResponse]
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/api/schemas/single_chat.py
git commit -m "feat: 添加单聊数据模型 schemas"
```

---

## Task 4: 扩展 agent_bridge 支持 fork

**Files:**
- Modify: `agents_hub/agent_bridge/bridge.py`
- Modify: `agents_hub/agent_bridge/executors/claude.py`
- Modify: `agents_hub/agent_bridge/executors/codex.py`

- [ ] **Step 1: 修改 ClaudeExecutor 支持 fork**

```python
# agents_hub/agent_bridge/executors/claude.py

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
    ) -> AsyncIterator[str]:
        """启动 Claude CLI 并返回原始输出流"""
        cmd = self._build_command(prompt, config, session_id, fork_from)
        # ... 其余代码不变 ...
    
    def _build_command(self, prompt: str, config: RoleConfig, session_id: str | None, fork_from: str | None) -> list:
        """构建 Claude CLI 命令"""
        cmd = [
            CLAUDE_COMMAND,
            "--print",
            "--verbose",
            "--output-format",
            "stream-json",
            "--include-partial-messages",
        ]
        
        if config.bare:
            cmd.append("--bare")
        
        if fork_from:
            # Fork: --fork-session --resume <fork_from>
            cmd.extend(["--fork-session", "--resume", fork_from])
        elif session_id:
            # 继续: --resume <session_id>
            cmd.extend(["--resume", session_id])
        
        cmd.append(prompt)
        return cmd
```

- [ ] **Step 2: 修改 CodexExecutor 支持 fork**

```python
# agents_hub/agent_bridge/executors/codex.py

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
    ) -> AsyncIterator[str]:
        """启动 Codex CLI 并返回原始输出流"""
        cmd = self._build_command(prompt, config, session_id, fork_from)
        # ... 其余代码不变 ...
    
    def _build_command(self, prompt: str, config: RoleConfig, session_id: str | None, fork_from: str | None) -> list:
        """构建 Codex CLI 命令"""
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

- [ ] **Step 3: 修改 AgentBridge.execute_stream**

```python
# agents_hub/agent_bridge/bridge.py

    async def execute_stream(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: str | None = None,
        cwd: str | None = None,
        fork_from: str | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """流式执行 Agent 调用"""
        # 验证平台是否支持
        if config.platform not in self._executors:
            supported = [p.value for p in self._executors]
            raise PlatformNotSupportedError(
                platform=config.platform.value, supported_platforms=supported
            )
        
        executor = self._executors[config.platform]
        parser = self._parsers[config.platform]
        
        try:
            raw_stream = executor.execute(prompt, config, session_id, cwd, fork_from=fork_from)
            async for raw_line in raw_stream:
                if raw_line.strip():
                    try:
                        parsed_event = parser.parse_event(raw_line)
                        if parsed_event is not None:
                            parsed_event.agent_name = config.name
                            parsed_event.platform = config.platform
                            parsed_event.role_type = config.role_type
                            yield parsed_event
                    except Exception as e:
                        logger.warning(f"Failed to parse event: {e}")
        except Exception as e:
            logger.error(f"Execute stream failed: {e}")
            raise
```

- [ ] **Step 4: Commit**

```bash
git add agents_hub/agent_bridge/bridge.py agents_hub/agent_bridge/executors/claude.py agents_hub/agent_bridge/executors/codex.py
git commit -m "feat: agent_bridge 支持 fork_from 参数"
```

---

## Task 5: 创建单聊 Service 层

**Files:**
- Create: `agents_hub/api/services/single_chat_service.py`

- [ ] **Step 1: 创建 SingleChatManager**

```python
# agents_hub/api/services/single_chat_service.py

"""单聊 Service 层"""

import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from agents_hub.agent_bridge import agent_bridge
from agents_hub.agent_bridge.models import AgentEventType
from agents_hub.api.schemas.single_chat import (
    CreateSingleChatRequest,
    CreateSingleChatResponse,
    SingleChatIndex,
    SingleChatListResponse,
    SingleChatResponse,
    SingleChatType,
)
from agents_hub.config import config
from agents_hub.config.types import AgentPlatform
from agents_hub.core.foundation.exceptions import SessionFileNotFoundError
from agents_hub.roles import RoleManager
from agents_hub.utils.logger import get_logger
from agents_hub.utils.session_parser import SessionMessage, parse_session_file

logger = get_logger(__name__)


class SingleChatManager:
    """单聊管理器"""
    
    def __init__(self, data_path: Path | None = None):
        self._data_path = data_path or Path(config.data_path) / "single_chats"
        self._index_file = self._data_path / "index.json"
        self._index: dict[str, SingleChatIndex] = {}
        self._cache: OrderedDict[str, list[SessionMessage]] = OrderedDict()
        self._max_cached = 15
        self._role_manager = RoleManager()
        
        # 确保目录存在
        self._data_path.mkdir(parents=True, exist_ok=True)
        
        # 加载索引
        self._load_index()
    
    def _load_index(self):
        """从文件加载索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data.get("single_chats", []):
                        index = SingleChatIndex(**item)
                        self._index[index.single_chat_id] = index
            except Exception as e:
                logger.error(f"Failed to load index: {e}")
    
    def _save_index(self):
        """保存索引到文件"""
        data = {
            "single_chats": [idx.model_dump() for idx in self._index.values()]
        }
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    async def create_single_chat(self, request: CreateSingleChatRequest) -> CreateSingleChatResponse:
        """创建单聊"""
        single_chat_id = str(uuid4())
        role = self._role_manager.get_role(request.agent_name)
        role_config = role.get_role_config()
        
        # 获取 session_id 和 cwd
        session_id = None
        session_path = None
        cwd = request.cwd
        
        if request.type == SingleChatType.FORK or request.type == SingleChatType.CONTINUE_GROUP_CHAT:
            # 从群聊获取 session 和 cwd
            if not request.group_chat_id:
                raise ValueError("group_chat_id is required for fork/continue")
            
            from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
            
            group_chat = await group_chat_manager.load_group_chat(request.group_chat_id)
            
            # 检查 Agent 空闲状态
            # TODO: 实现 Agent 状态检查
            
            # 获取 session 和 cwd
            agent_info = group_chat.runtime.get_agent_member_info(request.agent_name)
            if agent_info:
                session_id = agent_info.main_session
                cwd = cwd or agent_info.cwd
            
            if request.type == SingleChatType.FORK:
                # Fork: 先不设置 session_id，首次发送时 fork
                session_id = None
            # continue: 直接使用 session_id
        
        index = SingleChatIndex(
            single_chat_id=single_chat_id,
            single_chat_name=request.single_chat_name,
            type=request.type,
            agent_name=request.agent_name,
            platform=role_config.platform,
            session_id=session_id,
            session_path=session_path,
            group_chat_id=request.group_chat_id,
            cwd=cwd or str(Path.cwd()),
        )
        
        self._index[single_chat_id] = index
        self._save_index()
        
        return CreateSingleChatResponse(
            single_chat_id=single_chat_id,
            single_chat_name=request.single_chat_name,
            type=request.type,
        )
    
    def get_single_chat(self, single_chat_id: str) -> SingleChatIndex:
        """获取单聊索引"""
        if single_chat_id not in self._index:
            raise ValueError(f"Single chat not found: {single_chat_id}")
        return self._index[single_chat_id]
    
    def list_single_chats(self) -> SingleChatListResponse:
        """列出所有单聊"""
        chats = [self._to_response(idx) for idx in self._index.values()]
        chats.sort(key=lambda x: x.last_active_at, reverse=True)
        return SingleChatListResponse(single_chats=chats)
    
    def _to_response(self, index: SingleChatIndex) -> SingleChatResponse:
        """转换为响应格式"""
        return SingleChatResponse(
            single_chat_id=index.single_chat_id,
            single_chat_name=index.single_chat_name,
            type=index.type,
            agent_name=index.agent_name,
            platform=index.platform,
            session_id=index.session_id,
            group_chat_id=index.group_chat_id,
            cwd=index.cwd,
            created_at=index.created_at,
            last_active_at=index.last_active_at,
        )
    
    async def send_message_stream(self, single_chat_id: str, content: str):
        """发送消息（流式）"""
        index = self.get_single_chat(single_chat_id)
        role = self._role_manager.get_role(index.agent_name)
        role_config = role.get_role_config()
        
        # 确定 fork_from 和 session_id
        fork_from = None
        session_id = index.session_id
        
        if index.type == SingleChatType.FORK and not index.session_id:
            # Fork 模式：从群聊获取 session 作为 fork_from
            if index.group_chat_id:
                from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
                group_chat = await group_chat_manager.load_group_chat(index.group_chat_id)
                agent_info = group_chat.runtime.get_agent_member_info(index.agent_name)
                if agent_info:
                    fork_from = agent_info.main_session
        
        # 流式执行
        async for event in agent_bridge.execute_stream(
            prompt=content,
            config=role_config,
            session_id=session_id,
            cwd=index.cwd,
            fork_from=fork_from,
        ):
            yield event
            
            # 更新 session_id
            if event.session_id and not index.session_id:
                index.session_id = event.session_id
                self._save_index()
            
            # 更新 last_active_at
            index.last_active_at = datetime.now().isoformat()
            self._save_index()
    
    async def get_messages(self, single_chat_id: str) -> list[SessionMessage]:
        """获取消息历史"""
        index = self.get_single_chat(single_chat_id)
        
        # 尝试从缓存加载
        if single_chat_id in self._cache:
            # 移到最后（LRU）
            self._cache.move_to_end(single_chat_id)
            return self._cache[single_chat_id]
        
        # 从文件加载
        if not index.session_path:
            return []
        
        try:
            session_path = Path(index.session_path)
            messages = parse_session_file(session_path, index.platform)
            
            # 缓存
            self._cache[single_chat_id] = messages
            if len(self._cache) > self._max_cached:
                self._cache.popitem(last=False)
            
            return messages
        except Exception as e:
            logger.error(f"Failed to load messages: {e}")
            return []


# 全局实例
single_chat_manager = SingleChatManager()
```

- [ ] **Step 2: Commit**

```bash
git add agents_hub/api/services/single_chat_service.py
git commit -m "feat: 添加单聊 Service 层"
```

---

## Task 6: 创建单聊 API 路由

**Files:**
- Create: `agents_hub/api/routes/single_chat.py`
- Modify: `agents_hub/api/app.py` (注册路由)

- [ ] **Step 1: 创建路由文件**

```python
# agents_hub/api/routes/single_chat.py

"""单聊 API 路由"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from agents_hub.api.schemas.single_chat import (
    CreateSingleChatRequest,
    CreateSingleChatResponse,
    MessageHistoryResponse,
    SendMessageRequest,
    SessionMessageResponse,
    SingleChatListResponse,
    SingleChatResponse,
)
from agents_hub.api.services.single_chat_service import single_chat_manager
from agents_hub.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/single-chats", tags=["single-chats"])


@router.post("", response_model=CreateSingleChatResponse)
async def create_single_chat(request: CreateSingleChatRequest):
    """创建单聊"""
    try:
        return await single_chat_manager.create_single_chat(request)
    except Exception as e:
        logger.error(f"Failed to create single chat: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=SingleChatListResponse)
async def list_single_chats():
    """列出所有单聊"""
    return single_chat_manager.list_single_chats()


@router.get("/{single_chat_id}", response_model=SingleChatResponse)
async def get_single_chat(single_chat_id: str):
    """获取单聊详情"""
    try:
        index = single_chat_manager.get_single_chat(single_chat_id)
        return single_chat_manager._to_response(index)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{single_chat_id}/messages/stream")
async def send_message_stream(single_chat_id: str, request: SendMessageRequest):
    """发送消息（流式）"""
    try:
        async def event_generator():
            async for event in single_chat_manager.send_message_stream(
                single_chat_id, request.content
            ):
                yield f"data: {event.model_dump_json()}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{single_chat_id}/messages", response_model=MessageHistoryResponse)
async def get_messages(single_chat_id: str):
    """获取消息历史"""
    try:
        messages = await single_chat_manager.get_messages(single_chat_id)
        return MessageHistoryResponse(
            messages=[
                SessionMessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    timestamp=m.timestamp,
                    model=m.model,
                )
                for m in messages
            ]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: 注册路由到 app.py**

```python
# agents_hub/api/app.py

from agents_hub.api.routes import single_chat  # 新增

# ... 其他代码 ...

app.include_router(single_chat.router)  # 新增
```

- [ ] **Step 3: Commit**

```bash
git add agents_hub/api/routes/single_chat.py agents_hub/api/app.py
git commit -m "feat: 添加单聊 API 路由"
```

---

## Task 7: 集成测试

**Files:**
- Create: `tests/api/test_single_chat.py`

- [ ] **Step 1: 创建集成测试**

```python
# tests/api/test_single_chat.py

"""单聊 API 集成测试"""

import pytest
from fastapi.testclient import TestClient

from agents_hub.api.app import app
from agents_hub.api.schemas.single_chat import SingleChatType


@pytest.fixture
def client():
    return TestClient(app)


def test_create_single_chat(client):
    """测试创建单聊"""
    response = client.post("/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "single_chat_id" in data
    assert data["single_chat_name"] == "测试单聊"


def test_list_single_chats(client):
    """测试列出单聊"""
    # 先创建一个
    client.post("/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })
    
    response = client.get("/single-chats")
    assert response.status_code == 200
    data = response.json()
    assert "single_chats" in data


def test_get_single_chat_not_found(client):
    """测试获取不存在的单聊"""
    response = client.get("/single-chats/nonexistent")
    assert response.status_code == 404


def test_get_messages_empty(client):
    """测试获取空消息历史"""
    # 创建单聊
    create_response = client.post("/single-chats", json={
        "type": "new",
        "single_chat_name": "测试单聊",
        "agent_name": "test_agent",
        "cwd": "/tmp/test",
    })
    single_chat_id = create_response.json()["single_chat_id"]
    
    response = client.get(f"/single-chats/{single_chat_id}/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == []
```

- [ ] **Step 2: 运行测试**

```bash
pytest tests/api/test_single_chat.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/api/test_single_chat.py
git commit -m "test: 添加单聊 API 集成测试"
```

---

## 执行顺序

1. **Task 1**: 添加异常类
2. **Task 2**: 创建 Session 解析器（含测试）
3. **Task 3**: 创建单聊数据模型
4. **Task 4**: 扩展 agent_bridge 支持 fork
5. **Task 5**: 创建单聊 Service 层
6. **Task 6**: 创建单聊 API 路由
7. **Task 7**: 集成测试

每个 Task 完成后运行测试并 commit，确保代码质量和可追溯性。
