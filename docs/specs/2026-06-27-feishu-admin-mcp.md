---
version: 1.0
created_at: 2026-06-27
updated_at: 2026-06-27
last_updated: 初始版本
abstract: 飞书管理 MCP 工具规格，定义飞书助手专用的会话管理工具和服务层设计
---

# 飞书管理 MCP

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：飞书助手 Agent 需要专用的 MCP 工具来管理飞书会话绑定，包括查询群聊列表、切换会话模式、创建单聊等操作。

**核心设计**：
- **飞书助手专用**：6 个 MCP 工具专门为飞书助手 Agent 设计，通过 `feishu_chat_id` 标识操作目标
- **服务层封装**：跨模块编排逻辑封装在 `FeishuSessionService` 中，保持 `feishu_session_manager` 职责单一
- **读写分离**：读操作（`list_*`、`get_*`）使用只读方法，不创建状态；写操作（`bind_*`、`create_*`）修改状态并持久化

**核心职责**：
- 提供群聊列表查询能力
- 提供单聊历史查询能力
- 提供会话绑定切换能力（群聊/单聊）
- 提供单聊会话创建能力
- 提供当前绑定状态查询能力

## Scope

### 范围内

- 飞书管理 MCP 工具定义（6 个）
- FeishuSessionService 服务层
- 飞书助手角色配置
- 工具禁用列表

### 范围外

- **飞书 Channel 核心**：`docs/specs/2026-06-27-feishu-channel.md` - 消息接收/发送、命令系统
- **单聊模块**：`docs/specs/2026-06-08-single-chat.md` - 单聊会话的创建和管理
- **群聊 API**：`docs/specs/2026-06-03-group-chat-api.md` - 群聊生命周期管理

## Technical Contract

### MCP 工具列表

工具定义在 `agents_hub/mcp/server.py`，通过 FastMCP 注册。

<key_function last_update="2026-06-28T09:38:27+08:00">
- agents_hub/mcp/server.py
  - server.list_group_chats:1567
  - server.list_single_chat_history:1598
  - server.bind_to_group_chat:1632
  - server.bind_to_single_chat:1668
  - server.create_single_chat:1702
  - server.get_current_binding:1738
</key_function>

#### list_group_chats

**功能**：列出所有可用的 Agent Hub 群聊

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feishu_chat_id` | `str` | 是 | 飞书群 ID（oc_xxx 格式） |

**返回值**：

```json
{
  "group_chats": [
    {
      "group_chat_id": "group_123",
      "name": "Research Team",
      "members": ["manager", "coder", "reviewer"]
    }
  ]
}
```

**行为**：
- 调用 `group_chat_manager.list_all_group_chats()` 获取所有群聊
- 为每个群聊加载成员列表
- 只读操作，不创建或修改状态

#### list_single_chat_history

**功能**：列出飞书群的单聊历史记录

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feishu_chat_id` | `str` | 是 | 飞书群 ID |
| `agent_name` | `str` | 否 | 按 agent 名称过滤 |

**返回值**：

```json
{
  "history": [
    {
      "session_id": "sc_123",
      "agent_name": "researcher",
      "first_message": "你好",
      "created_at": "2026-06-27T10:00:00"
    }
  ]
}
```

**行为**：
- 使用 `get_state()` 只读方法，不存在时返回空列表
- 支持按 `agent_name` 过滤
- 不创建或修改状态

#### bind_to_group_chat

**功能**：将飞书群绑定到 Agent Hub 群聊，切换到群聊模式

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feishu_chat_id` | `str` | 是 | 飞书群 ID |
| `group_chat_id` | `str` | 是 | Agent Hub 群聊 ID |

**返回值**：

成功：
```json
{
  "status": "bound",
  "group_chat_id": "group_123",
  "group_chat_name": "Research Team"
}
```

失败：
```json
{
  "error": {
    "code": "GROUP_CHAT_NOT_FOUND",
    "message": "群聊 group_invalid 不存在，请先使用 list_group_chats 查看可用群聊"
  }
}
```

**行为**：
- 调用 `FeishuSessionService.bind_to_group_chat()`
- 验证群聊存在 → 获取群聊名称 → 切换状态 → 保存
- 群聊不存在时抛出 `GroupChatNotFoundError`

#### bind_to_single_chat

**功能**：将飞书群绑定到已有单聊会话，切换到单聊模式

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feishu_chat_id` | `str` | 是 | 飞书群 ID |
| `session_id` | `str` | 是 | 单聊会话 ID |

**返回值**：

成功：
```json
{
  "status": "bound",
  "session_id": "sc_123",
  "agent_name": "researcher"
}
```

失败：
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "单聊会话 sc_invalid 不存在或操作失败: ..."
  }
}
```

**行为**：
- 调用 `FeishuSessionService.bind_to_single_chat()`
- 验证会话存在 → 获取 agent_name → 切换状态 → 保存
- 会话不存在时抛出异常

#### create_single_chat

**功能**：为飞书群创建新的单聊会话并绑定

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feishu_chat_id` | `str` | 是 | 飞书群 ID |
| `agent_name` | `str` | 是 | Agent 角色名称 |
| `cwd` | `str` | 否 | Agent 工作目录（不传则使用默认工作目录） |

**返回值**：

成功：
```json
{
  "single_chat_id": "sc_new",
  "agent_name": "researcher",
  "status": "created"
}
```

失败：
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "创建单聊失败: ..."
  }
}
```

**行为**：
- 调用 `FeishuSessionService.create_single_chat()`
- 创建单聊会话 → 记录历史 → 切换状态 → 保存
- 创建失败时抛出异常

#### get_current_binding

**功能**：查看飞书群当前的绑定状态

**参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `feishu_chat_id` | `str` | 是 | 飞书群 ID |

**返回值**：

```json
{
  "feishu_chat_id": "oc_xxx",
  "session_type": "group_chat",
  "session_id": "group_123",
  "session_name": "Research Team",
  "single_chat_id": "",
  "last_message_id": 100,
  "default_agent": "manager",
  "single_chat_history": [...]
}
```

**行为**：
- 使用 `get_state()` 只读方法
- 不存在时返回 idle 状态默认值
- 返回完整的状态信息（包括内部字段）

### FeishuSessionService（服务层）

<key_function last_update="2026-06-27T19:00:00+08:00">
- agents_hub/channels/feishu/service.py
  - service.FeishuSessionService.bind_to_group_chat:31
  - service.FeishuSessionService.bind_to_single_chat:65
  - service.FeishuSessionService.create_single_chat:97
</key_function>

**职责**：封装 MCP 工具中的跨模块编排逻辑

**设计要点**：
- 抛出领域异常，不返回 error dict（调用方负责转换）
- 全局实例 `feishu_session_service` 通过模块导入使用
- 保持 `feishu_session_manager` 职责单一（只管状态存储和切换）

**对外接口**：

| 接口 | 说明 | 异常 |
|------|------|------|
| `bind_to_group_chat(feishu_chat_id, group_chat_id)` | 验证群聊存在 → 切换状态 → 保存 | `GroupChatNotFoundError` |
| `bind_to_single_chat(feishu_chat_id, session_id)` | 验证会话存在 → 切换状态 → 保存 | `ValueError` |
| `create_single_chat(feishu_chat_id, agent_name)` | 创建单聊 → 记录历史 → 切换状态 → 保存 | `Exception` |

### 飞书助手角色配置

**角色名称**：`config.default_feishu_assistant_name`（默认 "Feishu-Assistant"）

**创建位置**：`agents_hub/bootstrap.py`

**Prompt 模板**：`agents_hub/roles/prompt_file.py` 中的 `Feishu_Assistant_Prompt`

**禁用工具列表**：`FEISHU_ASSISTANT_DISABLED_TOOLS`

```python
FEISHU_ASSISTANT_DISABLED_TOOLS = [
    "AskUserQuestion",
    "call_agent",
    "health_check",
    "check_agent_call",
    "assign_tasks_to_team",
    "archive_task_list",
    "create_loop",
    "start_loop",
    "stop_loop",
    "delete_loop",
    "get_loop_status",
    "list_loops",
    "list_loop_executions",
    "get_memory_context",
]
```

**设计要点**：
- 飞书助手只能使用飞书管理工具和 create_group_chat/create_agent
- 禁用所有编排类工具（call_agent、loop、memory 等）
- 禁用列表在 bootstrap 时动态设置，无论角色是否已存在

## Design Rationale

**为什么使用 feishu_chat_id 而非 agent_token？**
- 飞书助手直接从用户消息中提取 feishu_chat_id
- 飞书会话状态以 feishu_chat_id 为 key，直接使用避免额外映射
- 飞书助手不需要 agent_token 的权限隔离（它本身就是受限角色）

**为什么提取 FeishuSessionService？**
- MCP 工具中的跨模块编排逻辑（调用 group_chat_manager、single_chat_manager）不属于 feishu_session_manager 的职责
- 服务层封装保持 feishu_session_manager 职责单一（只管状态存储和切换）
- 便于未来扩展（如 API 端点复用服务层逻辑）

**为什么读操作使用 get_state() 而非 get_or_create_state()？**
- list_single_chat_history 和 get_current_binding 是只读查询
- get_or_create_state 有写副作用（首次访问时创建状态）
- 使用 get_state() 避免意外创建空状态条目

**为什么飞书助手需要禁用工具列表？**
- 飞书助手只需要会话管理能力，不需要编排团队协作
- 禁用列表防止助手误用 call_agent、loop 等工具
- 列表在 bootstrap 时动态设置，便于维护

**相关 ADR**：
- 无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **飞书 Channel 核心**：`docs/specs/2026-06-27-feishu-channel.md` - 消息接收/发送、命令系统
- **单聊模块**：`docs/specs/2026-06-08-single-chat.md` - 单聊会话的创建和管理
- **群聊 API**：`docs/specs/2026-06-03-group-chat-api.md` - 群聊生命周期管理
