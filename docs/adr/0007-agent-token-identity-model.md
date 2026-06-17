---
version: 1.0
created_at: 2026-05-31
updated_at: 2026-05-31
last_updated: 2026-05-31
abstract: MCP Tool 调用者的身份模型选用 Agent Token：Server 维护 token→(agent_name, group_chat_id) 映射，LLM 通过 runtime user prompt 拿到 token 并在 tool 调用时回传，Server 据此派生身份并校验权限。否决了"LLM 自报身份"和"每 Agent 一个 MCP Server 子进程"两条路。
status: decided
---

# Agent Token 身份模型

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0  | 创建文档初稿 |

## 问题界定

### 问题简述

agents-hub 通过 MCP Tool 把 `call_agent` 等工具暴露给 Agent 平台（Claude Code / Codex）的 LLM。Server 处理 tool 调用时，必须知道**谁在调**（agent_name）和**在哪个群聊里调**（group_chat_id）才能：

1. 将消息正确投递到目标 Agent 的私有队列
2. 校验调用者是否有权限（如测试阶段仅 Leader 可调 `call_agent`）
3. 持久化记录调用记录（AgentCall）

身份识别有几种走法，需要在协议层做出选择。

### 讨论范围

- MCP Tool 调用者的 agent_name 和 group_chat_id 从哪来
- 身份伪造的攻击面
- 部署形态（一个 MCP Server 还是多个）
- token 在 LLM prompt 中的注入方式与生命周期
- token 泄漏面

### 非讨论范围

- 具体的 MCP Tool 列表和签名（属于 spec-mcp-tools 范畴）
- 权限策略的具体规则（按群聊类型配置，属于业务规则）
- 前端业务代码（user 入站）的身份校验（不走 MCP 路径）

### 模糊信息的明确定义

- **身份**：(agent_name, group_chat_id) 二元组，确定一个 agent 在哪个群聊里运行
- **token**：随机字符串（如 `tok_<uuid>`），由 Server 生成、内部维护、注入 LLM prompt
- **runtime user prompt**：每次调用 LLM 时通过 user message 注入的运行时元信息，区别于 system prompt 的"角色级永久指令"

## 现状

### 已有线索

- `RoleType.LEADER` / `TEAM_MEMBER` 已在 [foundation/models.py](agents_hub/core/foundation/models.py) 定义
- `RoleConfig.role_type` 由 `role.json` 派生，是 SSOT
- 当前 [group_chat_manager.py:65-120](agents_hub/core/orchestration/group_chat_manager.py:65) 的 `call_agent` 函数把 `send_from` 和 `group_chat_id` 当作普通参数接收，没有身份校验

### 当前问题

1. **身份是 LLM 自报**：当前签名让 LLM 在 tool_use 里填 `send_from` 和 `group_chat_id`。LLM 可以伪造身份冒充 Leader 调用工具
2. **LLM 必须知道自己是谁**：要让 LLM 正确填 `send_from`，必须把"你叫 X，在群聊 Y"塞进 system prompt，prompt 一旦被覆盖就乱
3. **权限校验不可信**：在 (1) 的基础上做权限判断，等于让小偷自己声明"我是房东"

## 可选方案

### 方案 A：每个 Agent 一个独立 MCP Server 子进程

**做法**：Agent CLI 启动时通过 `claude mcp add --transport stdio` 关联一个独立的 MCP Server 进程。该 Server 进程通过环境变量或命令行参数携带 `agent_name` 和 `group_chat_id`，serve 期间身份固定。

**优势**：
- 身份不可伪造（Server 进程的身份由启动配置决定）
- LLM 完全感知不到身份，prompt 无需教育

**劣势**：
- **进程爆炸**：N 个 Agent × M 个并发群聊 = N*M 个 MCP Server 子进程
- 每个 Server 进程要持有同一份 `GroupChatManager` 状态，要么共享内存（不可能，进程隔离）要么走二级 IPC，复杂度暴涨
- 用户场景：4 agent × 2 群聊 = 8 个 MCP Server，资源浪费明显

### 方案 B：LLM 自报身份（当前代码思路）

**做法**：保持现状，`call_agent(send_from, send_to, group_chat_id, content, ...)`，LLM 在 tool_use 里填写自己的 send_from 和 group_chat_id。

**优势**：
- 一个 MCP Server 服务所有 Agent，部署简单
- 实现成本最低

**劣势**：
- 身份可伪造，权限校验形同虚设
- LLM 必须在 system prompt 中固定知晓自己的 (agent_name, group_chat_id)
- system prompt 被压缩 / 改写后身份会乱

### 方案 C：Agent Token + runtime prompt 注入（本方案）

**做法**：

1. **Token 注册**：GroupChat.start() / load() 时，为每个成员生成随机 token，写入 `GroupChatManager` 的全局反向索引：`token → (agent_name, group_chat_id)`
2. **持久化**：token 写入 `agent_member.json`（agents-hub 内部数据，Agent 子进程读不到）
3. **运行时注入**：Agent.run() 渲染 LLM prompt 时，通过 `render_runtime(...)` 在 user prompt 前部加 `<agent_runtime>` 块，包含 token + agent_name + group_chat 上下文 + （仅 Manager）team_workboard
4. **工具签名**：所有 MCP Tool 的第一个参数是 `agent_token`，Server 用 token 解析出身份，不再要求 LLM 传 `send_from` 或 `group_chat_id`
5. **权限校验**：Server 拿到可信身份后，对照 `RoleType.LEADER` 等规则判断
6. **部署形态**：一个 MCP Server，HTTP transport，与 agents-hub 后端同进程

**优势**：
- **身份不可伪造**：Worker 不知道 Manager 的 token，无法冒充
- **一个 MCP Server**，无进程爆炸
- **LLM 不需要永久记住自己是谁**：token 每轮 prompt 现注入，role system prompt 可以完全通用
- **未来权限策略升级零协议改动**：从"测试阶段 Leader-only"切到"协作型群聊全员开放"，只要改 Server 端的判断函数

**劣势**：
- 引入"token 表"这个新概念，需要在 GroupChatManager 维护
- 多一道渲染（runtime 注入），但成本极低
- token 泄漏面需要评估（详见下文）

## 最终决策

选择**方案 C：Agent Token + runtime prompt 注入**。

## 决策原因

### 原因 1：身份必须可信，否则权限校验是装饰品

当前 MCP Tool 的核心场景是 `call_agent`，权限规则是"测试阶段仅 Leader 可调"。这个规则唯一的可信前提是 Server 知道**真正的**调用者。

方案 B 让 LLM 自报，等于让 Worker 的 LLM 写入 `send_from="Leader"` 就能绕过——这违反了任何合理意义上的权限语义。

方案 C 通过 token 把身份从"LLM 提供"变成"Server 派发"，从根上杜绝伪造。

### 原因 2：方案 A 的进程模型与现有架构冲突

agents-hub 的部署形态是 FastAPI + GroupChatManager 单例 + N 个 CLI 子进程（由 bridge.py 启动）。`GroupChatManager` 持有所有群聊的 MessageRouter、AgentCallManager、token 表，**这些状态必须在同一个内存空间**才能高效协作。

方案 A 让 N*M 个 MCP Server 子进程都需要访问 `GroupChatManager`，而它们互相进程隔离——要么走 IPC（性能差且复杂），要么共享数据库（违反内存数据结构的初衷）。

方案 C 把 MCP Server 嵌入主进程（FastMCP 的 HTTP transport），所有状态共享，调用 `MessageRouter.send_message()` 是 in-memory dict + queue 操作，零序列化损耗。

### 原因 3：token 泄漏面在受控部署下足够窄

讨论中评估了 token 的潜在泄漏路径：

| 路径 | 风险 |
|------|------|
| LLM 在公开发言或最终回复中复述 token | **存在**，但通过显式群聊写入工具的"剥离过滤"（替换 `tok_xxx` 为 `[REDACTED]`）兜底 |
| Agent 子进程读取持久化文件 | **不存在**，token 持久化在 agents-hub 内部数据目录（`local_data/teams/...`），Agent 子进程的 cwd 是 `work_root/`，没理由跨目录访问 |
| CLI 内部 session compact 把 token 暴露 | **不存在**，CLI 内部 session 是 CLI 自己的私有数据，外部读不到 |
| 群聊 compact 把 token 暴露 | **不存在**，剥离过滤保证 token 不进群聊记录，群聊 compact 自然没有 |
| LLM 把 token 当 send_to 错填 | **不会泄漏**，server 在 MessageRouter 找不到这个 agent_name，返回 AgentNotFoundError，token 不进任何持久化 |

剩余的真实泄漏面只有"LLM 复述"，靠剥离过滤 + tool 描述里的"永不复述"提示双保险。在测试阶段，token 采用**群聊级生命周期**（GroupChat 运行期不变，cleanup 时清空），不做 per-turn 轮换——后者属于过度设计。

### 原因 4：与 ADR 0005 的"按需提供"原则一致

ADR 0005 已经确立"Agent 只能拿到它需要的东西"作为多 agent 通信的核心原则。Token 模型让每个 Agent 只知道**自己的** token，不知道**别人的** token，这是"按需提供身份凭证"的自然延伸。

### 原因 5：协议向后兼容地支持权限策略演化

测试阶段权限是"Leader-only"。未来按群聊类型配置（执行型 Leader-only / 协作型全员开放），方案 C 完全不需要改协议——只改 Server 端判断函数。

如果选 B，"开放给所有 agent" 后伪造问题加剧；如果选 A，每次权限策略变化要重启所有 Server 子进程。

## 后续影响

### 对 MCP Tool 签名的影响

所有 MCP Tool 的第一个参数统一是 `agent_token: str`。例如：

```python
def call_agent(
    agent_token: str,
    send_to: str,
    content: str,
    need_response: bool,
    timeout_seconds: int | None = None,
) -> str: ...

def assign_tasks_to_team(
    agent_token: str,
    tasks: list[Task],
) -> dict: ...

def check_agent_call(
    agent_token: str,
    call_id: str,
) -> dict: ...

def archive_task_list(
    agent_token: str,
) -> dict: ...
```

`send_from` 和 `group_chat_id` 不再出现在签名里，由 Server 派生。

### 对 GroupChatManager 的影响

新增全局 token 反向索引：

```python
class GroupChatManager:
    _group_chats: dict[str, GroupChat]
    _tokens: dict[str, tuple[str, str]]  # token -> (agent_name, group_chat_id)
```

`register(group_chat_id, group_chat)` 时把所有成员的 token 加入索引；`unregister(...)` 时移除该群聊所有 token。

### 对 GroupChat 的影响

`start()` / `load()` 流程新增"生成或恢复 token"步骤。每个 Agent 实例携带自己的 token（仅 GroupChat 内部知道）。`cleanup()` 时清空 token。

### 对持久化的影响

`agent_member.json` 增加 `agent_token` 字段：

```json
{
  "Leader": {
    "main_session": "...",
    "btw_session": [],
    "agent_token": "tok_abc123..."
  }
}
```

### 对 Agent.run() 的影响

新增 `render_runtime(agent_name, group_chat_id, token, team_info, [team_workboard])` 纯函数（位于 `core/foundation/renderer.py`）。`Agent._process_message` 在拼接 prompt 时调用 `render_runtime` 并把结果作为 `<agent_runtime>` 块前置到 user prompt。

### 对 MCP Server 部署的影响

- MCP Server 与 agents-hub 后端同进程嵌入（FastMCP HTTP transport）
- 监听独立端口（建议 8001）
- 每个 Agent 的 `work_root/.mcp.json` 写死指向 `http://localhost:8001/mcp`

### 对错误响应的影响

新增错误码 `INVALID_TOKEN`：当 token 不在索引中时返回，message 提示 LLM 重新读取 `<agent_runtime>` 块。

### 需要后续验证的事项

1. **剥离过滤的鲁棒性**：`tok_<uuid>` 模式应当用足够强的正则匹配，防止 LLM 用变形（空格、断行）绕过
2. **token 长度选择**：建议 32+ 字符，碰撞概率忽略
3. **打招呼轮（_initialize_new_members）的 token 注入**：测试阶段不处理（详见 status-report Q13）

## 与其他决策的关联

- ADR 0005（消息架构）：本决策延续 0005 的"避免越权""按需提供"原则
- ADR 0006（群聊发言重构）：本决策不依赖具体的公开发言工具形态。token 模型对显式群聊发言与显式调用闭环都成立
- 本决策体现用户的一贯偏好：**安全性 > 部署简单度**（参见 user-design-summary.md）
