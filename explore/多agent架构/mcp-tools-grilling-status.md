# MCP Tool 设计 grilling 结论汇总

> 创建日期：2026-05-31
> 来源：基于初版 MCP 工具构想（call_agent / 任务设置 / 查询 agent_call）的 grill-with-docs 会话
> 输出位置：本文件 + CONTEXT.md（术语更新）+ ADR 0006/0007（设计决策）
> 下一步动作：撰写 MCP Tool 正式 spec（建议路径 `docs/specs/2026-XX-XX-mcp-tools.md`），按下文结论展开实现

---

## 总览

本次 grilling 走完 13 棵分支，输出：

| 类型 | 文件 | 状态 |
|------|------|------|
| 术语更新 | `CONTEXT.md` | 已更新（Manager 唯一性、Task/TaskList、双入站路径、user 保留标识） |
| ADR | `docs/design-decisions/0006-explicit-group-chat-speech.md` | deferred（方向已定，待 MCP 跑通后实施） |
| ADR | `docs/design-decisions/0007-agent-token-identity-model.md` | decided（核心架构，本次实施依据） |
| spec | `docs/specs/2026-XX-XX-mcp-tools.md` | **待撰写** |

---

## 关键决策清单

### Q1 Manager 判定基准

**决定**：基于 `RoleType.LEADER` 判定，不是基于"GroupChat 当前指定的 manager"。

**理由**：`RoleType` 是 `role.json` 的 SSOT，已在 foundation 层定义。一个 GroupChat 有且仅有一个 Leader 这个不变量已写入 CONTEXT.md。

### Q2 权限模型

- **2a 失败反馈形式**：返回 MCP error 响应（`PERMISSION_DENIED`），message 教育 LLM 改走其他渠道
- **2b 短期实现**：测试阶段仅 Leader 可调 `call_agent`、`assign_tasks_to_team`、`archive_task_list`
- **2b 长期实现**：按群聊类型配置权限（执行型 Leader-only / 协作型全员开放）。当前实现不要硬编码 LEADER-only 到工具内部，留出未来切换为"按群聊权限策略"的接口

### Q3 / Q7 / Q8 Agent Token 身份模型 → ADR 0007

**核心**：

- 所有 MCP Tool 第一个参数是 `agent_token: str`
- Server 维护全局反向索引 `_tokens: dict[str, tuple[str, str]]`（位于 `GroupChatManager`）
- token 在 GroupChat.start/load 生成，cleanup 清空
- token 持久化在 `agent_member.json`（agents-hub 内部目录）
- token 通过 runtime user prompt 注入（不进 system prompt）
- token 防泄漏：剥离过滤（出口 A 写群聊前 redact `tok_xxx`） + tool 描述里的"永不复述"提示
- MCP Server 与 agents-hub 后端**同进程嵌入**（FastMCP HTTP transport，监听 8001）
- Agent 的 `work_root/.mcp.json` 写死指向 `http://localhost:8001/mcp`
- 测试阶段不加锁（dict 单写 GIL 原子；token 表运行期只读；cleanup 时 Agent 已停）

### Q4 / Q5 Task 与 TaskList

- **Task 与 AgentCall 完全独立的状态机**。AgentCall.COMPLETED ≠ Task.COMPLETED（worker 回 "不明确" 时 Call 完成但 Task 未完成）
- **Task 状态完全由 Manager 显式控制**（参照 Claude Code TodoWrite 模式）
- **Task 1:1 owner 不变量**：每个 Task 有且只有一个 worker owner，多个 worker 间任务必须正交
- **Task 状态机**：PENDING → RUNNING → COMPLETED / FAILED
- **TaskList 状态机**：ACTIVE / ARCHIVED
- **重做语义**：同一 Task + 新 AgentCall（不创建新 Task）
- **工具命名**：`assign_tasks_to_team`（强调"团队"语义，与 Claude Code 内置 `TodoWrite` 区分）
- **归档独立工具**：`archive_task_list`（不并入 assign_tasks_to_team）
- **Manager 看见当前 task 列表**：通过 `<agent_runtime>` runtime prompt 注入 `<team_workboard>`，仅 Manager 注入

### Q6 check_agent_call

- **定位**：心智工具（让 LLM 安心），不是核心轮询机制
- **call_agent 始终 fire-and-forget**：返回 call_id，worker 完成后通过 Agent.run() 出口 B 自动回执
- **返回内容**：`{call_id, status, send_from, send_to, message_type, timestamps}`，**不返回 result.text**（result 通过群聊回执拿）
- **权限**：任何 agent 只能查 `send_from == self` 的 call（无 Leader 特权——Leader 也只能查自己发的，因为它本来也只看见自己发的 call_id）
- **不提供 list_calls**（避免诱导 LLM 形成轮询习惯）

### Q9 MCP Tool 列表（最终）

测试阶段总共 4 个工具：

```python
def call_agent(
    agent_token: str,
    send_to: str,
    content: str,
    need_response: bool,
    timeout_seconds: int | None = None,
) -> str:
    """权限：仅 Leader（测试阶段）；返回 call_id"""

def assign_tasks_to_team(
    agent_token: str,
    tasks: list[Task],
) -> dict:
    """权限：仅 Leader；整张 list 覆盖式更新（参照 TodoWrite）；返回 {created, updated, unchanged}"""

def archive_task_list(
    agent_token: str,
) -> dict:
    """权限：仅 Leader；当前 ACTIVE list 整体归档，新规划自动进入新 list"""

def check_agent_call(
    agent_token: str,
    call_id: str,
) -> dict:
    """权限：任何 agent 但 send_from 必须 == self；返回 {status, send_from, send_to, message_type, timestamps}"""
```

### Q9 错误响应格式

```python
{
    "error": {
        "code": "...",  # 见下表
        "message": "...",  # 可读说明，包含 LLM 自纠所需信息
        "details": {...}  # 可选
    }
}
```

错误码集合：

| code | 触发场景 |
|------|---------|
| `INVALID_TOKEN` | token 不在索引中（已过期 / 被注销） |
| `PERMISSION_DENIED` | 角色无权限（如 Worker 调 call_agent） |
| `AGENT_NOT_FOUND` | send_to 不存在 |
| `INVALID_RECIPIENT` | send_to="user"（不是 agent，引导走出口 A） |
| `GROUP_CHAT_NOT_FOUND` | token 解析后的 group 已被注销 |
| `INVALID_TASK` | task 字段缺失或非法 |
| `CALL_NOT_FOUND` | check 时 call_id 不存在 |
| `CALL_ACCESS_DENIED` | check 时 call_id 的 send_from 不是自己 |
| `TIMEOUT` | call 已超时 |

### Q12 user 路径分流

- **MCP `call_agent` 不允许 send_to="user"**，返回 `INVALID_RECIPIENT`
- **user 入站不走 MCP**：前端通过 FastAPI 调用业务函数（如 `user_send_message`），后端构造 `AgentMessage(send_from="user", send_to=<agent>, ...)` 直接走 `MessageRouter.send_message()`
- Agent 处理 `send_from="user"` 的消息时：出口 A 照常写群聊，出口 B 跳过（user 没有 message_queue）

### Q13 打招呼轮（_initialize_new_members）的 token 注入

**测试阶段不处理**：`_initialize_new_members` 直接调 `agent.execute()` 跳过 run loop，不注入 token。理由：

- 自我介绍轮 LLM 不会调 MCP 工具（prompt 是简单的 hardcoded 介绍）
- 即使误调，server 拒绝（无 token），对功能没影响

如果实测遇到误调，通过 role 的 CLAUDE.md 加一句"自我介绍时不要调用工具"即可。

---

## 待解决/延后问题

### 9d 输出延迟可见性（与 ADR 0006 联动）

`bridge.execute()` 全部 text_delta 拼接才返回 → user 等到 Manager 整个 turn 结束才看到任何回复 → "Manager 沉默几十秒后突然冒出整段话，这时 worker 们已经在做了"

- **测试阶段不解决**（接受体验问题）
- **未来候选方案**：(α) 改用 `execute_stream()` 并增量推送 / (β) Manager 多轮通信（先回信再派活）
- **真正的瓶颈在前端**（增量渲染、消息状态机），后端切换成本不大

### ADR 0006 群聊发言重构（deferred）

把出口 A/B 的隐式自动写入改为显式 `report_progress` 工具。完整讨论见 ADR 0006。在 MCP 主流程跑通后立项实施。

---

## 实施清单（按依赖顺序）

| # | 工作项 | 依赖 |
|---|--------|------|
| 1 | 撰写 spec：`docs/specs/2026-XX-XX-mcp-tools.md`（综合上文所有结论） | 本文件 |
| 2 | foundation 层：新增 `render_runtime` 纯函数 | spec |
| 3 | foundation 层：新增 `Token` 类型 / 工具函数（生成 / 剥离正则） | spec |
| 4 | communication 层：新增 `Task` 数据模型、`TaskList` 状态机、持久化 | spec |
| 5 | orchestration 层：`GroupChatManager._tokens` 全局索引，注册/注销逻辑 | (3) |
| 6 | orchestration 层：`GroupChat.start/load` 生成 / 恢复 token，`cleanup` 清空 | (5) |
| 7 | context 层：`agent_member.json` 加 `agent_token` 字段 | (5) |
| 8 | agent 层：`Agent._process_message` 调 `render_runtime` 注入 token | (2)(6) |
| 9 | agent 层：`Agent.run()` 出口 A 在写群聊前调 token redact | (3) |
| 10 | mcp 层：FastMCP HTTP transport，注册 4 个 tool | (4)-(9) |
| 11 | mcp 层：每个 tool 的权限校验、错误响应 | (10) |
| 12 | bridge 层：每个 role 的 `work_root/.mcp.json` 模板 | (10) |
| 13 | 业务层：`user_send_message` 业务函数（走 MessageRouter，非 MCP） | (8) |
| 14 | 集成测试：Manager 派活 → Worker 完成 → 出口 B 回执 → Manager check_agent_call | 全部 |

---

## 本次 grilling 未涉及（实施时再定）

| 项 | 说明 |
|----|------|
| `<agent_runtime>` 的精确 XML 结构 | 实现 `render_runtime` 时按 [renderer.py](agents_hub/core/foundation/renderer.py) 现有 Tag 风格扩展 |
| Task 字段细节（task_id 生成、content 长度限制等） | 实现 `Task` 数据模型时定 |
| TaskList 持久化文件名 | 建议 `tasks.jsonl`，与 `agent_calls.jsonl` 同目录 |
| Token 剥离正则的具体形式 | 建议 `tok_<8+ hex>`，正则 `r"tok_[a-f0-9]{8,}"` |
| Token 长度 | 建议 32+ 字符（如 `tok_<uuid4-hex>`） |

---

## 与现有文档的交叉引用

- [CONTEXT.md](../../CONTEXT.md) — Manager 唯一性、Task/TaskList、双入站路径、user 保留标识
- [docs/design-decisions/0005-multi-agent-message-architecture.md](../design-decisions/0005-multi-agent-message-architecture.md) — 本次决策延续 0005 的"避免越权""按需提供"原则
- [docs/design-decisions/0006-explicit-group-chat-speech.md](../design-decisions/0006-explicit-group-chat-speech.md) — 出口 A/B 重构（deferred）
- [docs/design-decisions/0007-agent-token-identity-model.md](../design-decisions/0007-agent-token-identity-model.md) — Token 身份模型（decided）
- [docs/specs/2026-05-31-core-agent-orchestration.md](../specs/2026-05-31-core-agent-orchestration.md) — 现有 spec，本次结论会扩充其中 "MCP 工具入口" 章节
- [docs/specs/2026-05-31-core-communication.md](../specs/2026-05-31-core-communication.md) — 现有 spec，AgentCall 与 Task 的关系（business_task_id）已在其中
