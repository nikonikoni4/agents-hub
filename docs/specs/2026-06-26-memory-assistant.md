---
version: 1.0
created_at: 2026-06-26
updated_at: 2026-06-26
last_updated: 创建 memory-assistant spec 初稿
abstract: 记忆助手 Agent 的职责规格，定义 4 类记忆文件的生成规则、MCP 工具调用契约和知识文件同步机制
id: memory-assistant
title: 记忆助手 Agent
status: draft
module: roles
source_spec:
related_plan:
code_scope: agents_hub/roles/, agents_hub/scheduler/, template/memory-assistant/
contract_refs: agents_hub/mcp/server.py, agents_hub/roles/prompt_file.py, agents_hub/scheduler/state_manager.py
---

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：群聊积累了大量对话记录，包含用户决策、AI 错误和协作改进点，但这些知识散落在聊天历史中无法复用。需要一个自动化机制，定期从群聊对话中提取有价值的知识并分类沉淀。

**核心职责**：
- 从群聊对话中识别并提取 4 类知识：任务日志、用户决策、AI 错误、协作建议
- 按照知识文件编写规范生成结构化文档
- 通过 MCP 工具获取群聊上下文（历史总结 + 新消息）
- 将执行结果写入 history.jsonl 供下次执行参考

## Scope

### 范围内

- 记忆助手的身份定义和角色职责
- 4 类记忆文件的生成规则和判断标准
- MCP 工具 `get_memory_context` 的输入输出契约
- 记忆文件存储结构（history.jsonl、index.json、result.json）
- knowledge-base 文件同步机制

### 范围外

- 定时调度机制（由 `scheduler` spec 负责）
- 群聊消息的存储和管理（由 `core-context` spec 负责）
- Agent 执行引擎（由 `agent-bridge` spec 负责）

## Technical Contract

### 记忆助手身份

**角色名称**：由 `config.default_memory_assistant_name` 定义（默认 `Agents-Hub-Memory-Assistant`）

**角色类型**：`RoleType.SYSTEM`（系统角色，不可删除）

**Token 机制**：使用独立的 `config.memory_assistant_token`，不依赖群聊 token 机制

### 4 类记忆文件

| 类型 | 存储路径 | 触发条件 | 写入频率 |
|------|---------|---------|---------|
| 任务日志 | `{data_path}/schedule/memory/agents_hub_history/history.jsonl` | 每次执行 | 每次 |
| 用户决策 | `{decision_path}/` | 存在难以逆转的选择 | 按需 |
| AI 错误 | `{data_path}/schedule/memory/ai_mistake/` | Agent 被纠正或犯错 | 按需 |
| 协作建议 | `{data_path}/schedule/memory/suggestions/` | 存在协作方式改进 | 按需 |

### 判断标准

#### 任务日志（每次都写）

基础记录，每次记忆更新都应写入。

#### 用户决策（按需写入）

**写入信号**：
- 用户在两个方案间做了选择（"用 A 方案"、"我觉得 B 更好"）
- 用户否定了 AI 的建议并给出理由
- 讨论中出现了明确的权衡取舍
- 用户表达了对某种方式的偏好（"以后都这样做"）

**不写入**：
- 只是执行常规操作，没有权衡
- 问题有唯一解，不存在替代方案
- AI 自行做出的技术选择（不代表用户意图）

#### AI 错误（按需写入）

**写入信号**：
- 用户明确纠正了 Agent（"不是这样"、"错了"、"你应该..."）
- Agent 的方案被否决，用户给出了正确方向
- Agent 执行了错误操作导致需要回滚或修复
- Agent 遗漏了明显问题，用户指出后才发现
- Agent 完全不知道自己该做什么
- Agent 表现出困惑、无法继续

**不写入**：
- 正常的需求澄清过程
- 用户改变主意（不是 Agent 的错）
- 技术限制导致的方案调整
- 用户输入不明确导致的误解（属于建议范畴）

#### 协作改进建议（按需写入）

**写入信号**：
- 用户明确提出了协作改进建议（"下次能不能..."、"我希望你..."）
- 反复出现的协作摩擦点（同一类问题被指出 2 次以上）
- 用户建立了新的工作习惯或流程偏好
- 用户输入不明确导致 Agent 误解（给用户的建议）

**不写入**：
- 技术问题（属于 AI 错误）
- 任务需求本身（属于任务日志）
- 架构/技术决策（属于决策记录）

### MCP 工具：get_memory_context

<key_function last_update="2026-06-28T09:38:27+08:00">
- agents_hub/mcp/server.py
  - server.get_memory_context:1480
  - server._verify_memory_token:131
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `get_memory_context(agent_token, group_chat_id, last_updated)` | 获取群聊上下文 | 使用 `config.memory_assistant_token` 验证身份 |

**输入参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `agent_token` | str | 记忆助手的身份令牌 |
| `group_chat_id` | str | 群聊 ID |
| `last_updated` | str \| None | 上次更新时间（ISO 8601 格式） |

**返回值**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `group_chat_id` | str | 群聊 ID |
| `last_updated` | str | 上次更新时间 |
| `history_summary` | str | 历史总结内容（从 history.jsonl 最后一行读取） |
| `new_messages` | str | 新消息内容（通过 `get_group_chat_messages` 获取） |
| `context` | str | 拼接后的完整上下文 |

### 数据模型

#### history.jsonl

每条记录包含：
```json
{
  "group_chat_id": "群聊ID",
  "timestamp": "2026-06-26T10:00:00Z",
  "summary": "总结内容"
}
```

**约束**：保留最近 1000 条记录，超出时裁剪最旧的记录

#### memory/index.json

```json
{
  "<group_chat_id>": {
    "last_updated": "2026-06-26T10:00:00Z"
  }
}
```

#### memory/result.json

```json
[
  {
    "timestamp": "2026-06-26T10:00:05Z",
    "group_chat_id": "群聊ID",
    "success": true,
    "result": "记忆收集完成，已更新 4 份文件"
  }
]
```

**字段说明**：
- `timestamp` (str): 执行时间戳（ISO 8601 格式）
- `group_chat_id` (str): 群聊 ID
- `success` (bool): 是否执行成功
- `result` (str): 执行结果文本

**约束**：保留最近 10 条记录，用于调试

### knowledge-base 文件同步

**同步时机**：每次系统启动时，通过 `bootstrap.py` 自动同步

**同步机制**：
1. 从 `template/memory-assistant/` 复制到 `{data_path}/agents/{role_name}/work_root/knowledge-base/`
2. 如果已存在则先删除再复制，确保是最新版本

**文件清单**：
```
knowledge-base/
├── task-log.md        # 任务日志编写规范
├── decisions.md       # 决策记录编写规范
├── ai-mistake.md      # AI 错误记录编写规范
├── suggestions.md     # 协作改进建议编写规范
└── references/        # 参考资料
    ├── decision-template.md
    └── user-design-summary-template.md
```

## Design Rationale

**为什么这样设计？**
- **4 维度分类**：覆盖用户决策、AI 错误、协作建议、任务日志四个关键知识维度
- **按需写入**：只有存在明确信号时才写入，避免无意义的日志堆积
- **独立 Token**：记忆助手使用独立 token，与群聊 token 机制解耦
- **knowledge-base 同步**：每次启动自动同步，确保记忆助手使用最新的编写规范

**有哪些约束？**
- 记忆助手只能通过 `get_memory_context` 获取群聊数据，不能直接访问文件系统
- history.jsonl 保留 1000 条上限，超出时自动裁剪
- 用户决策路径（`decision_path`）与系统数据路径（`data_path`）分离，决策可跨项目复用

**有哪些已知限制？**
- 记忆助手不支持增量更新，每次执行都处理全部新消息
- history.jsonl 只读取最后一行作为历史总结，不支持多轮总结合并
- knowledge-base 文件修改后需要重启系统才能生效

**相关 ADR**：
- 无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **Scheduler**：定时调度机制（见 `scheduler` spec）
- **Core Context**：群聊消息存储（见 `core-context` spec）
- **Agent Bridge**：Agent 执行引擎（见 `agent-bridge` spec）
