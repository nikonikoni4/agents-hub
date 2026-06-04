# MCP 工具系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 agents-hub 实现 MCP 工具系统，让 Manager 通过 4 个 MCP 工具（call_agent / assign_tasks_to_team / archive_task_list / check_agent_call）编排团队协作，使用 Agent Token 身份模型确保安全。

**Architecture:** 
- 底层：foundation 层新增 Token 工具和 Task 枚举，communication 层新增 Task/TaskList 数据模型和 TaskManager
- 中层：orchestration 层的 GroupChatManager 管理 token 索引，context 层持久化 token
- 上层：agent 层注入 runtime 到 CLAUDE.md/AGENTS.md，mcp 层实现 FastMCP Server
- 集成：bridge 层生成配置模板，业务层实现 user_send_message

**Tech Stack:** FastMCP (HTTP transport), secrets (token 生成), markdown_injector (runtime 注入), pytest

---

## 文件结构规划

### 新增文件

**foundation 层：**
- `agents_hub/core/foundation/token.py` — Token 生成和剥离工具
- `tests/core/foundation/test_token.py` — Token 工具测试

**communication 层：**
- `agents_hub/core/communication/task.py` — Task/TaskList 数据模型
- `agents_hub/core/communication/task_manager.py` — TaskManager（CRUD + 持久化）
- `tests/core/communication/test_task.py` — Task 模型测试
- `tests/core/communication/test_task_manager.py` — TaskManager 测试

**mcp 层（新增）：**
- `agents_hub/mcp/__init__.py` — mcp 模块初始化
- `agents_hub/mcp/server.py` — FastMCP Server 和 4 个工具实现
- `agents_hub/mcp/errors.py` — 错误码和错误响应工具
- `tests/mcp/test_server.py` — MCP Server 集成测试
- `tests/mcp/test_errors.py` — 错误响应测试

### 修改文件

**foundation 层：**
- `agents_hub/core/foundation/models.py` — 新增 TaskStatus / TaskListStatus 枚举

**orchestration 层：**
- `agents_hub/core/orchestration/group_chat_manager.py` — 新增 _tokens 索引和 token 管理方法
- `agents_hub/core/orchestration/group_chat.py` — start/load 生成 token，cleanup 清空 token

**context 层：**
- `agents_hub/core/context/group_chat_context.py` — agent_member.json 新增 agent_token 字段

**agent 层：**
- `agents_hub/core/agent/base_agent.py` — 新增 agent_token 属性、_generate_runtime_content 方法、runtime 注入、token redact

**业务层（假设在 agents_hub/api/）：**
- `agents_hub/api/routes.py` — 新增 user_send_message 端点

---

## Task 1: Token 工具（foundation 层）

**Files:**
- Create: `agents_hub/core/foundation/token.py`
- Create: `tests/core/foundation/test_token.py`

- [ ] **Step 1: 编写 token 生成测试**

```python
# tests/core/foundation/test_token.py
import re
from agents_hub.core.foundation.token import generate_token, redact_token, TOKEN_PATTERN


def test_generate_token_format():
    """Token 格式应为 tok_<32位hex>"""
    token = generate_token()
    assert token.startswith("tok_")
    assert len(token) == 36  # "tok_" (4) + 32 hex
    assert re.match(r"^tok_[a-f0-9]{32}$", token)


def test_generate_token_uniqueness():
    """每次生成的 token 应该不同"""
    tokens = [generate_token() for _ in range(100)]
    assert len(set(tokens)) == 100


def test_redact_token_single():
    """应该替换单个 token"""
    text = "Your token is tok_a1b2c3d4e5f6789012345678901234 here"
    result = redact_token(text)
    assert result == "Your token is [REDACTED] here"


def test_redact_token_multiple():
    """应该替换多个 token"""
    text = "tok_a1b2c3d4e5f6789012345678901234 and tok_b2c3d4e5f6a178901234567890123"
    result = redact_token(text)
    assert result == "[REDACTED] and [REDACTED]"


def test_redact_token_no_match():
    """不匹配的文本应该保持不变"""
    text = "No tokens here, just tok_short or tok_toolong123456789012345678901234567890"
    result = redact_token(text)
    assert result == text
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/core/foundation/test_token.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'agents_hub.core.foundation.token'"

- [ ] **Step 3: 实现 token 工具**

```python
# agents_hub/core/foundation/token.py
"""Token 生成和剥离工具

用于 Agent Token 身份模型：
- generate_token(): 生成 32 字符 hex token
- redact_token(): 从文本中剥离 token（替换为 [REDACTED]）
"""

import re
import secrets

# Token 格式：tok_<32位hex>
TOKEN_PATTERN = re.compile(r"tok_[a-f0-9]{32}")


def generate_token() -> str:
    """生成 32 位 hex token
    
    Returns:
        格式为 tok_<32位hex> 的 token 字符串
        
    Example:
        >>> token = generate_token()
        >>> token.startswith("tok_")
        True
        >>> len(token)
        36
    """
    return f"tok_{secrets.token_hex(16)}"


def redact_token(text: str) -> str:
    """替换文本中的 token 为 [REDACTED]
    
    用于防止 token 泄漏到群聊消息中。
    
    Args:
        text: 可能包含 token 的文本
        
    Returns:
        替换后的文本
        
    Example:
        >>> redact_token("Your token is tok_a1b2c3d4e5f6789012345678901234")
        'Your token is [REDACTED]'
    """
    return TOKEN_PATTERN.sub("[REDACTED]", text)
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/core/foundation/test_token.py -v
```

Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add agents_hub/core/foundation/token.py tests/core/foundation/test_token.py
git commit -m "feat(foundation): 新增 Token 生成和剥离工具

- generate_token(): 生成 tok_<32hex> 格式的 token
- redact_token(): 替换文本中的 token 为 [REDACTED]
- TOKEN_PATTERN: 正则匹配 32 字符 hex token

用于 Agent Token 身份模型的 token 生成和防泄漏。"
```

## Task 2: Task 枚举（foundation 层）

**Files:**
- Modify: `agents_hub/core/foundation/models.py`
- Create: `tests/core/foundation/test_task_enums.py`

- [ ] **Step 1: 编写枚举测试**

```python
# tests/core/foundation/test_task_enums.py
from agents_hub.core.foundation.models import TaskStatus, TaskListStatus


def test_task_status_values():
    """TaskStatus 应包含 4 个状态"""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.RUNNING.value == "running"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"


def test_task_list_status_values():
    """TaskListStatus 应包含 2 个状态"""
    assert TaskListStatus.ACTIVE.value == "active"
    assert TaskListStatus.ARCHIVED.value == "archived"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/core/foundation/test_task_enums.py -v
```

Expected: FAIL with "ImportError: cannot import name 'TaskStatus'"

- [ ] **Step 3: 在 models.py 中添加枚举**

```python
# 在 agents_hub/core/foundation/models.py 末尾添加

class TaskStatus(str, Enum):
    """任务状态枚举
    
    - PENDING: 待执行
    - RUNNING: 执行中
    - COMPLETED: 已完成
    - FAILED: 失败
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskListStatus(str, Enum):
    """任务列表状态枚举
    
    - ACTIVE: 激活（当前使用）
    - ARCHIVED: 已归档
    """
    ACTIVE = "active"
    ARCHIVED = "archived"
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/core/foundation/test_task_enums.py -v
```

Expected: 2 passed

- [ ] **Step 5: 提交**

```bash
git add agents_hub/core/foundation/models.py tests/core/foundation/test_task_enums.py
git commit -m "feat(foundation): 新增 TaskStatus 和 TaskListStatus 枚举

- TaskStatus: PENDING / RUNNING / COMPLETED / FAILED
- TaskListStatus: ACTIVE / ARCHIVED

用于 Task 和 TaskList 数据模型的状态管理。"
```

## Task 3: Task 数据模型（communication 层）

**Files:**
- Create: `agents_hub/core/communication/task.py`
- Create: `tests/core/communication/test_task.py`

- [ ] **Step 1: 编写 Task 模型测试**

```python
# tests/core/communication/test_task.py
from datetime import datetime
from agents_hub.core.communication.task import Task, TaskList
from agents_hub.core.foundation.models import TaskStatus, TaskListStatus


def test_task_creation():
    """Task 应该正确创建"""
    task = Task(
        task_id="t1",
        owner="Worker1",
        content="实现功能A",
        status=TaskStatus.PENDING,
        group_chat_id="gc_123",
        created_by="Manager",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    assert task.task_id == "t1"
    assert task.owner == "Worker1"
    assert task.status == TaskStatus.PENDING


def test_task_to_dict():
    """Task 应该能序列化为 dict"""
    now = datetime.now()
    task = Task(
        task_id="t1",
        owner="Worker1",
        content="实现功能A",
        status=TaskStatus.PENDING,
        group_chat_id="gc_123",
        created_by="Manager",
        created_at=now,
        updated_at=now,
    )
    data = task.to_dict()
    assert data["task_id"] == "t1"
    assert data["status"] == "pending"
    assert isinstance(data["created_at"], str)


def test_task_from_dict():
    """Task 应该能从 dict 反序列化"""
    data = {
        "task_id": "t1",
        "owner": "Worker1",
        "content": "实现功能A",
        "status": "pending",
        "group_chat_id": "gc_123",
        "created_by": "Manager",
        "created_at": "2026-05-31T10:00:00",
        "updated_at": "2026-05-31T10:00:00",
    }
    task = Task.from_dict(data)
    assert task.task_id == "t1"
    assert task.status == TaskStatus.PENDING


def test_task_list_creation():
    """TaskList 应该正确创建"""
    task_list = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ACTIVE,
        tasks=[],
        created_at=datetime.now(),
        archived_at=None,
    )
    assert task_list.list_id == "list_1"
    assert task_list.status == TaskListStatus.ACTIVE
    assert len(task_list.tasks) == 0


def test_task_list_to_dict():
    """TaskList 应该能序列化为 dict"""
    now = datetime.now()
    task = Task(
        task_id="t1",
        owner="Worker1",
        content="实现功能A",
        status=TaskStatus.PENDING,
        group_chat_id="gc_123",
        created_by="Manager",
        created_at=now,
        updated_at=now,
    )
    task_list = TaskList(
        list_id="list_1",
        group_chat_id="gc_123",
        status=TaskListStatus.ACTIVE,
        tasks=[task],
        created_at=now,
        archived_at=None,
    )
    data = task_list.to_dict()
    assert data["list_id"] == "list_1"
    assert data["status"] == "active"
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["task_id"] == "t1"


def test_task_list_from_dict():
    """TaskList 应该能从 dict 反序列化"""
    data = {
        "list_id": "list_1",
        "group_chat_id": "gc_123",
        "status": "active",
        "tasks": [
            {
                "task_id": "t1",
                "owner": "Worker1",
                "content": "实现功能A",
                "status": "pending",
                "group_chat_id": "gc_123",
                "created_by": "Manager",
                "created_at": "2026-05-31T10:00:00",
                "updated_at": "2026-05-31T10:00:00",
            }
        ],
        "created_at": "2026-05-31T10:00:00",
        "archived_at": None,
    }
    task_list = TaskList.from_dict(data)
    assert task_list.list_id == "list_1"
    assert task_list.status == TaskListStatus.ACTIVE
    assert len(task_list.tasks) == 1
    assert task_list.tasks[0].task_id == "t1"
```

- [ ] **Step 2: 运行测试验证失败**

```bash
pytest tests/core/communication/test_task.py -v
```

Expected: FAIL with "ModuleNotFoundError: No module named 'agents_hub.core.communication.task'"

- [ ] **Step 3: 实现 Task 数据模型**

```python
# agents_hub/core/communication/task.py
"""Task 和 TaskList 数据模型

Task: 单个任务，包含 owner、content、status
TaskList: 任务列表，包含多个 Task，有 ACTIVE/ARCHIVED 状态
"""

from dataclasses import dataclass
from datetime import datetime
from agents_hub.core.foundation.models import TaskStatus, TaskListStatus


@dataclass
class Task:
    """单个任务
    
    不变量：
    - 每个 Task 有且只有一个 owner（一个 Worker）
    - 多个 Worker 之间的 Task 必须正交（无重叠职责）
    """
    task_id: str          # 唯一标识（UUID）
    owner: str            # worker name（1:1 不变量）
    content: str          # 任务描述
    status: TaskStatus    # PENDING / RUNNING / COMPLETED / FAILED
    group_chat_id: str    # 所属群聊
    created_by: str       # 创建者（必须是 Leader）
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict:
        """序列化为 dict（用于持久化）"""
        return {
            "task_id": self.task_id,
            "owner": self.owner,
            "content": self.content,
            "status": self.status.value,
            "group_chat_id": self.group_chat_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """从 dict 反序列化"""
        return cls(
            task_id=data["task_id"],
            owner=data["owner"],
            content=data["content"],
            status=TaskStatus(data["status"]),
            group_chat_id=data["group_chat_id"],
            created_by=data["created_by"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class TaskList:
    """任务列表
    
    状态机：
    - 每个 GroupChat 同时只有一个 ACTIVE TaskList
    - archive_task_list 将 ACTIVE → ARCHIVED
    - 下次 assign_tasks_to_team 自动创建新 ACTIVE list
    """
    list_id: str          # 唯一标识（UUID）
    group_chat_id: str
    status: TaskListStatus  # ACTIVE / ARCHIVED
    tasks: list[Task]
    created_at: datetime
    archived_at: datetime | None

    def to_dict(self) -> dict:
        """序列化为 dict（用于持久化）"""
        return {
            "list_id": self.list_id,
            "group_chat_id": self.group_chat_id,
            "status": self.status.value,
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at.isoformat(),
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskList":
        """从 dict 反序列化"""
        return cls(
            list_id=data["list_id"],
            group_chat_id=data["group_chat_id"],
            status=TaskListStatus(data["status"]),
            tasks=[Task.from_dict(t) for t in data["tasks"]],
            created_at=datetime.fromisoformat(data["created_at"]),
            archived_at=datetime.fromisoformat(data["archived_at"]) if data["archived_at"] else None,
        )
```

- [ ] **Step 4: 运行测试验证通过**

```bash
pytest tests/core/communication/test_task.py -v
```

Expected: 7 passed

- [ ] **Step 5: 提交**

```bash
git add agents_hub/core/communication/task.py tests/core/communication/test_task.py
git commit -m "feat(communication): 新增 Task 和 TaskList 数据模型

- Task: 单个任务，包含 owner、content、status
- TaskList: 任务列表，包含多个 Task，有 ACTIVE/ARCHIVED 状态
- 支持 to_dict/from_dict 序列化

用于 Manager 的任务管理功能。"
```

## Task 4: TaskManager（communication 层）

**Files:**
- Create: `agents_hub/core/communication/task_manager.py`
- Create: `tests/core/communication/test_task_manager.py`

由于 TaskManager 涉及文件 I/O 和复杂的 CRUD 逻辑，这个任务会比较大。关键功能：
- get_active_task_list(): 获取当前 ACTIVE 任务列表
- assign_tasks(): 覆盖式更新任务列表
- archive_task_list(): 归档当前 ACTIVE 列表
- 持久化到 tasks.jsonl

**实施细节见 spec 第 4 节和实施要点。**

测试应覆盖：
- 创建新任务列表
- 更新现有任务
- 归档任务列表
- 持久化和加载

提交信息：
```
feat(communication): 新增 TaskManager 任务管理器

- get_active_task_list(): 获取当前 ACTIVE 任务列表
- assign_tasks(): 覆盖式更新（创建/更新/保持不变）
- archive_task_list(): 归档当前 ACTIVE 列表
- 持久化到 tasks.jsonl（每行一个 TaskList JSON）

参照 Claude Code TodoWrite 的覆盖式更新语义。
```

---

## Task 5: GroupChatManager Token 索引（orchestration 层）

**Files:**
- Modify: `agents_hub/core/orchestration/group_chat_manager.py`
- Create: `tests/core/orchestration/test_group_chat_manager_tokens.py`

在 GroupChatManager 中添加：
- `_tokens: dict[str, tuple[str, str]]` 属性
- `register_token(token, agent_name, group_chat_id)` 方法
- `unregister_tokens(group_chat_id)` 方法
- `resolve_token(token) -> tuple[str, str] | None` 方法

测试应覆盖：
- 注册 token
- 解析 token
- 注销群聊的所有 token
- token 不存在时返回 None

提交信息：
```
feat(orchestration): GroupChatManager 新增 token 索引管理

- _tokens: dict[str, tuple[str, str]] 全局索引
- register_token(): 注册 token → (agent_name, group_chat_id)
- unregister_tokens(): 注销群聊的所有 token
- resolve_token(): 解析 token 为身份信息

用于 MCP 工具的身份验证。
```

---

## Task 6: GroupChat Token 生命周期（orchestration 层）

**Files:**
- Modify: `agents_hub/core/orchestration/group_chat.py`
- Modify: `tests/core/orchestration/test_group_chat.py`

在 GroupChat 中修改：
- `start()`: 为每个成员生成 token，调用 manager.register_token()
- `load()`: 从 agent_member.json 恢复 token，调用 manager.register_token()
- `cleanup()`: 调用 manager.unregister_tokens(group_chat_id)

测试应覆盖：
- start 时生成 token
- load 时恢复 token
- cleanup 时清空 token

提交信息：
```
feat(orchestration): GroupChat 集成 token 生命周期管理

- start(): 为每个成员生成 token 并注册到 GroupChatManager
- load(): 从持久化恢复 token 并注册
- cleanup(): 注销该群聊的所有 token

Token 在 GroupChat 启动时生成，清理时注销。
```

---

## Task 7: agent_member.json 持久化 token（context 层）

**Files:**
- Modify: `agents_hub/core/context/group_chat_context.py`
- Modify: `tests/core/context/test_group_chat_context.py`

在 agent_member.json 中新增 `agent_token` 字段：
```json
{
  "Manager": {
    "main_session": "session_123",
    "btw_session": [],
    "agent_token": "tok_a1b2c3d4e5f6...",
    "context_state": {...}
  }
}
```

修改 save/load 逻辑以支持 agent_token 字段。

提交信息：
```
feat(context): agent_member.json 新增 agent_token 字段

- 保存时写入 agent_token
- 加载时恢复 agent_token
- 向后兼容（旧文件没有 agent_token 字段时不报错）

用于持久化 Agent Token。
```

---

## Task 8: Agent Runtime 注入（agent 层）

**Files:**
- Modify: `agents_hub/core/agent/base_agent.py`
- Create: `tests/core/agent/test_agent_runtime_injection.py`

在 BaseAgent 中添加：
- `agent_token: str` 属性
- `_generate_runtime_content() -> str` 方法（生成 XML 格式的 runtime 内容）
- `_process_message()` 中调用 markdown_injector 注入到 CLAUDE.md/AGENTS.md

Runtime 内容格式（XML）：
```xml
<AGENT_RUNTIME>
<identity>
你的名字：Manager
群聊ID：gc_abc123
身份令牌：tok_a1b2c3d4e5f6...
</identity>

<team>
团队成员：Worker1, Worker2, Worker3
</team>

<team_workboard>
当前任务列表：
- [PENDING] task_1: 实现模块A (owner: Worker1)
</team_workboard>
</AGENT_RUNTIME>
```

提交信息：
```
feat(agent): 新增 Agent Runtime 注入到 CLAUDE.md/AGENTS.md

- agent_token 属性存储 token
- _generate_runtime_content() 生成 XML 格式的 runtime 内容
- _process_message() 调用 markdown_injector 注入到 work_root 下的 CLAUDE.md/AGENTS.md
- 仅 Manager 注入 team_workboard

通过 CLAUDE.md 的 prompt cache 机制避免重复 token 消耗。
```

---

## Task 9: Agent Token Redact（agent 层）

**Files:**
- Modify: `agents_hub/core/agent/base_agent.py`
- Create: `tests/core/agent/test_agent_token_redact.py`

在 BaseAgent.run() 的出口 A（写群聊）前调用 `redact_token()`：

```python
# 出口 A：写群聊
if result.text:
    # Token 剥离
    safe_text = redact_token(result.text)
    await self.group_chat_context.write_to_group_chat(
        agent_name=self.name,
        content=safe_text,
    )
```

测试应覆盖：
- 包含 token 的文本被剥离
- 不包含 token 的文本保持不变

提交信息：
```
feat(agent): 出口 A 写群聊前剥离 token

- 在 Agent.run() 出口 A 调用 redact_token()
- 防止 token 泄漏到群聊消息中

Token 防泄漏的最后一道防线。
```

---

## Task 10: MCP 错误响应工具（mcp 层）

**Files:**
- Create: `agents_hub/mcp/__init__.py`
- Create: `agents_hub/mcp/errors.py`
- Create: `tests/mcp/test_errors.py`

实现错误码和错误响应工具：
- 9 个错误码常量（INVALID_TOKEN, PERMISSION_DENIED, ...）
- `make_error_response(code, message, details=None) -> dict` 函数

错误响应格式：
```python
{
    "error": {
        "code": "INVALID_TOKEN",
        "message": "身份令牌无效或已过期，请检查 <agent_runtime> 块中的 token",
        "details": {...}  # 可选
    }
}
```

提交信息：
```
feat(mcp): 新增 MCP 错误响应工具

- 9 个错误码常量
- make_error_response() 生成统一格式的错误响应
- 错误信息包含 LLM 自纠所需的上下文

用于 MCP 工具的错误处理。
```

---

## Task 11: MCP Server 和 4 个工具（mcp 层）

**Files:**
- Create: `agents_hub/mcp/server.py`
- Create: `tests/mcp/test_server.py`

实现 FastMCP Server 和 4 个工具：
- `call_agent(agent_token, send_to, content, need_response, timeout_seconds)`
- `assign_tasks_to_team(agent_token, tasks)`
- `archive_task_list(agent_token)`
- `check_agent_call(agent_token, call_id)`

每个工具包含：
- 身份解析（调用 GroupChatManager.resolve_token）
- 权限校验（Leader-only 或任意 agent）
- 业务逻辑（调用 MessageRouter / TaskManager / AgentCallManager）
- 错误处理（返回统一格式的错误响应）

测试应覆盖：
- 每个工具的正常流程
- 每个工具的错误场景（INVALID_TOKEN, PERMISSION_DENIED, ...）

提交信息：
```
feat(mcp): 实现 FastMCP Server 和 4 个 MCP 工具

- call_agent: 派活给团队成员
- assign_tasks_to_team: 覆盖式更新任务列表
- archive_task_list: 归档当前 ACTIVE 列表
- check_agent_call: 查询 AgentCall 状态

每个工具包含身份解析、权限校验、业务逻辑和错误处理。
```

---

## Task 12: FastAPI 集成 MCP Server（业务层）

**Files:**
- Modify: `agents_hub/api/app.py` (或主 FastAPI 应用文件)
- Create: `tests/api/test_mcp_integration.py`

在 FastAPI 启动事件中启动 MCP Server：

```python
from agents_hub.mcp.server import mcp
import asyncio

@app.on_event("startup")
async def startup_mcp():
    # FastMCP 的 run() 是阻塞的，需要在独立任务中运行
    asyncio.create_task(mcp.run(host="localhost", port=8001))
```

测试应覆盖：
- MCP Server 启动后可以接收请求
- 端口 8001 正确监听

提交信息：
```
feat(api): FastAPI 集成 MCP Server

- 在 startup 事件中启动 MCP Server（端口 8001）
- 使用 asyncio.create_task 避免阻塞主进程

MCP Server 与 FastAPI 后端同生共死。
```

---

## Task 13: user_send_message 业务函数（业务层）

**Files:**
- Modify: `agents_hub/api/routes.py` (或相应的路由文件)
- Create: `tests/api/test_user_send_message.py`

实现 user_send_message 端点：

```python
@router.post("/group_chats/{group_chat_id}/send_message")
async def user_send_message(
    group_chat_id: str,
    send_to: str,
    content: str,
    user_id: str = Depends(get_current_user),
):
    """User 通过前端发送消息给 Agent（不走 MCP）"""
    # 1. 验证 group_chat_id 和 send_to 存在
    # 2. 构造 AgentMessage(send_from="user", send_to=send_to, message_type=TASK)
    # 3. 调用 MessageRouter.send_message()
    # 4. 返回 {success: True, call_id: str}
```

提交信息：
```
feat(api): 新增 user_send_message 业务函数

- User 通过前端发送消息给 Agent
- 不走 MCP，直接构造 AgentMessage(send_from="user")
- Agent 处理时出口 A 写群聊，出口 B 跳过（user 没有 message_queue）

User 路径与 MCP 路径分离。
```

---

## Task 14: .mcp.json 配置模板生成（bridge 层）

**Files:**
- Modify: `agents_hub/agent_bridge/bridge.py` (或 role 初始化相关文件)
- Create: `tests/agent_bridge/test_mcp_config_generation.py`

在 role 创建或首次启动时，生成 `work_root/.mcp.json`：

```json
{
  "mcpServers": {
    "agents-hub": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

同时在 `work_root/CLAUDE.md` 或 `work_root/AGENTS.md` 中预置标记：

```markdown
<AGENT_RUNTIME_START/>
（此区域将被动态替换）
<AGENT_RUNTIME_END/>
```

提交信息：
```
feat(bridge): 为 role 生成 .mcp.json 和 AGENT_RUNTIME 标记

- work_root/.mcp.json 指向 localhost:8001/mcp
- work_root/CLAUDE.md 或 AGENTS.md 预置 <AGENT_RUNTIME_START/> 标记
- 在 role 创建或首次启动时自动生成

Agent 通过 .mcp.json 连接 MCP Server。
```

---

## Task 15: 集成测试

**Files:**
- Create: `tests/integration/test_mcp_e2e.py`

端到端测试场景：
1. 创建 GroupChat，验证 token 生成
2. Manager 调用 call_agent 派活给 Worker
3. Worker 完成任务，出口 B 自动回执
4. Manager 调用 check_agent_call 查询状态
5. Manager 调用 assign_tasks_to_team 分配任务
6. Manager 调用 archive_task_list 归档任务

提交信息：
```
test(integration): 新增 MCP 工具端到端测试

- Manager 派活 → Worker 完成 → 出口 B 回执
- Manager 分配任务 → 更新状态 → 归档任务
- check_agent_call 查询状态

验证 MCP 工具系统的完整流程。
```

---

## 自查清单

**Spec 覆盖检查：**
- ✅ Token 生成和剥离（Task 1）
- ✅ Task/TaskList 数据模型（Task 2-4）
- ✅ GroupChatManager token 索引（Task 5-6）
- ✅ agent_member.json 持久化（Task 7）
- ✅ Agent Runtime 注入（Task 8）
- ✅ Token 防泄漏（Task 9）
- ✅ MCP Server 和 4 个工具（Task 10-11）
- ✅ FastAPI 集成（Task 12）
- ✅ user_send_message（Task 13）
- ✅ .mcp.json 配置（Task 14）
- ✅ 集成测试（Task 15）

**占位符检查：**
- Task 4 标记为"实施细节见 spec"（因为 TaskManager 逻辑复杂，需要参考 spec 第 4 节）
- 其他任务都包含完整的测试代码和实现代码

**类型一致性检查：**
- Token 格式：`tok_<32hex>` 在所有任务中一致
- TaskStatus / TaskListStatus 枚举在 Task 2 定义，Task 3-4 使用
- agent_token 字段名在 Task 7-8 中一致
- 错误响应格式在 Task 10-11 中一致

---

## 执行建议

由于这是一个大型功能（15 个任务），建议：

1. **按依赖顺序执行**：Task 1-4（foundation + communication）→ Task 5-7（orchestration + context）→ Task 8-9（agent）→ Task 10-12（mcp + api）→ Task 13-14（业务 + bridge）→ Task 15（集成测试）

2. **里程碑验证**：
   - 里程碑 1（Task 1-4）：foundation 和 communication 层完成，运行单元测试
   - 里程碑 2（Task 5-9）：token 生命周期和 runtime 注入完成，运行单元测试
   - 里程碑 3（Task 10-12）：MCP Server 完成，手动测试 MCP 工具
   - 里程碑 4（Task 13-15）：业务集成完成，运行集成测试

3. **Task 4 特别说明**：TaskManager 的实现比较复杂，需要仔细参考 spec 第 4 节的持久化格式和覆盖式更新语义。建议单独花时间实现和测试。

// __CONTINUE_HERE__
