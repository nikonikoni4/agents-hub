---
version: 2.0
created_at: 2026-06-12
updated_at: 2026-06-12
last_updated: 重新设计：MCP 工具触发改为前端 HTTP 主动触发，新增 slash command 框架和成员列表下拉菜单
abstract: Agent 上下文主动压缩设计规格，定义前端触发入口、HTTP API 契约、Agent 压缩核心逻辑、系统消息展示和 slash command 框架
id: agent-context-compression
title: Agent 上下文主动压缩设计
status: draft
module: core/agent
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/core/agent/
  - agents_hub/core/orchestration/
  - agents_hub/core/foundation/
  - agents_hub/api/routes/
  - frontend/src/layouts/
  - frontend/src/core/api/
  - frontend/src/shared/types/
contract_refs:
  - agents_hub/core/agent/base_agent.py
  - agents_hub/core/orchestration/group_chat.py
  - agents_hub/api/routes/group_chat.py
  - agents_hub/core/context/group_chat_runtime.py
  - frontend/src/layouts/RightSidebar/RightSidebar.tsx
  - frontend/src/layouts/ChatArea/ChatInput.tsx
---

# Agent 上下文主动压缩设计

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建设计初稿（MCP 工具触发） |
| 2.0 | 重新设计：改为前端 HTTP 主动触发，新增成员列表下拉菜单、通用 slash command 框架、compressing 状态管理 |

## 设计定位

本文是 `superpowers:brainstorming` 生成的设计稿，用于指导 Agent 上下文主动压缩功能的实现。

## 背景问题

### 现状

- 每个 Agent 底层调用的是外部 Agent 平台的 CLI（Claude Code、Codex、OpenCode）
- CLI 维护自己的 session 上下文，随着对话增多逐渐膨胀
- 外部 CLI **没有提供 compact 压缩指令**
- `context_usage`（input_tokens / 1000）已在追踪每个 Agent 的上下文使用量
- 现有 `GroupChatContext.compact_messages` 压缩的是**群聊消息历史**，不是 Agent 的 CLI session 上下文

### 问题

当 Agent 的 CLI session 上下文过大时：
1. 推理质量下降
2. API 成本上升
3. 可能触发 CLI 的 context window 限制

### 目标

实现 Agent 级别的 CLI session 上下文主动压缩：
- 前端通过 HTTP 请求主动触发（成员列表下拉菜单 + 输入框 slash command）
- Agent 自我总结工作内容和接下来的任务
- 用总结作为输入新建 session，获得新 session_id
- 压缩完成后通过系统消息在聊天流中展示结果
- 留痕供调试和 hand-off 使用

## 核心决策

### 决策 1：前端 HTTP 主动触发（替代 MCP 工具）

v1.0 设计中手动触发通过 MCP 工具 `compact_agent_context` 实现，需要 Agent 在 session 中主动调用。v2.0 改为前端直接发送 HTTP POST 请求触发。

**理由**：
- 用户主动控制压缩时机，无需依赖 Agent 行为
- 前端可以直接感知压缩状态（loading、完成、失败）
- 复用现有 REST API 模式，与 `toggle_use_docker` 等操作一致
- MCP 工具触发需要 Agent 在 session 中调用，用户无法直接控制

### 决策 2：Agent 层内聚

压缩逻辑放在 `Agent` 基类中，而非独立的 CompressService 或编排层。

**理由**：
- 压缩是 Agent 执行流程的一部分，天然属于 Agent 层
- 不需要跨层依赖（Agent 层 → orchestration 层）
- 符合现有 `_process_message` 的处理模式
- 保持 core 分层架构：`foundation/`、`communication/`、`context/` 不依赖 `agent/` 或 `orchestration/`

### 决策 3：Agent 自我总结

摘要由 Agent 在当前 CLI session 中自我生成，而非通过 `bare_claude_call` 独立生成。

**理由**：
- Agent 最了解自己的工作上下文
- 生成的摘要更准确、更有针对性

### 决策 4：立即新建 session

压缩后立即用摘要作为首轮 prompt 新建 session，而非延迟到下次调用。

**理由**：
- 避免前端出现空白状态（main_session 为 None 的中间态最短化）
- 压缩和重建是原子操作，对外表现为一个完整的事务

### 决策 5：忙碌 Agent 不可压缩

前端根据 `status === 'busy'` 禁用压缩操作，后端在执行压缩前再次校验。

**理由**：
- 压缩会重建 session，与正在执行的任务冲突
- 前后端双重校验防止竞态条件（前端状态可能不同步）

### 决策 6：通用 slash command 框架

输入框的 `/` 命令设计为通用框架，当前只注册"压缩上下文"一个命令。

**理由**：
- 后续可能有更多斜杠命令需求（如 `/clear`、`/status`）
- 通用框架避免每次新增命令都要重新设计交互

## Scope

### 范围内

- 前端成员列表 `...` 下拉菜单（压缩上下文选项）
- 前端输入框通用 slash command 框架
- HTTP API 端点（单个压缩 + 全量压缩）
- Agent 层 `compress_context()` 方法
- 编排层 `compress_all()` 方法
- 忙碌校验（前后端双重）
- compressing 状态管理（前端本地状态）
- 压缩 prompt 模板（`core/foundation/prompt.py`）
- 压缩流程：发送 prompt → 提取摘要 → 留痕 → 新建 session → 更新状态
- 留痕文件写入
- 系统消息展示（后端 add_message）
- WebSocket refresh 同步

### 范围外

- 群聊消息历史压缩（已有 `compact_messages`）
- 压缩策略的自动调参
- 压缩历史的可视化 UI
- 固定阈值自动触发（v1.0 保留，v2.0 不实现）

## 整体架构与数据流

```
前端触发入口                    HTTP API                    后端执行
─────────────                  ─────────                   ─────────
成员列表 ... → 压缩上下文  ──→ POST /members/{name}/compress ──→ Agent.compress_context()
输入框 @X /压缩上下文     ──→ POST /members/{name}/compress ──→ Agent.compress_context()
输入框 /压缩上下文        ──→ POST /compress-all            ──→ GroupChat.compress_all()
                                                                    ↓
                                                              逐个检查 busy → 逐个压缩
                                                                    ↓
                                                              add_message 系统消息
                                                                    ↓
                                                              WebSocket refresh → 前端刷新成员状态
```

## HTTP API 契约

### 端点 1：单个 Agent 压缩

```
POST /group-chats/{chat_id}/members/{agent_name}/compress
```

**请求**：无 body

**成功响应 200**：
```json
{
  "message": "Agent X 上下文已压缩",
  "old_session_id": "abc123",
  "new_session_id": "def456",
  "context_usage_before": 150,
  "context_usage_after": 0
}
```

**错误响应 409（Agent 忙碌）**：
```json
{
  "detail": "Agent X 正在执行任务，无法压缩上下文"
}
```

**错误响应 404（Agent 不存在）**：
```json
{
  "detail": "Agent X 不在此群聊中"
}
```

### 端点 2：全量压缩

```
POST /group-chats/{chat_id}/compress-all
```

**请求**：无 body

**成功响应 200**：
```json
{
  "message": "已压缩 3 个 Agent 的上下文",
  "results": [
    { "agent_name": "Alice", "status": "compressed", "old_session_id": "a1", "new_session_id": "a2" },
    { "agent_name": "Bob", "status": "skipped", "reason": "busy" },
    { "agent_name": "Charlie", "status": "compressed", "old_session_id": "c1", "new_session_id": "c2" }
  ]
}
```

**关键设计**：全量压缩不因个别 Agent 忙碌而整体失败，而是逐个处理，返回每个 Agent 的结果。忙碌的 Agent 被跳过（`status: "skipped"`），而非报错。

## 核心行为

### Agent 压缩逻辑

`Agent.compress_context()`:

```
1. 忙碌校验：if self.status == "busy" → raise AgentBusyError

2. 构建压缩 prompt（从 prompt.py 获取模板）

3. 调用 self.execute(compress_prompt) 发送给当前 CLI session
   - 使用现有 main_session_id，让 Agent 在当前上下文中自我总结
   - 阻塞等待执行完成（同步行为）

4. 从 result.text 提取摘要

5. 写入留痕文件：
   路径: {agent_cwd}/docs/hand-off/{YYYY-MM-DD-HHmm}-{agent_name}-compact.md

6. 清空 main_session（设为 None）

7. 用摘要作为首轮 prompt 调用 self.execute(summary)
   → 获得新 session_id

8. 更新 main_session 为新 session_id

9. 重置 context_usage 为 0

10. 调用 runtime._notify_change() 广播 refresh

11. 返回 CompressResult
```

### 全量压缩逻辑

`GroupChat.compress_all()`:

```
遍历所有在线成员：
  try:
    result = await member.compress_context()
    记录成功结果
    写入系统消息：f"Agent {member.name} 上下文已压缩"
  except AgentBusyError:
    记录跳过结果（reason: "busy"）
  except Exception:
    记录失败结果

返回所有结果列表
```

### 压缩 Prompt

定义位置：`agents_hub/core/foundation/prompt.py`

```python
COMPACT_CONTEXT_PROMPT = """\
<compact_request>
请总结你当前的工作上下文：
1. 已经完成的工作内容
2. 当前正在做的事情
3. 接下来需要完成的任务
4. 关键决策和约束

请简洁明了，控制在 500 字以内。
</compact_request>
"""
```

### 留痕文件

路径格式：`{agent_cwd}/docs/hand-off/{YYYY-MM-DD-HHmm}-{agent_name}-compact.md`

文件内容：
```markdown
# Context Compact - {agent_name} - {timestamp}

## 原 Session
- session_id: {old_session_id}
- context_usage: {usage}K tokens

## 摘要
{agent 的总结内容}

## 新 Session
- session_id: {new_session_id}
```

### 系统消息

压缩完成后，后端通过 `GroupChatContext.add_message()` 写入系统消息（`role="system"`），前端在聊天流中展示：

```
⚙️ Agent Alice 上下文已压缩
   旧 session: abc123 → 新 session: def456
   150K tokens → 0K tokens
```

**写入位置**：`Agent.compress_context()` 完成后，在步骤 10（`_notify_change()`）之前调用 `runtime.add_system_message()`。全量压缩时由 `GroupChat.compress_all()` 统一写入。

### 异常类

定义位置：`agents_hub/core/foundation/errors.py`

```python
class AgentBusyError(Exception):
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        super().__init__(f"Agent {agent_name} 正在执行任务，无法压缩上下文")
```

## 前端设计

### 成员列表下拉菜单

**文件**：`RightSidebar.tsx` 的 `MemberItem` 组件

在现有 `dockerToggle` 按钮右侧新增 `...` 按钮，点击弹出下拉菜单：

```
┌─────────────────────────┐
│ [头像] Alice   忙碌  ●  │  ← 现有 MemberItem
│          负责人 · Claude  │
│          120K tokens     │
│              [🐳] [⋮]   │  ← 新增 ... 按钮
└─────────────────────────┘
          │
          ▼ 点击 ... 弹出下拉
    ┌──────────────────┐
    │  压缩上下文       │  ← 点击触发压缩
    └──────────────────┘
```

**状态联动**：
- `member.status === 'busy'` → 菜单项置灰 + tooltip "Agent 正在执行任务"
- `member.compressing === true` → 菜单项显示 "压缩中..." + spinner，禁用点击
- `member.isOnline === false` → 菜单项置灰

### 输入框 Slash Command 框架

**文件**：`ChatInput.tsx`

新增通用 slash command 检测逻辑，与现有 `@` mention 并行：

**触发检测**：
- 用户输入 `/` 时，检测是否在行首或 `@name ` 之后
- 弹出命令列表下拉菜单（当前只有"压缩上下文"一个命令）
- 输入 `@name /` 时，弹出命令列表，选中后触发该 agent 的压缩

**交互流程**：

```
场景 1：@X /压缩上下文
  输入: "@Alice /" → 弹出命令列表 → 选"压缩上下文" →
  替换为: "" (清空输入框) → 调用 POST /members/Alice/compress

场景 2：/压缩上下文（全量）
  输入: "/" → 弹出命令列表 → 选"压缩上下文" →
  替换为: "" → 调用 POST /compress-all
```

**命令注册表**（可扩展）：

```typescript
interface SlashCommand {
  name: string;          // "压缩上下文"
  description: string;   // "压缩 Agent 的 CLI session 上下文"
  requiresMention: boolean; // false（@ 可选）
  execute: (context: { chatId: string; agentName?: string }) => Promise<void>;
}
```

### compressing 状态管理

**方案：前端本地状态，不持久化到后端**

`compressing` 是短时状态（几秒到十几秒），不需要后端持久化。前端通过本地 state 管理：

```typescript
// useMembers.ts 中新增
const [compressingAgents, setCompressingAgents] = useState<Set<string>>(new Set());

// 触发压缩时
const startCompress = (agentName: string) => {
  setCompressingAgents(prev => new Set(prev).add(agentName));
};

// 压缩完成/失败时
const endCompress = (agentName: string) => {
  setCompressingAgents(prev => {
    const next = new Set(prev);
    next.delete(agentName);
    return next;
  });
};
```

**WebSocket refresh 不会覆盖**：`compressingAgents` 是独立于 `members` 的本地状态，`fetchMembers` 只更新 `members`，不影响 `compressingAgents`。

**MemberWithRole 扩展**：

```typescript
export interface MemberWithRole extends GroupChatMemberApiItem {
  role: RoleApiResponse | null;
  isOnline: boolean;
  compressing: boolean;  // 由 compressingAgents 计算得出
}
```

在 `useMembers` 的 `useMemo` 中合并：`compressing: compressingAgents.has(member.name)`

## 边界情况

### 忙碌校验（前后端双重）

**前端**：成员列表下拉菜单根据 `status === 'busy'` 置灰，阻止点击
**后端**：API 层调用前检查 `status`，忙碌返回 409
**竞态防护**：前端点击瞬间 Agent 可能刚好变忙，后端 409 兜底

### 压缩失败降级

| 失败场景 | 处理方式 |
|---------|---------|
| Agent 忙碌 | 返回 409，前端提示 "Agent 正在执行任务" |
| CLI session 执行压缩 prompt 失败 | 内部 catch，不中断，跳过该 Agent（全量场景）或返回 500（单个场景） |
| 新建 session 失败 | 回滚 main_session 到旧值，标记异常状态 |
| 留痕文件写入失败 | 仅 log warning，不影响压缩流程 |

### 并发压缩

- 同一 Agent 不会被重复压缩：前端 `compressing` 状态禁用 + 后端 `busy` 校验
- 全量压缩是串行逐个执行（复用 Agent 的消息队列顺序性），不会并发冲突

### 压缩期间 Agent 收到新消息

Agent 的 `message_queue` 是顺序处理的。压缩通过 `self.execute()` 发送到当前 session，期间新消息会排入队列。压缩完成后队列继续处理，新消息使用新 session。

## 前端同步

压缩完成后，通过现有 `broadcast_group_chat_refresh` 机制广播 refresh 信号。前端 `useMembers` hook 全量拉取成员信息（`GET /members`），`main_session` 变化直接覆盖旧值，`isOnline` 判断 `main_session !== null`。

**关键约束**：压缩过程中不广播中间状态。`compact_context()` 内部先清空 main_session、再设置新 main_session，两步完成后才调用 `_notify_change()` 广播一次 refresh。这样前端看到的是一步到位的状态更新，避免短暂显示 Agent 离线。

**时序**：
1. 后端 `compact_context()` 执行：清空 main_session → 新建 session → 设置新 main_session
2. 调用 `runtime._notify_change()` 广播一次 refresh 信号
3. 前端收到信号 → `fetchMembers()` 全量拉取 → main_session 已是新值 → isOnline 保持 true

## Technical Contract

### 新增文件

| 文件 | 职责 |
|------|------|
| `agents_hub/core/foundation/prompt.py` | 系统级 prompt 模板（COMPACT_CONTEXT_PROMPT） |
| `agents_hub/core/foundation/errors.py` | AgentBusyError 异常类 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `agents_hub/core/agent/base_agent.py` | 新增 `compress_context()` 方法 |
| `agents_hub/core/orchestration/group_chat.py` | 新增 `compress_all()` 方法 |
| `agents_hub/api/routes/group_chat.py` | 新增两个 POST 端点（单个压缩 + 全量压缩） |
| `agents_hub/api/schemas/` | 新增压缩响应 Schema |
| `agents_hub/core/context/group_chat_runtime.py` | 新增 `add_system_message()` 方法（供压缩写入系统消息） |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | MemberItem 新增 `...` 下拉菜单 |
| `frontend/src/layouts/ChatArea/ChatInput.tsx` | 新增通用 slash command 框架 |
| `frontend/src/core/api/groupChatApi.ts` | 新增压缩 API 调用函数 |
| `frontend/src/shared/types/api-schemas.ts` | MemberWithRole 新增 `compressing` 字段（前端本地计算） |

### 跨层依赖

- API 层调用 Agent.compress_context()（通过 GroupChat 编排层访问 Agent 实例）
- Agent 层调用 `self.execute()`（已有能力，无新依赖）
- Agent 层写入 `agent_cwd / docs / hand-off/`（文件 IO，无层间依赖）
- Agent 层通过 `group_chat_context.runtime` 更新状态（已有模式）
- API 层 catch AgentBusyError → 返回 409（新增错误处理模式）

### 资源清理

压缩过程中不涉及新的资源分配，无需额外清理。新建的 session 复用现有 main_session 生命周期管理。
