# Claude Code Python SDK (Agent SDK) 能力调研

**研究日期**: 2026-05-23
**研究目标**: 调研 Claude Code Python SDK 的完整能力，对比 CLI 原生功能，评估其在 agents-hub 中的应用价值。
**研究结论**: Claude Agent SDK (`claude-agent-sdk`) 是对 Claude Code CLI 的 Python 封装，继承了 CLI 的全部内置工具和 agentic 循环能力，并额外提供 in-process 自定义工具、程序化子代理、会话持久化适配器等 CLI 不具备的能力。适合将 Claude Code 能力嵌入 Python 应用。

---

## 一、概述

### 1.1 两个包的区别

| 包名 | 导入名 | 封装层级 | 定位 |
|------|--------|---------|------|
| `anthropic` | `anthropic` | 直接 HTTP API | 调用 Claude 模型，自己管理工具和 agent 循环 |
| `claude-agent-sdk` | `claude_agent_sdk` | Claude Code CLI 子进程 | 复用 Claude Code 全部 agentic 能力 |

`claude-agent-sdk` 内部启动 Claude Code CLI 作为子进程，通过 JSON 协议通信。CLI 已内置在包中，无需单独安装。

- **GitHub**: `anthropics/claude-code-sdk-python`
- **PyPI**: `pip install claude-agent-sdk`
- **Python**: 3.10+
- **License**: MIT

---

## 二、核心 API

### 2.1 `query()` — 简单异步生成器

单次调用，返回异步消息流：

```python
import anyio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock

async def main():
    async for message in query(prompt="分析 src/main.py 的代码质量"):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)

anyio.run(main)
```

### 2.2 `ClaudeSDKClient` — 双向流式客户端

支持多轮对话、中断、自定义工具：

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async with ClaudeSDKClient() as client:
    await client.query("分析项目架构")
    async for msg in client.receive_response():
        print(msg)

    # 同一会话内继续
    await client.query("有哪些改进建议？")
    async for msg in client.receive_response():
        print(msg)
```

关键方法：

| 方法 | 说明 |
|------|------|
| `query(prompt)` | 发送消息 |
| `receive_response()` | 异步迭代器，返回当前轮次响应 |
| `receive_messages()` | 异步迭代器，返回所有消息 |
| `interrupt()` | 中断当前操作 |
| `get_server_info()` | 获取服务器元数据 |

---

## 三、`ClaudeAgentOptions` 配置项

| 字段 | 类型 | 说明 |
|------|------|------|
| `system_prompt` | `str \| dict` | 自定义系统提示，支持 `{"type": "preset", "preset": "claude_code", "append": "..."}` |
| `max_turns` | `int` | 限制 agentic 轮次 |
| `max_budget_usd` | `float` | 成本上限（超限停止） |
| `allowed_tools` | `list[str]` | 自动批准的工具列表，如 `["Read", "Write", "Bash"]` |
| `disallowed_tools` | `list[str]` | 禁用的工具列表 |
| `permission_mode` | `str` | `"default"` / `"acceptEdits"` / `"plan"` / `"bypassPermissions"` / `"dontAsk"` / `"auto"` |
| `cwd` | `str` | 工作目录 |
| `model` | `str` | 模型，如 `"sonnet"` / `"claude-sonnet-4-6"` |
| `effort` | `str` | `"low"` / `"medium"` / `"high"` / `"xhigh"` / `"max"` |
| `agents` | `dict` | 程序化子代理定义 |
| `mcp_servers` | `dict` | MCP 服务器（in-process SDK + 外部 stdio） |
| `hooks` | `dict` | Hook 拦截器 |
| `env` | `dict` | 环境变量 |
| `setting_sources` | `list[str]` | 设置来源 `["user", "project", "local"]` |
| `skills` | — | 控制可用 skills |
| `cli_path` | `str` | 自定义 CLI 路径 |

---

## 四、SDK 独有能力（CLI 不具备）

### 4.1 In-Process 自定义工具

通过 `@tool` 装饰器定义 Python 函数作为工具，无子进程开销：

```python
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions, ClaudeSDKClient

@tool("greet", "Greet a user", {"name": str})
async def greet_user(args):
    return {"content": [{"type": "text", "text": f"Hello, {args['name']}!"}]}

server = create_sdk_mcp_server(name="my-tools", version="1.0.0", tools=[greet_user])

options = ClaudeAgentOptions(
    mcp_servers={"tools": server},
    allowed_tools=["mcp__tools__greet"]
)

async with ClaudeSDKClient(options=options) as client:
    await client.query("Greet Alice")
    async for msg in client.receive_response():
        print(msg)
```

可与外部 stdio MCP 服务器混合使用。

### 4.2 程序化子代理

在代码中定义专业化子代理，无需文件系统配置：

```python
from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query

options = ClaudeAgentOptions(
    agents={
        "code-reviewer": AgentDefinition(
            description="Reviews code for best practices",
            prompt="你是一个代码审查专家。分析代码中的 bug 和安全问题。",
            tools=["Read", "Grep"],
            model="sonnet",
        ),
    },
)

async for message in query(
    prompt="Use the code-reviewer agent to review src/main.py",
    options=options,
):
    ...
```

### 4.3 会话持久化适配器

内置示例适配器，支持跨重启的会话持久化：

| 适配器 | 位置 |
|--------|------|
| S3 | `examples/session_stores/s3_session_store.py` |
| Redis | `examples/session_stores/redis_session_store.py` |
| PostgreSQL | `examples/session_stores/postgres_session_store.py` |

支持 `fork_session` 进行会话分支。

### 4.4 精细化 Hook 控制

在代码中拦截工具执行，比 CLI 的 settings.json 配置更灵活：

```python
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, HookMatcher

async def check_bash(input_data, tool_use_id, context):
    if input_data["tool_name"] != "Bash":
        return {}
    command = input_data["tool_input"].get("command", "")
    if "forbidden" in command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Command is forbidden",
            }
        }
    return {}

options = ClaudeAgentOptions(
    allowed_tools=["Bash"],
    hooks={"PreToolUse": [HookMatcher(matcher="Bash", hooks=[check_bash])]},
)
```

Hook 事件类型：

| 事件 | 说明 |
|------|------|
| `PreToolUse` | 工具执行前（可 deny/allow/defer） |
| `PostToolUse` | 工具执行后（可修改输出、停止执行） |
| `UserPromptSubmit` | 用户提示提交时（可注入上下文） |
| `SessionStart` | 会话初始化 |

---

## 五、消息类型

| 类型 | 说明 |
|------|------|
| `AssistantMessage` | Claude 的响应（包含 `TextBlock`、`ToolUseBlock`） |
| `UserMessage` | 用户输入（包含 `TextBlock`、`ToolResultBlock`） |
| `SystemMessage` | 系统级消息 |
| `ResultMessage` | 轮次结束结果（包含 `total_cost_usd`、`subtype`、`api_error_status`） |

---

## 六、错误处理

```python
from claude_agent_sdk import (
    ClaudeSDKError,      # 基础错误
    CLINotFoundError,    # CLI 未找到
    CLIConnectionError,  # 连接问题
    ProcessError,        # 进程失败（有 .exit_code）
    CLIJSONDecodeError,  # JSON 解析问题
)
```

---

## 七、CLI vs SDK 完整对比

### 7.1 功能覆盖

| 能力 | CLI | SDK | 说明 |
|------|:---:|:---:|------|
| 交互式 REPL | ✅ | ❌ | CLI 核心体验 |
| Headless 模式 (`-p`) | ✅ | ✅ | SDK 本质封装 `-p` |
| 流式输出 | ✅ | ✅ | CLI: `--output-format stream-json`，SDK: `query()` |
| 内置工具 (Read/Write/Edit/Bash/Grep/Glob) | ✅ | ✅ | SDK 继承全部 |
| In-process 自定义工具 (`@tool`) | ❌ | ✅ | SDK 独有 |
| 外部 MCP 服务器 | ✅ | ✅ | CLI: `claude mcp add`，SDK: `mcp_servers` |
| Hooks | ✅ | ✅ | CLI: settings.json，SDK: 代码级 `HookMatcher` |
| 子代理 | ✅ | ✅ | CLI: `--agents`，SDK: `AgentDefinition` |
| 会话管理 (resume/fork) | ✅ | ✅ | CLI: `-c`/`-r`/`--fork-session`，SDK: `ClaudeSDKClient` |
| 会话持久化 (S3/Redis/PG) | ❌ | ✅ | SDK 独有 |
| Slash 命令 / Skills | ✅ | ❌ | CLI 交互式专属 |
| 插件系统 | ✅ | ❌ | `claude plugin` |
| MCP Server 模式 | ✅ | ❌ | `claude mcp serve` |
| Ultrareview | ✅ | ❌ | 云端多代理代码审查 |
| IDE 集成 | ✅ | ❌ | VS Code / JetBrains |
| Git Worktree 隔离 | ✅ | ❌ | `claude -w` |
| 权限模式 | ✅ | ✅ | `permission_mode` |
| 成本控制 | ✅ | ✅ | `max_budget_usd` |
| 结构化输出 (JSON Schema) | ✅ | ✅ | CLI: `--json-schema`，SDK: 消息解析 |
| 模型选择 | ✅ | ✅ | `model` / `--model` |
| Effort 控制 | ✅ | ✅ | `effort` / `--effort` |
| 认证管理 | ✅ | ❌ | `claude auth` |
| 健康检查 | ✅ | ❌ | `claude doctor` |
| Remote Control | ✅ | ❌ | `--remote-control` |
| 通知推送 | ✅ | ❌ | `PushNotification` 工具 |
| 定时任务 | ✅ | ❌ | `CronCreate` / `CronDelete` |
| 后台监控 | ✅ | ❌ | `Monitor` 工具 |

### 7.2 选择决策树

```
需要什么？

├── 交互式开发 / 终端操作
│   └── CLI
│       ├── 日常编码 → `claude` REPL
│       ├── 简单脚本 → `claude -p "prompt"`
│       ├── MCP/插件管理 → `claude mcp` / `claude plugin`
│       └── IDE 集成 → VS Code / JetBrains 扩展
│
├── 编程集成 / Python 应用
│   └── SDK
│       ├── 单次调用 → `query()`
│       ├── 多轮对话 → `ClaudeSDKClient`
│       ├── 自定义工具 → `@tool` + `create_sdk_mcp_server`
│       └── 持久化会话 → S3/Redis/PG 适配器
│
└── 混合场景
    └── 开发用 CLI，部署用 SDK
```

---

## 八、与 agents-hub 的关系

### 8.1 当前 agents-hub 架构

```text
AgentBridge
  -> ClaudeCodeExecutor
  -> claude.cmd -p --output-format stream-json <prompt>
  -> ClaudeCodeParser
  -> AgentEvent
```

### 8.2 SDK 迁移路径

如果采用 SDK，架构变为：

```text
AgentBridge
  -> ClaudeSDKExecutor (使用 claude-agent-sdk)
  -> claude_agent_sdk.query(prompt=...)
  -> SDK 消息流 (AssistantMessage / ResultMessage)
  -> AgentEvent
```

### 8.3 迁移收益

| 收益 | 说明 |
|------|------|
| 结构化消息 | SDK 返回类型化对象，无需解析 JSON 流 |
| In-process 工具 | 可将 agents-hub 的能力注册为 Claude 可调用的工具 |
| 程序化子代理 | 可在代码中定义专业化的审查/测试代理 |
| 会话持久化 | 复用 SDK 的 S3/Redis/PG 适配器 |
| 错误处理 | 类型化异常，比解析 stderr 更可靠 |

### 8.4 迁移成本

| 成本 | 说明 |
|------|------|
| 新依赖 | 引入 `claude-agent-sdk` 包 |
| API 差异 | 消息类型和事件模型需要适配 |
| 子进程管理 | SDK 内部仍启动 CLI 子进程，调试链路变长 |
| 版本耦合 | SDK 版本与 CLI 版本绑定 |

---

## 九、参考资源

- **GitHub**: https://github.com/anthropics/claude-code-sdk-python
- **Demos**: https://github.com/anthropics/claude-agent-sdk-demos（含 email agent、Excel demo、研究代理等）
- **文档**: https://platform.claude.com/docs/en/agent-sdk/python
- **PyPI**: `pip install claude-agent-sdk`
