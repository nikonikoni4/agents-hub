# 记忆助手定时调度系统 - 架构约束文件

## 模块职责边界

### 新建模块：`agents_hub/scheduler/`

**职责**：定时调度记忆助手执行，管理调度状态和记忆索引

**目录结构**：
```
agents_hub/scheduler/
├── __init__.py              # 模块入口，导出 scheduler_service 单例
├── scheduler_service.py     # 调度器核心（APScheduler 封装）
├── state_manager.py         # 状态文件管理（.schedule_state.json、index.json）
└── task/
    ├── __init__.py
    └── memory_task.py       # 记忆更新任务实现
```

**依赖关系**：
```
scheduler → config (config.memory_path, config.default_memory_assistant_name)
scheduler → utils/session_parser.py (get_group_chat_messages)
scheduler → mcp/server.py (新增 MCP 工具)
scheduler → api/app.py (lifespan 集成)
```

### MCP 工具：`get_memory_context`

**职责**：为记忆助手提供群聊历史总结和新消息的拼接内容

**位置**：`agents_hub/mcp/server.py` 中新增

**接口设计**：
```python
async def get_memory_context(
    agent_token: str,
    group_chat_id: str,
    last_updated: str | None = None,
) -> dict:
    """
    获取记忆助手所需的上下文数据

    Args:
        agent_token: 记忆助手的身份令牌
        group_chat_id: 群聊ID
        last_updated: 上次更新时间（ISO 8601 格式）

    Returns:
        成功: {
            "group_chat_id": "...",
            "last_updated": "...",
            "history_summary": "...",  # 历史总结内容
            "new_messages": "...",     # 新消息内容
            "context": "..."           # 拼接后的完整上下文
        }
        失败: {"error": {"code": "...", "message": "..."}}
    """
```

**验证逻辑**：
1. 验证 agent_token 有效性（通过 group_chat_manager.resolve_token）
2. 验证调用者是否为记忆助手角色（通过 config.default_memory_assistant_name 判断）
3. 读取历史总结文件（{memory_path}/agents_hub_history/history.jsonl）
4. 调用 get_group_chat_messages 获取新消息
5. 拼接返回

## 数据流

### 定时触发流程

```
APScheduler CronTrigger (每天 10:00)
  → scheduler_service._execute_memory_task()
    → state_manager.load_memory_index()  # 读取 index.json
    → 获取所有活跃群聊列表
    → 对每个群聊：
      → 检查是否需要更新（对比 last_updated）
      → 调用 memory_task.execute(group_chat_id, last_updated)
        → 启动记忆助手 Agent（通过 GroupChatManager）
        → Agent 调用 get_memory_context 获取上下文
        → Agent 执行记忆收集（生成 4 份文件）
        → Agent 执行完成后更新 index.json
      → state_manager.save_memory_index()  # 更新 last_updated
    → state_manager.save_schedule_state()  # 更新 .schedule_state.json
```

### 补偿执行流程

```
FastAPI lifespan startup
  → scheduler_service.start()
    → 加载 .schedule_state.json
    → 检查 memory_task 今天是否已执行
    → 如果已过 10:00 且未执行：
      → asyncio.create_task(_execute_memory_task())
    → 注册 CronTrigger 任务
```

## 配置项设计

在 `config` 模块中新增定时任务执行时间配置：

| 字段名 | 类型 | 默认值 | 语义 |
|--------|------|--------|------|
| `memory_task_cron_hour` | int | 10 | 记忆任务执行小时（0-23） |
| `memory_task_cron_minute` | int | 0 | 记忆任务执行分钟（0-59） |

**Config 属性**：
```python
@property
def memory_task_cron_time(self) -> tuple[int, int]:
    """获取记忆任务的 Cron 执行时间（hour, minute）"""
    return (self._config.get("memory_task_cron_hour", 10),
            self._config.get("memory_task_cron_minute", 0))
```

## 依赖关系

### 外部依赖

| 依赖 | 用途 | 导入方式 |
|------|------|---------|
| APScheduler | 定时任务调度 | `from apscheduler.schedulers.asyncio import AsyncIOScheduler` |
| config | 配置项访问（含 memory_task_cron_time） | `from agents_hub.config import config` |
| session_parser | 获取群聊消息 | `from agents_hub.utils.session_parser import get_group_chat_messages` |
| group_chat_manager | MCP 工具中验证 Token 和获取群聊实例 | `from agents_hub.core.orchestration import group_chat_manager` |

### 内部依赖

| 模块 | 依赖方 | 说明 |
|------|--------|------|
| scheduler_service | api/app.py | lifespan 中启动/关闭 |
| state_manager | scheduler_service | 状态文件读写 |
| memory_task | scheduler_service | 记忆更新任务执行 |
| get_memory_context (MCP) | memory_task | 获取上下文数据 |

## 接口契约

### SchedulerService

```python
class SchedulerService:
    """定时任务调度服务（单例）"""

    def start(self) -> None:
        """启动调度器，应在 FastAPI lifespan startup 中调用。
        具有幂等性：如果已启动则跳过。
        """

    def shutdown(self) -> None:
        """关闭调度器，应在 FastAPI lifespan shutdown 中调用。
        具有幂等性：如果未启动则跳过。
        """

    async def _execute_memory_task(self) -> None:
        """执行记忆更新任务（内部方法）。
        容错策略：单群聊失败时跳过并记录到 result.json，继续处理下一个群聊。
        """
```

**容错策略**：
- 单群聊执行失败时，记录错误到 result.json，跳过该群聊继续处理下一个
- 只有在所有群聊都处理完毕后，才更新 .schedule_state.json
- 单个群聊失败不影响其他群聊的更新

**并发保护**：
- `start()` 方法具有幂等性，已启动时直接返回
- 补偿执行和定时触发不会重叠：补偿执行使用 `asyncio.create_task`，APScheduler 的 CronTrigger 会在下一个触发时间执行
- `_execute_memory_task` 内部使用简单的状态标志防止重入

### StateManager

```python
class StateManager:
    """状态文件管理"""

    def __init__(self, data_path: Path):
        self._schedule_state_path = data_path / "schedule" / ".schedule_state.json"
        self._memory_index_path = data_path / "schedule" / "memory" / "index.json"
        self._result_path = data_path / "schedule" / "memory" / "result.json"

    def load_schedule_state(self) -> dict:
        """加载 .schedule_state.json"""

    def save_schedule_state(self, state: dict) -> None:
        """保存 .schedule_state.json"""

    def load_memory_index(self) -> dict:
        """加载 index.json"""

    def save_memory_index(self, index: dict) -> None:
        """保存 index.json"""

    def should_execute_today(self) -> bool:
        """判断今天是否需要执行记忆任务。
        实现逻辑：读取 .schedule_state.json 的 memory_task 字段，
        提取日期部分（YYYY-MM-DD）与今天比较。
        如果日期不同或字段不存在，返回 True。
        """

    def append_result(self, group_chat_id: str, result: str, success: bool) -> None:
        """追加执行结果到 result.json（保留最近10条）

        Args:
            group_chat_id: 群聊ID
            result: 执行结果文本
            success: 是否执行成功
        """
```

### MemoryTask

```python
class MemoryTask:
    """记忆更新任务"""

    async def execute(self, group_chat_id: str, last_updated: str | None) -> str:
        """
        执行单个群聊的记忆更新

        Args:
            group_chat_id: 群聊ID
            last_updated: 上次更新时间（ISO 8601 格式）

        Returns:
            执行结果文本（成功时为成功消息，失败时为错误描述）

        Raises:
            不抛出异常，内部捕获并返回错误描述
        """
```

## Agent 触发机制

### 设计决策

参考单聊模式（`single_chat_service.py`），使用 `agent_platform_client.execute_stream` 直接执行记忆助手，无需创建 GroupChat。

### 触发流程

```
SchedulerService._execute_memory_task()
  → 遍历 index.json 中的群聊列表
    → 对每个需要更新的群聊：
      → 获取记忆助手的 RoleConfig
      → 构建 prompt（包含任务描述 + agent token）
      → 调用 agent_platform_client.execute(prompt, role_config, session_id)
      → 记忆助手执行：
        → 调用 get_memory_context 获取上下文
        → 生成 4 份记忆文件
        → 返回执行结果
      → Scheduler 更新 index.json 的 last_updated
      → 记录执行结果到 result.md（用于调试）
```

### Prompt 构建

参考 `single_chat_service.py:284` 的 `_build_prompt` 方法：

```python
def _build_memory_prompt(group_chat_id: str, last_updated: str | None) -> str:
    """构建记忆助手的 prompt"""
    task = f"请处理群聊 {group_chat_id} 的记忆收集。"
    if last_updated:
        task += f"上次更新时间：{last_updated}"
    else:
        task += "这是首次执行，需要处理所有历史消息。"
    return f"{task}\n\n[系统提示] 你的 agent token 是: {config.assistant_token}"
```

### Token 管理

- 使用 `config.assistant_token`（系统助手统一 token）
- Token 在 prompt 中传递给记忆助手
- 记忆助手使用此 token 调用 `get_memory_context` MCP 工具

## 依赖补充

### APScheduler 依赖

需要在 `pyproject.toml` 中添加：
```toml
dependencies = [
    ...
    "apscheduler>=3.10.0",
    ...
]
```

## 文件存储结构

### 调度数据（`{data_path}/schedule/`）

```
{data_path}/
└── schedule/                        # 定时任务调度
    ├── memory/                      # 群聊记忆数据
    │   ├── index.json               # 记录群聊记忆更新时间
    │   └── result.json              # 记录每次更新的输出（保留最近10条，用于调试）
    └── .schedule_state.json         # 调度状态持久化
```

### 记忆文件（`{memory_path}/`）

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

### Index.json 设计

```json
{
  "<group_chat_id>": {
    "last_updated": "2026-06-24T10:00:00Z"
  }
}
```

### .schedule_state.json 设计

```json
{
  "memory_task": "2026-06-24T10:00:00Z"
}
```

### result.json 设计

记录每次记忆任务的执行结果，保留最近 10 条，用于调试。

```json
[
  {
    "timestamp": "2026-06-24T10:00:05Z",
    "group_chat_id": "ba8e155a-8339-448f-bea1-f25252381e89",
    "success": true,
    "result": "记忆收集完成，已更新 4 份文件"
  },
  {
    "timestamp": "2026-06-24T10:00:02Z",
    "group_chat_id": "another-group-chat-id",
    "success": false,
    "result": "错误：群聊消息文件不存在"
  }
]
```

## 实现位置

| 功能 | 文件位置 | 说明 |
|------|---------|------|
| 调度器核心 | `agents_hub/scheduler/scheduler_service.py` | APScheduler 封装，单例模式 |
| 状态管理 | `agents_hub/scheduler/state_manager.py` | 状态文件读写 |
| 记忆任务 | `agents_hub/scheduler/task/memory_task.py` | 记忆更新任务实现 |
| MCP 工具 | `agents_hub/mcp/server.py` | 新增 get_memory_context 工具 |
| 生命周期 | `agents_hub/api/app.py` | lifespan 中集成调度器 |

## 相关文档

- [Config Spec](../../docs/specs/2026-06-06-config.md) - 配置项定义
- [Core Agent Orchestration Spec](../../docs/specs/2026-05-31-core-agent-orchestration.md) - Agent 执行模型和 MCP 工具入口
- [Backend Concurrency Rules](../../docs/coding-rules/backend-concurrency.md) - 并发安全规则
- [Backend Singleton Rules](../../docs/coding-rules/backend-singleton.md) - 单例规则
- [LifeWatch-AI ScheduleService](../../../LifeWatch-AI/lifeprism/server/services/schedule_service.py) - 参考实现
