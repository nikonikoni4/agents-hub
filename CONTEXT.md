# Agents-hub 术语表

## 核心实体

### Agent（智能体）
- 系统的基本执行单元，所有 Agent 的基类
- 属性：role_config、name、role_type、message_queue、group_chat_context、agent_context
- 职责：接收消息、执行任务、返回结果
- 支持两种执行模式：主会话（群聊）和单聊（btw）

### Manager（管理者）
- 继承自 Agent，角色类型为 LEADER
- 职责：协调 Worker，任务分配和调度
- 状态：设计中，尚未完全实现

### Worker（工作者）
- 继承自 Agent，角色类型为 TEAM_MEMBER
- 职责：执行具体任务
- 状态：设计中，尚未完全实现

### GroupChatContext（群聊上下文）
- 群聊业务逻辑的核心管理器
- 职责：消息管理、session 管理、上下文压缩
- 属性：group_chat_id、repository、group_chat_session、agent_session_id

### GroupChatSession（群聊会话）
- 管理群聊的消息历史和元数据
- 属性：group_chat_id、name、messages、created_at、updated_at、last_compacted_loc
- 支持消息压缩和增量加载

## 通信系统

### AgentMessage（智能体消息）
- Agent 之间传递的消息结构
- 属性：call_id、content、send_from、send_to、session_type、message_type、timestamp
- session_type：MAIN（群聊）或 BTW（单聊）
- message_type：TASK（需要回复）或 NOTIFICATION（不需要回复）
- **content 不可变约定**：在 Agent 之间投递时，content 始终保持原始内容，
  不被预渲染（如包上 `[X] 发送消息给 [Y]:` 之类的包络）。所有渲染都发生在
  Agent 边界（参见 [Renderer](#渲染层renderer)），避免"包络套包络"问题。

### AgentCall（智能体调用）
- 记录一次 Agent 调用的完整信息
- 生命周期：PENDING → RUNNING → COMPLETED/FAILED/TIMEOUT
- 属性：call_id、send_from、send_to、content、message_type、status、result、error
- 用途：跟踪跨 Agent 的异步调用状态

### AgentCallManager（调用管理器）
- 统一管理所有跨 Agent 的异步调用
- 职责：创建调用、更新状态、设置结果/错误
- 存储：内存中的 _calls 字典（call_id → AgentCall）

### MessageRouter（消息路由器）
- 负责 Agent 之间的消息投递
- 管理每个 Agent 的私有消息队列
- 职责：注册/注销 Agent、验证消息、投递消息

## 渲染层（Renderer）

定义 `AgentMessage`（结构化数据）与可读字符串之间的对偶转换。
位于 `agents_hub/core/foundation/renderer.py`，三个纯函数。

### 三个表面

同一条消息在系统中存在三种字符串形态，由对应的渲染函数生成：

| 表面 | 内容 | 渲染函数 | 触发位置 |
|------|------|---------|---------|
| AgentMessage.content | 原始内容（始终不可变） | —— | —— |
| LLM prompt | `[{send_from}] 发送消息给 [{send_to}(你)]: {content}` | `render_for_llm(msg)` | Agent.run() 第 2 步 |
| jsonl / UI 群聊串 | `@{send_to} {content}` | `render_for_chat(send_from, send_to, content)` | Agent.run() 出口 A |
| 前端原始输入 → 结构化 | `@xxx 内容` → `(send_to, content)` | `parse_chat_input(raw)` | 前端→后端边界 |

### 核心约束

1. **AgentMessage.content 永不就地改写**：Agent 之间投递时 content 始终为原文。
2. **渲染只发生在三个边界**：入口（前端→AgentMessage）、LLM 出口、jsonl 出口。
3. **回复方向不预渲染**：worker 回复 manager 时，新构造的 AgentMessage.content
   就是 `result.text` 原文，不带 `[X] 对[Y(你)]的回复:` 包装。下游 agent 的
   `run()` 会用 `render_for_llm` 统一加唯一一层包络。

### 设计动机

避免"包络套包络"：如果在投递前预渲染一层包装，下游 `run()` 又会基于
`render_for_llm` 再加一层，LLM 看到的 prompt 会出现两层嵌套。
统一在出口边界渲染保证 LLM 入站格式唯一。

### parse_chat_input

- 解析前端输入（必须以 `@xxx` 开头），返回 `(send_to, content)`
- 解析失败抛 `InvalidMessageError`，不做兜底（前端契约保证 `@` 选择）

### XML 标签工具

- `wrap_xml(tag, content) -> str`：用 XML 标签单层包裹内容（不嵌套）
- `Tag` 常量集合：约定项目内常用的 LLM prompt 结构标签
  - `INCOMING_MESSAGE`：当前传入消息（`render_for_llm` 输出）
  - `GROUP_HISTORY` / `RECENT_MESSAGES`：历史摘要 / 最近消息（`AgentContext.get_context` 输出）
  - `SUMMARY_OVERALL` / `SUMMARY_FOR_YOU`：摘要内的整体内容 / 针对当前 agent 的内容
- 使用约定：稳定结构用 `Tag` 常量，临时结构直接传 str 字面量
- 嵌套深度遵循 Anthropic 官方建议——只在内容有"自然层级"时嵌套，普通分块用平铺标签

## 上下文管理

### AgentContext（智能体上下文）
- 为 Agent 每次调用提供增量加载的上下文
- 职责：只加载未加载的压缩历史和未压缩消息
- 实现：基于 last_loaded_compact_index 和 last_loaded_message_index 的增量加载

### AgentSessionInfo（会话信息）
- Agent 的会话信息
- 属性：main_session、btw_session、context_state
- main_session：主会话 ID
- btw_session：单聊会话 ID 列表

### AgentContextState（上下文状态）
- Agent 的上下文加载状态
- 属性：last_loaded_compact_index、last_loaded_message_index
- 用于实现增量加载，避免重复加载

### GroupChatRepository（群聊持久化层）
- 负责群聊数据的文件读写和并发控制
- 职责：GroupChatSession 持久化、Agent Session State 持久化、Compact History 持久化
- 并发控制：使用 asyncio.Lock 保护文件读写

## 枚举类型

### SessionType（会话类型）
- MAIN：主会话（群聊）
- BTW：单聊会话（by the way）

### MessageType（消息类型）
- TASK：需要回复的任务
- NOTIFICATION：不需要回复的通知

### CallStatus（调用状态）
- PENDING：已创建，等待执行
- RUNNING：正在执行
- COMPLETED：执行完成
- FAILED：执行失败
- TIMEOUT：执行超时

### RoleType（角色类型）
- LEADER：领导者角色，负责任务分派和协调
- TEAM_MEMBER：团队成员角色，执行具体任务

## 异常体系

### AgentsHubError（基类）
- 所有 agents-hub 错误的基类
- 属性：message、error_code、details
- 方法：to_mcp_response() 转换为 MCP Tool 错误响应格式

### 业务异常
- AgentNotFoundError：Agent 不存在
- GroupChatNotFoundError：GroupChat 不存在
- MessageDeliveryError：消息投递失败
- AgentExecutionError：Agent 执行失败
- AgentTimeoutError：Agent 执行超时

### 验证异常
- InvalidMessageError：消息格式错误

### 系统异常
- FileSystemError：文件系统错误
- CompactionError：压缩失败

## 常量定义

### MAX_TOKEN（压缩阈值）
- 值：1000
- 用途：当未压缩消息的估算 token 数量超过此阈值时，触发压缩

### LOCAL_DATA_PATH（本地数据路径）
- 值：'local_data'
- 用途：本地数据存储的根路径

## agent_bridge 数据模型

### AgentResult（执行结果）
- Agent 非流式调用的返回值
- 属性：text、session_id、timestamp、agent_name、platform、role_type、usage
- 用途：封装 Agent 执行的完整结果

### StreamEvent（流式事件）
- Agent 流式调用的事件格式
- 属性：type、content、session_id、timestamp、agent_name、platform、role_type
- 用途：封装流式输出的增量事件

### AgentEventType（事件类型）
- INIT：会话开始元数据
- TEXT_DELTA：文本增量（流式输出的主要内容）
- TOOL_USE：工具调用（命令执行）
- TURN_COMPLETE：回合完成（包含 token 使用统计）
- RESULT：完整结果（非流式输出）

### AgentPlatform（智能体平台）
- CLAUDE：Claude Code 平台
- CODEX：Codex 平台
- 用途：标识 Agent 所使用的 CLI 工具平台

## 架构分层

### core（核心层）
- **foundation**：基础层（零依赖），提供数据模型、枚举、异常类和常量
- **agent**：智能体层，定义 Agent、Manager、Worker
- **communication**：通信层，提供消息路由、调用管理
- **context**：上下文层，管理群聊上下文、会话状态、持久化

### agent_bridge（桥接层）
- 负责调用 CLI 工具（Claude Code、Codex）
- 提供 execute() 和 execute_stream() 接口
- 不关心业务逻辑、会话管理

### roles（角色管理层）
- 角色配置、skill 管理
- 为 agent_bridge 提供 RoleConfig
- 角色发现机制：扫描 `local_data/agents/*/role.json`

### config（配置层）
- 定义 RoleType、Platform 等枚举类型
- 提供配置验证和类型定义

## 角色配置体系

### RoleConfig（角色配置）
- 面向 agent_bridge 的运行时配置
- 属性：name、platform、description、work_root、role_type、bare
- system_prompt 和 skills 由 CLI 从目录自动加载，不在此配置
- bare：Claude CLI 极简模式，跳过 hooks/LSP/plugin sync/auto-memory/CLAUDE.md 自动发现

### RoleInfo（角色摘要信息）
- 用于列表和摘要场景
- 属性：name、platform、avatar、abilities、type、description、scope
- 不包含完整的配置数据

### SkillInfo（Skill 摘要信息）
- 表示已启用的 Skill 的基本信息
- 属性：id、name、description

### Role（角色实例）
- 单个角色的配置和操作
- 职责：从 role.json 加载配置，构造 RoleConfig
- 属性：role_dir（角色目录路径）

### RoleManager（角色管理器）
- 角色生命周期管理
- 职责：创建、删除、查询、列表功能
- 管理 local_data/agents/ 目录下的所有角色
- 方法：list_roles()、get_role()、create_role()、delete_role()

## 数据存储结构

```
local_data/
├── agents/                        # Agent 工作目录
│   ├── assets/                    # 头像文件统一存放
│   │   └── *.png/jpg/gif/webp
│   └── <role_name>/               # 角色目录
│       ├── role.json              # 角色配置（SSOT）
│       └── work_root/             # 工作目录
│           ├── CLAUDE.md          # Claude 平台 system_prompt
│           ├── AGENTS.md          # Codex 平台 system_prompt
│           ├── settings.json      # Claude 平台配置
│           ├── config.toml        # Codex 平台配置
│           └── skills/            # 已启用的 skills
│               └── <skill_id>/
│                   └── skill.json
│
├── skills/                        # 全局 skill 库
│   └── <skill_id>/
│       └── skill.json
│
└── teams/                         # Team 数据
    └── <team_name>/
        └── <project_path>/
            └── <group_chat_id>/
                ├── <group_chat_id>.jsonl          # 群聊消息历史
                ├── agent_session_state.json       # Agent session 和上下文状态
                └── memory/
                    └── compact_history.jsonl      # 压缩历史
```

## role.json 格式

```json
{
    "name": "角色名称",
    "platform": "claude|codex",
    "description": "角色职责描述",
    "avatar": "头像文件名（位于 assets/ 目录）",
    "abilities": ["能力标签1", "能力标签2"],
    "type": "leader|team_member",
    "scope": ["群聊ID1", "群聊ID2"],
    "skills": ["skill_id1", "skill_id2"]
}
```

## 关键设计决策

1. **Agent 继承体系**：Agent 是基类，Manager 和 Worker 继承自 Agent，通过 RoleType 区分角色
2. **消息驱动**：Agent 之间通过 MessageRouter 投递消息，每个 Agent 有私有消息队列
3. **调用跟踪**：通过 AgentCall 和 AgentCallManager 跟踪跨 Agent 的异步调用状态
4. **增量加载**：AgentContext 实现基于索引的增量加载，避免重复加载历史消息
5. **并发控制**：GroupChatRepository 使用 asyncio.Lock 保护文件读写
6. **压缩机制**：当消息 token 数超过 MAX_TOKEN 时，触发压缩生成摘要
7. **会话管理**：支持主会话（群聊）和单聊（btw）两种模式
8. **异常体系**：统一的异常层次结构，支持 MCP Tool 错误响应格式
9. **角色配置 SSOT**：role.json 是角色配置的唯一来源，RoleConfig 由 role.json 派生
10. **Skill 管理**：全局 skill 库 + 角色级 skill 激活，通过复制实现隔离
11. **头像管理**：头像文件统一存放在 assets/ 目录，角色只存储文件名引用
