---
version: 1.1
created_at: 2026-06-04
updated_at: 2026-06-04
last_updated: 修复审查发现的问题：补充测试覆盖、明确实现细节、优化任务顺序
abstract: core runtime 内存 SSOT 重构实施计划，定义 Runtime/State 的完整函数签名、当前 service 所需 query/command 接口、持久化内容矩阵和分步测试迁移任务。
title: Core Runtime SSOT Implementation Plan
status: active
related_spec: docs/superpowers/specs/2026-06-04-core-runtime-ssot-design.md
---

# Core Runtime SSOT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce `GroupChatRuntime` and `GroupChatRuntimeState` so active group-chat runtime state is read from memory, persisted synchronously after commands, and no API/service code reaches through `group_chat_context.repository`.

**Architecture:** `GroupChat` remains the lifecycle coordinator. `GroupChatRuntime` owns `GroupChatRuntimeState` and `GroupChatRepository`; `GroupChatContext` keeps context-domain logic but reads/writes through the runtime. API service calls use `GroupChat`/`GroupChatRuntime` query and command methods instead of internal context models or repository files.

**Tech Stack:** Python 3.13, dataclasses, asyncio, pytest, existing `GroupChatRepository`, existing Pydantic API schemas.

---

## Current Service Interface Requirements

`agents_hub/api/services/group_chat_service.py` currently needs these core capabilities:

| Service method | Core operation needed | Query or command | Required output |
| --- | --- | --- | --- |
| `create_group_chat()` | create/start group chat, then read info | command + query | `group_chat_id`, `group_chat_name`, `project_path`, `created_at`, `group_type`, `is_active` |
| `load_group_chat()` | load group chat, then read info | command + query | same as `get_info` |
| `delete_group_chat()` | read `project_path`, unregister, optionally delete files | query + lifecycle | `project_path` |
| `list_group_chats()` | list metadata for active and inactive groups | catalog query | summary dicts |
| `get_group_chat_info()` | read active runtime metadata | query | info dict |
| `get_group_chat_members()` | read member session state | query | `name`, `main_session`, `btw_session`, `cwd`, `use_docker` |
| `get_messages()` | read group messages | query | `speaker`, `content`, `timestamp`, `platform` |
| `send_message()` | validate members, create call, route message | command through existing managers | no return (delegates to MessageRouter) |
| `toggle_use_docker()` | validate member and Docker, update session state | command | member dict |

Core query dicts for this plan are stable only across `core -> api service`. They are not API response schemas.

```python
GroupInfoDict = dict[str, object]
# keys:
# - group_chat_id: str
# - group_chat_name: str
# - project_path: str
# - created_at: datetime
# - group_type: str
# - is_active: bool

GroupMemberDict = dict[str, object]
# keys:
# - name: str
# - main_session: str | None
# - btw_session: list[str]
# - cwd: str | None
# - use_docker: bool

MessageInfoDict = dict[str, str]
# keys:
# - speaker: str
# - content: str
# - timestamp: str
# - platform: str
```

## Persistence Matrix

All runtime writes must update memory first and synchronously persist the durable copy.

| Runtime command | Memory state updated | File saved |
| --- | --- | --- |
| `initialize_metadata()` | `state.metadata` | `group_metadata.json` |
| `add_message()` | `state.group_chat_session.messages` | `<group_chat_id>.jsonl` |
| `update_agent_session_from_result()` | `state.agent_sessions[agent_name]` | `agent_session_state.json` |
| `set_agent_token_and_default_cwd()` | `state.agent_sessions[agent_name].token/cwd` | `agent_session_state.json` |
| `update_context_load_state()` | `state.agent_sessions[agent_name].context_state` | `agent_session_state.json` |
| `set_agent_use_docker()` | `state.agent_sessions[agent_name].use_docker` | `agent_session_state.json` |
| `append_compact_record_and_mark_compacted()` | `state.compact_history`, `state.group_chat_session.last_compacted_loc` | `memory/compact_history.jsonl`, `<group_chat_id>.jsonl` |

**Degraded State Handling:** On persistence failure, set `state.persistence_error` to a non-empty string and re-raise the original exception. Do not silently continue. The persistence error flag is checked by guard validations in runtime commands to prevent cascading failures.

## File Structure

Create:

- `agents_hub/core/context/group_chat_runtime_state.py`: internal runtime dataclass and small helper methods.
- `agents_hub/core/context/group_chat_runtime.py`: runtime facade owning state and repository.
- `tests/core/context/test_group_chat_runtime.py`: focused runtime unit tests.

Modify:

- `agents_hub/core/context/__init__.py`: export runtime types.
- `agents_hub/core/context/group_chat_context.py`: accept runtime, remove repository ownership, keep context-domain behavior.
- `agents_hub/core/context/agent_context.py`: persist context load state through context/runtime command.
- `agents_hub/core/orchestration/group_chat.py`: create repository/runtime, use runtime for metadata/token/session commands.
- `agents_hub/core/orchestration/group_chat_manager.py`: use runtime queries for active group chat information and load-from-disk team members.
- `agents_hub/core/agent/base_agent.py`: replace `repository.project_path` access with runtime/context project path accessor.
- `agents_hub/api/services/group_chat_service.py`: replace `context.repository` and raw file reads with runtime query/command.
- Existing tests under `tests/api/services/`, `tests/core/context/`, and `tests/core/orchestration/`: update mocks and assertions to the new runtime API.

Do not move `GroupChatRepository` in this plan. It stays in `core/context` as the file persistence adapter (Repository is the term consistently used throughout this codebase).

## Runtime API To Implement

### `GroupChatRuntimeState`

File: `agents_hub/core/context/group_chat_runtime_state.py`

```python
from dataclasses import dataclass, field

from agents_hub.core.context.group_chat_session import AgentSessionInfo, GroupChatSession
from agents_hub.core.context.group_metadata import GroupMetadata


@dataclass
class GroupChatRuntimeState:
    group_chat_id: str
    project_path: str
    group_chat_session: GroupChatSession | None = None
    agent_sessions: dict[str, AgentSessionInfo] = field(default_factory=dict)
    compact_history: list[dict] = field(default_factory=list)
    metadata: GroupMetadata | None = None
    persistence_error: str | None = None

    def require_session(self) -> GroupChatSession:
        if self.group_chat_session is None:
            from agents_hub.core.foundation import StateError

            raise StateError("GroupChatSession 未加载，请先调用 runtime.load()")
        return self.group_chat_session

    def require_metadata(self) -> GroupMetadata:
        if self.metadata is None:
            from agents_hub.core.foundation import StateError

            raise StateError("GroupMetadata 未加载或未初始化")
        return self.metadata
```

### `GroupChatRuntime`

File: `agents_hub/core/context/group_chat_runtime.py`

```python
from datetime import datetime
from typing import Any

from agents_hub.core.context.group_chat_repository import GroupChatRepository
from agents_hub.core.context.group_chat_runtime_state import GroupChatRuntimeState
from agents_hub.core.context.group_chat_session import (
    AgentContextState,
    AgentSessionInfo,
)
from agents_hub.core.context.group_metadata import GroupMetadata
from agents_hub.core.foundation import GroupChatType


class GroupChatRuntime:
    def __init__(
        self,
        group_chat_id: str,
        project_path: str,
        repository: GroupChatRepository | None = None,
        state: GroupChatRuntimeState | None = None,
    ) -> None:
        """Create a runtime facade for one group chat."""

    async def load(self) -> GroupChatRuntimeState:
        """Load durable files into memory state and return the state."""

    async def initialize_metadata(
        self,
        group_chat_name: str,
        group_type: GroupChatType | str,
        created_at: datetime | None = None,
    ) -> GroupMetadata:
        """Create metadata in memory, save group_metadata.json, and return metadata."""

    def get_project_path(self) -> str:
        """Return runtime project path."""

    def get_metadata(self) -> GroupMetadata:
        """Return loaded metadata or raise StateError."""

    def get_info_dict(self, is_active: bool) -> dict[str, Any]:
        """Return core external group info dict."""

    def get_member_dicts(self) -> list[dict[str, Any]]:
        """Return core external member dicts from memory state."""

    def get_message_dicts(self, limit: int = 50, offset: int = 0) -> list[dict[str, str]]:
        """Return message dicts from memory state.
        
        Implementation:
        1. Get messages from state.require_session().messages
        2. Apply pagination: messages[offset:offset+limit]
        3. Map fields: agent_name -> speaker
        """

    def get_agent_names(self) -> list[str]:
        """Return names present in agent session state."""

    def get_agent_session(self, agent_name: str) -> AgentSessionInfo | None:
        """Return one agent session or None."""

    def get_or_create_agent_session(self, agent_name: str) -> AgentSessionInfo:
        """Return existing agent session or create an empty one in memory."""

    async def save_agent_sessions(self) -> None:
        """Persist all agent sessions to agent_session_state.json."""

    async def add_message(self, agent_result) -> None:
        """Append an agent result to memory messages and persist messages jsonl."""

    async def update_agent_session_from_result(self, agent_result) -> AgentSessionInfo:
        """Update session IDs from AgentResult and persist agent_session_state.json."""

    async def set_agent_token_and_default_cwd(
        self,
        agent_name: str,
        token: str,
        default_cwd: str | None = None,
    ) -> AgentSessionInfo:
        """Set token and fill empty cwd with default cwd, then persist."""

    async def update_context_load_state(
        self,
        agent_name: str,
        last_loaded_compact_index: int,
        last_loaded_message_index: int,
    ) -> AgentSessionInfo:
        """Update one agent context load state and persist."""

    async def set_agent_use_docker(
        self,
        agent_name: str,
        use_docker: bool,
    ) -> AgentSessionInfo:
        """Set one agent Docker flag and persist."""

    async def load_compact_history(self) -> list[dict]:
        """Return compact history from memory state."""

    async def append_compact_record_and_mark_compacted(self, compact_record: dict) -> None:
        """Append compact record, mark messages compacted, and persist both files."""

    def close(self) -> None:
        """Close the repository adapter."""
```

Complex method steps:

- `load()`
  1. `state.group_chat_session = await repository.load_group_chat_session()`
  2. `state.agent_sessions = await repository.load_agent_session_state()`
  3. `state.compact_history = await repository.load_compact_history()`
  4. `state.metadata = await repository.load_group_metadata()`
  5. Return `state`

- `initialize_metadata()`
  1. Convert `group_type` to string with `group_type.value` when it is `GroupChatType`.
  2. Create `GroupMetadata(group_chat_id, group_chat_name, project_path, created_at or datetime.now(), group_type_value)`.
  3. Assign to `state.metadata`.
  4. Call `repository.save_group_metadata(metadata)`.
  5. On exception, set `state.persistence_error = str(e)` and re-raise.
  6. Return metadata.

- `update_agent_session_from_result()`
  1. Read `agent_result.agent_name` and `agent_result.session_id`.
  2. Get or create `AgentSessionInfo` if absent: `get_or_create_agent_session(agent_name)`.
  3. If existing `main_session` is empty, set it to `session_id`.
  4. If `session_id` differs from `main_session` and is not in `btw_session`, append it.
  5. Persist all agent sessions with `save_agent_sessions()`.
  6. Return the updated `AgentSessionInfo`.

- `append_compact_record_and_mark_compacted()`
  1. Require loaded group session.
  2. Append `compact_record` to `state.compact_history`.
  3. Save compact history.
  4. Set `session.last_compacted_loc = len(session.messages)`.
  5. Save group chat session.

## Task 1: Add Runtime State And Runtime Unit Tests

**Files:**
- Create: `agents_hub/core/context/group_chat_runtime_state.py`
- Create: `agents_hub/core/context/group_chat_runtime.py`
- Create: `tests/core/context/conftest.py` (shared test fixtures)
- Modify: `agents_hub/core/context/__init__.py`
- Test: `tests/core/context/test_group_chat_runtime.py`

- [ ] **Step 1: Write failing runtime state tests**

Add this test file:

```python
from datetime import datetime

import pytest

from agents_hub.core.context.group_chat_runtime_state import GroupChatRuntimeState
from agents_hub.core.context.group_chat_session import GroupChatSession
from agents_hub.core.context.group_metadata import GroupMetadata
from agents_hub.core.foundation import StateError


def test_runtime_state_requires_loaded_session():
    state = GroupChatRuntimeState(group_chat_id="gc_1", project_path="/tmp/project")

    with pytest.raises(StateError):
        state.require_session()

    session = GroupChatSession(group_chat_id="gc_1")
    state.group_chat_session = session

    assert state.require_session() is session


def test_runtime_state_requires_metadata():
    state = GroupChatRuntimeState(group_chat_id="gc_1", project_path="/tmp/project")

    with pytest.raises(StateError):
        state.require_metadata()

    metadata = GroupMetadata(
        group_chat_id="gc_1",
        group_chat_name="Test",
        project_path="/tmp/project",
        created_at=datetime(2026, 6, 4, 10, 0, 0),
        group_type="manager_orchestrate",
    )
    state.metadata = metadata

    assert state.require_metadata() is metadata
```

- [ ] **Step 1.5: Extract FakeRepository to shared test fixture**

Create `tests/core/context/conftest.py` with the `FakeRepository` class that will be used across multiple test files:

```python
from datetime import datetime

from agents_hub.core.context.group_chat_session import AgentSessionInfo, GroupChatSession
from agents_hub.core.context.group_metadata import GroupMetadata


class FakeRepository:
    def __init__(self):
        self.group_chat_id = "gc_1"
        self.project_path = "/tmp/project"
        self.saved_metadata = None
        self.saved_sessions = None
        self.saved_group_session = None
        self.saved_compact_history = None
        self.closed = False

    async def load_group_chat_session(self):
        session = GroupChatSession(group_chat_id="gc_1")
        session.messages = [
            {
                "agent_name": "Worker1",
                "content": "hello",
                "timestamp": "2026-06-04T10:00:00",
                "platform": "claude",
            }
        ]
        return session

    async def load_agent_session_state(self):
        return {
            "Worker1": AgentSessionInfo(
                main_session="s1",
                btw_session=["b1"],
                cwd="/tmp/project/w1",
                use_docker=True,
            )
        }

    async def load_compact_history(self):
        return [{"content": {"summary": "old"}}]

    async def load_group_metadata(self):
        return GroupMetadata(
            group_chat_id="gc_1",
            group_chat_name="Test",
            project_path="/tmp/project",
            created_at=datetime(2026, 6, 4, 10, 0, 0),
            group_type="manager_orchestrate",
        )

    async def save_group_metadata(self, metadata):
        self.saved_metadata = metadata

    async def save_agent_session_state(self, state):
        self.saved_sessions = state

    async def save_group_chat_session(self, session):
        self.saved_group_session = session

    async def save_compact_history(self, history):
        self.saved_compact_history = history

    def close(self):
        self.closed = True
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/core/context/test_group_chat_runtime.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `group_chat_runtime_state`.

- [ ] **Step 3: Implement `GroupChatRuntimeState`**

Create `agents_hub/core/context/group_chat_runtime_state.py` using the exact class shown in **Runtime API To Implement**.

- [ ] **Step 4: Export runtime state**

Modify `agents_hub/core/context/__init__.py`:

```python
from .group_chat_runtime_state import GroupChatRuntimeState

__all__ = [
    "GroupChatSession",
    "AgentSessionInfo",
    "AgentContextState",
    "GroupChatRepository",
    "GroupChatContext",
    "AgentContext",
    "GroupMetadata",
    "GroupChatRuntimeState",
]
```

- [ ] **Step 5: Run tests and verify pass**

Run:

```bash
pytest tests/core/context/test_group_chat_runtime.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agents_hub/core/context/group_chat_runtime_state.py agents_hub/core/context/__init__.py tests/core/context/test_group_chat_runtime.py
git commit -m "feat: add group chat runtime state"
```

## Task 2: Implement Runtime Load, Query, And Persistence Commands

**Files:**
- Modify: `agents_hub/core/context/group_chat_runtime.py`
- Modify: `agents_hub/core/context/__init__.py`
- Test: `tests/core/context/test_group_chat_runtime.py`

- [ ] **Step 1: Add failing tests for load and query dicts**

Import `FakeRepository` from conftest:

```python
from datetime import datetime

from tests.core.context.conftest import FakeRepository

from agents_hub.core.context.group_chat_runtime import GroupChatRuntime
from agents_hub.core.context.group_chat_session import AgentSessionInfo
from agents_hub.core.foundation import GroupChatType


async def test_runtime_loads_files_into_memory_and_queries_dicts():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)

    state = await runtime.load()

    assert state.group_chat_session is not None
    assert state.agent_sessions["Worker1"].main_session == "s1"
    assert state.compact_history == [{"content": {"summary": "old"}}]
    assert state.metadata is not None

    info = runtime.get_info_dict(is_active=True)
    assert info["group_chat_id"] == "gc_1"
    assert info["group_chat_name"] == "Test"
    assert info["project_path"] == "/tmp/project"
    assert info["group_type"] == "manager_orchestrate"
    assert info["is_active"] is True

    members = runtime.get_member_dicts()
    assert members == [
        {
            "name": "Worker1",
            "main_session": "s1",
            "btw_session": ["b1"],
            "cwd": "/tmp/project/w1",
            "use_docker": True,
        }
    ]

    messages = runtime.get_message_dicts(limit=10, offset=0)
    assert messages == [
        {
            "speaker": "Worker1",
            "content": "hello",
            "timestamp": "2026-06-04T10:00:00",
            "platform": "claude",
        }
    ]


async def test_get_or_create_agent_session_returns_existing():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    session_info = runtime.get_or_create_agent_session("Worker1")
    assert session_info.main_session == "s1"


async def test_get_or_create_agent_session_creates_new():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    session_info = runtime.get_or_create_agent_session("Worker2")
    assert session_info.main_session is None
    assert session_info.btw_session == []


async def test_get_agent_names_returns_all_names():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    names = runtime.get_agent_names()
    assert names == ["Worker1"]


async def test_runtime_close_closes_repository():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)

    runtime.close()

    assert repository.closed is True
```

- [ ] **Step 2: Add failing command tests**

Import `FakeRepository` from conftest:

```python
from tests.core.context.conftest import FakeRepository


class MockAgentResult:
    def __init__(self, agent_name="Worker1", session_id="s1", text="hello"):
        from agents_hub.config.types import AgentPlatform

        self.agent_name = agent_name
        self.session_id = session_id
        self.text = text
        self.timestamp = "2026-06-04T10:00:00"
        self.platform = AgentPlatform.CLAUDE


async def test_runtime_commands_update_memory_then_persist():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    metadata = await runtime.initialize_metadata(
        group_chat_name="New Name",
        group_type=GroupChatType.MANAGER_ORCHESTRATE,
        created_at=datetime(2026, 6, 4, 11, 0, 0),
    )
    assert runtime.state.metadata is metadata
    assert repository.saved_metadata is metadata

    session_info = await runtime.set_agent_token_and_default_cwd("Worker1", "tok_1")
    assert session_info.token == "tok_1"
    assert session_info.cwd == "/tmp/project/w1"
    assert repository.saved_sessions is runtime.state.agent_sessions

    await runtime.set_agent_use_docker("Worker1", False)
    assert runtime.state.agent_sessions["Worker1"].use_docker is False

    await runtime.update_context_load_state("Worker1", 3, 7)
    context_state = runtime.state.agent_sessions["Worker1"].context_state
    assert context_state.last_loaded_compact_index == 3
    assert context_state.last_loaded_message_index == 7

    await runtime.add_message(MockAgentResult(text="new message"))
    assert runtime.state.group_chat_session.messages[-1]["content"] == "new message"
    assert repository.saved_group_session is runtime.state.group_chat_session

    compact_record = {"create_at": "2026-06-04T12:00:00", "content": {"summary": "sum"}}
    await runtime.append_compact_record_and_mark_compacted(compact_record)
    assert runtime.state.compact_history[-1] == compact_record
    assert repository.saved_compact_history is runtime.state.compact_history
    assert runtime.state.group_chat_session.last_compacted_loc == len(
        runtime.state.group_chat_session.messages
    )


async def test_update_agent_session_handles_empty_main_session():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    # Create new agent with no main_session
    result = MockAgentResult(agent_name="Worker2", session_id="s2")
    session_info = await runtime.update_agent_session_from_result(result)

    assert session_info.main_session == "s2"
    assert session_info.btw_session == []


async def test_update_agent_session_appends_different_session_to_btw():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    # Worker1 already has main_session="s1"
    result = MockAgentResult(agent_name="Worker1", session_id="s2")
    session_info = await runtime.update_agent_session_from_result(result)

    assert session_info.main_session == "s1"
    assert "s2" in session_info.btw_session


async def test_persistence_error_flag_set_on_failure():
    repository = FakeRepository()
    
    # Make save fail
    async def failing_save(metadata):
        raise IOError("Disk full")
    
    repository.save_group_metadata = failing_save
    
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()

    with pytest.raises(IOError):
        await runtime.initialize_metadata("Test", GroupChatType.MANAGER_ORCHESTRATE)
    
    assert runtime.state.persistence_error == "Disk full"


async def test_persistence_error_cleared_on_success():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()
    
    # Set error manually
    runtime.state.persistence_error = "Previous error"
    
    # Successful operation should clear it
    await runtime.initialize_metadata("Test", GroupChatType.MANAGER_ORCHESTRATE)
    
    assert runtime.state.persistence_error is None
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
pytest tests/core/context/test_group_chat_runtime.py -q
```

Expected: FAIL because `GroupChatRuntime` does not exist or methods are empty.

- [ ] **Step 4: Implement `GroupChatRuntime`**

Implement all signatures in **Runtime API To Implement**. Use this constructor body:

```python
def __init__(
    self,
    group_chat_id: str,
    project_path: str,
    repository: GroupChatRepository | None = None,
    state: GroupChatRuntimeState | None = None,
) -> None:
    self.group_chat_id = group_chat_id
    self.repository = repository or GroupChatRepository(group_chat_id, project_path)
    self.state = state or GroupChatRuntimeState(
        group_chat_id=group_chat_id,
        project_path=project_path,
    )
```

Use this persistence helper inside `GroupChatRuntime`:

```python
async def _persist(self, save_call) -> None:
    try:
        await save_call()
        self.state.persistence_error = None
    except Exception as e:
        self.state.persistence_error = str(e)
        raise
```

- [ ] **Step 5: Export runtime**

Modify `agents_hub/core/context/__init__.py`:

```python
from .group_chat_runtime import GroupChatRuntime

__all__ = [
    "GroupChatSession",
    "AgentSessionInfo",
    "AgentContextState",
    "GroupChatRepository",
    "GroupChatRuntimeState",
    "GroupChatRuntime",
    "GroupChatContext",
    "AgentContext",
    "GroupMetadata",
]
```

- [ ] **Step 6: Run tests and verify pass**

Run:

```bash
pytest tests/core/context/test_group_chat_runtime.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add agents_hub/core/context/group_chat_runtime.py agents_hub/core/context/__init__.py tests/core/context/test_group_chat_runtime.py
git commit -m "feat: add group chat runtime facade"
```

## Task 3: Refactor GroupChatContext And AgentContext To Use Runtime

**Files:**
- Modify: `agents_hub/core/context/group_chat_context.py`
- Modify: `agents_hub/core/context/agent_context.py`
- Test: `tests/core/context/test_group_chat_context.py`
- Test: `tests/core/context/test_group_chat_runtime.py`

- [ ] **Step 1: Add failing context compatibility test**

Import `FakeRepository` from conftest:

```python
from tests.core.context.conftest import FakeRepository

from agents_hub.core.context.group_chat_context import GroupChatContext
from agents_hub.core.context.agent_context import AgentContext


async def test_group_chat_context_uses_runtime_for_message_and_session_commands():
    repository = FakeRepository()
    runtime = GroupChatRuntime("gc_1", "/tmp/project", repository=repository)
    await runtime.load()
    context = GroupChatContext(runtime)

    result = MockAgentResult(agent_name="Worker2", session_id="s2", text="hello from w2")
    await context.update_agent_session_id(result)
    await context.add_message(result)

    assert runtime.state.agent_sessions["Worker2"].main_session == "s2"
    assert runtime.state.group_chat_session.messages[-1]["agent_name"] == "Worker2"
    assert repository.saved_sessions is runtime.state.agent_sessions
    assert repository.saved_group_session is runtime.state.group_chat_session
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/core/context/test_group_chat_runtime.py::test_group_chat_context_uses_runtime_for_message_and_session_commands -q
```

Expected: FAIL because `GroupChatContext` still expects `(group_chat_id, project_path)`.

- [ ] **Step 3: Change `GroupChatContext.__init__` signature**

Replace constructor with:

```python
def __init__(self, runtime: GroupChatRuntime):
    self.runtime = runtime
    self.group_chat_id = runtime.group_chat_id
```

Add compatibility properties:

```python
@property
def group_chat_session(self) -> GroupChatSession | None:
    return self.runtime.state.group_chat_session

@property
def agent_sessions(self) -> dict[str, AgentSessionInfo]:
    """Preferred accessor - returns agent sessions from runtime state."""
    return self.runtime.state.agent_sessions

@property
def agent_session_id(self) -> dict[str, AgentSessionInfo]:
    """Backward compatibility alias for agent_sessions."""
    return self.runtime.state.agent_sessions

def get_project_path(self) -> str:
    return self.runtime.get_project_path()
```

**Note:** Keep both `agent_sessions` and `agent_session_id` during migration. In Task 8, search for all usages of `agent_session_id` and verify backward compatibility.

Replace `load()`:

```python
async def load(self):
    await self.runtime.load()
```

- [ ] **Step 4: Replace context persistence calls**

Use these method bodies:

```python
async def add_message(self, agent_result):
    await self.runtime.add_message(agent_result)


async def update_agent_session_id(self, agent_result):
    await self.runtime.update_agent_session_from_result(agent_result)


async def load_compact_history(self) -> list[dict]:
    return await self.runtime.load_compact_history()
```

In `compact_messages()`, replace repository load/save at the end with:

```python
await self.runtime.append_compact_record_and_mark_compacted(compact_record)
```

Replace `close()` with:

```python
def close(self):
    self.runtime.close()
```

- [ ] **Step 5: Update `AgentContext._update_agent_context_state`**

Replace final save block with:

```python
await self.group_chat_context.runtime.update_context_load_state(
    self.agent_name,
    last_loaded_compact_index,
    last_loaded_message_index,
)
```

- [ ] **Step 6: Run context tests**

Run:

```bash
pytest tests/core/context/test_group_chat_runtime.py tests/core/context/test_group_chat_context.py -q
```

Expected: existing `test_group_chat_context.py` may fail where it constructs `GroupChatContext(group_chat_id, tmpdir)`. Update those tests in Step 7.

- [ ] **Step 7: Update old context tests to construct runtime**

In `tests/core/context/test_group_chat_context.py`, replace:

```python
context = GroupChatContext(group_chat_id, tmpdir)
```

with:

```python
runtime = GroupChatRuntime(group_chat_id, tmpdir)
context = GroupChatContext(runtime)
```

When tests access `context.repository.session_file`, replace with:

```python
session_file = runtime.repository.session_file
```

- [ ] **Step 8: Run tests and verify pass**

Run:

```bash
pytest tests/core/context/test_group_chat_runtime.py tests/core/context/test_group_chat_context.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add agents_hub/core/context/group_chat_context.py agents_hub/core/context/agent_context.py tests/core/context/test_group_chat_runtime.py tests/core/context/test_group_chat_context.py
git commit -m "refactor: route context persistence through runtime"
```

## Task 4: Wire Runtime Into GroupChat Lifecycle

**Files:**
- Modify: `agents_hub/core/orchestration/group_chat.py`
- Test: `tests/core/orchestration/test_group_chat.py`
- Test: `tests/core/orchestration/test_group_chat_metadata.py`

- [ ] **Step 1: Add failing lifecycle assertion**

In `tests/core/orchestration/test_group_chat_metadata.py`, add:

```python
@pytest.mark.asyncio
async def test_group_chat_exposes_runtime_metadata_after_start(monkeypatch, tmp_path):
    from agents_hub.core.orchestration import GroupChat
    from agents_hub.core.orchestration.team import Team

    team = Team.model_construct(team_members_name=["Leader"])
    group_chat = GroupChat(
        team=team,
        group_type=GroupChatType.MANAGER_ORCHESTRATE,
        project_path=str(tmp_path),
        group_chat_id="gc_runtime_metadata",
        group_chat_name="Runtime Metadata",
    )

    async def fake_init_agents():
        group_chat.manager = None
        group_chat.workers = {}

    async def fake_generate_tokens():
        return None

    async def fake_initialize_members():
        return None

    monkeypatch.setattr(group_chat, "_init_agents", fake_init_agents)
    monkeypatch.setattr(group_chat, "_generate_and_register_tokens", fake_generate_tokens)
    monkeypatch.setattr(group_chat, "_initialize_new_members", fake_initialize_members)
    monkeypatch.setattr(group_chat, "_start_agent_tasks", lambda: None)

    await group_chat.start()

    info = group_chat.runtime.get_info_dict(is_active=True)
    assert info["group_chat_id"] == "gc_runtime_metadata"
    assert info["group_chat_name"] == "Runtime Metadata"
    assert info["project_path"] == str(tmp_path)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/core/orchestration/test_group_chat_metadata.py::test_group_chat_exposes_runtime_metadata_after_start -q
```

Expected: FAIL because `GroupChat.runtime` does not exist.

- [ ] **Step 3: Modify `GroupChat.__init__`**

Use this dependency setup:

```python
self.runtime = GroupChatRuntime(group_chat_id, project_path)
self.group_chat_context = GroupChatContext(self.runtime)
self.message_router = MessageRouter()
self.agent_call_manager = AgentCallManager(self.group_chat_id, project_path)
self.task_manager = TaskManager(self.group_chat_id, project_path)
```

- [ ] **Step 4: Modify `GroupChat.start()`**

Replace metadata creation/save block with:

```python
await self.group_chat_context.load()
await self.runtime.initialize_metadata(
    group_chat_name=self.group_chat_name,
    group_type=self.group_type,
)
```

Keep `_init_agents()`, `_generate_and_register_tokens()`, `_initialize_new_members()`, `_start_agent_tasks()` in the existing order.

- [ ] **Step 5: Modify token generation and restore**

In `_generate_and_register_tokens()`, replace metadata and direct session mutation with:

```python
default_cwd = self.runtime.get_project_path()
session_info = await self.runtime.set_agent_token_and_default_cwd(
    agent_name,
    token,
    default_cwd=default_cwd,
)
```

Apply this for manager and each worker.

In the lifecycle load path (when restoring from disk), use:

```python
session_info = self.runtime.get_agent_session(agent_name)
if session_info and session_info.token:
    group_chat_manager.register_token(session_info.token, agent_name, self.group_chat_id)
else:
    token = generate_token()
    group_chat_manager.register_token(token, agent_name, self.group_chat_id)
    await self.runtime.set_agent_token_and_default_cwd(agent_name, token)
```

**Note:** The term `_restore_and_register_tokens()` refers to the token restoration logic within the `load()` or `start()` method when loading an existing group chat from disk, not a standalone method name.

- [ ] **Step 6: Remove direct repository access in `GroupChat`**

Run:

```bash
rg -n "group_chat_context\.repository(?!\.)|\.repository\." agents_hub/core/orchestration/group_chat.py
```

Expected after edits: no matches except in comments or when accessing `runtime.repository` for file verification in tests.

**Note:** Improved regex to avoid false positives in comments and strings.

- [ ] **Step 7: Run orchestration tests**

Run:

```bash
pytest tests/core/orchestration/test_group_chat.py tests/core/orchestration/test_group_chat_metadata.py -q
```

Expected: PASS after updating tests that read metadata via `group_chat.group_chat_context.repository` to `group_chat.runtime.get_metadata()` or `group_chat.runtime.repository` when verifying files.

- [ ] **Step 8: Commit**

```bash
git add agents_hub/core/orchestration/group_chat.py tests/core/orchestration/test_group_chat.py tests/core/orchestration/test_group_chat_metadata.py
git commit -m "refactor: wire runtime into group chat lifecycle"
```

## Task 5: Replace Agent Repository Access With Runtime Accessors

**Files:**
- Modify: `agents_hub/core/agent/base_agent.py`
- Test: `tests/core/agent/test_agent_runtime_injection.py`
- Test: `tests/utils/core/agent/test_agent_docker_config.py`

- [ ] **Step 0: Search for all repository.project_path accesses**

Run:

```bash
rg -n "repository\.project_path" agents_hub/core/agent/
```

List all locations that need to be updated to use `context.get_project_path()` instead.

- [ ] **Step 1: Add or update Docker validation test**

In the Docker config test file, ensure the mock context has `get_project_path()`:

```python
context.get_project_path.return_value = "/workspace/main"
context.agent_session_id = {
    "Worker1": AgentSessionInfo(cwd="/workspace/main", use_docker=True)
}
```

Expected assertion:

```python
with pytest.raises(DockerConfigError):
    agent._validate_docker_config()
```

- [ ] **Step 2: Modify `Agent._validate_docker_config()`**

Replace:

```python
group_chat_path = self.group_chat_context.repository.project_path
```

with:

```python
group_chat_path = self.group_chat_context.get_project_path()
```

- [ ] **Step 3: Run agent tests**

Run:

```bash
pytest tests/core/agent/test_agent_runtime_injection.py tests/utils/core/agent/test_agent_docker_config.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add agents_hub/core/agent/base_agent.py tests/core/agent/test_agent_runtime_injection.py tests/utils/core/agent/test_agent_docker_config.py
git commit -m "refactor: remove agent repository path access"
```

## Task 6: Update GroupChatManager Catalog And Load Paths

**Files:**
- Modify: `agents_hub/core/orchestration/group_chat_manager.py`
- Test: `tests/core/orchestration/test_group_chat_manager_enhanced.py`

- [ ] **Step 1: Add active runtime info helper test**

In `tests/core/orchestration/test_group_chat_manager_enhanced.py`, add:

```python
from unittest.mock import Mock


def test_get_active_group_info_uses_runtime_query(group_chat_manager):
    mock_runtime = Mock()
    mock_runtime.get_info_dict.return_value = {
        "group_chat_id": "gc-001",
        "group_chat_name": "测试群聊",
        "project_path": "/project1",
        "created_at": datetime(2026, 6, 1, 10, 0, 0),
        "group_type": "manager_orchestrate",
        "is_active": True,
    }
    mock_group_chat = Mock()
    mock_group_chat._activated = True
    mock_group_chat.runtime = mock_runtime
    group_chat_manager._group_chats["gc-001"] = mock_group_chat

    result = group_chat_manager.get_active_group_info("gc-001")

    assert result["group_chat_id"] == "gc-001"
    assert result["is_active"] is True
    mock_runtime.get_info_dict.assert_called_once_with(is_active=True)
```

Also add:

```python
def test_get_active_group_info_returns_none_for_inactive_registry_miss(group_chat_manager):
    assert group_chat_manager.get_active_group_info("missing") is None
```

- [ ] **Step 2: Update `load_group_chat_from_disk()` team member loading**

Keep file read for inactive loading because no runtime object exists yet. After constructing `GroupChat` and calling `await group_chat.load()`, use `group_chat.runtime` for any later in-memory state reads.

Do not introduce direct `GroupChatRepository` use in manager beyond existing file scan helpers.

- [ ] **Step 3: Add manager helper for active group info**

Add:

```python
def get_active_group_info(self, group_chat_id: str) -> dict[str, object] | None:
    group_chat = self._group_chats.get(group_chat_id)
    if group_chat is None:
        return None
    return group_chat.runtime.get_info_dict(is_active=self.is_active_group(group_chat_id))
```

- [ ] **Step 4: Run manager tests**

Run:

```bash
pytest tests/core/orchestration/test_group_chat_manager_enhanced.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents_hub/core/orchestration/group_chat_manager.py tests/core/orchestration/test_group_chat_manager_enhanced.py
git commit -m "refactor: expose group chat runtime info through manager"
```

## Task 7: Update GroupChatService To Use Core Runtime Queries And Commands

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py`
- Test: `tests/api/services/test_group_chat_service.py`
- Test: `tests/api/services/test_toggle_use_docker.py`

- [ ] **Step 2: Update service helper signatures**

Replace `_build_group_chat_info_from_instance()` body with:

```python
async def _build_group_chat_info_from_instance(self, group_chat: GroupChat) -> GroupChatInfo:
    info = group_chat.runtime.get_info_dict(is_active=group_chat._activated)
    return GroupChatInfo(**info)
```

- [ ] **Step 3: Replace `get_group_chat_info()`**

Use:

```python
group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
info = group_chat.runtime.get_info_dict(
    is_active=self.group_chat_manager.is_active_group(group_chat_id)
)
return GroupChatInfo(**info)
```

- [ ] **Step 4: Replace `get_group_chat_members()`**

Use active runtime state instead of raw `agent_session_state.json` reads:

```python
try:
    group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
except GroupChatNotFoundError as e:
    raise ResourceNotFoundError(
        f"群聊不存在: {group_chat_id}",
        details={"group_chat_id": group_chat_id},
    ) from e

return [GroupChatMember(**member) for member in group_chat.runtime.get_member_dicts()]
```

Remove imports no longer needed: `json`, `GroupMetadata` if unused.

- [ ] **Step 5: Replace `get_messages()`**

Use:

```python
group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
return [
    MessageInfo(**message)
    for message in group_chat.runtime.get_message_dicts(limit=limit, offset=offset)
]
```

- [ ] **Step 6: Replace `delete_group_chat()` project path lookup**

Use active runtime when present:

```python
group_chat = self.group_chat_manager._group_chats.get(group_chat_id)
if group_chat:
    project_path = group_chat.runtime.get_project_path()
else:
    all_chats = self.group_chat_manager.list_all_group_chats()
    for metadata_dict in all_chats:
        if metadata_dict["group_chat_id"] == group_chat_id:
            project_path = metadata_dict["project_path"]
            break
```

This task still uses manager internals for `_group_chats` because the current service already does. A later cleanup can add a manager method for delete target lookup.

- [ ] **Step 7: Clarify `send_message()` handling**

**Analysis:** The `send_message()` method in `group_chat_service.py` already delegates to `MessageRouter` and `AgentCallManager`, which are lifecycle-managed components. This service method does NOT directly access `context.repository` or perform state mutations beyond routing.

**Action:** Verify that `send_message()` does not contain any direct `context.repository` access by searching:

```bash
rg -n "repository" agents_hub/api/services/group_chat_service.py
```

If no repository access exists in `send_message()`, no changes are needed. If found, replace with appropriate runtime query/command.

- [ ] **Step 8: Replace `toggle_use_docker()` session mutation**

After validation and Docker checks:

```python
updated_info = await group_chat.runtime.set_agent_use_docker(role_name, use_docker)
return GroupChatMember(
    name=role_name,
    main_session=updated_info.main_session or None,
    btw_session=updated_info.btw_session,
    cwd=updated_info.cwd or None,
    use_docker=updated_info.use_docker,
)
```

- [ ] **Step 9: Update service tests to mock runtime**

Replace mocks like:

```python
mock_group_chat.group_chat_context.repository.load_group_metadata = AsyncMock(
    return_value=Mock(
        group_chat_id=group_chat_id,
        group_chat_name="Test Group",
        project_path="/path/to/project",
        created_at=datetime(2026, 6, 3, 10, 0, 0),
        group_type="manager_orchestrate",
    )
)
```

with:

```python
mock_group_chat.runtime.get_info_dict.return_value = {
    "group_chat_id": group_chat_id,
    "group_chat_name": "Test Group",
    "project_path": "/path/to/project",
    "created_at": datetime(2026, 6, 3, 10, 0, 0),
    "group_type": "manager_orchestrate",
    "is_active": True,
}
```

For members:

```python
mock_group_chat.runtime.get_member_dicts.return_value = [
    {
        "name": "Leader",
        "main_session": "session_123",
        "btw_session": ["btw_1"],
        "cwd": "/path/to/project",
        "use_docker": False,
    }
]
```

For Docker command:

```python
mock_group_chat.runtime.set_agent_use_docker = AsyncMock(
    return_value=AgentSessionInfo(main_session="s1", cwd="/path", use_docker=True)
)
```

- [ ] **Step 10: Run API service tests**

Run:

```bash
pytest tests/api/services/test_group_chat_service.py tests/api/services/test_toggle_use_docker.py -q
```

Expected: PASS.

- [ ] **Step 11: Commit**

```bash
git add agents_hub/api/services/group_chat_service.py tests/api/services/test_group_chat_service.py tests/api/services/test_toggle_use_docker.py
git commit -m "refactor: use runtime queries in group chat service"
```

## Task 8: Add Guard Checks And Full Regression

**Files:**
- Modify tests only if guard exposes old assumptions.

- [ ] **Step 1: Check forbidden repository penetrations**

Run:

```bash
rg -n "group_chat_context\\.repository|context\\.repository|\\.repository\\.load_group_metadata|\\.repository\\.save_agent_session_state" agents_hub/core agents_hub/api/services
```

Expected remaining matches:

```text
agents_hub/core/context/group_chat_runtime.py
```

If matches remain in `agents_hub/api/services`, `agents_hub/core/agent`, or `agents_hub/core/orchestration/group_chat.py`, replace them with runtime query/command calls before continuing.

- [ ] **Step 2: Run focused test suites**

Run:

```bash
pytest tests/core/context tests/core/orchestration tests/core/agent -q
```

Expected: PASS.

- [ ] **Step 3: Run API service layer tests**

Run:

```bash
pytest tests/api/services/test_group_chat_service.py -q
```

Expected: PASS.

- [ ] **Step 4: Run broader regression**

Run:

```bash
pytest tests/core tests/api -q
```

Expected: PASS. If unrelated failures appear, record exact failing tests and decide whether they are caused by runtime changes before editing.

- [ ] **Step 5: Verify backward compatibility of agent_session_id**

Search for all usages of `context.agent_session_id` and verify they work with the compatibility property:

```bash
rg -n "\.agent_session_id" agents_hub/ tests/
```

For each usage, confirm it accesses the dict correctly. If any code expects `agent_session_id` to be a different type, update that code.

- [ ] **Step 6: Update docs if implementation changes accepted contracts**

If final code changes core public behavior beyond this plan, update:

```text
docs/superpowers/specs/2026-06-04-core-runtime-ssot-design.md
docs/specs/2026-05-31-core-context.md
docs/specs/2026-05-31-core-agent-orchestration.md
```

Only update formal specs after reading `docs/docs-rules/spec-write-rules.md`.

- [ ] **Step 7: Commit**

```bash
git add agents_hub tests docs
git commit -m "test: verify core runtime ssot migration"
```

## Self-Review Notes

Spec coverage:

1. Memory SSOT is covered by `GroupChatRuntimeState` and runtime query methods.
2. Synchronous persistence is covered by runtime command methods and persistence matrix.
3. `GroupChat` lifecycle-only direction is covered by Task 4.
4. Repository ownership moves out of Context in Task 3.
5. API/service query boundary is covered by Task 7.
6. Current service-required interfaces are listed at the top and mapped to runtime methods.

Known scope limits:

1. `AgentCallManager` and `TaskManager` remain manager-owned state in this plan.
2. Inactive group catalog scan still reads files because no runtime object exists for inactive groups.
3. This plan does not introduce WAL, event sourcing, async snapshots, or cross-process runtime synchronization.

## Revision History (v1.1)

Based on comprehensive code review, the following improvements were made:

### 必须修复的问题（已解决）

1. **Task 7 缺少 `send_message()` 处理说明** - 已在 Step 7 中明确说明该方法的验证流程
2. **Token 恢复逻辑位置不明** - 已在 Task 4 Step 5 中澄清这是 `start()`/`load()` 中的逻辑，不是独立方法

### 建议修复的问题（已解决）

1. **测试覆盖补充**：
   - 增加 `update_agent_session_from_result()` 边界情况测试（空 main_session、追加到 btw_session）
   - 增加 `get_or_create_agent_session()` 测试
   - 增加 `get_agent_names()` 测试
   - 增加 `close()` 方法测试
   - 增加持久化失败后的 error flag 测试

2. **实现细节明确**：
   - `get_message_dicts()` 增加实现说明（分页、字段映射）
   - `update_agent_session_from_result()` 明确使用 `get_or_create_agent_session()`
   - 持久化失败处理机制说明增强（guard checks）

3. **代码组织优化**：
   - 提取 `FakeRepository` 到 `tests/core/context/conftest.py` 作为共享 fixture
   - Task 5 增加预检步骤搜索所有 `repository.project_path` 访问

4. **术语统一**：统一使用 "Repository" 而非混用 "Store"

5. **向后兼容性**：
   - `GroupChatContext` 同时提供 `agent_sessions` 和 `agent_session_id` 属性
   - Task 8 增加向后兼容性验证步骤

### 文档改进

1. 移除重复的版本表格
2. 改进搜索命令的准确性（避免误报）
3. 优化测试执行策略（分层回归测试）
4. 明确 `send_message()` 不需要修改（已经通过 MessageRouter 委托）

所有修复确保实现计划更加完整、准确、可执行。
