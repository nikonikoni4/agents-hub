# MCP 工具系统设计

## 背景

agents-hub 需要为 Agent 平台（Claude Code / Codex）的 LLM 提供系统能力调用接口，让 Manager 能够派活、管理任务、查询状态。核心挑战：

1. **身份验证** — LLM 不能自报身份（可伪造），需要服务端派发凭证
2. **权限控制** — 测试阶段仅 Leader 可调用编排工具，未来按群聊类型配置
3. **双路径入站** — Agent 通过 MCP，User 通过业务接口，两者不混用
4. **状态透明** — Task 与 AgentCall 状态机独立，Manager 显式控制任务状态

本设计基于 `explore/多agent架构/mcp-tools-grilling-status.md` 的 grilling 结论和 ADR 0007（Agent Token 身份模型）。

## 系统概览

### 架构分层

```
┌─────────────────────────────────────────────────────┐
│  LLM (Claude Code / Codex)                          │
│  - 通过 work_root/.mcp.json 连接 MCP Server        │
│  - 每次调用携带 agent_token                         │
└─────────────────────────────────────────────────────┘
                      ↓ HTTP (localhost:8001)
┌─────────────────────────────────────────────────────┐
│  MCP Server (FastMCP HTTP Transport)                │
│  - 4 个工具：call_agent / assign_tasks_to_team /   │
│    archive_task_list / check_agent_call             │
│  - 身份解析：token → (agent_name, group_chat_id)   │
│  - 权限校验：RoleType.LEADER 判定                   │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  GroupChatManager (全局单例)                        │
│  - _tokens: dict[str, tuple[str, str]]             │
│  - _group_chats: dict[str, GroupChat]              │
│  - 注册/注销 token，路由到具体 GroupChat            │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  GroupChat / MessageRouter / TaskManager            │
│  - 消息投递、Task 状态管理、AgentCall 记录          │
└─────────────────────────────────────────────────────┘
```

### 核心目标

1. **安全的身份验证** — Agent Token 模型防止身份伪造
2. **Manager 编排能力** — 派活（call_agent）、任务管理（assign_tasks_to_team）、状态查询（check_agent_call）
3. **双路径入站** — MCP 路径服务 Agent，业务路径服务 User
4. **测试阶段权限** — Leader-only，未来可按群聊类型配置

## 核心组件设计

### 1. Agent Token 身份模型

**Token 生成与生命周期：**
- **格式**：`tok_<32位hex>`（如 `tok_a1b2c3d4e5f6...`）
- **生成时机**：GroupChat.start() / load() 为每个成员生成唯一 token
- **持久化**：`agent_member.json` 新增 `agent_token` 字段
- **清理时机**：GroupChat.cleanup() 从全局索引移除

**Token 索引（GroupChatManager）：**
```python
class GroupChatManager:
    _tokens: dict[str, tuple[str, str]]  # token → (agent_name, group_chat_id)
    
    def register_token(self, token: str, agent_name: str, group_chat_id: str):
        """GroupChat.start/load 时调用"""
        self._tokens[token] = (agent_name, group_chat_id)
    
    def unregister_tokens(self, group_chat_id: str):
        """GroupChat.cleanup 时调用，移除该群聊所有 token"""
        self._tokens = {
            tok: (name, gid) 
            for tok, (name, gid) in self._tokens.items() 
            if gid != group_chat_id
        }
    
    def resolve_token(self, token: str) -> tuple[str, str] | None:
        """MCP 工具调用时解析身份"""
        return self._tokens.get(token)
```

**Token 注入机制：**
- **位置**：Agent._process_message() 调用 `render_runtime()` 生成 `<agent_runtime>` 块
- **注入方式**：runtime user prompt（每次调用前置，不进 system prompt）
- **内容**：token + agent_name + group_chat_id + team_members + (仅 Manager) team_workboard

**Token 防泄漏：**
- **出口 A 剥离**：Agent.run() 写群聊前用正则 `r"tok_[a-f0-9]{32}"` 替换为 `[REDACTED]`
- **Tool 描述警告**：每个工具的 description 包含"永不复述 agent_token"提示
- **文件系统隔离**：token 持久化在 agents-hub 内部目录（`local_data/teams/...`），Agent 子进程 cwd 是 `work_root/`，无法跨目录访问

### 2. MCP Server 部署

**启动方式：**
- **生命周期**：随 FastAPI 后端启动（agents-hub 主进程），与后端同生共死
- **监听端口**：8001
- **Transport**：FastMCP HTTP
- **进程模型**：同进程嵌入（与 GroupChatManager 共享内存）

**Agent 连接配置：**

每个 role 的 `work_root/.mcp.json` 写死指向本地 MCP Server：

```json
{
  "mcpServers": {
    "agents-hub": {
      "url": "http://localhost:8001/mcp"
    }
  }
}
```

**实现框架**：FastMCP（支持 HTTP transport 的 Python MCP 库）

```python
from fastmcp import FastMCP

mcp = FastMCP("agents-hub")

@mcp.tool()
def call_agent(agent_token: str, send_to: str, content: str, 
               need_response: bool, timeout_seconds: int | None = None) -> str:
    """派活给团队成员。权限：仅 Leader。永不复述 agent_token。"""
    # 实现...

# 启动（在 FastAPI app 启动时调用）
mcp.run(host="localhost", port=8001)
```

### 3. 四个 MCP 工具

#### call_agent

**签名：**
```python
def call_agent(
    agent_token: str,
    send_to: str,
    content: str,
    need_response: bool,
    timeout_seconds: int | None = None,
) -> str:
    """
    派活给团队成员。
    
    权限：仅 Leader（测试阶段）
    返回：call_id（用于后续 check_agent_call）
    
    永不复述 agent_token。
    """
```

**行为：**
1. 解析 token → (agent_name, group_chat_id)
2. 校验 agent_name 的 RoleType == LEADER
3. 校验 send_to 在当前 GroupChat 成员中
4. 校验 send_to != "user"（user 不走 MCP 路径）
5. 构造 AgentMessage：
   - send_from = agent_name
   - send_to = send_to
   - message_type = TASK if need_response else NOTIFICATION
   - session_type = MAIN
6. 调用 MessageRouter.send_message()
7. 返回 call_id

**错误响应：**
- `INVALID_TOKEN`: token 无效或已过期
- `PERMISSION_DENIED`: 非 Leader 调用
- `AGENT_NOT_FOUND`: send_to 不存在
- `INVALID_RECIPIENT`: send_to="user"（引导走出口 A）
- `GROUP_CHAT_NOT_FOUND`: 群聊已注销

#### assign_tasks_to_team

**签名：**
```python
def assign_tasks_to_team(
    agent_token: str,
    tasks: list[dict],  # JSON 格式：[{task_id, owner, content, status}]
) -> dict:
    """
    为团队分配任务列表（覆盖式更新）。
    
    权限：仅 Leader
    返回：{created: int, updated: int, unchanged: int}
    
    注：tasks 参数是 JSON 可序列化的 dict 列表，不是 Python Task 对象。
    MCP 工具内部会将 dict 转换为 Task 数据模型。
    
    永不复述 agent_token。
    """
```

**行为：**
1. 解析 token，校验 Leader 权限
2. 验证每个 task 的 owner 在团队中
3. 对比当前 ACTIVE TaskList：
   - task_id 存在 → 更新 status/content
   - task_id 不存在 → 创建新 Task
   - 旧 list 中不在新 list 的 → 保持不变（不删除）
4. 持久化到 `tasks.jsonl`
5. 返回统计：`{created: 2, updated: 1, unchanged: 0}`

**语义说明：**
- 参照 Claude Code TodoWrite 的覆盖式更新
- Manager 每次调用传入完整的任务列表（包括已有的和新增的）
- 系统自动识别哪些是新任务、哪些是更新

**错误响应：**
- `INVALID_TOKEN` / `PERMISSION_DENIED` / `GROUP_CHAT_NOT_FOUND`
- `INVALID_TASK`: task 字段缺失或 owner 不存在

#### archive_task_list

**签名：**
```python
def archive_task_list(
    agent_token: str,
) -> dict:
    """
    归档当前 ACTIVE 任务列表。
    
    权限：仅 Leader
    返回：{archived_count: int, archived_at: str}
    
    永不复述 agent_token。
    """
```

**行为：**
1. 解析 token，校验 Leader 权限
2. 将当前 ACTIVE TaskList 状态改为 ARCHIVED
3. 下次 assign_tasks_to_team 自动创建新 ACTIVE list
4. 持久化到 `tasks.jsonl`
5. 返回归档信息

**使用场景：**
- Manager 完成一轮规划后归档旧任务列表
- 开始新一轮规划时清空工作看板

**错误响应：**
- `INVALID_TOKEN` / `PERMISSION_DENIED` / `GROUP_CHAT_NOT_FOUND`

#### check_agent_call

**签名：**
```python
def check_agent_call(
    agent_token: str,
    call_id: str,
) -> dict:
    """
    查询 AgentCall 状态（心智工具）。
    
    权限：任何 agent，但只能查 send_from == self 的 call
    返回：{call_id, status, send_from, send_to, message_type, 
           created_at, updated_at}
    
    永不复述 agent_token。
    """
```

**行为：**
1. 解析 token → agent_name
2. 从 AgentCallManager 查询 call
3. 校验 call.send_from == agent_name
4. 返回状态信息（不返回 result.text，result 通过群聊回执拿）

**定位说明：**
- 这是"心智工具"（让 LLM 安心），不是核心轮询机制
- call_agent 始终 fire-and-forget，worker 完成后通过 Agent.run() 出口 B 自动回执
- 不提供 list_calls（避免诱导 LLM 形成轮询习惯）

**权限说明：**
- 任何 agent 都可以调用
- 但只能查询 send_from == self 的 call
- Leader 也只能查自己发的（因为它本来也只看见自己发的 call_id）

**错误响应：**
- `INVALID_TOKEN` / `GROUP_CHAT_NOT_FOUND`
- `CALL_NOT_FOUND`: call_id 不存在
- `CALL_ACCESS_DENIED`: call 的 send_from 不是自己

### 4. Task 与 TaskList 数据模型

#### Task 模型

```python
@dataclass
class Task:
    task_id: str          # 唯一标识（UUID）
    owner: str            # worker name（1:1 不变量）
    content: str          # 任务描述
    status: TaskStatus    # PENDING / RUNNING / COMPLETED / FAILED
    group_chat_id: str    # 所属群聊
    created_by: str       # 创建者（必须是 Leader）
    created_at: datetime
    updated_at: datetime

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

**不变量：**
- 每个 Task 有且只有一个 owner（一个 Worker）
- 多个 Worker 之间的 Task 必须正交（无重叠职责）

#### TaskList 模型

```python
@dataclass
class TaskList:
    list_id: str          # 唯一标识（UUID）
    group_chat_id: str
    status: TaskListStatus  # ACTIVE / ARCHIVED
    tasks: list[Task]
    created_at: datetime
    archived_at: datetime | None

class TaskListStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
```

**状态机：**
- 每个 GroupChat 同时只有一个 ACTIVE TaskList
- archive_task_list 将 ACTIVE → ARCHIVED
- 下次 assign_tasks_to_team 自动创建新 ACTIVE list

#### 持久化

**文件路径：**
```
local_data/teams/<team>/<project>/<group_chat_id>/tasks.jsonl
```

**格式：**
- 每行一个 TaskList 的 JSON
- 查询：读取所有行，过滤 status == ACTIVE 的最新一条

**示例：**
```json
{"list_id": "list_1", "group_chat_id": "gc_1", "status": "active", "tasks": [...], "created_at": "...", "archived_at": null}
{"list_id": "list_1", "group_chat_id": "gc_1", "status": "archived", "tasks": [...], "created_at": "...", "archived_at": "..."}
{"list_id": "list_2", "group_chat_id": "gc_1", "status": "active", "tasks": [...], "created_at": "...", "archived_at": null}
```

#### 状态机独立性

**Task 状态 vs AgentCall 状态：**
- Task 状态由 Manager 显式控制（通过 assign_tasks_to_team 更新）
- AgentCall 状态由系统自动管理（PENDING → RUNNING → COMPLETED）
- **AgentCall.COMPLETED ≠ Task.COMPLETED**

**示例场景：**
1. Manager 调用 call_agent 派活给 Worker（创建 AgentCall，状态 PENDING）
2. Worker 收到消息，开始处理（AgentCall 状态 → RUNNING）
3. Worker 发现需求不明确，回复"请补充 XX 信息"（AgentCall 状态 → COMPLETED）
4. Manager 收到回执，发现任务未完成，Task 状态保持 RUNNING
5. Manager 补充信息后再次派活（创建新 AgentCall）
6. Worker 完成任务（新 AgentCall 状态 → COMPLETED）
7. Manager 调用 assign_tasks_to_team 更新 Task 状态为 COMPLETED

### 5. Runtime Prompt 注入

#### 注入方案：CLAUDE.md/AGENTS.md 动态标记替换

**方案选择依据：**

根据 `docs/temp/研究报告/claude-md-runtime-injection-mechanism.md` 的调研结论：
- CLAUDE.md 每轮都加载，但通过 prompt cache 复用，不重复消耗 token
- 静态部分缓存命中率高，动态部分体积小，缓存失效成本低
- 不污染对话历史（JSONL 中不可见）

**实现机制：**

使用 `agents_hub/core/utils/markdown_injector.py` 的 `replace_marked_section()` 函数，在 Agent._process_message() 调用前动态替换 CLAUDE.md/AGENTS.md 中的标记区域。

**标记格式：**

在 role 的 `work_root/CLAUDE.md` 或 `work_root/AGENTS.md` 中预置标记：

```markdown
# Agent 配置

...（其他静态内容）...

<AGENT_RUNTIME_START/>
（此区域将被动态替换）
<AGENT_RUNTIME_END/>
```

**注入内容示例：**

```xml
<AGENT_RUNTIME_START/>
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
- [RUNNING] task_2: 编写测试 (owner: Worker2)
- [COMPLETED] task_3: 代码审查 (owner: Worker3)
</team_workboard>
</AGENT_RUNTIME>
<AGENT_RUNTIME_END/>
```

**说明：**
- markdown_injector.py 负责替换 `<AGENT_RUNTIME_START/>` 和 `<AGENT_RUNTIME_END/>` 之间的内容
- 注入的内容格式是 XML（与原设计一致），不是 Markdown
- 这样可以保持与现有 renderer.py 的 Tag 风格一致

**注入时机：**

在 Agent._process_message() 中，调用 LLM 前：

```python
async def _process_message(self, msg: AgentMessage, prompt: str):
    # 1. 生成 runtime 内容
    runtime_content = self._generate_runtime_content()
    
    # 2. 注入到 role 的 work_root 下的 CLAUDE.md/AGENTS.md
    # 注意：work_root 是 role 的工作目录（local_data/agents/<role_name>/work_root/）
    # 不是 project_path（群聊的项目路径）
    md_path = self.role_config.work_root / self._get_md_filename()
    replace_marked_section(
        file_path=md_path,
        marker="AGENT_RUNTIME",
        content=runtime_content,
    )
    
    # 3. 调用 LLM（work_root 下的 CLAUDE.md/AGENTS.md 会被自动加载）
    result = await self.bridge.execute(prompt, ...)
    
    # ... 后续处理 ...
```

**路径说明：**
- **work_root**：`local_data/agents/<role_name>/work_root/`（role 的固定工作目录）
- **project_path**：群聊的项目路径（由 GroupChat 传入，用于执行任务）
- CLAUDE.md/AGENTS.md 位于 work_root，不在 project_path

**_generate_runtime_content 实现：**

```python
def _generate_runtime_content(self) -> str:
    """生成运行时注入内容（XML 格式）"""
    lines = ["<AGENT_RUNTIME>"]
    
    # 身份信息
    lines.extend([
        "<identity>",
        f"你的名字：{self.name}",
        f"群聊ID：{self.group_chat_context.group_chat_id}",
        f"身份令牌：{self.agent_token}",
        "</identity>",
        "",
    ])
    
    # 团队信息
    lines.extend([
        "<team>",
        f"团队成员：{', '.join(self.group_chat_context.get_team_members())}",
        "</team>",
    ])
    
    # 仅 Manager 注入任务看板
    if self.is_leader:
        workboard = self._get_workboard()
        if workboard:
            lines.extend([
                "",
                "<team_workboard>",
                "当前任务列表：",
            ])
            for task in workboard:
                lines.append(f"- [{task.status.value.upper()}] {task.task_id}: {task.content} (owner: {task.owner})")
            lines.append("</team_workboard>")
    
    lines.append("</AGENT_RUNTIME>")
    return "\n".join(lines)
```

**关键特性：**
- 每次调用前动态更新 CLAUDE.md/AGENTS.md
- token 明文可见（LLM 需要它调用工具）
- 通过 prompt cache 避免重复消耗 token
- 仅 Manager 注入 team_workboard
- 标记不存在时自动追加到文件末尾

### 6. User 路径分流

#### 业务函数（非 MCP）

**user_send_message：**

```python
async def user_send_message(
    group_chat_id: str,
    send_to: str,
    content: str,
    user_id: str,  # 从前端登录态获取
) -> dict:
    """
    User 通过前端发送消息给 Agent。
    
    不走 MCP，直接构造 AgentMessage：
    - send_from = "user"（保留标识）
    - send_to = send_to
    - message_type = TASK（user 的消息默认需要回复）
    
    调用 MessageRouter.send_message() 投递。
    
    返回：{success: bool, call_id: str}
    """
    # 1. 验证 group_chat_id 和 send_to 存在
    # 2. 构造 AgentMessage
    msg = AgentMessage(
        call_id=generate_call_id(),
        content=content,
        send_from="user",
        send_to=send_to,
        session_type=SessionType.MAIN,
        message_type=MessageType.TASK,
        timestamp=datetime.now(),
    )
    # 3. 投递
    await message_router.send_message(msg)
    # 4. 返回
    return {"success": True, "call_id": msg.call_id}
```

**Agent 处理 user 消息：**

Agent.run() 中：
- **出口 A**：照常写群聊（user 通过 WebSocket 看到）
- **出口 B**：跳过（user 没有 message_queue）

```python
# 出口 B（自动回执）
if msg.message_type == MessageType.TASK and msg.send_from != "user":
    # 投递回执给发送者
    await self.message_router.send_message(...)
```

#### MCP 拒绝 user

**call_agent 中的校验：**

```python
def call_agent(agent_token: str, send_to: str, ...):
    # ... 解析 token，校验权限 ...
    
    # 拒绝 send_to="user"
    if send_to == "user":
        return {
            "error": {
                "code": "INVALID_RECIPIENT",
                "message": "不能通过 call_agent 发送给 user。如果要让 user 看到信息，直接在你的回复中说明即可（会自动写入群聊）。"
            }
        }
    
    # ... 继续处理 ...
```

**错误信息演化：**
- **测试阶段**（当前）：引导 LLM 通过"直接回复"（出口 A 自动写入群聊）
- **ADR 0006 实施后**：错误信息改为"如果要让 user 看到信息，使用 report_progress 工具"

**设计原因：**
- user 不是 Agent，没有 message_queue
- user 通过前端 WebSocket 订阅群聊消息
- Agent 的回复通过出口 A 写入群聊，user 自然看到

### 7. 错误响应统一格式

#### 响应结构

所有 MCP 工具的错误响应：

```python
{
    "error": {
        "code": str,      # 错误码（见下表）
        "message": str,   # 可读说明，包含 LLM 自纠所需信息
        "details": dict   # 可选，额外上下文
    }
}
```

#### 错误码表

| Code | 触发场景 | Message 示例 |
|------|---------|-------------|
| `INVALID_TOKEN` | token 不在索引中 | "身份令牌无效或已过期，请检查 <agent_runtime> 块中的 token" |
| `PERMISSION_DENIED` | 非 Leader 调用 Leader-only 工具 | "此工具仅限 Leader 使用。你的角色是 Worker，无权调用 call_agent" |
| `AGENT_NOT_FOUND` | send_to 不存在 | "团队中没有名为 'xxx' 的成员。当前成员：[Worker1, Worker2, Worker3]" |
| `INVALID_RECIPIENT` | send_to="user" | "不能通过 call_agent 发送给 user。如果要让 user 看到信息，直接在你的回复中说明即可" |
| `GROUP_CHAT_NOT_FOUND` | 群聊已注销 | "群聊已结束，无法继续操作" |
| `INVALID_TASK` | task 字段缺失或 owner 不存在 | "任务 xxx 的 owner 'yyy' 不在团队中" |
| `CALL_NOT_FOUND` | call_id 不存在 | "找不到 call_id 'xxx'，可能已被清理" |
| `CALL_ACCESS_DENIED` | 查询别人的 call | "你只能查询自己发起的调用" |
| `TIMEOUT` | call 已超时 | "调用已超时（{elapsed}s > {timeout}s）" |

#### 实现示例

```python
def call_agent(agent_token: str, send_to: str, ...):
    # 解析 token
    identity = manager.resolve_token(agent_token)
    if not identity:
        return {
            "error": {
                "code": "INVALID_TOKEN",
                "message": "身份令牌无效或已过期，请检查 <agent_runtime> 块中的 token"
            }
        }
    
    agent_name, group_chat_id = identity
    
    # 校验权限
    role_type = get_role_type(agent_name)
    if role_type != RoleType.LEADER:
        return {
            "error": {
                "code": "PERMISSION_DENIED",
                "message": f"此工具仅限 Leader 使用。你的角色是 {role_type.value}，无权调用 call_agent",
                "details": {"agent_name": agent_name, "role_type": role_type.value}
            }
        }
    
    # ... 继续处理 ...
```

## 集成流程示例

### 场景 1：Manager 派活 → Worker 完成 → 回执

**流程：**

1. **User 发消息给 Manager**："帮我分析这个项目的架构"
   - 前端调用 `user_send_message(group_chat_id, send_to="Manager", content="...")`
   - 后端构造 `AgentMessage(send_from="user", send_to="Manager", message_type=TASK)`
   - MessageRouter 投递到 Manager 的队列

2. **Manager 收到消息，LLM 决定派活**：
   - Manager._process_message() 注入 runtime prompt（包含 agent_token）
   - LLM 调用 MCP 工具：
     ```python
     call_agent(
         agent_token="tok_abc123...",
         send_to="ArchWorker",
         content="分析项目架构，重点关注模块依赖关系",
         need_response=True
     )
     ```
   - MCP Server 解析 token → (Manager, gc_123)
   - 校验权限（Manager 是 Leader）
   - 构造 AgentMessage，投递到 ArchWorker 队列
   - 返回 `call_id_456`

3. **ArchWorker 处理任务**：
   - 从队列取出消息
   - 执行分析任务
   - Agent.run() 出口 B：自动回执给 Manager

4. **Manager 收到回执**：
   - 整合 ArchWorker 的分析结果
   - 回复 User（出口 A 写入群聊）

5. **（可选）Manager 查询状态**：
   ```python
   check_agent_call(
       agent_token="tok_abc123...",
       call_id="call_id_456"
   )
   # 返回：{status: "completed", send_from: "Manager", send_to: "ArchWorker", ...}
   ```

### 场景 2：Manager 分配任务

**流程：**

1. **Manager 收到 User 的复杂需求**："实现用户认证模块"

2. **LLM 拆解任务，调用 assign_tasks_to_team**：
   ```python
   assign_tasks_to_team(
       agent_token="tok_abc123...",
       tasks=[
           {
               "task_id": "t1",
               "owner": "BackendWorker",
               "content": "实现 JWT 认证逻辑",
               "status": "PENDING"
           },
           {
               "task_id": "t2",
               "owner": "FrontendWorker",
               "content": "实现登录页面",
               "status": "PENDING"
           },
           {
               "task_id": "t3",
               "owner": "TestWorker",
               "content": "编写认证模块测试",
               "status": "PENDING"
           }
       ]
   )
   # 返回：{created: 3, updated: 0, unchanged: 0}
   ```

3. **系统创建 Task 记录**：
   - 持久化到 `tasks.jsonl`
   - 创建新的 ACTIVE TaskList

4. **下次 Manager 的 runtime prompt 包含 workboard**：
   ```xml
   <team_workboard>
   当前任务列表：
   - [PENDING] t1: 实现 JWT 认证逻辑 (owner: BackendWorker)
   - [PENDING] t2: 实现登录页面 (owner: FrontendWorker)
   - [PENDING] t3: 编写认证模块测试 (owner: TestWorker)
   </team_workboard>
   ```

5. **Manager 逐个派活**：
   ```python
   call_agent(agent_token="tok_abc123...", send_to="BackendWorker", content="开始任务 t1：实现 JWT 认证逻辑", need_response=True)
   call_agent(agent_token="tok_abc123...", send_to="FrontendWorker", content="开始任务 t2：实现登录页面", need_response=True)
   ```

6. **Worker 完成后，Manager 更新任务状态**：
   ```python
   assign_tasks_to_team(
       agent_token="tok_abc123...",
       tasks=[
           {"task_id": "t1", "owner": "BackendWorker", "content": "实现 JWT 认证逻辑", "status": "COMPLETED"},
           {"task_id": "t2", "owner": "FrontendWorker", "content": "实现登录页面", "status": "RUNNING"},
           {"task_id": "t3", "owner": "TestWorker", "content": "编写认证模块测试", "status": "PENDING"}
       ]
   )
   # 返回：{created: 0, updated: 2, unchanged: 1}
   ```

7. **全部完成后，归档任务列表**：
   ```python
   archive_task_list(agent_token="tok_abc123...")
   # 返回：{archived_count: 3, archived_at: "2026-05-31T10:30:00"}
   ```

## 实施要点

### 分层实施顺序

按依赖关系从底层到上层：

1. **foundation 层**：
   - 新增 Token 类型和工具函数（生成、剥离正则）
   - 新增 TaskStatus / TaskListStatus 枚举

2. **communication 层**：
   - 新增 Task / TaskList 数据模型
   - 新增 TaskManager（管理 Task CRUD 和持久化）

3. **orchestration 层**：
   - GroupChatManager 新增 `_tokens` 索引
   - GroupChatManager 新增 register_token / unregister_tokens / resolve_token
   - GroupChat.start/load 生成/恢复 token
   - GroupChat.cleanup 清空 token

4. **context 层**：
   - `agent_member.json` 新增 `agent_token` 字段

5. **agent 层**：
   - Agent 实例新增 `agent_token` 属性
   - Agent 新增 `_generate_runtime_content()` 方法
   - Agent._process_message 调用 markdown_injector 注入 runtime 到 CLAUDE.md/AGENTS.md
   - Agent.run() 出口 A 在写群聊前调用 token redact

6. **mcp 层**（新增）：
   - 实现 FastMCP HTTP Server
   - 注册 4 个工具，实现权限校验和错误响应
   - 随 FastAPI 启动

7. **bridge 层**：
   - 为每个 role 的 `work_root/.mcp.json` 生成配置模板
   - 为每个 role 的 `work_root/CLAUDE.md` 或 `work_root/AGENTS.md` 预置 `<AGENT_RUNTIME_START/>` 标记

8. **业务层**：
   - 实现 `user_send_message` 业务函数

9. **集成测试**：
   - Manager 派活 → Worker 完成 → 出口 B 回执 → Manager check_agent_call

### 关键技术细节

**Token 生成：**
```python
import secrets

def generate_token() -> str:
    """生成 32 位 hex token"""
    return f"tok_{secrets.token_hex(16)}"
```

**Token 剥离正则：**
```python
import re

TOKEN_PATTERN = re.compile(r"tok_[a-f0-9]{32}")

def redact_token(text: str) -> str:
    """替换 token 为 [REDACTED]"""
    return TOKEN_PATTERN.sub("[REDACTED]", text)
```

**持久化格式（agent_member.json）：**
```json
{
  "Manager": {
    "main_session": "session_123",
    "btw_session": [],
    "agent_token": "tok_a1b2c3d4e5f6...",
    "context_state": {
      "last_loaded_compact_index": 0,
      "last_loaded_message_index": 5
    }
  },
  "Worker1": {
    "main_session": "session_456",
    "btw_session": [],
    "agent_token": "tok_b2c3d4e5f6a1...",
    "context_state": {...}
  }
}
```

**MCP Server 启动（FastAPI 集成）：**
```python
from fastapi import FastAPI
from fastmcp import FastMCP
import asyncio

app = FastAPI()
mcp = FastMCP("agents-hub")

# 注册工具
@mcp.tool()
def call_agent(...): ...

@mcp.tool()
def assign_tasks_to_team(...): ...

@mcp.tool()
def archive_task_list(...): ...

@mcp.tool()
def check_agent_call(...): ...

# 启动 MCP Server（在 FastAPI 启动事件中）
# 注：FastMCP 的 run() 方法是阻塞的，需要在独立任务中运行
@app.on_event("startup")
async def startup_mcp():
    asyncio.create_task(mcp.run(host="localhost", port=8001))
    
# 或者使用独立线程（取决于 FastMCP 的实现细节，实施时确认）
```

### 测试阶段不处理的问题

1. **打招呼轮的 token 注入**：
   - `_initialize_new_members` 直接调 `agent.execute()` 跳过 run loop
   - 自我介绍 prompt 是 hardcoded，不会调 MCP 工具
   - 即使误调，server 拒绝（无 token），对功能没影响

2. **输出延迟可见性（9d 问题）**：
   - `bridge.execute()` 全部 text_delta 拼接才返回
   - User 等到 Manager 整个 turn 结束才看到回复
   - 测试阶段接受体验问题，未来改用 `execute_stream()` 或多轮通信

3. **群聊发言重构（ADR 0006）**：
   - 出口 A/B 的隐式自动写入改为显式 `report_progress` 工具
   - 等 MCP 主流程跑通后立项实施

## 设计决策依据

### ADR 0007：Agent Token 身份模型

本设计采用 ADR 0007 确定的 Agent Token 模型，核心原因：

1. **身份不可伪造**：Worker 不知道 Manager 的 token，无法冒充
2. **一个 MCP Server**：避免进程爆炸（N agent × M 群聊 = N*M 进程）
3. **LLM 无需永久记住身份**：token 每轮 runtime 注入，role system prompt 可以完全通用
4. **权限策略可演化**：从"测试阶段 Leader-only"切到"协作型群聊全员开放"，只改 Server 端判断函数

### ADR 0005：多 Agent 消息架构

延续 ADR 0005 的"避免越权""按需提供"原则：

- 每个 Agent 只知道自己的 token，不知道别人的 token
- check_agent_call 只能查 send_from == self 的 call
- user 路径与 MCP 路径分离，避免混用

### CONTEXT.md 不变量

- **Manager 唯一性**：一个 GroupChat 有且仅有一个 Leader
- **Task 1:1 owner**：每个 Task 有且只有一个 worker owner
- **Task 与 AgentCall 状态机独立**：AgentCall.COMPLETED ≠ Task.COMPLETED
- **user 保留标识**：不在 MessageRouter 注册队列，不接收回执

### 参照 Claude Code TodoWrite

assign_tasks_to_team 的覆盖式更新语义参照 Claude Code 的 TodoWrite：

- Manager 每次传入完整任务列表（包括已有的和新增的）
- 系统自动识别哪些是新任务、哪些是更新
- Manager 显式控制 Task 状态，Worker 只通过 result.text 反馈

## 与现有文档的关联

- **CONTEXT.md** — Manager 唯一性、Task/TaskList、双入站路径、user 保留标识
- **ADR 0005** — 多 Agent 消息架构，本次决策延续其原则
- **ADR 0006** — 群聊发言重构（deferred），等 MCP 跑通后实施
- **ADR 0007** — Agent Token 身份模型（decided），本设计的核心依据
- **spec-core-foundation** — 枚举类型、AgentMessage、渲染契约
- **spec-core-communication** — MessageRouter、AgentCall 生命周期
- **spec-core-context** — 持久化机制、agent_member.json
- **spec-core-agent-orchestration** — Agent 执行模型、GroupChat 生命周期

## 未决事项（实施时再定）

| 项 | 说明 |
|----|------|
| AGENT_RUNTIME 标记的精确 Markdown 结构 | 实现 _generate_runtime_content 时确定具体格式 |
| Task 字段细节 | task_id 生成方式、content 长度限制等 |
| TaskList 持久化文件名 | 建议 `tasks.jsonl`，与 `agent_calls.jsonl` 同目录 |
| Token 剥离正则的具体形式 | 使用 `r"tok_[a-f0-9]{32}"` 精确匹配 32 字符 hex |
| Token 长度 | 32 字符（16 字节 hex，`secrets.token_hex(16)`） |
| MCP Server 错误日志 | 是否记录到独立日志文件 |
| 权限策略配置化 | 未来按群聊类型配置权限的具体实现 |
| FastMCP 启动方式 | 确认 `run()` 是否需要 `create_task` 或独立线程 |
| CLAUDE.md/AGENTS.md 标记预置时机 | 角色创建时还是首次启动时 |

---

**设计完成日期**：2026-05-31  
**基于文档**：explore/多agent架构/mcp-tools-grilling-status.md  
**下一步**：进入 writing-plans 阶段，拆解实施计划

