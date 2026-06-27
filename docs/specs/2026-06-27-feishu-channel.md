---
version: 1.4
created_at: 2026-06-27
updated_at: 2026-06-27
last_updated: 添加 iter_states() 公共方法，修复 _on_broadcast 无条件 save
abstract: 飞书 Channel 模块规格，定义飞书消息接收/发送、命令系统、会话状态管理和消息广播同步
---

# 飞书 Channel

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.4 | 添加 iter_states() 公共方法，修复 _on_broadcast 无条件 save |
| 1.3 | 提取 FeishuSessionService 服务层，MCP 写操作委托给 service |
| 1.2 | 添加飞书管理 MCP 工具（6个）、get_state 只读方法、Feishu-Assistant 角色 |
| 1.1 | 命令系统重构：9个命令精简为3个，引入助手模式作为控制面板 |
| 1.0 | 创建 spec 初稿 |

## Overview

**业务问题**：让用户通过飞书与 agents-hub 系统交互，支持与 agent 单聊、群聊协作和助手对话。

**核心设计**：
- **一对一绑定**：每个飞书群（chat_id）同时只能绑定一个 Agent Hub 会话（单聊或群聊）
- **三种会话模式**：
  - `assistant`：与默认助手 agent 单聊
  - `single_chat`：与指定 agent 单聊
  - `group_chat`：绑定到一个 Agent Hub 群聊
- **绑定持久化**：`/back` 返回 idle 只切换显示模式，不清空绑定关系；绑定新会话时才覆盖之前的绑定
- **消息双向同步**：飞书消息转发到 Agent Hub 会话，Agent Hub 会话的响应回同步到飞书群

**核心职责**：
- 接收飞书 WebSocket 消息，解析并路由到绑定的 Agent Hub 会话
- 提供命令系统，支持绑定/解绑会话
- 管理每个飞书群的绑定状态（idle/assistant/single_chat/group_chat）
- 将 Agent Hub 会话的响应回同步到飞书群

## Scope

### 范围内

- 飞书 WebSocket 消息接收和解析
- 命令系统（/start, /back, /default）
- 会话状态管理（每个飞书群独立状态）
- 消息发送到飞书（格式化 + API 调用）
- 群聊消息增量同步到飞书
- 消息去重（OrderedDict LRU 缓存）

### 范围外

- **单聊模块**：`docs/specs/2026-06-08-single-chat.md` - 单聊会话的创建和管理
- **群聊 API**：`docs/specs/2026-06-03-group-chat-api.md` - 群聊生命周期管理
- **WebSocket 后端**：`docs/specs/2026-06-03-websocket-backend.md` - 前端 WebSocket 连接管理

## Technical Contract

### FeishuChannel（主类）

<key_function last_update="2026-06-27T16:00:18+08:00">
- agents_hub/channels/feishu/channel.py
  - channel.FeishuChannel.start:48
  - channel.FeishuChannel.stop:224
  - channel.FeishuChannel.on_message:234
  - channel.FeishuChannel.send_to_feishu:310
  - channel.FeishuChannel._on_broadcast:349
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `start()` | 启动 channel：初始化客户端 → 注册回调 | 必须在 event loop 中调用 |
| `stop()` | 停止 channel：断开连接 → 清理资源 | - |
| `on_message(event)` | 处理接收到的飞书消息 | event 必须包含 message 字段 |
| `send_to_feishu(chat_id, content, agent_name)` | 发送消息到飞书群 | content 为纯文本，内部转 JSON |

### FeishuCommander（命令系统）

<key_function last_update="2026-06-27T18:00:00+08:00">
- agents_hub/channels/feishu/commander.py
  - commander.FeishuCommander.handle:54
  - commander.FeishuCommander._forward_to_assistant:148
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `handle(user_id, content, chat_id)` | 处理命令或消息，返回响应文本 | content 以 `/` 开头为命令，否则为消息 |

**助手消息格式**：
- 转发给助手的消息自动添加 `[feishu_chat_id:oc_xxx]` 前缀
- 助手 Agent 从消息中提取 `feishu_chat_id`，传递给所有 MCP 工具
- 助手使用 `config.default_feishu_assistant_name` 角色（非 `default_assistant_name`）

**命令列表**：

| 命令 | 说明 | 可用状态 |
|------|------|----------|
| `/start` | 进入助手模式 | idle |
| `/back` | 返回 idle 状态（最高优先级） | 任意状态 |
| `/default <agent_name>` | 设置群聊默认对话对象 | group_chat |

**消息路由逻辑**：
1. `/back` 最高优先级，任何状态下返回 idle
2. `idle` 状态：`/start` 进入助手模式，其他返回欢迎文本
3. `assistant` 状态：消息转发给助手，检测状态变化（MCP 工具切换）
4. `group_chat` 状态：`/default` 拦截，其他转发到群聊
5. `single_chat` 状态：消息转发到单聊

### FeishuSessionService（会话管理服务）

<key_function last_update="2026-06-27T19:00:00+08:00">
- agents_hub/channels/feishu/service.py
  - service.FeishuSessionService.bind_to_group_chat
  - service.FeishuSessionService.bind_to_single_chat
  - service.FeishuSessionService.create_single_chat
</key_function>

**职责**：封装 MCP 工具中的跨模块编排逻辑（调用 group_chat_manager、single_chat_manager、feishu_session_manager），保持 feishu_session_manager 职责单一。

**对外接口**：

| 接口 | 说明 | 异常 |
|------|------|------|
| `bind_to_group_chat(feishu_chat_id, group_chat_id)` | 验证群聊存在 → 切换状态 → 保存 | `GroupChatNotFoundError` |
| `bind_to_single_chat(feishu_chat_id, session_id)` | 验证会话存在 → 切换状态 → 保存 | `ValueError` |
| `create_single_chat(feishu_chat_id, agent_name)` | 创建单聊 → 记录历史 → 切换状态 → 保存 | `Exception` |

**设计要点**：
- 抛出领域异常，不返回 error dict（调用方负责转换）
- 全局实例 `feishu_session_service` 通过模块导入使用
- MCP 工具捕获异常并转为 `make_error_response`

### FeishuSessionManager（会话状态管理）

<key_function last_update="2026-06-27T18:00:00+08:00">
- agents_hub/channels/feishu/session.py
  - session.FeishuSessionManager.get_or_create_state:119
  - session.FeishuSessionManager.iter_states:148
  - session.FeishuSessionManager.get_state:155
  - session.FeishuSessionManager.switch_to_idle:160
  - session.FeishuSessionManager.switch_to_group_chat:174
  - session.FeishuSessionManager.switch_to_single_chat:197
  - session.FeishuSessionManager.switch_to_assistant:215
  - session.FeishuSessionManager.update_sync_state:250
  - session.FeishuSessionManager.add_single_chat_history:263
  - session.FeishuSessionManager.save:310
  - session.FeishuSessionManager.load:318
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `get_or_create_state(feishu_chat_id)` | 获取或创建状态（首次消息自动创建） | 线程安全 |
| `get_state(feishu_chat_id)` | 只读获取状态，不存在返回 None | 线程安全 |
| `iter_states()` | 返回所有状态的快照列表（只读遍历） | 线程安全 |
| `switch_to_idle(feishu_chat_id)` | 切换到 idle 状态 | 保留 single_chat_id |
| `switch_to_group_chat(feishu_chat_id, group_chat_id, group_chat_name)` | 切换到群聊模式 | 清空 single_chat_id |
| `switch_to_single_chat(feishu_chat_id, agent_name, single_chat_id)` | 切换到单聊模式 | - |
| `switch_to_assistant(feishu_chat_id)` | 切换到助手模式 | 保留 single_chat_id |
| `update_sync_state(feishu_chat_id, last_message_id)` | 更新增量同步位置 | 仅群聊模式使用 |
| `add_single_chat_history(feishu_chat_id, session_id, agent_name, first_message)` | 添加单聊历史记录 | 最多50条，去重 |
| `save()` | 持久化状态到文件 | - |
| `load()` | 加载状态（支持自动迁移旧格式） | - |

### 数据模型

#### FeishuSessionState（会话状态）

```
# 基本信息
feishu_chat_id: str    # 飞书群 ID（唯一标识，oc_xxx）
session_type: str      # 会话类型：idle/assistant/single_chat/group_chat
session_id: str        # 关联 ID：群聊 ID / agent 名称 / "assistant"
session_name: str      # 显示名称（群聊名称或 agent 名称）

# 单聊关联
single_chat_id: str    # 单聊会话 ID（single_chat 和 assistant 模式使用）

# 增量同步
last_message_id: int   # 增量同步位置（仅群聊模式使用）
last_sync_at: str      # 最后同步时间（ISO 8601）

# 元数据
created_at: str        # 创建时间（ISO 8601）
default_agent: str     # 群聊默认对话 Agent（仅群聊模式使用）

# 单聊历史
single_chat_history: list[dict]  # 单聊历史记录（最多50条）
```

**关键字段说明**：
- `session_type`：决定消息路由目标，idle 模式显示欢迎文本
- `single_chat_id`：assistant 和 single_chat 模式复用，避免重复创建
- `last_message_id`：群聊模式增量同步的游标，避免重复推送
- `default_agent`：群聊模式下默认接收消息的 Agent
- `single_chat_history`：记录单聊会话历史，支持查看和恢复

#### FeishuConfig（配置）

```
app_id: str            # 飞书开放平台应用 ID
app_secret: str        # 飞书开放平台应用 Secret
encrypt_key: str       # 事件加密密钥（可选）
verification_token: str # 验证 token（可选）
group_policy: str      # 群聊响应策略："open" 响应所有 / "mention" 只响应 @bot
domain: str            # 飞书域名："feishu" 国内版 / "lark" 国际版
```

#### 全局配置

```
default_feishu_assistant_name: str  # 飞书助手角色名，默认 "Feishu-Assistant"
```

### 飞书管理 MCP 工具

飞书助手 Agent 使用以下 MCP 工具管理会话绑定，工具定义在 `agents_hub/mcp/server.py`。

| 工具 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `list_group_chats` | `feishu_chat_id` | 群聊列表 | 列出所有 Agent Hub 群聊 |
| `list_single_chat_history` | `feishu_chat_id`, `agent_name?` | 单聊历史列表 | 只读，不创建状态 |
| `bind_to_group_chat` | `feishu_chat_id`, `group_chat_id` | 绑定结果 | 切换到群聊模式 |
| `bind_to_single_chat` | `feishu_chat_id`, `session_id` | 绑定结果 | 切换到单聊模式 |
| `create_single_chat` | `feishu_chat_id`, `agent_name` | session_id | 创建新单聊并绑定 |
| `get_current_binding` | `feishu_chat_id` | 当前绑定信息 | 只读，不创建状态 |

**设计要点**：
- 所有工具以 `feishu_chat_id` 为标识（不使用 `agent_token`）
- 读操作（`list_*`、`get_*`）使用 `get_state()` 只读方法，不创建状态
- 写操作（`bind_*`、`create_*`）使用 `switch_to_*` 方法并调用 `save()`
- 飞书助手角色通过 `default_feishu_assistant_name` 配置，禁用非飞书工具

### 状态机规则

#### 会话状态转换

```
                      /start
         ┌──────────────────────────────┐
         │                              ▼
    ┌────┴────┐                   ┌────────────┐
    │  idle   │                   │ assistant  │
    │(欢迎文本)│                   │ (助手模式) │
    └────┬────┘                   └─────┬──────┘
         │                              │
         │         MCP 工具切换         │
         │    ┌─────────────────────────┤
         │    │                         │
         │    ▼                         ▼
         │  ┌────────────┐    ┌────────────┐
         │  │ group_chat │    │ single_chat│
         │  │  (群聊)    │    │  (单聊)    │
         │  └────────────┘    └────────────┘
         │         │                 │
         │         │    /back        │
         └─────────┴─────────────────┘
```

**状态转换规则**：
- `idle` → `assistant`：用户发送 `/start`
- `assistant` → `group_chat`/`single_chat`：助手调用 MCP 工具完成切换
- 任意状态 → `idle`：用户发送 `/back`（最高优先级）
- `idle` 状态下非命令消息：返回欢迎文本

**绑定关系说明**：
- 一个飞书群同一时间只能绑定一个 Agent Hub 会话（单聊或群聊）
- `/back` 返回 idle 时，之前的绑定关系保留（single_chat_id 不清空）
- 助手调用 MCP 工具切换会话时，覆盖之前的绑定关系

### 异常体系

```
ExternalServiceError
  └── FeishuError（飞书 Channel 基础异常）
        ├── FeishuAuthError（认证失败：app_id/app_secret 无效、token 过期）
        ├── FeishuAPIError（API 调用失败）
        └── FeishuConnectionError（WebSocket 连接异常）
```

## Design Rationale

**为什么每个飞书群独立状态？**
- 飞书群是用户的主要交互单元，每个群可能有不同的使用场景
- 独立状态允许同时存在多个群聊/单聊会话

**为什么是一对一绑定？**
- 简化消息路由逻辑：每个飞书群的消息只需要转发到一个目标
- 避免消息歧义：用户在飞书群发的消息只有一个明确的接收方
- 符合用户预期：一个飞书群通常对应一个工作场景

**为什么 `/back` 保留绑定关系？**
- 用户可能临时查看命令面板，然后继续之前的会话
- 保留绑定避免重复创建会话，减少资源消耗
- 用户通过 `/status` 可以查看当前绑定，通过绑定新会话来覆盖

**为什么 assistant 和 single_chat 复用 single_chat_id？**
- 助手模式本质是与默认 agent 的单聊
- 复用避免重复创建单聊会话，简化状态管理

**为什么使用 OrderedDict 做消息去重？**
- 飞书 WebSocket 可能重复投递消息
- OrderedDict 提供 O(1) 查找和自动 LRU 淘汰

**为什么群聊消息使用增量同步？**
- 避免重复推送到飞书群
- last_message_id 作为游标，只推送新消息

**相关 ADR**：
- 无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **单聊模块**：`docs/specs/2026-06-08-single-chat.md` - 单聊会话的创建和管理
- **群聊 API**：`docs/specs/2026-06-03-group-chat-api.md` - 群聊生命周期管理
- **实时通信**：`docs/specs/2026-06-06-realtime.md` - WebSocket 连接管理和广播机制
