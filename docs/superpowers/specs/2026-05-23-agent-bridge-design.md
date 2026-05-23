# Agent Bridge 模块设计文档

**设计日期**: 2026-05-23  
**设计目标**: 设计一个统一的 agent_bridge 模块，用于调用不同的 AI 平台 CLI 工具  
**架构方案**: 扁平化架构（方案 B）

---

## 一、设计概述

### 1.1 模块定位

agent_bridge 是一个**纯执行层**模块，负责：
- 启动 AI 平台 CLI 工具（Claude Code、Codex）
- 解析 CLI 输出为统一格式
- 提供统一的流式调用接口

**不负责**：
- 业务逻辑
- 会话管理（由 CLI 工具内部处理）
- 错误重试（留白，之后实现）

### 1.2 核心需求

| 需求项 | 说明 |
|--------|------|
| **配置管理** | 角色配置固定，作为参数传入 |
| **输出模式** | 底层统一流式输出，上层提供流式/非流式两种接口 |
| **错误处理** | 留白，之后实现 |

### 1.3 设计原则

1. **职责分离**：执行和解析独立
2. **无状态设计**：Executor 和 Parser 可复用
3. **类型安全**：使用枚举和 Protocol
4. **易于扩展**：新增平台只需添加 Executor 和 Parser
5. **易于测试**：每个组件可独立测试

---

## 二、架构设计

### 2.1 目录结构

```
backend/agent_bridge/
├── __init__.py
├── config.py          # 配置数据类 + 平台枚举
├── protocols.py       # Executor, Parser 协议定义
├── bridge.py          # AgentBridge 统一接口
├── executors/
│   ├── __init__.py
│   ├── claude.py      # ClaudeExecutor
│   └── codex.py       # CodexExecutor
└── parsers/
    ├── __init__.py
    ├── claude.py      # ClaudeParser
    └── codex.py       # CodexParser
```

### 2.2 模块职责

| 模块 | 职责 | 状态 |
|------|------|------|
| **config.py** | 定义 `AgentPlatform` 枚举和 `RoleConfig` 数据类 | 无状态 |
| **protocols.py** | 定义 `Executor` 和 `Parser` 接口协议 | 接口定义 |
| **executors/** | 构建 CLI 命令 + 启动子进程 + 返回原始输出流 | 无状态 |
| **parsers/** | 解析原始输出 + 转换为统一格式 | 无状态 |
| **bridge.py** | 组装 Executor 和 Parser，提供统一接口 | 有状态（缓存实例） |

### 2.3 数据流

```
用户调用
    ↓
bridge.execute_stream(prompt, session_id, config)
    ↓
根据 config.platform 选择 Executor + Parser
    ↓
executor.execute(prompt, session_id, config)
    ↓ 返回原始 JSON 字符串流
parser.parse_event(raw_line)
    ↓ 转换为统一格式
yield 统一事件
    ↓
返回给用户
```

---

## 三、详细设计

### 3.1 config.py - 配置数据类

```python
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

**设计要点**：
- 使用 `Enum` 而非字符串，提供类型安全
- `codex_home` 仅 Codex 平台使用
- 留白字段为未来扩展预留空间

---

### 3.2 protocols.py - 接口协议

```python
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
            session_id: 会话 ID（可选,用于恢复已有会话或指定新会话ID）
            
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

**设计要点**：
- 使用 `Protocol` 定义接口契约（而非抽象类）
- Executor 和 Parser 都是无状态的
- `config` 在执行时传入，而非初始化时
- `session_id` 会话 ID（可选，用于恢复已有会话或指定新会话 ID）

---

### 3.3 executors/ - 执行器

#### ClaudeExecutor

**职责**：
1. 根据 `config` 构建 Claude CLI 命令
2. 启动子进程
3. 返回原始输出流

**关键方法**：
- `execute()` - 主入口
- `_build_command()` - 构建命令行参数
- `_get_skills_path()` - 根据 config.skills 获取 plugin 目录路径

**命令示例**：
```bash
# 新建会话
claude --print --verbose --output-format stream-json \
  --include-partial-messages \
  --append-system-prompt <system_prompt> \
  --plugin-dir <skills_path> \
  <prompt>

# 恢复会话
claude --print --verbose --output-format stream-json \
  --include-partial-messages \
  --append-system-prompt <system_prompt> \
  --plugin-dir <skills_path> \
  --resume <session_id> \
  <prompt>
```

**参数说明**：
- `--print` - 非交互模式，直接输出结果
- `--verbose` - 详细输出（与 stream-json 配合使用）
- `--output-format stream-json` - 流式 JSON 输出
- `--include-partial-messages` - 包含部分消息（逐字输出）
- `--append-system-prompt` - 追加 system prompt
- `--plugin-dir` - 加载指定目录的 plugin（用于 skill）
- `--resume <session_id>` - 恢复之前的会话（可选）
- `--resume <session_id>` - 继续已有会话
- `--session-id <uuid>` - 创建新会话并指定 ID（已存在则报错，不可用于恢复会话）

**会话管理**（已验证）：
- 恢复已有会话 → 使用 `--resume <session_id>`
- 新建会话并指定 ID → 使用 `--session-id <uuid>`（UUID 已存在则报错 `Session ID <uuid> is already in use`）
- 新建会话（系统自动生成 UUID）→ 不传 session 相关参数

#### CodexExecutor

**职责**：
1. 根据 `config.codex_home` 设置 `CODEX_HOME` 环境变量
2. 构建 Codex CLI 命令
3. 启动子进程
4. 返回原始输出流

**关键方法**：
- `execute()` - 主入口
- `_build_command()` - 构建命令行参数
- `_build_env()` - 构建环境变量

**命令示例**：
```bash
# 新建会话
CODEX_HOME=<codex_home> codex exec --json <prompt>

# 恢复会话
CODEX_HOME=<codex_home> codex exec --json --session-id <session_id> <prompt>
```

**参数说明**：
- `CODEX_HOME` - 环境变量，指向角色配置目录
- `exec` - 执行命令
- `--json` - JSON 格式输出（流式）
- `--session-id` - 恢复会话（可选）

**会话管理**：
- 如果有 session_id，使用 `--session-id` 恢复会话
- 如果没有 session_id，创建新会话
- Codex 通过 `CODEX_HOME` 目录下的配置文件控制 skill、权限等

---

### 3.4 parsers/ - 解析器

#### 统一事件格式

所有平台的事件都转换为以下统一格式（使用 TypedDict）：

```python
from typing import TypedDict
from enum import Enum

class AgentEventType(Enum):
    """事件类型枚举，避免字符串拼写错误"""
    INIT = "init"               # 会话开始元数据
    TEXT_DELTA = "text_delta"   # 文本增量（流式输出的主要内容）
    TOOL_USE = "tool_use"       # 工具调用（命令执行）
    TURN_COMPLETE = "turn_complete"  # 回合完成（包含 token 使用统计）
    RESULT = "result"           # 完整结果（非流式输出）

class AgentEvent(TypedDict):
    type: AgentEventType    # 事件类型（使用枚举）
    data: dict              # 具体数据
    session_id: str         # 会话 ID
    timestamp: str          # 时间戳（可选）
```

**事件类型说明**：
- `init` - 会话开始元数据
  - `data`: `{"model": str, "tools": list, ...}`
- `text_delta` - 文本增量（流式输出的主要内容）
  - `data`: `{"text": str}`
- `tool_use` - 工具调用（命令执行）
  - `data`: `{"command": str, "output": str, "exit_code": int, ...}`
- `turn_complete` - 回合完成（包含 token 使用统计）
  - `data`: `{"usage": dict}`
- `result` - 完整结果（非流式 `execute()` 返回，内部拼接所有 `text_delta`）
  - `data`: `{"text": str, "usage": dict}`

**说明**：
- 返回的是**流式事件**，每个事件是解析后的对象
- 用户可以通过 `async for` 逐个接收事件
- 最终结果是所有 `text_delta` 事件的文本拼接

#### ClaudeParser

**职责**：解析 Claude CLI 的流式输出

**事件映射**：
- `stream_event.content_block_delta` → `text_delta`
- `system.init` → `init`
- 其他事件类型...

#### CodexParser

**职责**：解析 Codex CLI 的流式输出

**事件映射**：
- `item.completed (agent_message)` → `text_delta`
- `item.completed (command_execution)` → `tool_use`
- `turn.completed` → `turn_complete`

---

### 3.5 bridge.py - 统一接口

```python
from typing import AsyncIterator, Dict, Any
from .config import RoleConfig, AgentPlatform
from .protocols import Executor, Parser
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

        async for event in self.execute_stream(prompt, config, session_id):
            if event["type"] == AgentEventType.TEXT_DELTA:
                full_text.append(event["data"]["text"])
            elif event["type"] == AgentEventType.TURN_COMPLETE:
                usage = event["data"].get("usage")

        return AgentEvent(
            type=AgentEventType.RESULT,
            data={"text": "".join(full_text), "usage": usage},
            session_id=session_id or "",
            timestamp=""
        )
```

**设计要点**：
- Executor 和 Parser 在初始化时创建，可复用
- 通过字典映射快速选择对应的组件
- 流式处理，不缓存完整结果

---

## 四、使用示例

### 4.1 基本使用

```python
from agent_bridge import AgentBridge, RoleConfig, AgentPlatform, AgentEventType

# 创建 bridge（可复用）
bridge = AgentBridge()

# 创建角色配置
config = RoleConfig(
    platform=AgentPlatform.CLAUDE,
    system_prompt="你是一个代码审查专家",
    skills=["code-review", "security-check"]
)

# 流式调用 - 给人看（新建会话）
async for event in bridge.execute_stream(
    prompt="审查这段代码",
    config=config
):
    if event["type"] == AgentEventType.TEXT_DELTA:
        print(event["data"]["text"], end="", flush=True)

# 流式调用 - 恢复会话
async for event in bridge.execute_stream(
    prompt="继续审查",
    config=config,
    session_id="session_123"
):
    handle_event(event)

# 非流式调用 - 给 A2A 用（返回完整结果）
result = await bridge.execute(
    prompt="审查这段代码",
    config=config
)
# result["type"] == AgentEventType.RESULT
# result["data"]["text"] == "完整审查结果文本"
print(result["data"]["text"])
```

### 4.2 多角色使用

```python
# 创建多个角色配置
reviewer_config = RoleConfig(
    platform=AgentPlatform.CLAUDE,
    system_prompt="你是代码审查专家",
    skills=["code-review"]
)

developer_config = RoleConfig(
    platform=AgentPlatform.CODEX,
    system_prompt="你是前端开发专家",
    skills=["frontend-dev"],
    codex_home="/path/to/frontend-developer"
)

# 同一个 bridge 可以服务多个角色
bridge = AgentBridge()

# 角色 1（新建会话）
async for event in bridge.execute_stream("审查代码", reviewer_config):
    handle_event(event)

# 角色 2（恢复会话）
async for event in bridge.execute_stream("优化组件", developer_config, session_id="xxx"):
    handle_event(event)
```

---

## 五、扩展性设计

### 5.1 添加新平台

假设要添加 OpenCode 平台：

**步骤 1**：在 `config.py` 添加枚举值

```python
class AgentPlatform(Enum):
    CLAUDE = "claude"
    CODEX = "codex"
    OPENCODE = "opencode"  # 新增
```

**步骤 2**：新增 `executors/opencode.py`

```python
class OpenCodeExecutor:
    async def execute(self, prompt: str, session_id: str, config: RoleConfig):
        # 实现 OpenCode 的执行逻辑
        pass
```

**步骤 3**：新增 `parsers/opencode.py`（或复用已有 Parser）

```python
class OpenCodeParser:
    def parse_event(self, raw_line: str) -> Dict[str, Any]:
        # 实现 OpenCode 的解析逻辑
        pass
```

**步骤 4**：在 `bridge.py` 添加映射

```python
self._executors = {
    AgentPlatform.CLAUDE: ClaudeExecutor(),
    AgentPlatform.CODEX: CodexExecutor(),
    AgentPlatform.OPENCODE: OpenCodeExecutor()  # 新增
}
self._parsers = {
    AgentPlatform.CLAUDE: ClaudeParser(),
    AgentPlatform.CODEX: CodexParser(),
    AgentPlatform.OPENCODE: OpenCodeParser()  # 新增
}
```

### 5.2 复用场景

如果 OpenCode 的输出格式与 Claude 相同，可以直接复用 Parser：

```python
self._parsers = {
    AgentPlatform.CLAUDE: ClaudeParser(),
    AgentPlatform.CODEX: CodexParser(),
    AgentPlatform.OPENCODE: ClaudeParser()  # 复用 ClaudeParser
}
```

---

## 六、测试策略

### 6.1 单元测试

**测试 Parser（独立测试）**：

```python
def test_claude_parser():
    parser = ClaudeParser()
    raw_line = '{"type":"stream_event","event":{"type":"content_block_delta","delta":{"text":"测试"}}}'
    event = parser.parse_event(raw_line)
    
    assert event["type"] == "text_delta"
    assert event["data"]["text"] == "测试"
```

**测试 Executor（Mock 子进程）**：

```python
async def test_claude_executor():
    executor = ClaudeExecutor()
    config = RoleConfig(
        platform=AgentPlatform.CLAUDE,
        system_prompt="测试",
        skills=[]
    )
    
    # Mock subprocess
    with patch('asyncio.create_subprocess_exec') as mock_exec:
        # 测试命令构建逻辑
        pass
```

### 6.2 集成测试

**测试完整流程**：

```python
async def test_bridge_integration():
    bridge = AgentBridge()
    config = RoleConfig(
        platform=AgentPlatform.CLAUDE,
        system_prompt="测试",
        skills=[]
    )
    
    events = []
    async for event in bridge.execute_stream("测试", "session_1", config):
        events.append(event)
    
    assert len(events) > 0
    assert all(isinstance(e, dict) for e in events)
```

---

## 七、未来扩展

### 7.1 留白功能

以下功能已在设计中预留空间，但暂不实现：

1. **错误处理与重试**
   - 网络错误重试
   - CLI 崩溃处理
   - 超时控制

2. **权限控制**
   - `RoleConfig.permissions` 字段
   - 工具白名单/黑名单

3. **工具配置**
   - `RoleConfig.tools` 字段
   - 自定义工具集

### 7.2 性能优化

未来可能的优化方向：

1. **连接池**：复用 CLI 进程，避免频繁启动
2. **缓存机制**：缓存常用配置的解析结果
3. **并发控制**：限制同时运行的 CLI 进程数量

---

## 八、设计决策记录

### 8.1 为什么选择扁平化架构？

**决策**：采用扁平化架构（方案 B），而非继承架构（方案 A）

**理由**：
1. Claude 和 Codex 差异较大，几乎没有可复用的公共逻辑
2. 职责分离带来更好的可测试性
3. 为未来的复用场景留下空间（Parser 可独立复用）
4. 符合"先做简单"的原则

**参考文档**：`docs/temp/研究报告/agent-bridge-architecture-comparison.md`

### 8.2 为什么 config 在执行时传入？

**决策**：`config` 作为 `execute()` 的参数，而非在初始化时传入

**理由**：
1. Executor 和 Parser 应该是无状态的工具类
2. 一个实例可以服务多个角色，提高复用性
3. 更符合"纯执行层"的定位

### 8.3 为什么提供流式和非流式两种接口？

**决策**：底层统一流式输出，上层提供 `execute_stream()`（流式）和 `execute()`（非流式）两种接口

**理由**：
1. Codex 的非流式输出格式不好解析，底层统一走流式更可靠
2. 用户交互场景需要流式输出（实时显示）
3. A2A 场景（主 Agent 调用 Sub Agent）只需要完整结果，流式反而增加复杂度
4. `execute()` 是 `execute_stream()` 的包装，不重复实现解析逻辑
5. 通过 `AgentEventType.RESULT` 区分非流式返回，格式统一

### 8.4 为什么使用枚举定义事件类型？

**决策**：使用 `AgentEventType(Enum)` 定义事件类型，而非裸字符串

**理由**：
1. 避免字符串拼写错误（`text_dleta` 静默失败）
2. IDE 自动补全，开发体验好
3. 类型检查工具可以静态发现错误
4. 事件类型是固定集合，适合用枚举

### 8.5 为什么使用 Protocol 而非抽象类？

**决策**：使用 `Protocol` 定义接口，而非 `ABC` 抽象类

**理由**：
1. Protocol 更轻量，不需要显式继承
2. 支持结构化子类型（structural subtyping）
3. 更符合 Python 的"鸭子类型"哲学

---

## 九、实现计划

### 9.1 实现顺序

1. **Phase 1：基础框架**
   - `config.py` - 配置数据类
   - `protocols.py` - 接口定义
   - `bridge.py` - 统一接口（空实现）

2. **Phase 2：Claude 平台**
   - `executors/claude.py` - Claude 执行器
   - `parsers/claude.py` - Claude 解析器
   - 集成到 `bridge.py`

3. **Phase 3：Codex 平台**
   - `executors/codex.py` - Codex 执行器
   - `parsers/codex.py` - Codex 解析器
   - 集成到 `bridge.py`

4. **Phase 4：测试与文档**
   - 单元测试
   - 集成测试
   - 使用文档

### 9.2 预估工作量

| 阶段 | 预估时间 | 优先级 |
|------|---------|--------|
| Phase 1 | 2 小时 | P0 |
| Phase 2 | 4 小时 | P0 |
| Phase 3 | 4 小时 | P0 |
| Phase 4 | 3 小时 | P1 |

**总计**：约 13 小时

---

## 十、参考文档

1. **架构对比研究**：`docs/temp/研究报告/agent-bridge-architecture-comparison.md`
2. **CLI 输出研究**：`docs/temp/研究报告/claude-codex-cli-output-analysis.md`
3. **Claude CLI 配置研究**：`docs/temp/研究报告/claude-cli-config-override-research.md`
4. **Claude CLI 最小命令集**：`docs/temp/研究报告/claude-cli-minimal-command-set.md`
5. **Codex 配置策略**：`docs/design-decisions/2026-05-23-codex-system-prompt-strategy.md`

---

**设计完成时间**: 2026-05-23  
**设计人员**: 用户、Claude Opus 4.7  
**审查人员**: Subagent (Opus)
