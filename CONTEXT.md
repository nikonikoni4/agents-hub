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
- **不变量**：一个 GroupChat / Team 有且仅有一个 Leader（即一个 Manager）
- **默认加载**：每个 GroupChat 在 `_init_agents()` 时始终初始化 Manager，与 `team_members_name` 无关
- 状态：设计中，尚未完全实现

### Worker（工作者）
- 继承自 Agent，角色类型为 TEAM_MEMBER
- 职责：执行具体任务
- 状态：设计中，尚未完全实现

### Team（团队）
- 团队定义，包含 `team_members_name` 列表
- **`team_members_name` 语义**：包含 manager + worker 的完整成员列表
- **初始化分离**：虽然 `team_members_name` 包含所有成员，但在 `GroupChat._init_agents()` 中，manager 和 worker 是分开初始化的
  - Manager：始终由系统默认加载（使用 `config.default_manager_name`），不依赖 `team_members_name` 中是否包含
  - Worker：遍历 `team_members_name`，跳过与 `default_manager_name` 同名的成员后，逐一创建
- **不变量**：每个 GroupChat 有且仅有一个 Manager，由系统自动注入，不需要显式列入 `team_members_name` 也不会导致异常

### GroupChatContext（群聊上下文）
- 群聊业务逻辑的核心管理器
- 职责：消息管理、session 管理、上下文压缩
- 属性：group_chat_id、repository、group_chat_session、agent_member_info

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
- 与 Task 的关系：一个 Task 在执行过程中可能产生 1 个或多个 AgentCall（重试、追问等），通过 `business_task_id` 关联

### Task（任务）
- Manager 对 user 输入进行拆分后产生的工作项，比 AgentCall 高一层
- **不变量**：每个 Task 有且只有一个 owner（一个 Worker），多个 Worker 之间的 Task 必须正交（无重叠职责）
- **状态机独立性**：Task 状态机与 AgentCall 状态机相互独立，AgentCall.COMPLETED ≠ Task.COMPLETED。
  例：Worker 回复 "不明确" → AgentCall 完成、Task 未完成
- **状态控制权**：Task 状态完全由 Manager 显式控制（参照 Claude Code TodoWrite 模式），Worker 没有写 Task 状态的权力，只通过 result.text 反馈
- 属性：task_id、owner（worker name）、content（任务描述）、状态、所属 group_chat_id、创建者（必须是该 GroupChat 的 Leader）
- 状态：PENDING → RUNNING → COMPLETED / FAILED
- 与 AgentCall 的关系：执行时产生 AgentCall，AgentCall.business_task_id 指向 Task.task_id（一对多，重做产生新 AgentCall 但 Task 不变）

### TaskList（任务列表）
- 每个 GroupChat 持有一份 TaskList，承载该群聊当前规划中的 Task 集合
- 状态：ACTIVE（活跃）/ ARCHIVED（已归档）
- 由 Manager 显式调用工具切换状态：完成一轮规划后归档当前 list，新规划自动进入新的 ACTIVE list
- 归档不删除，历史可查
- 用途：前端看板展示、Manager 的工作记忆

### AgentCallManager（调用管理器）
- 统一管理所有跨 Agent 的异步调用
- 职责：创建调用、更新状态、设置结果/错误
- 存储：内存中的 _calls 字典（call_id → AgentCall）

### MessageRouter（消息路由器）
- 负责 Agent 之间的消息投递
- 管理每个 Agent 的私有消息队列
- 职责：注册/注销 Agent、验证消息、投递消息

### 系统入站路径（双路径汇入 MessageRouter）

系统接收消息有**两条独立入口**，最终都汇入 `MessageRouter.send_message()`：

1. **MCP 入站（Agent → Agent）**：Agent 平台的 LLM 通过 MCP 工具 `call_agent` 入站
   - 必须携带 `agent_token`，Server 用 token 解析出 `send_from`（agent_name）和 `group_chat_id`
   - `send_from` 永远是 agent 的名字，**永远不会是 `"user"`**
   - 仅服务 LLM tool_use，业务代码不经此路径

2. **业务入站（User → Agent）**：前端通过 FastAPI（REST/WebSocket）让 user 进入系统
   - 后端业务函数（如 `user_send_message`）构造 `AgentMessage(send_from="user", send_to=<agent>, ...)`
   - 不携带 token，身份由前端登录态保证
   - 仅服务 user，不服务 LLM

**`"user"` 是保留发送者标识**（值来自 `config.default_user_name`）：在 `MessageRouter` 注册空队列，不接收回执。Agent 处理 send_from=user 的消息时：
- 出口 A（写群聊）：照常执行，user 通过前端 WebSocket 看到 Agent 回复
- 出口 B（自动回执）：跳过（user 没有队列）

**禁止跨路径混用**：MCP `call_agent` 不允许 `send_to="user"`，返回 `INVALID_RECIPIENT` 错误，引导 LLM 通过普通回复（出口 A）让 user 看到信息。

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

### AgentMemberInfo（会话信息）
- Agent 的会话信息
- 属性：main_session、btw_session、context_state、token、cwd
- main_session：主会话 ID
- btw_session：单聊会话 ID 列表
- context_state：上下文加载状态
- token：Agent 的身份验证令牌
- cwd：CLI 命令启动的工作目录路径

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
                ├── group_metadata.json            # 群聊元数据（GroupChat.start() 时立即创建）
                ├── <group_chat_id>.jsonl          # 群聊消息历史（首次消息时创建）
                ├── agent_member.json       # Agent session 和上下文状态
                └── memory/
                    └── compact_history.jsonl      # 压缩历史
```

## GroupMetadata（群聊元数据）

保存在 `group_metadata.json` 中，独立于消息历史，在 GroupChat.start() 时立即创建。

### 字段说明
- **group_chat_id**：群聊唯一标识
- **group_chat_name**：群聊名称（默认使用 group_chat_id）
- **project_path**：项目路径，用于：
  1. 计算群聊数据存储路径
  2. 作为所有 agent 的默认 cwd（工作目录）
- **created_at**：创建时间
- **group_type**：群聊类型（如 MANAGER_ORCHESTRATE）

### 设计动机
- **立即创建**：metadata 在 GroupChat.start() 时立即创建，不依赖消息历史
- **延迟创建消息**：group_chat_session.jsonl 在首次消息时才创建，避免空文件
- **SSOT 原则**：project_path 只存储在 metadata 中，作为单一数据源

### CWD 优先级规则
```
Agent 实际使用的 cwd = AgentMemberInfo.cwd (如果非空) 
                      OR metadata.project_path 
                      OR None (使用当前工作目录)
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
