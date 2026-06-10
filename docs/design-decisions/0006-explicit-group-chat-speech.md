---
version: 1.1
created_at: 2026-05-31
updated_at: 2026-06-04
last_updated: 明确 complete_task 对 Agent 调用方投递完成通知，对 user 调用方写入群聊并刷新前端
abstract: 将群聊发言从 Agent.run() 出口 A/B 的隐式自动写入，改为显式 MCP 工具调用；普通公开发言使用 report_progress，需要回复的 AgentCall 使用 complete_task 闭环，Agent 调用方通过完成通知唤醒，user 调用方通过群聊消息和 refresh 感知结果
status: decided
---

# 群聊发言：从隐式自动写入改为显式工具调用

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 0.1  | 创建草案，捕获讨论结论，等待 MCP 主流程跑通后实施 |
| 1.0  | 采纳显式发言与显式调用闭环方案，明确 report_progress 不负责关闭 AgentCall |
| 1.1  | 明确 complete_task 不默认写群聊；闭环后对 Agent 调用方创建完成通知，对 user 调用方写入群聊并刷新前端 |

## 状态说明

本 ADR 状态为 `decided`：已采纳显式工具方案，并进一步拆分为两个语义不同的工具：

- `report_progress`：公开发言，只写入群聊，不创建、不关闭 AgentCall
- `complete_task`：结束一次需要回复的 AgentCall；原调用方是 Agent 时投递完成通知，原调用方是 user 时写入群聊消息

核心原则：**调用/指令是控制面事实，群聊消息是公开协作记录**。群聊消息不反向驱动 Agent 调用状态。

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
- 新增 `report_progress` MCP 工具的定位和职责
- 新增 `complete_task` MCP 工具的定位和职责
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

### 方案 B：显式发言工具，并由 speak 自动回执

**做法**：

1. 取消出口 A、出口 B 的自动写入
2. 新增 MCP 工具 `report_progress(agent_token, content)`
3. 该工具承担两个职责：
   - 把 content 写入群聊历史（替代旧出口 A）
   - 如果当前 agent 正在处理的 call 是 TASK，自动回执给 send_from（替代旧出口 B）
4. LLM 的所有 text 输出**默认私下**，只有调用 `report_progress` 时才公开
5. role 的 system prompt（CLAUDE.md）明确指引这一约定

**优势**：
- "私下思考"与"公开发言"的边界由 LLM 主动控制，符合人类沟通直觉
- 群聊历史只包含被显式标记为公开的内容，干净
- 派活（call_agent，私信不进群聊）和发言（report_progress，公开进群聊）语义彻底分开
- 其他 agent 加载上下文时不再被噪音污染

**劣势**：
- LLM 可能忘记调用 `report_progress`，导致信息丢失
- 对 system prompt 的依赖加强，prompt 工程成本上升
- Agent 层重构涉及 base_agent.run() 的核心结构
- `report_progress` 同时表示"公开说话"和"完成调用"，语义过载

### 方案 C：保留出口但只写"最终段"

**做法**：让 LLM 用某个标记（如 `<final>...</final>`）标注哪部分是公开发言，Agent 层 parse 这个标记后只写标记内的内容。

**优势**：
- 不引入新工具，改动较小

**劣势**：
- 依赖 LLM 严格遵守标记格式（极易遗漏或错位）
- 标记被 prompt injection 攻击的可能性（虽然在内部场景下不现实）
- 不如显式工具调用清晰

### 方案 D：显式发言 + 显式调用闭环（本方案）

**做法**：

1. 取消 `Agent.run()` 出口 A、出口 B 的自动写入
2. 新增 `report_progress`，只负责在群聊公开发言
3. 新增 `complete_task`，只负责结束需要回复的 AgentCall
4. AgentCall 增加"是否已被 Agent 显式回复"的闭环标志
5. 当 TASK 执行一轮后仍未闭环，系统给该 Agent 发送提醒消息，要求调用 `complete_task`
6. LLM 普通 text 输出默认私下保留，不进入群聊，也不作为回执

**优势**：
- 公开发言和任务回执语义清晰，不再互相覆盖
- `call_id` 只由调用闭环工具消费，便于 AgentCall 状态机维护
- Worker 可以先用 `report_progress` 说"收到/处理中"，不提前关闭任务
- 任务完成、失败或无法继续时，必须通过 `complete_task` 明确结束调用

**劣势**：
- MCP tool 数量增加到 6 个，prompt 指引需要更清楚
- LLM 可能忘记 `complete_task`，需要系统提醒兜底

## 最终决策

选择**方案 D：显式发言 + 显式调用闭环**。

## 决策原因

### 原因 1：与 ADR 0005 的设计哲学一致

ADR 0005 已确立"按需提供上下文""避免越权访问"为多 agent 通信的核心原则。让其他 agent 看到 Manager 的工具调用细节，违反了"按需提供上下文"。

### 原因 2：显式优于隐式

当前的"自动写入"是一个隐式契约——LLM 不知道它的所有输出都会被广播。显式工具调用让"对外发言"成为 LLM 主动决策的一部分，符合可观察性和可预测性的设计原则。

### 原因 3：tool 数量增长可控

测试阶段的 MCP 工具集已有 `call_agent` `assign_tasks_to_team` `archive_task_list` `check_agent_call`。新增 `report_progress` 和 `complete_task` 后总共 6 个，数量仍可控；更重要的是每个工具职责边界更清晰。

### 原因 4：回复闭环必须绑定 AgentCall，而不是绑定群聊发言

`call_agent` 创建的是一次控制面调用，`call_id` 是这次调用的回执凭证。完成任务时传回 `call_id`，系统才能准确更新 AgentCall 状态、停止等待、保留可查询记录。`report_progress` 是公开说话动作，不应该因为携带一个 ID 就改变调用生命周期。

### 原因 5：完成事件应唤醒原调用方，而不是要求轮询

Manager 派活后会立即拿到 `call_id`，并可能结束当前 LLM turn；如果 Worker 完成后只更新 AgentCall 状态，Manager 需要额外等待或轮询才能继续协作。`complete_task` 闭环后创建一条 `NOTIFICATION` 投递给原调用方，可以自然唤醒 Manager 的下一轮 LLM 调用。该机制同样适用于未来开放 Worker 之间相互派活的场景：例如执行型 Worker 向顾问型 Worker 发起 TASK，顾问完成后通过完成通知唤醒执行者继续处理。

当原调用方是 `user` 时，`MessageRouter` 中的 user 只是路由身份占位，没有对应的 Agent run loop 消费队列。因此 user 调用方不走完成通知队列，而是把最终回复写入群聊历史，并通过 realtime refresh 让前端拉取展示。

## 实施细节

- `report_progress`：用于普通群聊公开发言，可选 @ 某个对象；写入前执行 token 剥离
- `complete_task`：只能用于需要回复的 TASK 调用；只有调用接收者可以结束该 call；notification 调用使用该工具会报错；闭环后如果原调用方是 Agent，则创建一条 `NOTIFICATION` 投递给原调用方，用于唤醒其下一轮处理；如果原调用方是 user，则写入群聊历史并触发前端 refresh
- `AgentCall` 增加显式回复闭环标志，用于判断 TASK 是否已经由 Agent 主动结束
- TASK 执行一轮后如果仍未闭环，Agent.run() 给该 Agent 私有队列追加系统提醒，要求调用 `complete_task`
- `Agent.run()` 不再把 `result.text` 自动写入群聊，也不再自动给发送者投递回执

- 取消出口 A 后，前端如何感知"Manager 还没说话但 turn 已结束"（涉及流式输出问题，与 9d 联动）
- role 的 CLAUDE.md 模板更新

## 后续影响

### 对当前 MCP 工具设计的影响

MCP 工具集新增两个明确的群聊协作工具：
- `report_progress`：公开发言
- `complete_task`：结束需要回复的调用；Agent 调用方收到完成通知，user 调用方通过群聊消息和 refresh 收到结果

`call_agent` 仍负责创建调用；`check_agent_call` 仍负责查询调用状态；二者不承担公开发言职责。

### 对未来 spec 的影响

需要同步修订 `core-agent-orchestration` 和 `core-communication` spec 中关于 Agent 消息循环、AgentCall 生命周期、MCP 工具入口的描述。

## 与其他决策的关联

- ADR 0005（消息架构）：本 ADR 是 0005 的延伸细化，把"按需提供上下文"原则推进到"按意愿公开发言"层面
- 9d 待解决问题（流式输出 vs 非流式输出）：当前 `execute()` 全部完成才返回的设计，与本 ADR 共同导致"user 等很久才看到 Manager 说话"的体验问题。两者可以独立推进，但合并解决体验最佳
