---
version: 1.1
created_at: 2026-06-27
updated_at: 2026-06-27
last_updated: 命令系统重构：9个命令精简为3个，引入助手模式
abstract: 飞书 Channel 模块规格，定义飞书消息接收/发送、命令系统、会话状态管理和消息广播同步
---

# 飞书 Channel

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
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

<key_function last_update="2026-06-27T10:00:00+08:00">
- agents_hub/channels/feishu/commander.py
  - commander.FeishuCommander.handle:54
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `handle(user_id, content, chat_id)` | 处理命令或消息，返回响应文本 | content 以 `/` 开头为命令，否则为消息 |

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

### FeishuSessionManager（会话状态管理）

<key_function last_update="2026-06-27T10:00:00+08:00">
- agents_hub/channels/feishu/session.py
  - session.FeishuSessionManager.get_or_create_state:114
  - session.FeishuSessionManager.switch_to_idle:143
  - session.FeishuSessionManager.switch_to_group_chat:157
  - session.FeishuSessionManager.switch_to_single_chat:180
  - session.FeishuSessionManager.switch_to_assistant:198
  - session.FeishuSessionManager.update_sync_state:233
  - session.FeishuSessionManager.add_single_chat_history:246
  - session.FeishuSessionManager.save:289
  - session.FeishuSessionManager.load:297
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `get_or_create_state(feishu_chat_id)` | 获取或创建状态（首次消息自动创建） | 线程安全 |
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
