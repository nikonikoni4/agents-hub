# PRD: 记忆助手定时调度系统

**Triage Label**: ready-for-agent

---

## Problem Statement

Agents Hub 平台上的群聊积累了大量对话记录，但缺乏自动化的记忆提取机制。用户需要一个定时系统，能够每天自动扫描所有活跃群聊，启动记忆助手Agent对群聊内容进行总结，生成任务日志、用户决策、AI错误记录和协作建议。手动触发记忆收集效率低下，且容易遗漏。

---

## Solution

实现一个独立的定时调度模块（`agents_hub/scheduler/`），使用 APScheduler 框架，每天 10:00 自动触发记忆助手执行。调度模块通过读取 `local_data/memory/Index.json` 判断哪些群聊需要更新，启动记忆助手Agent调用MCP工具获取历史总结和新消息，完成记忆收集后更新 Index.json。

---

## User Stories

1. As a 系统管理员, I want 定时模块在每天10:00自动触发记忆收集, so that 群聊记忆能够持续更新而无需人工干预
2. As a 系统管理员, I want 如果10:00时系统未运行，在启动后自动补偿执行, so that 不会因为系统重启而遗漏记忆收集
3. As a 系统管理员, I want 通过Index.json记录每个群聊的最后更新时间, so that 系统能够判断哪些群聊需要更新
4. As a 系统管理员, I want 如果Index.json为空或不存在，自动处理所有群聊, so that 首次运行或数据丢失时能够完整初始化
5. As a 记忆助手Agent, I want 通过MCP工具获取群聊的历史总结和新消息, so that 我能够在完整上下文基础上进行总结
6. As a 记忆助手Agent, I want 输入群聊ID和上次更新时间给MCP工具, so that MCP工具能够获取对应的历史总结和新消息
7. As a 记忆助手Agent, I want MCP工具返回历史总结和新消息的拼接内容, so that 我能够在完整上下文基础上进行总结
8. As a 记忆助手Agent, I want MCP工具验证我的Token身份, so that 系统安全性得到保障
9. As a 记忆助手Agent, I want 将任务总结写入history.jsonl, so that 历史总结能够被下次执行时读取
10. As a 记忆助手Agent, I want 将用户决策写入my-decisions/目录, so that 决策记录能够被独立查阅
11. As a 记忆助手Agent, I want 将AI错误写入ai_mistake/目录, so that 错误记录能够用于改进Agent
12. As a 记忆助手Agent, I want 将协作建议写入suggestions/目录, so that 建议能够促进用户与AI的协作
13. As a 记忆助手Agent, I want history.jsonl保留最近1000条记录, so that 存储空间得到控制
14. As a 定时模块, I want 在记忆助手执行完成后更新Index.json, so that 下次执行时能够正确判断需要更新的群聊
15. As a 定时模块, I want 使用.schedule_state.json记录任务执行状态, so that 补偿执行逻辑能够正确判断是否需要补偿
16. As a 开发者, I want 定时模块通过FastAPI lifespan管理生命周期, so that 调度器能够随应用启动和关闭
17. As a 开发者, I want 定时模块是独立的顶层模块, so that 职责清晰且易于维护

---

## Implementation Decisions

### 1. 模块结构

定时模块作为独立顶层模块，目录为 `agents_hub/scheduler/`，与 `api/`、`core/` 平级。

内部结构：
- `scheduler/` - 调度器核心（APScheduler 封装）
- `scheduler/task/` - 具体任务实现（记忆更新任务）

### 2. APScheduler 配置

- 使用 `AsyncIOScheduler`（异步调度器）
- 使用 `CronTrigger` 实现每天 10:00 触发
- 支持补偿执行：启动时检查 `{data_path}/schedule/.schedule_state.json` 的 `memory_task` 字段，若今天未执行且已过10:00，则补偿执行一次

### 3. 生命周期管理

- 调度器在 FastAPI lifespan 的 startup 事件中初始化并启动
- 调度器在 FastAPI lifespan 的 shutdown 事件中关闭
- 系统任务在初始化时注册，启动时统一添加

### 4. Index.json 设计

存储位置：`{data_path}/schedule/memory/index.json`

字段设计：
```json
{
  "<group_chat_id>": {
    "last_updated": "2026-06-24T10:00:00Z"
  }
}
```

- 以 `group_chat_id` 为 key，对象包含 `last_updated` 字段
- 保留扩展性，后续可添加更多字段
- 空文件或不存在时，处理所有群聊

### 5. .schedule_state.json 设计

存储位置：`{data_path}/schedule/.schedule_state.json`

字段设计：
```json
{
  "memory_task": "2026-06-24T10:00:00Z"
}
```

- `memory_task`: 记录记忆任务最后一次执行时间
- 用于判断今天10:00是否已执行过记忆任务
- 补偿逻辑：如果10:00时app未启动，启动后检查该字段，若今天未执行则补偿执行

### 6. MCP 工具设计

工具职责：
1. 验证 Agent Token 身份
2. 获取历史群聊总结内容
3. 获取群聊新消息（使用 `session_parser.py` 的 `get_group_chat_messages`）
4. 拼接返回给记忆助手Agent

输入参数：
- `group_chat_id`: 群聊ID
- `last_updated`: 上次更新时间

输出：
- 拼接后的内容（历史总结 + 新消息）

### 7. 记忆助手 Agent 触发

- 定时模块通过调用 Agent 执行接口启动记忆助手
- 传入参数：群聊ID、上次更新时间、拼接后的数据
- Agent 执行完成后，定时模块更新 Index.json

### 8. 文件存储结构

**调度数据**（`{data_path}/schedule/`）：
```
{data_path}/
└── schedule/                        # 定时任务调度
    ├── memory/                      # 群聊记忆数据
    │   └── index.json               # 记录群聊记忆更新时间
    └── .schedule_state.json         # 调度状态持久化
```

**记忆文件**（`{memory_path}/`）：
```
{memory_path}/
├── my-decisions/                    # 用户决策记录
│   ├── index.md
│   ├── user-design-summary.md
│   └── {YYYY-mm-DD-<summary>}.md
├── ai_mistake/                      # AI 错误记录
│   ├── index.md
│   └── records.md
├── agents_hub_history/              # 会话历史
│   └── history.jsonl                # 保留1000条
└── suggestions/                     # 协作改进建议
    ├── index.md
    └── {YYYY-mm-DD-<summary>}.md
```

### 9. history.jsonl 字段设计

每条记录包含：
- `group_chat_id`: 群聊ID
- `timestamp`: 总结时间戳
- `summary`: 总结内容

---

## Testing Decisions

### 测试边界

| 边界 | 测试内容 |
|------|----------|
| **调度器** | APScheduler 初始化、任务注册、每天10:00触发、补偿执行逻辑 |
| **Index.json** | 读取群聊列表、写入更新时间、空文件/不存在时的处理 |
| **MCP工具** | Token验证、获取历史总结、获取新消息、拼接逻辑 |
| **Agent触发** | 定时模块启动记忆助手Agent、传入正确参数 |
| **文件写入** | Agent写入 history.jsonl（保留1000条）、decisions、mistakes、suggestions |

### 测试策略

1. **调度器测试**：模拟时间触发，验证任务注册和执行逻辑
2. **Index.json 测试**：测试空文件、正常文件、并发写入场景
3. **MCP工具测试**：Mock Token验证、Mock 数据源，验证拼接逻辑
4. **集成测试**：端到端测试定时触发到文件写入的完整流程

---

## Out of Scope

1. 记忆助手Agent内部的具体执行逻辑（任务log、决策编写、错误记录、建议生成）
2. MCP工具的具体实现位置（由架构师决定）
3. 记忆助手的提示词完善（`## 任务log` 部分）
4. 非记忆相关的定时任务扩展
5. 多实例部署下的任务调度协调

---

## Further Notes

### 参考实现

定时模块参考 LifeWatch-AI 的 `schedule_service.py` 实现，关键设计模式：
- APScheduler 单例模式
- 配置驱动的任务注册
- Cron 状态文件的幂等性保障
- 启动时的补偿执行逻辑
- `"D:\desktop\软件开发\LifeWatch-AI\lifeprism\server\services\schedule_service.py"`
### 依赖关系

- `agents_hub/utils/session_parser.py` - 获取群聊消息
- `agents_hub/config/config.py` - 配置项（memory_path、default_memory_assistant_name）
- `agents_hub/roles/prompt_file.py` - 记忆助手提示词
