# Issue 03: 状态管理

Status: ready-for-agent

## What to build

实现 `StateManager` 类，管理调度状态文件的读写。

状态文件：
- `.schedule_state.json`：记录 memory_task 最后执行时间
- `index.json`：记录每个群聊的 last_updated
- `result.json`：记录每次执行的输出（保留最近 10 条，用于调试）

## Acceptance criteria

- [ ] 实现 `StateManager` 类，初始化时创建必要的目录
- [ ] 实现 `.schedule_state.json` 的读写方法
- [ ] 实现 `index.json` 的读写方法
- [ ] 实现 `result.json` 的追加写入方法（保留最近 10 条）
- [ ] 处理文件不存在的情况（返回空字典/列表）
- [ ] 处理 JSON 解析错误（返回空字典/列表并记录警告）

## Blocked by

- Issue 01: 调度器基础框架（需要 scheduler 模块结构）

## Architecture reference

架构约束文件：`.scratch/memory-assistant-scheduler/architecture.md`

## Implementation notes

文件路径：
- `{data_path}/schedule/.schedule_state.json`
- `{data_path}/schedule/memory/index.json`
- `{data_path}/schedule/memory/result.json`

使用 `Path.mkdir(parents=True, exist_ok=True)` 确保目录存在。

接口签名（详见架构约束文件）：
```python
class StateManager:
    def __init__(self, data_path: Path)
    def load_schedule_state(self) -> dict
    def save_schedule_state(self, state: dict) -> None
    def load_memory_index(self) -> dict
    def save_memory_index(self, index: dict) -> None
    def should_execute_today(self) -> bool  # 比较 date 部分
    def append_result(self, group_chat_id: str, result: str, success: bool) -> None
```

StateManager 被 SchedulerService 持有，在 `__init__` 中创建：
```python
class SchedulerService:
    def __init__(self):
        self._state_manager = StateManager(config.data_path)
```

参考实现：`agents_hub/config/config.py` 中的 `_load_config()` / `_save_config()` 方法（JSON 文件读写模式）。
