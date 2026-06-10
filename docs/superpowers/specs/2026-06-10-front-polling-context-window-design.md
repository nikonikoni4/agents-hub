# context_window 实时刷新 + 前端显示

## 背景

前端右侧栏成员列表的 `context_window` 和 `status` 数据依赖 WebSocket `refresh` 信号触发前端重新拉取。但 `context_window` 和 `status` 的更新发生在 core 层（`BaseAgent.run()`），当前没有触发 `broadcast_group_chat_refresh`，导致这些字段的变更只有在其他事件（如新消息）触发 refresh 时才能被前端感知。

## 目标

1. 后端 `/group-chats/{id}/members` API 返回 `context_window` 字段（已完成）
2. 前端成员列表显示上下文窗口大小（格式 `"100K"`、`"200K"`）
3. `context_window` 和 `status` 变更时通过 WebSocket 实时通知前端

## 设计

### 1. 后端：暴露 context_window

**改动文件**：

- `agents_hub/core/context/group_chat_runtime.py` → `get_member_dicts()` 增加 `context_window` 字段
- `agents_hub/api/schemas/group_chats.py` → `GroupChatMember` schema 增加 `context_window: int | None = None`

**数据流**：
```
AgentMemberInfo.context_window (int, 单位 K)
  → GroupChatRuntime.get_member_dicts()
    → GroupChatMember schema
      → API 响应 JSON
```

### 2. 前端：context_window 显示

**改动文件**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`

在 `MemberItem` 组件中显示上下文窗口。后端返回 int（单位 K），前端格式化为 `"100K"` 字符串。值为 `null` 时不显示。

### 3. 后端：state 变更时广播 refresh

**方案**：在 `GroupChatRuntime` 中注入 `on_change` 回调，仅在 `update_agent_context_window()` 和 `update_agent_status()` 中触发（`add_message` 和 `update_message_field` 的 broadcast 已在 API/MCP 层处理）。core 不直接依赖 realtime 模块。

**改动文件**：

- `agents_hub/core/context/group_chat_runtime.py` — 构造函数增加 `on_change` 参数，`_notify_change()` 方法
- `agents_hub/core/orchestration/group_chat.py` — `GroupChat.__init__()` 中注入 `broadcast_group_chat_refresh` 作为 `on_change`

**数据流**：
```
BaseAgent.run()
  → runtime.update_agent_context_window() / update_agent_status()
    → _persist()                        # 保存到磁盘
    → _notify_change()                  # 新增：通知外部
      → on_change(group_chat_id)        # 即 broadcast_group_chat_refresh
        → WebSocket → 前端 refresh → 重新拉取 /members
```

**GroupChatRuntime 改动**：
```python
class GroupChatRuntime:
    def __init__(self, ..., on_change: Callable[[str], Awaitable[None]] | None = None):
        self._on_change = on_change

    def _notify_change(self):
        if self._on_change:
            self._on_change(self.state.group_chat_id)

    def update_agent_context_window(self, agent_name, context_window):
        # ... 现有逻辑 ...
        self._persist()
        self._notify_change()

    def update_agent_status(self, agent_name, status):
        # ... 现有逻辑 ...
        self._persist()
        self._notify_change()
```

**为什么只在这两个方法触发**：`add_message` 和 `update_message_field` 的 broadcast 已经在 API/MCP 层处理，从 `_persist()` 统一触发会导致重复广播。

**注入方式**（`GroupChat.__init__()`）：
```python
from agents_hub.realtime import broadcast_group_chat_refresh

self.runtime = GroupChatRuntime(
    group_chat_id,
    project_path,
    on_change=broadcast_group_chat_refresh,
)
```

## 不做的事

- 不做前端轮询，WebSocket 是唯一的实时通知机制
- core 模块不直接 import realtime 模块，通过回调解耦
- 不引入 event bus，用简单的 callback 足够
