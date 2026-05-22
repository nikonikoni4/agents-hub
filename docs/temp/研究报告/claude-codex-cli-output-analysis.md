# Claude Code 和 Codex CLI 输出格式研究报告

## 概述

本报告分析了 Claude Code 和 Codex CLI 的流式与非流式输出格式，说明各种输出的特点和包含的字段信息。

---

## 一、Claude Code 输出格式

### 1.1 非流式输出 (`-p`)

**特点：**
- 纯文本格式
- 只包含最终回答内容
- 不显示思考过程、工具调用、元数据
- 适合快速查询和脚本集成

**包含字段：**
- 最终回答文本（纯文本）

**示例：**
```
在 Claude Code CLI 中，我的 `<thinking>` 思考过程**默认不会显示**给用户。

具体行为：
- **流式输出**：你看到的是我的最终回答文本和工具调用结果，思考过程在后台进行
- **非流式输出**：同样只显示最终输出，不包含 `<thinking>` 标签内的内容
```

---

### 1.2 流式输出 (`-p --verbose --output-format=stream-json --include-partial-messages`)

**特点：**
- JSON Lines 格式（每行一个 JSON 对象）
- 包含完整的事件流
- 实时推送内容增量
- 包含丰富的元数据

**示例：**

```json
{"type":"system","subtype":"hook_started","hook_id":"...","hook_name":"SessionStart:startup","hook_event":"SessionStart","uuid":"6044579f-54ac-4faf-bb53-ea9d926a6ae1","session_id":"..."}
{"type":"system","subtype":"hook_response","hook_id":"...","hook_name":"SessionStart:startup","hook_event":"SessionStart","output":"...","stdout":"...","stderr":"","exit_code":0,"outcome":"success","uuid":"7ee9abbe-c682-4dc8-8ce8-4ea64f3f8920","session_id":"..."}
{"type":"system","subtype":"init","cwd":"D:\\desktop\\软件开发\\agents-hub","session_id":"...","tools":["Task","AskUserQuestion","Bash",...],"mcp_servers":[{"name":"MiniMax","status":"connected"}],"model":"claude-opus-4-7[1m]","permissionMode":"auto","slash_commands":["ai-news-push",...],"memory_paths":{"auto":"C:\\Users\\15535\\.claude\\projects\\..."},"fast_mode_state":"off"}
{"type":"system","subtype":"status","status":"requesting","uuid":"...","session_id":"..."}
{"type":"stream_event","event":{"type":"message_start","message":{"id":"msg_20260523032028","content":[],"model":"claude-opus-4-7","usage":{"input_tokens":1,"output_tokens":1,"cache_creation_input_tokens":47863,"cache_read_input_tokens":0},"stop_reason":null,"type":"message","role":"assistant"}},"session_id":"...","parent_tool_use_id":null,"uuid":"...","ttft_ms":2816}
{"type":"stream_event","event":{"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"index":0,"delta":{"type":"text_delta","text":"不"},"type":"content_block_delta"},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"会"}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"显"}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"text":"示。\n\n我","type":"text_delta"}},"session_id":"...","parent_tool_use_id":null,"uuid":"..."}
```

**事件类型：**

| 事件类型 | subtype | 说明 |
|---------|---------|------|
| `system` | `hook_started` | Hook 开始执行 |
| `system` | `hook_response` | Hook 执行完成，包含输出 |
| `system` | `init` | 会话初始化信息 |
| `system` | `status` | 状态变更（requesting 等） |
| `stream_event` | `message_start` | 消息开始，包含 token 使用统计 |
| `stream_event` | `content_block_start` | 内容块开始 |
| `stream_event` | `content_block_delta` | 内容增量（逐字输出） |
| `stream_event` | `content_block_stop` | 内容块结束 |
| `stream_event` | `message_delta` | 消息元数据更新 |
| `stream_event` | `message_stop` | 消息结束 |

**关键字段：**

**system.init 事件包含：**
- `cwd` - 工作目录
- `session_id` - 会话 ID
- `tools` - 可用工具列表
- `mcp_servers` - MCP 服务器列表（name, status）
- `model` - 模型名称
- `permissionMode` - 权限模式
- `slash_commands` - 可用的 slash 命令
- `memory_paths` - 内存路径
- `claude_code_version` - CLI 版本
- `agents` - 可用的 agent 列表
- `skills` - 可用的 skill 列表
- `plugins` - 已加载的插件列表

**stream_event.message_start 包含：**
- `message.id` - 消息 ID
- `message.model` - 模型名称
- `message.usage` - Token 使用统计
  - `input_tokens` - 输入 token 数
  - `output_tokens` - 输出 token 数
  - `cache_creation_input_tokens` - 缓存创建 token 数
  - `cache_read_input_tokens` - 缓存读取 token 数
- `ttft_ms` - Time to first token（首字延迟）

**stream_event.content_block_delta 包含：**
- `index` - 内容块索引
- `delta.type` - 增量类型（text_delta）
- `delta.text` - 增量文本内容
- `session_id` - 会话 ID
- `parent_tool_use_id` - 父工具调用 ID（如果有）
- `uuid` - 事件唯一标识

---

## 二、Codex CLI 输出格式

### 2.1 非流式输出 (`codex exec`)

**特点：**
- 格式化的文本输出
- 包含完整的工作日志
- 显示会话元数据、工具调用、Agent 思考过程
- 适合调试和审计

**输出结构：**

```
┌─────────────────────────────────────┐
│ 1. 会话元数据区                      │
│    - CLI 版本、模型、配置信息         │
├─────────────────────────────────────┤
│ 2. 对话交互区                        │
│    - user: 用户输入                  │
│    - codex: Agent 工作说明           │
├─────────────────────────────────────┤
│ 3. 工具执行区                        │
│    - exec: 命令                      │
│    - succeeded/failed: 结果          │
│    - 完整的 stdout 输出              │
├─────────────────────────────────────┤
│ 4. Agent 回复区                      │
│    - codex: 最终回答                 │
│    - tokens used: Token 统计         │
└─────────────────────────────────────┘
```

**包含字段：**

**1. 会话元数据区：**
- `version` - CLI 版本（如 "OpenAI Codex v0.133.0"）
- `workdir` - 工作目录
- `model` - 使用的模型
- `provider` - 提供商
- `approval` - 审批模式
- `sandbox` - 沙箱权限
- `reasoning effort` - 推理强度
- `reasoning summaries` - 推理摘要设置
- `session id` - 会话 ID

**2. 对话交互区：**
- 角色标识：`user` 或 `codex`（单独一行）
- 消息内容：角色标识后的所有行，直到下一个角色标识

**3. 工具执行区：**
- `exec` - 工具调用标识（单独一行）
- 命令行：完整的命令字符串（通常以引号开头）
- 执行结果：`succeeded in Xms:` 或 `failed in Xms:`
- 输出内容：`---` 分隔符后的所有内容，直到下一个 `codex` 标识

**4. Agent 回复区：**
- `codex` - 角色标识
- 回答内容：多行文本
- `tokens used` - Token 统计标识（单独一行）
- Token 数量：下一行的数字（可能包含逗号分隔符）

**可提取的信息：**
1. **对话内容** - 所有 user 和 codex 的消息
2. **Agent 思考过程** - 工具调用前的 codex 消息（工作说明）
3. **工具调用** - exec 块中的命令、执行时间、输出结果
4. **Token 使用** - tokens used 后的数字
5. **最终答案** - 最后一个 codex 消息

---

### 2.2 流式输出 (`codex exec --json`)

**特点：**
- JSON Lines 格式
- 事件驱动模型
- 实时推送工具执行和消息

**示例：**

```json
{"type":"thread.started","thread_id":"019e5122-2a0e-7c61-a26b-19c036bf9315"}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"我会先按当前会话规则加载 `superpowers:using-superpowers`，确认这类问题不需要额外项目文件读取。"}}
{"type":"item.started","item":{"id":"item_1","type":"command_execution","command":"\"C:\\\\Program Files\\\\PowerShell\\\\7\\\\pwsh.exe\" -Command \"Get-Content -LiteralPath '...'\"","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_1","type":"command_execution","command":"\"C:\\\\Program Files\\\\PowerShell\\\\7\\\\pwsh.exe\" -Command \"Get-Content -LiteralPath '...'\"","aggregated_output":"---\r\nname: using-superpowers\r\n...","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"不会。\n\n在这个 CLI/API 环境里，我的隐藏思考过程不会出现在流式或非流式输出中..."}}
{"type":"turn.completed","usage":{"input_tokens":24773,"cached_input_tokens":11264,"output_tokens":322,"reasoning_output_tokens":0}}
```

**事件类型：**

| 事件类型 | 说明 |
|---------|------|
| `thread.started` | 线程开始，包含 thread_id |
| `turn.started` | 回合开始 |
| `turn.completed` | 回合结束，包含 token 使用统计 |
| `item.started` | 项目开始（消息或工具调用） |
| `item.completed` | 项目完成 |

**Item 类型：**

| item.type | 说明 |
|-----------|------|
| `agent_message` | Agent 发送的消息 |
| `command_execution` | 命令执行（工具调用） |

**关键字段：**

**thread.started 包含：**
- `thread_id` - 线程 ID

**item.completed (agent_message) 包含：**
- `item.id` - 项目 ID
- `item.type` - 类型（"agent_message"）
- `item.text` - 消息内容

**item.started (command_execution) 包含：**
- `item.id` - 项目 ID
- `item.type` - 类型（"command_execution"）
- `item.command` - 执行的命令
- `item.aggregated_output` - 聚合输出（进行中为空）
- `item.exit_code` - 退出码（进行中为 null）
- `item.status` - 状态（"in_progress"）

**item.completed (command_execution) 包含：**
- `item.id` - 项目 ID
- `item.type` - 类型（"command_execution"）
- `item.command` - 执行的命令
- `item.aggregated_output` - 完整输出
- `item.exit_code` - 退出码
- `item.status` - 状态（"completed" 或 "failed"）

**turn.completed 包含：**
- `usage.input_tokens` - 输入 token 数
- `usage.cached_input_tokens` - 缓存输入 token 数
- `usage.output_tokens` - 输出 token 数
- `usage.reasoning_output_tokens` - 推理输出 token 数

---

## 三、输出对比总结

### 3.1 输出特点对比

| 特性 | Claude 非流式 | Claude 流式 | Codex 非流式 | Codex 流式 |
|-----|-------------|-----------|------------|----------|
| **格式** | 纯文本 | JSON Lines | 格式化文本 | JSON Lines |
| **元数据** | ❌ | ✅ 丰富 | ✅ 基础 | ✅ 基础 |
| **思考过程** | ❌ | ❌ | ✅ | ❌ |
| **工具调用** | ❌ | ✅ | ✅ 详细 | ✅ |
| **Token 统计** | ❌ | ✅ 详细 | ✅ 总计 | ✅ 详细 |
| **实时性** | ❌ | ✅ | ❌ | ✅ |
| **易解析性** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |

### 3.2 使用场景建议

**Claude Code 非流式：**
- ✅ 快速查询、脚本集成
- ✅ 只需要最终答案
- ❌ 需要调试信息

**Claude Code 流式：**
- ✅ 实时监控执行过程
- ✅ 需要详细的元数据
- ✅ 构建交互式应用

**Codex 非流式：**
- ✅ 调试和审计
- ✅ 需要完整的工作日志
- ✅ 理解 Agent 决策过程

**Codex 流式：**
- ✅ 实时监控
- ✅ 事件驱动应用
- ✅ 需要结构化数据

---

## 四、Codex 非流式解析要点

### 4.1 需要提取的信息

如果要解析 Codex 非流式输出，需要提取以下信息：

1. **对话内容**
   - 识别 `user` 和 `codex` 角色标识
   - 提取每个角色的消息内容

2. **Agent 思考过程**
   - 提取工具调用前的 codex 消息
   - 这些消息说明了 Agent 的工作计划

3. **工具调用**
   - 识别 `exec` 标识
   - 提取命令字符串
   - 提取执行结果（succeeded/failed）
   - 提取执行时间（Xms）
   - 提取工具输出内容（`---` 后的内容）
   - 格式化为：`{tool_call: "命令", tool_call_result: "输出"}`

4. **Token 使用**
   - 识别 `tokens used` 标识
   - 提取下一行的数字（去除逗号）

5. **最终答案**
   - 提取最后一个 codex 消息的内容

### 4.2 解析难点

1. **状态跟踪**
   - 需要跟踪当前处于哪个区域（元数据、对话、工具、回复）
   - 通过关键字切换状态

2. **角色识别**
   - 单独一行的 `user` 或 `codex` 表示角色切换
   - 后续行直到下一个角色标识都属于当前角色

3. **工具调用边界**
   - `exec` 开始，下一个 `codex` 结束
   - 中间包含命令、结果、输出

4. **内容去重**
   - Codex 可能输出重复内容
   - 需要检测并合并重复的消息

---

## 五、核心发现

1. **思考过程不可见**：两个 CLI 都不会在输出中显示内部推理过程（`<thinking>` 标签）
2. **格式差异明显**：Claude 简洁，Codex 详细
3. **流式输出统一**：都使用 JSON Lines 格式，易于解析
4. **非流式差异大**：Claude 纯文本，Codex 结构化文本

---

## 六、统一管理可行性

✅ **完全可行**

通过设计统一的数据结构，可以：
- 屏蔽不同 CLI 的格式差异
- 提供一致的 API 访问输出数据
- 支持灵活的数据提取和转换

**建议的统一数据结构应包含：**
- 元数据（CLI 类型、模式、会话 ID、模型等）
- 对话内容（角色、消息）
- 思考过程（可选，仅 Codex 非流式）
- 工具调用（命令、结果、状态、耗时）
- Token 使用统计
- 最终答案

---

**报告完成时间：** 2026-05-23  
**测试数据来源：** `tests/explore/claude_codex_cli_output/outputs/`  
**相关文件：** `test-cli-output.ps1`, `compare-outputs.ps1`
