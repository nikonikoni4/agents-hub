---
labels: [ready-for-agent]
---

# PRD: 飞书 Channel 命令系统重构与助手模式

## Problem Statement

当前飞书 Channel 的命令系统过于复杂，存在以下问题：

1. **命令过多**：用户需要记忆 9 个命令（/help, /a, /agents, /ag, /groups, /g, /default, /status, /back）才能完成基本操作，认知负担高
2. **交互不自然**：命令式交互与 AI 时代的自然语言交互习惯不符
3. **单聊历史丢失**：每次 `/ag` 都会创建新的单聊会话，无法查看和继续之前与某个 Agent 的对话
4. **状态切换繁琐**：进入群聊/单聊后想要查询其他信息或切换会话时，缺少便捷的方式

从用户视角：
- 飞书用户希望通过自然对话而非记忆命令来完成操作
- 飞书用户希望能够查看单聊历史并继续之前的对话
- 飞书用户希望有一个"控制面板"来管理会话切换和资源创建

## Solution

通过"助手作为控制面板"的设计，简化飞书 Channel 的交互模式：

1. **命令精简**：从 9 个命令缩减到 3 个核心命令
   - `/start` - 进入助手模式
   - `/back` - 返回命令面板（任何状态下可用）
   - `/default <agent_name>` - 设置群聊默认对话对象（仅群聊模式）

2. **助手模式**：引入专门的助手 Agent，作为管理控制台
   - 用户通过自然语言与助手对话
   - 助手调用专用的飞书管理 MCP 工具完成操作
   - 完成操作后立即退出助手模式，进入工作状态

3. **飞书管理 MCP**：创建 `agents-hub-feishu-admin` MCP
   - 提供会话查询工具（列出群聊、单聊历史）
   - 提供会话切换工具（绑定到群聊/单聊）
   - 提供资源创建工具（创建群聊、Agent）
   - 所有工具以 `feishu_chat_id` 为标识

4. **核心流程保持不变**：
   - 消息接收、解析、去重机制
   - 群聊消息增量同步（last_message_id）
   - WebSocket 连接管理
   - 消息发送格式化
   - 状态持久化机制

## User Stories

### 基础命令与状态切换

1. 作为飞书用户，我希望在 idle 状态下发送任意消息时看到欢迎提示，以便知道如何开始使用系统
2. 作为飞书用户，我希望通过 `/start` 命令进入助手模式，以便开始管理操作
3. 作为飞书用户，我希望在任何状态下都可以通过 `/back` 命令返回 idle 状态，以便重新开始
4. 作为飞书用户，我希望状态切换时收到系统消息提示，以便知道当前所处的模式

### 助手模式 - 查询信息

5. 作为飞书用户，我希望进入助手模式后看到助手的能力介绍，以便了解助手可以做什么
6. 作为飞书用户，我希望通过自然语言询问"有哪些群聊"，以便查看可用的群聊列表
7. 作为飞书用户，我希望通过自然语言询问"有哪些 Agent"，以便查看可用的 Agent 列表
8. 作为飞书用户，我希望通过自然语言询问"我之前和某个 Agent 聊过什么"，以便查看单聊历史
9. 作为飞书用户，我希望查看单聊历史时看到第一句话的摘要和创建时间，以便快速识别会话

### 助手模式 - 会话切换

10. 作为飞书用户，我希望通过自然语言说"进入 XXX 群聊"来切换到群聊模式，以便参与群聊
11. 作为飞书用户，我希望通过自然语言说"和 XXX Agent 聊天"来切换到单聊模式，以便与 Agent 对话
12. 作为飞书用户，我希望通过自然语言说"继续之前的对话"来恢复历史单聊，以便继续之前的上下文
13. 作为飞书用户，我希望助手调用 MCP 工具完成切换后，立即退出助手模式并进入目标会话，以便直接开始工作
14. 作为飞书用户，我希望切换到群聊/单聊后收到系统消息确认，以便知道已成功进入目标会话

### 助手模式 - 资源创建

15. 作为飞书用户，我希望通过自然语言说"创建一个新群聊"，以便让助手帮我创建群聊
16. 作为飞书用户，我希望通过自然语言说"创建一个新 Agent"，以便让助手帮我创建 Agent
17. 作为飞书用户，我希望助手在创建资源时询问必要的参数，以便提供准确的配置信息

### 群聊模式

18. 作为飞书用户，我希望进入群聊后，发送的消息直接转发到群聊，以便 Agent 处理
19. 作为飞书用户，我希望群聊的响应能够实时推送到飞书，以便看到 Agent 的回复
20. 作为飞书用户，我希望通过 `/default <agent_name>` 命令指定群聊的默认对话 Agent，以便无需每次 @ 就能发送消息
21. 作为飞书用户，我希望群聊消息底部显示当前默认对话对象和成员列表，以便了解群聊状态
22. 作为飞书用户，我希望群聊的增量同步机制保持不变，以便重启后不会丢失消息

### 单聊模式

23. 作为飞书用户，我希望进入单聊后，发送的消息直接转发到单聊 Agent，以便与 Agent 对话
24. 作为飞书用户，我希望单聊的流式响应能够收集完整后发送到飞书，以便看到完整的回复
25. 作为飞书用户，我希望单聊历史能够持久化保存，以便下次可以继续对话
26. 作为飞书用户，我希望单聊会话在飞书状态中保存，以便切换到其他会话后还能回来

### 核心流程保持不变

27. 作为飞书用户，我希望消息接收、解析、去重机制保持不变，以便系统稳定运行
28. 作为飞书用户，我希望 mention 占位符替换机制保持不变，以便正确解析 @ 消息
29. 作为飞书用户，我希望命令优先级处理保持不变，以便命令始终优先于普通消息
30. 作为飞书用户，我希望消息发送格式化（agent 名称前缀 + 内容）保持不变，以便清晰识别回复来源
31. 作为飞书用户，我希望 WebSocket 连接管理机制保持不变，以便系统能够自动重连
32. 作为飞书用户，我希望后台线程处理和异步桥接机制保持不变，以便不阻塞主事件循环
33. 作为飞书用户，我希望状态持久化机制保持不变，以便重启后保留会话绑定关系
34. 作为飞书用户，我希望 FeishuSessionState 数据结构保持不变，以便兼容现有数据

## Implementation Decisions

### 架构设计

**核心原则**：保持核心流程不变，只重构命令系统部分

**4 个状态**：
- `idle`：空闲状态，显示欢迎信息和 `/start` 提示
- `assistant`：助手模式，用户通过自然语言与助手对话完成管理操作
- `group_chat`：群聊模式，消息直接转发到群聊，不经过助手
- `single_chat`：单聊模式，消息直接转发到单聊，不经过助手

**状态转换流程**：
```
idle ──/start──> assistant ──MCP工具切换──> group_chat/single_chat
  ↑                                              │
  └──────────────────/back─────────────────────┘
```

### 模块 1：agents-hub-feishu-admin MCP（新增）

**目的**：为飞书助手 Agent 提供专用的管理工具

**位置**：`agents_hub/mcp/feishu_admin/`

**文件结构**：
```
agents_hub/mcp/feishu_admin/
├── __init__.py
├── server.py          # FastMCP 服务器，注册所有工具
├── tools/
│   ├── __init__.py
│   ├── session.py     # 会话查询和切换工具
│   └── resource.py    # 资源创建工具
└── models.py          # 数据模型
```

**MCP 工具列表**：

| 工具名称 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `list_group_chats` | `feishu_chat_id` | 群聊列表 | 列出所有 Agent Hub 群聊 |
| `list_single_chat_history` | `feishu_chat_id`, `agent_name?` | 单聊历史列表 | 列出当前飞书群的单聊历史 |
| `bind_to_group_chat` | `feishu_chat_id`, `group_chat_id` | 绑定结果 | 切换到群聊模式 |
| `bind_to_single_chat` | `feishu_chat_id`, `session_id` | 绑定结果 | 切换到单聊模式 |
| `create_single_chat` | `feishu_chat_id`, `agent_name` | session_id | 创建新单聊会话 |
| `get_current_binding` | `feishu_chat_id` | 当前绑定信息 | 查看当前绑定状态 |
| `create_group_chat` | `feishu_chat_id`, ... | 群聊信息 | 创建新群聊（复用现有 MCP） |
| `create_agent` | `feishu_chat_id`, ... | Agent 信息 | 创建新 Agent（复用现有 MCP） |

**工具实现要点**：
1. 所有工具以 `feishu_chat_id` 为标识（不使用 agent_token）
2. 工具内部调用 `FeishuSessionManager` 修改状态
3. 工具内部调用 agents-hub 的 HTTP API 或 Service 层获取数据
4. 工具返回后，状态立即改变，助手对话结束

**单聊历史数据模型**：
```python
@dataclass
class SingleChatHistoryItem:
    session_id: str           # 单聊会话 ID
    agent_name: str          # Agent 名称
    first_message: str       # 第一句话（前 10 个字）
    created_at: str          # 创建时间
```

**数据存储**：
- 单聊历史保存在 `FeishuSessionState` 中
- 新增字段：`single_chat_history: List[Dict[str, str]]`
- 每次创建或切换单聊时更新历史列表
- 限制列表长度为 50 条，超过则自动清理最旧的

### 模块 2：Commander 命令系统（修改）

**位置**：`agents_hub/channels/feishu/commander.py`

**修改内容**：

1. **简化命令列表**：
   - 保留：`/start`（新增）、`/back`、`/default`
   - 移除：`/help`、`/a`、`/assistant`、`/agents`、`/ag`、`/groups`、`/g`、`/status`

2. **消息路由逻辑**（伪代码）：
   ```python
   async def handle(user_id, content, chat_id):
       # 最高优先级：/back 命令
       if content.strip() == "/back":
           session_manager.switch_to_idle(chat_id)
           return "已返回命令面板\n/start - 进入助手模式"
       
       state = session_manager.get_or_create_state(chat_id)
       
       if state.session_type == "idle":
           if content.strip() == "/start":
               return await _enter_assistant_mode(chat_id)
           return WELCOME_TEXT
       
       elif state.session_type == "assistant":
           response = await _forward_to_assistant(chat_id, content)
           
           # 检查状态是否改变（助手调用了 MCP 工具）
           new_state = session_manager.get_state(chat_id)
           if new_state.session_type != "assistant":
               return response + f"\n\n✅ 已进入{new_state.session_name}\n/back 返回"
           return response
       
       elif state.session_type == "group_chat":
           if content.startswith("/default "):
               return await _cmd_default(chat_id, content)
           await _forward_to_group_chat(state, content)
       
       elif state.session_type == "single_chat":
           return await _forward_to_single_chat(state, content)
   ```

3. **保留的核心函数**（完全不修改）：
   - `_forward_to_group_chat()` - 群聊转发逻辑
   - `_forward_to_single_chat()` - 单聊转发逻辑
   - `_forward_to_assistant()` - 助手转发逻辑
   - `_collect_stream_response()` - 流式响应收集
   - `_cmd_default()` - 设置群聊默认 Agent

### 模块 3：SessionManager 状态管理（修改）

**位置**：`agents_hub/channels/feishu/session.py`

**修改内容**：

1. **扩展 FeishuSessionState 数据结构**：
   ```python
   @dataclass
   class FeishuSessionState:
       # 现有字段（不变）
       feishu_chat_id: str
       session_type: str
       session_id: str
       session_name: str
       single_chat_id: str
       last_message_id: int
       last_sync_at: str
       created_at: str
       default_agent: str
       
       # 新增字段
       single_chat_history: List[Dict[str, str]] = field(default_factory=list)
   ```

2. **新增方法**：
   - `switch_to_idle(feishu_chat_id)` - 切换到 idle 状态
   - `add_single_chat_history(feishu_chat_id, session_id, agent_name, first_message)` - 添加单聊历史

3. **保持不变的方法**：
   - `get_or_create_state()`
   - `switch_to_group_chat()`
   - `switch_to_single_chat()`
   - `switch_to_assistant()`
   - `update_sync_state()`
   - `save()` / `load()`

4. **数据迁移**：
   - `_migrate_old_format()` 自动处理旧格式数据
   - 新增字段 `single_chat_history` 默认为空列表

### 模块 4：飞书助手 Agent 配置（新增）

**位置**：`roles/feishu_assistant/`

**配置内容**：
```yaml
name: feishu_assistant
platform: claude
type: system
mcp_servers:
  - agents-hub-feishu-admin
instructions: |
  你是飞书用户的助手，帮助用户管理会话切换和创建资源。
  
  你可以：
  1. 查看群聊和单聊历史
  2. 切换到指定的群聊或单聊
  3. 创建新的群聊或 Agent
  
  当用户表达切换意图时（"进入xxx"、"切换到xxx"、"继续xxx"），
  调用对应的 MCP 工具完成绑定。绑定成功后，用户的后续消息将直接
  转发到目标会话，不再经过你。用户可以说"返回"或发送 /back 回到命令面板。
```

### 保持不变的模块

**以下模块和流程完全不修改**：

1. **message.py**：
   - `parse_message()` - 消息解析
   - `MessageDeduplicator` - 消息去重（LRU 缓存）
   - `parse_mentions()` - mention 占位符替换
   - `parse_agent_name()` - agent 名称解析

2. **client.py**：
   - `FeishuClient` - 飞书 API 客户端
   - `connect()` - WebSocket 连接
   - `send_message()` - 消息发送
   - 后台线程管理和异步桥接

3. **channel.py** 的核心流程：
   - `_on_ws_message()` - WebSocket 事件处理
   - `on_message()` - 消息接收、解析、去重、优先级判断
   - `send_to_feishu()` - 消息格式化发送
   - `_sync_missed_messages()` - 重启补偿同步
   - `_on_broadcast()` - 群聊消息增量同步
   - `start()` / `stop()` - Channel 生命周期管理

4. **config.py** / **exceptions.py**：
   - 配置模型和异常定义保持不变

## Testing Decisions

### 测试范围

**新增功能测试**：
1. 飞书管理 MCP 工具的单元测试
2. Commander 命令系统的重构逻辑测试
3. SessionManager 的单聊历史管理测试
4. 助手模式的端到端测试

**保持不变功能的回归测试**：
1. 消息接收、解析、去重流程
2. 群聊消息增量同步机制
3. WebSocket 连接和自动重连
4. 消息发送格式化
5. 状态持久化和加载

### 测试边界

**良好的测试**：
- 测试外部行为，而非实现细节
- 测试状态转换的正确性
- 测试 MCP 工具的输入输出契约
- 测试数据持久化和迁移逻辑

**测试用例示例**：

**场景 1：进入群聊**
```
1. 用户发送任意消息 → 验证收到欢迎提示
2. 用户发送 /start → 验证进入助手模式
3. 用户说"有哪些群聊" → 验证助手返回群聊列表
4. 用户说"进入 Research Team" → 验证助手调用 bind_to_group_chat
5. 验证状态改变：assistant → group_chat
6. 验证系统消息："✅ 已进入 Research Team\n/back 返回"
7. 用户发送普通消息 → 验证消息转发到群聊
```

**场景 2：查看和继续单聊历史**
```
1. 用户在助手模式说"我之前和 researcher 聊过什么" → 验证返回历史列表
2. 用户说"继续第一个对话" → 验证助手调用 bind_to_single_chat
3. 验证状态改变：assistant → single_chat
4. 验证 single_chat_id 正确
5. 用户发送消息 → 验证消息转发到单聊
```

**回归测试场景**：
```
1. 群聊增量同步：重启后验证 last_message_id 机制正常工作
2. WebSocket 重连：模拟断网后验证自动重连
3. 消息去重：发送重复消息验证去重机制
4. Mention 解析：发送 @agent_name 消息验证解析正确
```

### Prior Art

参考现有测试：
- `tests/mcp/test_server.py` - MCP 服务器测试
- `tests/api/test_group_chat_service.py` - 群聊服务测试
- `tests/channels/feishu/` - 飞书 Channel 测试（如果存在）

## Out of Scope

以下内容明确不在此次重构范围内：

1. **消息流转核心机制**：消息接收、解析、去重、发送、增量同步等核心流程完全不修改
2. **WebSocket 连接管理**：连接、重连、后台线程、异步桥接机制完全不修改
3. **状态持久化机制**：保存/加载逻辑、文件格式、迁移逻辑完全不修改
4. **群聊编排逻辑**：GroupChat 的运行机制、Agent 协作逻辑不涉及
5. **单聊模块**：SingleChatManager 的创建和管理逻辑不涉及
6. **飞书 API 客户端**：FeishuClient 的实现不涉及
7. **消息格式化**：`send_to_feishu()` 的格式化逻辑不涉及
8. **广播机制**：`_on_broadcast()` 的监听和推送逻辑不涉及

## Implementation Checklist

### Phase 1：飞书管理 MCP 创建

- [ ] 创建 `agents_hub/mcp/feishu_admin/` 目录结构
- [ ] 实现 `server.py` - FastMCP 服务器注册
- [ ] 实现 `list_group_chats` 工具
- [ ] 实现 `list_single_chat_history` 工具
- [ ] 实现 `bind_to_group_chat` 工具
- [ ] 实现 `bind_to_single_chat` 工具
- [ ] 实现 `create_single_chat` 工具
- [ ] 实现 `get_current_binding` 工具
- [ ] 实现 `create_group_chat` 工具（复用现有逻辑）
- [ ] 实现 `create_agent` 工具（复用现有逻辑）
- [ ] 编写 MCP 工具的单元测试

### Phase 2：SessionManager 扩展

- [ ] 扩展 `FeishuSessionState` 数据结构，添加 `single_chat_history` 字段
- [ ] 实现 `switch_to_idle()` 方法
- [ ] 实现 `add_single_chat_history()` 方法
- [ ] 更新 `save()` / `load()` 以支持新字段
- [ ] 编写数据迁移逻辑（兼容旧格式）
- [ ] 编写 SessionManager 扩展的单元测试

### Phase 3：Commander 命令系统重构

- [ ] 移除旧命令处理函数：`_cmd_help()`, `_cmd_assistant()`, `_cmd_agents()`, `_cmd_agent()`, `_cmd_groups()`, `_cmd_group()`, `_cmd_status()`
- [ ] 实现 `/start` 命令处理
- [ ] 修改 `/back` 命令逻辑（切换到 idle）
- [ ] 保留 `/default` 命令逻辑（仅群聊模式）
- [ ] 重构 `handle()` 方法的消息路由逻辑
- [ ] 添加助手模式状态检测和系统消息追加
- [ ] 编写命令系统重构的单元测试

### Phase 4：飞书助手 Agent 配置

- [ ] 创建 `roles/feishu_assistant/` 目录
- [ ] 编写 `role.yaml` 配置文件
- [ ] 配置 MCP 服务器引用（agents-hub-feishu-admin）
- [ ] 编写助手的 instructions（能力说明和使用指南）

### Phase 5：集成测试

- [ ] 测试 idle → assistant → group_chat 完整流程
- [ ] 测试 idle → assistant → single_chat 完整流程
- [ ] 测试单聊历史的保存和读取
- [ ] 测试助手调用 MCP 工具后状态的改变
- [ ] 测试 /back 命令在不同状态下的行为
- [ ] 测试 /default 命令在群聊模式的行为

### Phase 6：回归测试

- [ ] 验证消息接收、解析、去重流程未被破坏
- [ ] 验证群聊消息增量同步机制正常工作
- [ ] 验证 WebSocket 连接和自动重连正常工作
- [ ] 验证消息发送格式化正常工作
- [ ] 验证状态持久化和加载正常工作
- [ ] 验证 mention 占位符替换正常工作
- [ ] 验证命令优先级处理正常工作

### Phase 7：文档更新

- [ ] 更新飞书 Channel Spec（`docs/specs/2026-06-27-feishu-channel.md`）
- [ ] 更新飞书消息生命周期 Flow（`docs/flows/2026-06-27-feishu-message-lifecycle.md`）
- [ ] 创建飞书管理 MCP Spec（`docs/specs/2026-06-27-feishu-admin-mcp.md`）
- [ ] 更新用户使用文档（如果有）

## Further Notes

### 技术风险与缓解

1. **助手调用 MCP 工具后的状态同步**：
   - **风险**：助手调用 `bind_to_group_chat` 后，状态已改变，但 Commander 需要检测到这个变化
   - **缓解**：在 `handle()` 方法中，助手响应后重新读取状态，判断是否改变

2. **单聊历史数据量**：
   - **风险**：随着时间推移，single_chat_history 列表可能变得很大
   - **缓解**：只保留最近 50 条历史，超过则自动清理最旧的

3. **MCP 工具权限隔离**：
   - **风险**：普通群聊 Agent 可能误用飞书管理 MCP
   - **缓解**：飞书管理 MCP 只配置给 feishu_assistant，普通 Agent 使用 agents-hub-collaboration MCP

### 实现顺序建议

按照 Phase 1-7 的顺序实施，每个 Phase 完成后进行测试，确保功能正常后再进入下一个 Phase。

### 用户迁移

现有飞书用户的状态文件会自动迁移（通过 `_migrate_old_format`），无需手动操作。新增的 `single_chat_history` 字段默认为空列表，不影响现有功能。

### 性能考虑

单聊历史列表保存在内存和磁盘中，每次状态保存时会写入文件。如果历史列表过大，可能影响保存性能。建议限制列表长度为 50 条。
