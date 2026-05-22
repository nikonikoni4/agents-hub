# Agent Bridge 架构方案对比研究报告

**研究日期**: 2026-05-23  
**研究目标**: 对比两种 agent_bridge 模块的架构设计方案  
**研究结论**: 推荐方案 B（扁平化架构）

---

## 一、背景与需求

### 1.1 项目背景

agents-hub 需要一个统一的 agent_bridge 模块，用于调用不同的 AI 平台 CLI 工具（Claude Code、Codex）。

### 1.2 核心需求

| 需求项 | 说明 |
|--------|------|
| **配置管理** | 角色配置固定（system prompt、skill 选择），作为初始化参数传入 |
| **输出模式** | 只采用流式输出（更易解析，信息更丰富） |
| **模块定位** | 纯执行层（启动 CLI、解析输出），不涉及业务逻辑 |
| **会话管理** | session_id 由调用方传入，模块不管理会话 |
| **错误处理** | 留白，之后实现 |

### 1.3 调用接口

```python
# 初始化
config = RoleConfig(
    platform="claude",
    system_prompt="你是一个代码审查专家",
    skills=["code-review", "security-check"]
)
agent = AgentBridge(config)

# 流式调用
async for event in agent.execute_stream(user_prompt="审查这段代码", session_id="session_123"):
    # 处理事件
    print(event)
```

---

## 二、方案 A：继承架构

### 2.1 目录结构

```
backend/agent_bridge/
├── config.py          # RoleConfig（所有配置参数）
├── base.py            # BaseAgent（抽象类）
├── claude.py          # ClaudeAgent（继承 BaseAgent）
├── codex.py           # CodexAgent（继承 BaseAgent）
└── bridge.py          # AgentBridge（统一封装）
```

### 2.2 核心代码

**base.py - 抽象基类**

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any
from .config import RoleConfig

class BaseAgent(ABC):
    """抽象基类：定义 Agent 的完整接口"""
    
    def __init__(self, config: RoleConfig):
        self.config = config
    
    @abstractmethod
    async def execute_stream(
        self, 
        user_prompt: str, 
        session_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        执行 Agent 调用并返回解析后的事件流
        
        子类必须实现：
        1. 构建 CLI 命令
        2. 启动子进程
        3. 解析输出
        4. 返回统一格式的事件
        """
        pass
```

**claude.py - Claude 实现**

```python
import asyncio
import json
from typing import AsyncIterator, Dict, Any
from .base import BaseAgent

class ClaudeAgent(BaseAgent):
    """Claude Code 实现"""
    
    async def execute_stream(
        self, 
        user_prompt: str, 
        session_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """完整的执行+解析流程"""
        
        # 1. 构建命令（使用 self.config）
        cmd = self._build_command(user_prompt, session_id)
        
        # 2. 启动子进程
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # 3. 逐行读取并解析
        async for line in process.stdout:
            if line.strip():
                raw_event = json.loads(line.decode('utf-8'))
                # 4. 解析为统一格式
                parsed_event = self._parse_event(raw_event)
                yield parsed_event
    
    def _build_command(self, user_prompt: str, session_id: str) -> list:
        """构建 Claude CLI 命令"""
        return [
            "claude",
            "--print",
            "--verbose",
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--session-id", session_id,
            "--append-system-prompt", self.config.system_prompt,
            # 从 config 读取 skills
            "--plugin-dir", self._get_skills_dir(),
            user_prompt
        ]
    
    def _parse_event(self, raw_event: dict) -> Dict[str, Any]:
        """解析 Claude 特定的事件格式"""
        # 统一化事件结构
        if raw_event["type"] == "stream_event":
            return self._parse_stream_event(raw_event)
        elif raw_event["type"] == "system":
            return self._parse_system_event(raw_event)
        # ... 其他事件类型
    
    def _parse_stream_event(self, event: dict) -> Dict[str, Any]:
        """解析流式事件"""
        # 具体解析逻辑
        pass
    
    def _get_skills_dir(self) -> str:
        """根据 config.skills 获取 skills 目录"""
        pass
```

**codex.py - Codex 实现**

```python
import asyncio
import json
from typing import AsyncIterator, Dict, Any
from .base import BaseAgent

class CodexAgent(BaseAgent):
    """Codex 实现"""
    
    async def execute_stream(
        self, 
        user_prompt: str, 
        session_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """完整的执行+解析流程"""
        
        # 1. 设置环境变量（使用 self.config）
        env = self._build_env()
        
        # 2. 构建命令
        cmd = self._build_command(user_prompt, session_id)
        
        # 3. 启动子进程
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # 4. 逐行读取并解析
        async for line in process.stdout:
            if line.strip():
                raw_event = json.loads(line.decode('utf-8'))
                parsed_event = self._parse_event(raw_event)
                yield parsed_event
    
    def _build_env(self) -> dict:
        """构建环境变量（CODEX_HOME）"""
        import os
        env = os.environ.copy()
        # 根据 config 设置 CODEX_HOME
        env["CODEX_HOME"] = self._get_codex_home()
        return env
    
    def _build_command(self, user_prompt: str, session_id: str) -> list:
        """构建 Codex CLI 命令"""
        return [
            "codex",
            "exec",
            "--json",
            "--session-id", session_id,
            user_prompt
        ]
    
    def _parse_event(self, raw_event: dict) -> Dict[str, Any]:
        """解析 Codex 特定的事件格式"""
        # 统一化事件结构
        if raw_event["type"] == "item.completed":
            return self._parse_item_completed(raw_event)
        elif raw_event["type"] == "turn.completed":
            return self._parse_turn_completed(raw_event)
        # ... 其他事件类型
    
    def _get_codex_home(self) -> str:
        """根据 config 获取 CODEX_HOME 路径"""
        pass
```

**bridge.py - 统一封装**

```python
from typing import AsyncIterator, Dict, Any
from .config import RoleConfig
from .claude import ClaudeAgent
from .codex import CodexAgent

class AgentBridge:
    """统一封装类"""
    
    def __init__(self, config: RoleConfig):
        # 根据平台创建对应的 Agent
        if config.platform == "claude":
            self.agent = ClaudeAgent(config)
        elif config.platform == "codex":
            self.agent = CodexAgent(config)
        else:
            raise ValueError(f"Unsupported platform: {config.platform}")
    
    async def execute_stream(
        self, 
        user_prompt: str, 
        session_id: str
    ) -> AsyncIterator[Dict[str, Any]]:
        """直接委托给具体的 Agent"""
        async for event in self.agent.execute_stream(user_prompt, session_id):
            yield event
```

### 2.3 方案特点

| 特点 | 说明 |
|------|------|
| **核心思想** | 一个 Agent 类 = 完整流程（执行 + 解析） |
| **抽象方式** | 抽象类定义接口契约 |
| **代码组织** | 按平台分文件 |
| **职责** | 每个 Agent 类负责：命令构建 + 进程管理 + 输出解析 |

### 2.4 优势

✅ **符合直觉**：一个 Agent = 一个完整的执行单元  
✅ **接口强制**：抽象类强制子类实现 `execute_stream`  
✅ **IDE 友好**：IDE 可以提示缺失的方法  
✅ **配置统一**：所有参数都在 `RoleConfig` 中，子类只需读取

### 2.5 劣势

⚠️ **过度设计**：为简单场景引入了不必要的抽象  
⚠️ **测试困难**：无法独立测试解析逻辑，必须启动完整流程  
⚠️ **复用受限**：如果两个平台的解析逻辑相同，无法直接复用  
⚠️ **修改影响面大**：修改解析逻辑需要修改整个 Agent 类  
⚠️ **职责不单一**：一个类承担 3 个职责（命令构建、进程管理、解析）

---

## 三、方案 B：扁平化架构

### 3.1 目录结构

```
backend/agent_bridge/
├── config.py          # RoleConfig
├── protocols.py       # Executor, Parser 协议定义
├── executors/
│   ├── __init__.py
│   ├── claude.py      # ClaudeExecutor
│   └── codex.py       # CodexExecutor
├── parsers/
│   ├── __init__.py
│   ├── claude.py      # ClaudeParser
│   └── codex.py       # CodexParser
└── bridge.py          # AgentBridge
```

### 3.2 核心代码

**protocols.py - 协议定义**

```python
from typing import Protocol, AsyncIterator, Dict, Any
from .config import RoleConfig

class Executor(Protocol):
    """执行器协议"""
    async def execute(
        self, 
        prompt: str, 
        session_id: str, 
        config: RoleConfig
    ) -> AsyncIterator[str]:
        """返回原始输出流（未解析的 JSON 字符串）"""
        ...

class Parser(Protocol):
    """解析器协议"""
    def parse_event(self, raw_line: str) -> Dict[str, Any]:
        """解析单行 JSON 事件为统一格式"""
        ...
```

// __CONTINUE_HERE__
