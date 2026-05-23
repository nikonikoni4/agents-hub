# Agent Bridge 模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 agent_bridge 模块，提供统一的 Claude Code 和 Codex CLI 调用接口

**Architecture:** 扁平化架构（方案 B），职责分离：Executor（执行）+ Parser（解析）+ Bridge（统一接口），底层统一流式输出，上层提供流式/非流式双接口

**Tech Stack:** Python 3.11+, asyncio, subprocess, typing (Protocol, TypedDict, Enum)

---

## 文件结构

```
backend/agent_bridge/
├── __init__.py          # 模块入口，导出公共接口
├── config.py            # 配置数据类 + 平台枚举
├── protocols.py         # Executor, Parser 协议定义
├── bridge.py            # AgentBridge 统一接口
├── executors/
│   ├── __init__.py      # 导出所有执行器
│   ├── claude.py        # ClaudeExecutor
│   └── codex.py         # CodexExecutor
└── parsers/
    ├── __init__.py      # 导出所有解析器和事件类型
    ├── base.py          # AgentEvent, AgentEventType 定义
    ├── claude.py        # ClaudeParser
    └── codex.py         # CodexParser
```

---

## Task 1: 创建基础配置和类型定义

**Files:**
- Create: `backend/agent_bridge/__init__.py`
- Create: `backend/agent_bridge/config.py`
- Create: `backend/agent_bridge/parsers/__init__.py`
- Create: `backend/agent_bridge/parsers/base.py`
- Create: `backend/agent_bridge/executors/__init__.py`

- [ ] **Step 1: 创建模块目录结构**

```bash
mkdir -p backend/agent_bridge/executors
mkdir -p backend/agent_bridge/parsers
```

- [ ] **Step 2: 创建 `backend/agent_bridge/__init__.py`**

```python
"""Agent Bridge 模块 - 统一的 AI 平台 CLI 调用接口"""

from .config import AgentPlatform, RoleConfig
from .parsers.base import AgentEvent, AgentEventType
from .bridge import AgentBridge

__all__ = [
    "AgentPlatform",
    "RoleConfig",
    "AgentEvent",
    "AgentEventType",
    "AgentBridge",
]
```

- [ ] **Step 3: 创建 `backend/agent_bridge/config.py`**

```python
"""配置数据类和平台枚举"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class AgentPlatform(Enum):
    """Agent 平台枚举"""
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass
class RoleConfig:
    """角色配置"""
    platform: AgentPlatform    # 平台类型
    system_prompt: str         # system prompt 内容
    skills: List[str]          # skill 列表

    # Codex 专用字段
    codex_home: Optional[str] = None  # CODEX_HOME 路径

    # 留白字段（之后实现）
    permissions: Optional[dict] = None
    tools: Optional[List[str]] = None
```

- [ ] **Step 4: 创建 `backend/agent_bridge/parsers/base.py`**

```python"""事件类型定义"""from typing import TypedDict
from enum import Enum


class AgentEventType(Enum):
    """事件类型枚举，避免字符串拼写错误"""
    INIT = "init"                       # 会话开始元数据
    TEXT_DELTA = "text_delta"           # 文本增量（流式输出的主要内容）
    TOOL_USE = "tool_use"               # 工具调用（命令执行）
    TURN_COMPLETE = "turn_complete"     # 回合完成（包含 token 使用统计）
    RESULT = "result"                   # 完整结果（非流式输出）


class AgentEvent(TypedDict):
    """统一事件格式"""
    type: AgentEventType    # 事件类型（使用枚举）
    data: dict              # 具体数据
    session_id: str         # 会话 ID
    timestamp: str          # 时间戳（可选）
```

- [ ] **Step 5: 创建 `backend/agent_bridge/parsers/__init__.py`**

```python"""解析器模块"""from .base import AgentEvent, AgentEventTypefrom .claude import ClaudeParserfrom .codex import CodexParser__all__ = [    "AgentEvent",
    "AgentEventType",    "ClaudeParser",    "CodexParser",]
```

- [ ] **Step 6: 创建 `backend/agent_bridge/executors/__init__.py`**

```python"""执行器模块"""from .claude import ClaudeExecutorfrom .codex import CodexExecutor__all__ = [    "ClaudeExecutor",    "CodexExecutor",]
```

- [ ] **Step 7: 验证模块可以导入**

```bash
cd backend
python -c "from agent_bridge import AgentPlatform, RoleConfig, AgentEvent, AgentEventType; print('OK')"
```

Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add backend/agent_bridge/__init__.py backend/agent_bridge/config.py backend/agent_bridge/parsers/__init__.py backend/agent_bridge/parsers/base.py backend/agent_bridge/executors/__init__.py
git commit -m "feat(agent_bridge): add base config and types"
```

---

## Task 2: 创建协议定义

**Files:**
- Create: `backend/agent_bridge/protocols.py`

- [ ] **Step 1: 创建 `backend/agent_bridge/protocols.py`**

```python
"""Executor 和 Parser 协议定义"""

from typing import Protocol, AsyncIterator, Optional
from .config import RoleConfig
from .parsers.base import AgentEvent


class Executor(Protocol):
    """执行器协议：负责启动 CLI 并返回原始输出流"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        启动 CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复已有会话或指定新会话 ID）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流（每行一个事件）
        """
        ...


class Parser(Protocol):
    """解析器协议：负责解析原始输出为统一格式"""

    def parse_event(self, raw_line: str) -> Optional[AgentEvent]:
        """
        解析单行 JSON 事件

        Args:
            raw_line: 原始 JSON 字符串

        Returns:
            Optional[AgentEvent]: 统一格式的事件（如果无法解析则返回 None）
        """
        ...
```

- [ ] **Step 2: 验证协议可以导入**

```bash
cd backend
python -c "from agent_bridge.protocols import Executor, Parser; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/agent_bridge/protocols.py
git commit -m "feat(agent_bridge): add Executor and Parser protocols"
```

---

## Task 3: 实现 ClaudeParser

**Files:**
- Create: `backend/agent_bridge/parsers/claude.py`
- Create: `tests/unit/agent_bridge/parsers/__init__.py`
- Create: `tests/unit/agent_bridge/parsers/test_claude_parser.py`

- [ ] **Step 1: 创建测试文件 `tests/unit/agent_bridge/parsers/__init__.py`**

```python
```

- [ ] **Step 2: 编写 ClaudeParser 测试**

```python
"""ClaudeParser 单元测试"""

import json
import pytest
from backend.agent_bridge.parsers.claude import ClaudeParser
from backend.agent_bridge.parsers.base import AgentEventType


class TestClaudeParser:
    """ClaudeParser 测试类"""

    def setup_method(self):
        self.parser = ClaudeParser()

    def test_parse_text_delta(self):
        """测试解析文本增量事件"""
        raw_line = json.dumps({
            "type": "stream_event",
            "event": {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "你好"}
            },
            "session_id": "test-session-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.TEXT_DELTA
        assert result["data"]["text"] == "你好"
        assert result["session_id"] == "test-session-123"

    def test_parse_init(self):
        """测试解析初始化事件"""
        raw_line = json.dumps({
            "type": "system",
            "subtype": "init",
            "session_id": "test-session-123",
            "model": "claude-opus-4-7",
            "tools": ["Bash", "Read", "Write"]
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.INIT
        assert result["data"]["model"] == "claude-opus-4-7"
        assert "Bash" in result["data"]["tools"]

    def test_parse_unknown_event_returns_none(self):
        """测试解析未知事件返回 None"""
        raw_line = json.dumps({
            "type": "unknown_type",
            "session_id": "test-session-123"
        })
        result = self.parser.parse_event(raw_line)

        assert result is None

    def test_parse_invalid_json_returns_none(self):
        """测试解析无效 JSON 返回 None"""
        result = self.parser.parse_event("invalid json")

        assert result is None
```

- [ ] **Step 3: 运行测试确认失败**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/parsers/test_claude_parser.py -v
```

Expected: FAIL（因为 ClaudeParser 还不存在）

- [ ] **Step 4: 实现 ClaudeParser**

```python
"""Claude CLI 输出解析器"""

import json
from typing import Optional
from .base import AgentEvent, AgentEventType


class ClaudeParser:
    """解析 Claude CLI 的流式输出"""

    def parse_event(self, raw_line: str) -> Optional[AgentEvent]:
        """
        解析单行 JSON 事件

        Claude 流式输出事件类型：
        - stream_event.content_block_delta → text_delta
        - system.init → init
        """
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            return None

        event_type = event.get("type")
        session_id = event.get("session_id", "")

        # 流式文本事件
        if event_type == "stream_event":
            return self._parse_stream_event(event, session_id)

        # 系统事件
        if event_type == "system":
            return self._parse_system_event(event, session_id)

        return None

    def _parse_stream_event(self, event: dict, session_id: str) -> Optional[AgentEvent]:
        """解析流式事件"""
        inner_event = event.get("event", {})
        inner_type = inner_event.get("type")

        # 文本增量
        if inner_type == "content_block_delta":
            delta = inner_event.get("delta", {})
            if delta.get("type") == "text_delta":
                return AgentEvent(
                    type=AgentEventType.TEXT_DELTA,
                    data={"text": delta.get("text", "")},
                    session_id=session_id,
                    timestamp=""
                )

        return None

    def _parse_system_event(self, event: dict, session_id: str) -> Optional[AgentEvent]:
        """解析系统事件"""
        subtype = event.get("subtype")

        # 初始化事件
        if subtype == "init":
            return AgentEvent(
                type=AgentEventType.INIT,
                data={
                    "model": event.get("model", ""),
                    "tools": event.get("tools", []),
                },
                session_id=session_id,
                timestamp=""
            )

        return None
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/parsers/test_claude_parser.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/agent_bridge/parsers/claude.py tests/unit/agent_bridge/parsers/__init__.py tests/unit/agent_bridge/parsers/test_claude_parser.py
git commit -m "feat(agent_bridge): add ClaudeParser with tests"
```

---

## Task 4: 实现 CodexParser

**Files:**
- Create: `backend/agent_bridge/parsers/codex.py`
- Create: `tests/unit/agent_bridge/parsers/test_codex_parser.py`

- [ ] **Step 1: 编写 CodexParser 测试**

```python
"""CodexParser 单元测试"""

import json
import pytest
from backend.agent_bridge.parsers.codex import CodexParser
from backend.agent_bridge.parsers.base import AgentEventType


class TestCodexParser:
    """CodexParser 测试类"""

    def setup_method(self):
        self.parser = CodexParser()

    def test_parse_agent_message(self):
        """测试解析 agent 消息事件"""
        raw_line = json.dumps({
            "type": "item.completed",
            "item": {
                "id": "item_0",
                "type": "agent_message",
                "text": "我会帮你审查代码"
            }
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.TEXT_DELTA
        assert result["data"]["text"] == "我会帮你审查代码"

    def test_parse_command_execution(self):
        """测试解析命令执行事件"""
        raw_line = json.dumps({
            "type": "item.completed",
            "item": {
                "id": "item_1",
                "type": "command_execution",
                "command": "ls -la",
                "aggregated_output": "total 0\ndrwxr-xr-x  2 user  staff  64 Jan  1 00:00 .",
                "exit_code": 0,
                "status": "completed"
            }
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.TOOL_USE
        assert result["data"]["command"] == "ls -la"
        assert result["data"]["exit_code"] == 0

    def test_parse_turn_completed(self):
        """测试解析回合完成事件"""
        raw_line = json.dumps({
            "type": "turn.completed",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cached_input_tokens": 0
            }
        })
        result = self.parser.parse_event(raw_line)

        assert result is not None
        assert result["type"] == AgentEventType.TURN_COMPLETE
        assert result["data"]["usage"]["input_tokens"] == 100

    def test_parse_unknown_event_returns_none(self):
        """测试解析未知事件返回 None"""
        raw_line = json.dumps({
            "type": "unknown_type"
        })
        result = self.parser.parse_event(raw_line)

        assert result is None

    def test_parse_invalid_json_returns_none(self):
        """测试解析无效 JSON 返回 None"""
        result = self.parser.parse_event("invalid json")

        assert result is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/parsers/test_codex_parser.py -v
```

Expected: FAIL（因为 CodexParser 还不存在）

- [ ] **Step 3: 实现 CodexParser**

```python
"""Codex CLI 输出解析器"""

import json
from typing import Optional
from .base import AgentEvent, AgentEventType


class CodexParser:
    """解析 Codex CLI 的流式输出"""

    def parse_event(self, raw_line: str) -> Optional[AgentEvent]:
        """
        解析单行 JSON 事件

        Codex 流式输出事件类型：
        - item.completed (agent_message) → text_delta
        - item.completed (command_execution) → tool_use
        - turn.completed → turn_complete
        """
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            return None

        event_type = event.get("type")

        # 项目完成事件
        if event_type == "item.completed":
            return self._parse_item_completed(event)

        # 回合完成事件
        if event_type == "turn.completed":
            return self._parse_turn_completed(event)

        return None

    def _parse_item_completed(self, event: dict) -> Optional[AgentEvent]:
        """解析项目完成事件"""
        item = event.get("item", {})
        item_type = item.get("type")

        # 注意：Codex CLI 的 JSON 输出不包含 session_id 字段
        # session_id 需要在 Bridge 层通过其他方式获取（如从 thread.started 事件中提取）
        session_id = event.get("thread_id", "")

        # Agent 消息
        if item_type == "agent_message":
            return AgentEvent(
                type=AgentEventType.TEXT_DELTA,
                data={"text": item.get("text", "")},
                session_id=session_id,
                timestamp=""
            )

        # 命令执行
        if item_type == "command_execution":
            return AgentEvent(
                type=AgentEventType.TOOL_USE,
                data={
                    "command": item.get("command", ""),
                    "output": item.get("aggregated_output", ""),
                    "exit_code": item.get("exit_code"),
                    "status": item.get("status", ""),
                },
                session_id=session_id,
                timestamp=""
            )

        return None

    def _parse_turn_completed(self, event: dict) -> Optional[AgentEvent]:
        """解析回合完成事件"""
        usage = event.get("usage", {})
        return AgentEvent(
            type=AgentEventType.TURN_COMPLETE,
            data={"usage": usage},
            session_id=event.get("thread_id", ""),
            timestamp=""
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/parsers/test_codex_parser.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agent_bridge/parsers/codex.py tests/unit/agent_bridge/parsers/test_codex_parser.py
git commit -m "feat(agent_bridge): add CodexParser with tests"
```

---

## Task 5: 实现 ClaudeExecutor

**Files:**
- Create: `backend/agent_bridge/executors/claude.py`
- Create: `tests/unit/agent_bridge/executors/__init__.py`
- Create: `tests/unit/agent_bridge/executors/test_claude_executor.py`

- [ ] **Step 1: 创建测试目录和文件**

```python
"""ClaudeExecutor 单元测试"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.agent_bridge.executors.claude import ClaudeExecutor
from backend.agent_bridge.config import RoleConfig, AgentPlatform


class TestClaudeExecutor:
    """ClaudeExecutor 测试类"""

    def setup_method(self):
        self.executor = ClaudeExecutor()

    def test_build_command_basic(self):
        """测试构建基本命令"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="你是代码审查专家",
            skills=[]
        )
        cmd = self.executor._build_command("审查代码", config, None)

        assert "claude" in cmd
        assert "--print" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--append-system-prompt" in cmd
        assert "你是代码审查专家" in cmd
        assert "审查代码" in cmd

    def test_build_command_with_session_id(self):
        """测试构建带 session_id 的命令"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )
        cmd = self.executor._build_command("测试", config, "session-123")

        assert "--resume" in cmd
        assert "session-123" in cmd

    def test_build_command_with_skills(self):
        """测试构建带 skills 的命令"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=["code-review", "security-check"]
        )
        cmd = self.executor._build_command("测试", config, None)

        assert "--plugin-dir" in cmd
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/executors/test_claude_executor.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 ClaudeExecutor**

```python
"""Claude CLI 执行器"""

import asyncio
import json
from typing import AsyncIterator, Optional
from ..config import RoleConfig


class ClaudeExecutor:
    """执行 Claude CLI 命令"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        启动 Claude CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        cmd = self._build_command(prompt, config, session_id)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async for line in process.stdout:
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield decoded

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str]
    ) -> list:
        """构建 Claude CLI 命令"""
        cmd = [
            "claude",
            "--print",
            "--verbose",
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--append-system-prompt", config.system_prompt,
        ]

        # 添加 skills（plugin-dir）
        for skill in config.skills:
            cmd.extend(["--plugin-dir", skill])

        # 添加 session_id（恢复会话）
        if session_id:
            cmd.extend(["--resume", session_id])

        cmd.append(prompt)
        return cmd
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/executors/test_claude_executor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agent_bridge/executors/claude.py tests/unit/agent_bridge/executors/__init__.py tests/unit/agent_bridge/executors/test_claude_executor.py
git commit -m "feat(agent_bridge): add ClaudeExecutor with tests"
```

---

## Task 6: 实现 CodexExecutor

**Files:**
- Create: `backend/agent_bridge/executors/codex.py`
- Create: `tests/unit/agent_bridge/executors/test_codex_executor.py`

- [ ] **Step 1: 编写 CodexExecutor 测试**

```python
"""CodexExecutor 单元测试"""

import os
import pytest
from backend.agent_bridge.executors.codex import CodexExecutor
from backend.agent_bridge.config import RoleConfig, AgentPlatform


class TestCodexExecutor:
    """CodexExecutor 测试类"""

    def setup_method(self):
        self.executor = CodexExecutor()

    def test_build_command_basic(self):
        """测试构建基本命令"""
        config = RoleConfig(
            platform=AgentPlatform.CODEX,
            system_prompt="你是代码审查专家",
            skills=[],
            codex_home="/path/to/codex-home"
        )
        cmd = self.executor._build_command("审查代码", config, None)

        assert "codex" in cmd
        assert "exec" in cmd
        assert "--json" in cmd
        assert "审查代码" in cmd

    def test_build_command_with_session_id(self):
        """测试构建带 session_id 的命令"""
        config = RoleConfig(
            platform=AgentPlatform.CODEX,
            system_prompt="测试",
            skills=[],
            codex_home="/path/to/codex-home"
        )
        cmd = self.executor._build_command("测试", config, "session-123")

        assert "--session-id" in cmd
        assert "session-123" in cmd

    def test_build_env(self):
        """测试构建环境变量"""
        config = RoleConfig(
            platform=AgentPlatform.CODEX,
            system_prompt="测试",
            skills=[],
            codex_home="/path/to/codex-home"
        )
        env = self.executor._build_env(config)

        assert "CODEX_HOME" in env
        assert env["CODEX_HOME"] == "/path/to/codex-home"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/executors/test_codex_executor.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 CodexExecutor**

```python
"""Codex CLI 执行器"""

import asyncio
import os
from typing import AsyncIterator, Optional
from ..config import RoleConfig


class CodexExecutor:
    """执行 Codex CLI 命令"""

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        启动 Codex CLI 并返回原始输出流

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复会话）

        Returns:
            AsyncIterator[str]: 原始 JSON 字符串流
        """
        cmd = self._build_command(prompt, config, session_id)
        env = self._build_env(config)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        async for line in process.stdout:
            decoded = line.decode("utf-8").strip()
            if decoded:
                yield decoded

    def _build_command(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str]
    ) -> list:
        """构建 Codex CLI 命令"""
        cmd = [
            "codex",
            "exec",
            "--json",
        ]

        # 添加 session_id（恢复会话）
        if session_id:
            cmd.extend(["--session-id", session_id])

        cmd.append(prompt)
        return cmd

    def _build_env(self, config: RoleConfig) -> dict:
        """构建环境变量"""
        env = os.environ.copy()
        if config.codex_home:
            env["CODEX_HOME"] = config.codex_home
        return env
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/executors/test_codex_executor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agent_bridge/executors/codex.py tests/unit/agent_bridge/executors/test_codex_executor.py
git commit -m "feat(agent_bridge): add CodexExecutor with tests"
```

---

## Task 7: 实现 AgentBridge

**Files:**
- Create: `backend/agent_bridge/bridge.py`
- Create: `tests/unit/agent_bridge/test_bridge.py`

- [ ] **Step 1: 编写 AgentBridge 测试**

```python
"""AgentBridge 单元测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.agent_bridge.bridge import AgentBridge
from backend.agent_bridge.config import RoleConfig, AgentPlatform
from backend.agent_bridge.parsers.base import AgentEventType


class TestAgentBridge:
    """AgentBridge 测试类"""

    def setup_method(self):
        self.bridge = AgentBridge()

    def test_init_creates_executors_and_parsers(self):
        """测试初始化创建执行器和解析器"""
        assert AgentPlatform.CLAUDE in self.bridge._executors
        assert AgentPlatform.CODEX in self.bridge._executors
        assert AgentPlatform.CLAUDE in self.bridge._parsers
        assert AgentPlatform.CODEX in self.bridge._parsers

    @pytest.mark.asyncio
    async def test_execute_stream_calls_correct_executor(self):
        """测试流式调用使用正确的执行器"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )

        # Mock executor
        mock_executor = AsyncMock()
        mock_executor.execute.return_value = AsyncMock()
        mock_executor.execute.return_value.__aiter__ = AsyncMock(
            return_value=iter(['{"type":"system","subtype":"init","session_id":"123"}'])
        )
        self.bridge._executors[AgentPlatform.CLAUDE] = mock_executor

        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse_event.return_value = {
            "type": AgentEventType.INIT,
            "data": {},
            "session_id": "123",
            "timestamp": ""
        }
        self.bridge._parsers[AgentPlatform.CLAUDE] = mock_parser

        # 调用
        events = []
        async for event in self.bridge.execute_stream("测试", config):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == AgentEventType.INIT
        mock_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_result_event(self):
        """测试非流式调用返回 RESULT 事件"""
        config = RoleConfig(
            platform=AgentPlatform.CLAUDE,
            system_prompt="测试",
            skills=[]
        )

        # Mock execute_stream
        async def mock_stream(prompt, config, session_id):
            yield {
                "type": AgentEventType.TEXT_DELTA,
                "data": {"text": "你好"},
                "session_id": "123",
                "timestamp": ""
            }
            yield {
                "type": AgentEventType.TURN_COMPLETE,
                "data": {"usage": {"input_tokens": 100}},
                "session_id": "123",
                "timestamp": ""
            }

        self.bridge.execute_stream = mock_stream

        result = await self.bridge.execute("测试", config)

        assert result["type"] == AgentEventType.RESULT
        assert result["data"]["text"] == "你好"
        assert result["data"]["usage"]["input_tokens"] == 100
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/test_bridge.py -v
```

Expected: FAIL

- [ ] **Step 3: 实现 AgentBridge**

```python
"""AgentBridge 统一接口"""

from typing import AsyncIterator, Optional
from .config import RoleConfig, AgentPlatform
from .parsers.base import AgentEvent, AgentEventType
from .executors.claude import ClaudeExecutor
from .executors.codex import CodexExecutor
from .parsers.claude import ClaudeParser
from .parsers.codex import CodexParser


class AgentBridge:
    """统一的 Agent 调用接口"""

    def __init__(self):
        # 创建执行器和解析器实例（可复用）
        self._executors = {
            AgentPlatform.CLAUDE: ClaudeExecutor(),
            AgentPlatform.CODEX: CodexExecutor()
        }
        self._parsers = {
            AgentPlatform.CLAUDE: ClaudeParser(),
            AgentPlatform.CODEX: CodexParser()
        }

    async def execute_stream(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AsyncIterator[AgentEvent]:
        """
        流式执行 Agent 调用（给人看）

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选，用于恢复之前的会话）

        Yields:
            AgentEvent: 统一格式的事件流
        """
        executor = self._executors[config.platform]
        parser = self._parsers[config.platform]

        raw_stream = executor.execute(prompt, config, session_id)
        async for raw_line in raw_stream:
            if raw_line.strip():
                parsed_event = parser.parse_event(raw_line)
                if parsed_event is not None:
                    yield parsed_event

    async def execute(
        self,
        prompt: str,
        config: RoleConfig,
        session_id: Optional[str] = None
    ) -> AgentEvent:
        """
        非流式执行，返回完整结果（给 A2A 用）

        内部复用 execute_stream()，拼接所有 text_delta 后返回单个 RESULT 事件。

        Args:
            prompt: 用户输入
            config: 角色配置
            session_id: 会话 ID（可选）

        Returns:
            AgentEvent: type 为 AgentEventType.RESULT 的完整结果事件
        """
        full_text = []
        usage = None
        result_session_id = session_id or ""

        async for event in self.execute_stream(prompt, config, session_id):
            if event["type"] == AgentEventType.TEXT_DELTA:
                full_text.append(event["data"]["text"])
            elif event["type"] == AgentEventType.TURN_COMPLETE:
                usage = event["data"].get("usage")
            # 记录第一个返回的 session_id
            if not result_session_id and event.get("session_id"):
                result_session_id = event["session_id"]

        return AgentEvent(
            type=AgentEventType.RESULT,
            data={"text": "".join(full_text), "usage": usage},
            session_id=result_session_id,
            timestamp=""
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/test_bridge.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/agent_bridge/bridge.py tests/unit/agent_bridge/test_bridge.py
git commit -m "feat(agent_bridge): add AgentBridge with dual interface"
```

---

## Task 8: 运行完整测试套件

**Files:**
- Test: `tests/unit/agent_bridge/` (all tests)

- [ ] **Step 1: 运行所有 agent_bridge 测试**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/ -v
```

Expected: All PASS

- [ ] **Step 2: 检查代码覆盖率（可选）**

```bash
cd backend
python -m pytest ../tests/unit/agent_bridge/ --cov=agent_bridge --cov-report=term-missing
```

- [ ] **Step 3: Commit（如果有修复）**

```bash
git add -A
git commit -m "fix(agent_bridge): fix any test failures"
```

---

## Task 9: 创建集成测试（可选）

**Files:**
- Create: `tests/integration/test_agent_bridge_integration.py`

- [ ] **Step 1: 创建集成测试**

```python
"""AgentBridge 集成测试

注意：这些测试需要实际的 CLI 工具安装，可能会比较慢。
可以通过 pytest.mark.skipif 跳过。
"""

import pytest
import asyncio
from backend.agent_bridge import AgentBridge, RoleConfig, AgentPlatform, AgentEventType


@pytest.mark.asyncio
@pytest.mark.integration
async def test_claude_bridge_integration():
    """测试 Claude 实际调用"""
    bridge = AgentBridge()
    config = RoleConfig(
        platform=AgentPlatform.CLAUDE,
        system_prompt="你是测试助手，用一句话回答问题",
        skills=[]
    )

    events = []
    async for event in bridge.execute_stream("1+1等于几？", config):
        events.append(event)
        # 只收集前几个事件，避免测试太慢
        if len(events) >= 5:
            break

    assert len(events) > 0
    # 检查是否有文本事件
    text_events = [e for e in events if e["type"] == AgentEventType.TEXT_DELTA]
    assert len(text_events) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_claude_bridge_execute():
    """测试 Claude 非流式调用"""
    bridge = AgentBridge()
    config = RoleConfig(
        platform=AgentPlatform.CLAUDE,
        system_prompt="你是测试助手，用一句话回答问题",
        skills=[]
    )

    result = await bridge.execute("1+1等于几？", config)

    assert result["type"] == AgentEventType.RESULT
    assert len(result["data"]["text"]) > 0
```

- [ ] **Step 2: 运行集成测试**

```bash
cd backend
python -m pytest ../tests/integration/test_agent_bridge_integration.py -v -m integration
```

Expected: PASS（如果安装了 Claude CLI）

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_agent_bridge_integration.py
git commit -m "test(agent_bridge): add integration tests"
```

---

## 自审清单

### 1. Spec 覆盖检查

| 需求项 | 对应任务 | 状态 |
|--------|---------|------|
| 配置管理（AgentPlatform, RoleConfig） | Task 1 | ✅ |
| 接口协议（Executor, Parser） | Task 2 | ✅ |
| ClaudeParser | Task 3 | ✅ |
| CodexParser | Task 4 | ✅ |
| ClaudeExecutor | Task 5 | ✅ |
| CodexExecutor | Task 6 | ✅ |
| AgentBridge（双接口） | Task 7 | ✅ |
| 流式接口 execute_stream() | Task 7 | ✅ |
| 非流式接口 execute() | Task 7 | ✅ |
| session_id 支持 | Task 5, 6 | ✅ |
| 错误处理（留白） | N/A | ⏭️ |

### 2. 占位符检查

无 TBD、TODO 或未实现的占位符。

### 3. 类型一致性检查

- `AgentEvent`、`AgentEventType` 在所有文件中一致使用
- `RoleConfig`、`AgentPlatform` 在所有文件中一致使用
- 方法签名在协议和实现中一致

---

## 执行选项

计划完成并保存到 `docs/superpowers/plans/2026-05-23-agent-bridge-implementation.md`。

两种执行方式：

**1. Subagent-Driven（推荐）** - 每个任务分发给独立的 subagent 执行，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中执行任务，批量执行并设置检查点

你选择哪种方式？