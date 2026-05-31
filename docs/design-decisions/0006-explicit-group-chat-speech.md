---
version: 0.1
created_at: 2026-05-31
updated_at: 2026-05-31
last_updated: 创建草案，决策延后至 MCP 主流程跑通后再实施
abstract: 将群聊发言从 Agent.run() 出口 A/B 的隐式自动写入，改为显式 MCP 工具调用（speak_in_group_chat），目的是分离 LLM 的"私下思考过程"与"对外公开发言"，避免中间工具调用细节污染群聊历史与下游 agent 上下文
status: deferred
---

# 群聊发言：从隐式自动写入改为显式工具调用

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 0.1  | 创建草案，捕获讨论结论，等待 MCP 主流程跑通后实施 |

## 状态说明

本 ADR 状态为 `deferred`：方向已基本确定（改成显式工具调用），但**实施时机延后**至 MCP Server 主流程跑通、整体流程可端到端验证之后。原因：

- 当前阶段是 MCP 工具集首版交付，引入此重构会让 MCP 设计与 Agent 层重构相互纠缠，复杂度暴增
- 该问题属于"非阻塞性的体验和质量问题"，不影响 MCP 的功能正确性
- 等 MCP 流程完整运行后再回头改，能拿到真实的对话样本，更好评估"哪些内容应该进群聊"

## 问题界定

### 问题简述

当前 [Agent.run()](agents_hub/core/agent/base_agent.py) 在每次 LLM turn 完成后，无条件将 `result.text` 写入两个地方：

- **出口 A**：`group_chat_context.add_message(render_for_chat(self.name, msg.send_from, result.text))` —— 写入群聊历史
- **出口 B**：当 message_type=TASK 且 send_from!=user 时，把 result.text 自动作为回执投递给发起者

`result.text` 是 LLM 整个 turn 的所有 text_delta 拼接，包含：

- 思考过程（"明白，我来分析一下..."）
- 工具调用前的解释（"现在我搜索一下相关文件"）
- 工具调用之间的状态更新（"找到了，接下来读取"）
- 工具调用后的总结
- 最终对外的回应

这些内容混在一起，**没有结构化区分**就被写入群聊历史和回执。

### 影响

1. **语义混乱**：群聊里的一条 "Manager 的发言" 包含了内部工具调用细节，读者无法区分"哪部分是给我看的"
2. **上下文污染**：其他 Agent 通过 `agent_context.get_context()` 读群聊历史时，会读到 Manager 的工具调用过程，这些信息对它们完全无关
3. **Token 浪费**：噪音内容进入压缩前的群聊上下文，每次压缩都背着这些垃圾
4. **抽象层破坏**：Manager 的内部思考过程暴露给前端 user 和其他 agent，是合作平台不该有的隐私穿透

### 讨论范围

- Agent 输出哪些内容应当进群聊
- 出口 A 和出口 B 的存废与重构
- 新增 `speak_in_group_chat` MCP 工具的定位和职责
- LLM 遗忘调用工具的兜底机制

### 非讨论范围

- LLM prompt 工程的具体措辞（写入 role 的 CLAUDE.md 时再细化）
- 前端如何渲染群聊消息
- 流式输出（execute_stream）替代非流式的相关问题（详见 9d 待解决问题）

## 可选方案

### 方案 A：保持现状（隐式自动写入）

**做法**：不改动 `Agent.run()`，继续把 `result.text` 整段塞进群聊和回执。

**优势**：
- 实现简单，已经在跑
- LLM 不需要主动决定何时发言

**劣势**：
- 上述四类问题持续存在
- 长期看，对话质量随 token 累积而劣化

### 方案 B：显式工具调用（本方案）

**做法**：

1. 取消出口 A、出口 B 的自动写入
2. 新增 MCP 工具 `speak_in_group_chat(agent_token, content)`
3. 该工具承担两个职责：
   - 把 content 写入群聊历史（替代旧出口 A）
   - 如果当前 agent 正在处理的 call 是 TASK，自动回执给 send_from（替代旧出口 B）
4. LLM 的所有 text 输出**默认私下**，只有调用 `speak_in_group_chat` 时才公开
5. role 的 system prompt（CLAUDE.md）明确指引这一约定

**优势**：
- "私下思考"与"公开发言"的边界由 LLM 主动控制，符合人类沟通直觉
- 群聊历史只包含被显式标记为公开的内容，干净
- 派活（call_agent，私信不进群聊）和发言（speak_in_group_chat，公开进群聊）语义彻底分开
- 其他 agent 加载上下文时不再被噪音污染

**劣势**：
- LLM 可能忘记调用 `speak_in_group_chat`，导致信息丢失
- 对 system prompt 的依赖加强，prompt 工程成本上升
- Agent 层重构涉及 base_agent.run() 的核心结构

### 方案 C：保留出口但只写"最终段"

**做法**：让 LLM 用某个标记（如 `<final>...</final>`）标注哪部分是公开发言，Agent 层 parse 这个标记后只写标记内的内容。

**优势**：
- 不引入新工具，改动较小

**劣势**：
- 依赖 LLM 严格遵守标记格式（极易遗漏或错位）
- 标记被 prompt injection 攻击的可能性（虽然在内部场景下不现实）
- 不如显式工具调用清晰

## 最终决策（草案）

倾向**方案 B：显式工具调用**。等 MCP 主流程跑通后正式立项实施。

## 决策原因

### 原因 1：与 ADR 0005 的设计哲学一致

ADR 0005 已确立"按需提供上下文""避免越权访问"为多 agent 通信的核心原则。让其他 agent 看到 Manager 的工具调用细节，违反了"按需提供上下文"。

### 原因 2：显式优于隐式

当前的"自动写入"是一个隐式契约——LLM 不知道它的所有输出都会被广播。显式工具调用让"对外发言"成为 LLM 主动决策的一部分，符合可观察性和可预测性的设计原则。

### 原因 3：tool 数量增长可控

测试阶段的 MCP 工具集已经有 `call_agent` `assign_tasks_to_team` `archive_task_list` `check_agent_call`，加一个 `speak_in_group_chat` 后总共 5 个，对 LLM 的 tool selection 复杂度影响很小，且每个工具职责非常清晰。

## 实施细节（待真正立项时填充）

以下条目在 deferred 期间只做记录，不展开：

- `speak_in_group_chat` 的具体签名和返回值
- 取消出口 A 后，前端如何感知"Manager 还没说话但 turn 已结束"（涉及流式输出问题，与 9d 联动）
- LLM 遗忘调用工具的兜底机制：候选 (a) 强 prompt 教育、(b) Agent.run() 检查并补提示、(c) 不缓解
- worker 完成 task 时如何回执 manager（speak_in_group_chat 自动联动 vs 单独工具）
- role 的 CLAUDE.md 模板更新

## 后续影响

### 对当前 MCP 工具设计的影响

本 ADR `deferred` 期间，**首版 MCP 工具集仍假设"出口 A/B 自动写入"在跑**。即：
- `call_agent`、`assign_tasks_to_team`、`check_agent_call`、`archive_task_list` 这四个工具的设计**不依赖** speak_in_group_chat 是否存在
- 一旦本 ADR 立项实施，会**新增** `speak_in_group_chat`，并**修改** `Agent.run()` 的出口逻辑——但前四个工具的语义和签名不受影响

### 对未来 spec 的影响

本 ADR 立项实施时需要：
- 撰写 `speak_in_group_chat` 的工具 spec
- 修订 `core-agent-orchestration` spec 中的 Agent 消息循环段落
- 检查 ADR 0005 的"消息流转"描述是否需要同步更新

## 与其他决策的关联

- ADR 0005（消息架构）：本 ADR 是 0005 的延伸细化，把"按需提供上下文"原则推进到"按意愿公开发言"层面
- 9d 待解决问题（流式输出 vs 非流式输出）：当前 `execute()` 全部完成才返回的设计，与本 ADR 共同导致"user 等很久才看到 Manager 说话"的体验问题。两者可以独立推进，但合并解决体验最佳
