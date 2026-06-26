---
labels: [ready-for-agent]
---

# PRD：飞书 Channel 集成

## Problem Statement

当前 agents-hub 支持微信 channel 和本地前端两种交互方式，但存在以下问题：

1. **微信 channel 限制**：微信 ilinkai API 不支持群聊消息收发，只能通过命令模拟群聊体验，用户体验受限
2. **缺少飞书集成**：飞书作为主流 IM 平台，原生支持群聊、流式输出（CardKit）、WebSocket 长连接，适合与 agents-hub 集成
3. **消息同步需求**：本地前端和 IM 平台之间的消息需要实时同步，当前架构缺少统一的广播机制

## Solution

实现飞书 channel 集成，分为两个阶段：

### 阶段 1：广播机制修改（最小修改）

在现有 `broadcast_group_chat_refresh()` 方法中附加消息内容，保持向后兼容：
- 前端不需要修改，继续使用现有的刷新逻辑
- 飞书 channel 可以从广播中提取消息内容
- 为后续 IM 平台集成奠定基础

### 阶段 2：飞书 channel 实现

实现完整的飞书 channel，支持：
- **一个飞书 bot 代理整个 agents-hub 群聊**
- WebSocket 长连接（lark-oapi SDK）
- 消息格式：`**[agent name]** : 消息内容`，末尾附带当前群聊 agent 列表
- 接收消息解析 `@agent_name`，复用本地解析逻辑
- 流式输出：CardKit 流式卡片
- 命令系统：复用微信的命令
- Session 映射：飞书 chat_id 到 agents-hub group_chat_id

## User Stories

### 基础连接

1. 作为飞书用户，我希望通过 WebSocket 长连接与 agents-hub 通信，以便实时接收消息
2. 作为飞书用户，我希望 bot 能够自动重连，以便网络中断后自动恢复
3. 作为系统管理员，我希望通过配置文件管理飞书应用的 app_id 和 app_secret，以便安全地配置 bot

### 消息接收

4. 作为飞书用户，我希望在单聊中与 bot 对话，以便进行 1对1 交互
5. 作为飞书用户，我希望在群聊中 @bot 发送消息，以便触发 bot 响应
6. 作为飞书用户，我希望在群聊中 @agent_name 指定目标 agent，以便消息发送给特定 agent
7. 作为飞书用户，我希望 bot 能够检测 @_all，以便响应群聊中的所有消息
8. 作为飞书用户，我希望 bot 能够解析消息中的 mention 占位符，以便正确理解消息内容
9. 作为飞书用户，我希望 bot 能够去重重复消息，以便避免重复处理

### 消息发送

10. 作为飞书用户，我希望 bot 回复时显示 `[agent name] : 消息内容` 格式，以便知道是哪个 agent 的回复
11. 作为飞书用户，我希望 bot 回复末尾附带当前群聊 agent 列表，以便了解群聊中的 agent 成员
12. 作为飞书用户，我希望 bot 支持流式输出（CardKit 流式卡片），以便实时看到 agent 的回复过程
13. 作为飞书用户，我希望 bot 能够智能检测消息格式（短文本/富文本/卡片），以便获得最佳的显示效果
14. 作为飞书用户，我希望 bot 支持引用回复，以便明确回复某条特定消息
15. 作为飞书用户，我希望 bot 能够显示处理中/完成的表情状态，以便了解消息处理进度

### 群聊编排对接

16. 作为飞书用户，我希望通过 `/bind <group_chat_name>` 命令绑定飞书群到 agents-hub 群聊，以便建立映射关系
17. 作为飞书用户，我希望飞书群消息能够转发到 agents-hub 群聊，以便 agent 处理消息
18. 作为飞书用户，我希望 agent 回复能够推送到飞书群，以便看到处理结果
19. 作为飞书用户，我希望 Session 映射关系能够持久化，以便重启后继续之前的会话
20. 作为本地用户，我希望飞书消息能够同步到本地前端，以便看到飞书用户的发言
21. 作为飞书用户，我希望本地消息能够同步到飞书群，以便看到本地用户的发言

### 命令系统

22. 作为飞书用户，我希望通过 `/help` 命令查看帮助信息，以便了解可用命令
23. 作为飞书用户，我希望通过 `/agents` 命令列出可用 agent，以便选择目标 agent
24. 作为飞书用户，我希望通过 `/groups` 命令列出群聊，以便选择目标群聊
25. 作为飞书用户，我希望通过 `/agent <名称>` 命令进入单聊模式，以便与特定 agent 1对1 对话
26. 作为飞书用户，我希望通过 `/group <名称>` 命令进入群聊模式，以便参与群聊交互
27. 作为飞书用户，我希望通过 `/create-group` 命令创建群聊，以便组织多 agent 协作
28. 作为飞书用户，我希望通过 `/create-role` 命令创建角色，以便扩展 agent 能力

### 媒体处理（可选/分期）

29. 作为飞书用户，我希望 bot 能够接收图片消息，以便处理图片内容
30. 作为飞书用户，我希望 bot 能够接收文件消息，以便处理文件内容
31. 作为飞书用户，我希望 bot 能够上传图片，以便返回图片结果
32. 作为飞书用户，我希望 bot 能够上传文件，以便返回文件结果

## Implementation Decisions

### 阶段 1：广播机制修改

**模块**：`agents_hub/core/context/group_chat_runtime.py`

**修改内容**：
- 扩展 `broadcast_group_chat_refresh()` 方法，添加可选的 `message` 参数
- 在 `add_message()` 方法中调用扩展后的广播方法，附加消息内容
- 保持向后兼容：前端继续使用现有的刷新逻辑，不需要修改

**接口变更**：
```python
async def broadcast_group_chat_refresh(self, message: AgentMessage = None):
    """广播群聊刷新信号（可选携带消息内容）"""
    payload = {
        "type": "group_chat_refresh",
        "group_chat_id": self.group_chat_id,
    }
    if message:
        payload["message"] = {
            "content": message.content,
            "send_from": message.send_from,
            "send_to": message.send_to,
            "timestamp": message.timestamp,
        }
    await self._broadcast(payload)
```

### 阶段 2：飞书 channel 实现

**新增模块**：`agents_hub/channels/feishu/`

**文件结构**：
- `channel.py`：主 channel 类，WebSocket 连接管理、消息接收/发送
- `config.py`：配置模型（app_id, app_secret, encrypt_key 等）
- `client.py`：lark-oapi 封装，API 调用
- `message.py`：消息解析，@Mention 检测，@agent_name 解析
- `streaming.py`：CardKit 流式输出，缓冲区管理
- `commander.py`：命令处理，复用微信的命令系统
- `session.py`：Session 映射，chat_id 到 group_chat_id 的持久化
- `exceptions.py`：异常定义

**核心设计决策**：

1. **一个飞书 bot 代理整个群聊**：
   - 飞书群里只有 1 个 bot，作为群聊的代理入口
   - 不是每个 agent 对应一个飞书 bot（复杂度太高）
   - 发送消息格式：`**[agent_name]** : 消息内容`
   - 消息末尾附带当前群聊 agent 列表

2. **消息携带 channel 引用**：
   - 在 `AgentMessage` 中添加 `reply_channel` 字段
   - 定义 `ReplyChannel` 接口，支持 `send_delta()` 和 `send()` 方法
   - 飞书 channel 实现 `FeishuReplyChannel`
   - Agent 处理消息时，检查 `reply_channel`，有就流式输出到 channel

3. **Session 映射**：
   - 飞书 chat_id 到 agents-hub group_chat_id 的映射
   - 持久化到 JSON 文件
   - 通过 `/bind <group_chat_name>` 命令建立映射

4. **异步通知**：
   - 飞书 channel 连接到 agents-hub 的 WebSocket
   - 监听 `group_chat_refresh` 事件
   - 从广播中提取消息内容，推送到飞书群

**技术依赖**：
- `lark-oapi >= 1.0.0`：飞书官方 SDK
- WebSocket 长连接：无需公网 IP，自动重连
- CardKit API：流式输出支持

**配置模型**：
```python
@dataclass
class FeishuConfig:
    app_id: str  # 飞书开放平台应用 ID
    app_secret: str  # 飞书开放平台应用 Secret
    encrypt_key: str = ""  # 事件加密密钥（可选）
    verification_token: str = ""  # 验证 token（可选）
    group_policy: str = "mention"  # "open" 响应所有群消息 / "mention" 只响应 @bot
    domain: str = "feishu"  # "feishu" 国内版 / "lark" 国际版
    streaming: bool = True  # 启用 CardKit 流式输出
```

## Testing Decisions

### 测试边界

1. **广播机制**：测试 `broadcast_group_chat_refresh()` 方法是否正确附加消息内容
2. **消息接收**：测试飞书消息接收入口 `on_message()` 是否正确解析消息
3. **消息发送**：测试 `send_to_feishu()` 是否正确格式化并推送消息
4. **流式输出**：测试 `FeishuReplyChannel.send_delta()` 是否正确更新 CardKit 卡片
5. **Session 映射**：测试 `FeishuSessionManager` 是否正确持久化映射关系
6. **命令系统**：测试命令路由是否正确分发到对应的处理函数

### 测试方法

1. **单元测试**：测试各个模块的独立功能
2. **集成测试**：测试飞书 channel 与 GroupChatService 的集成
3. **端到端测试**：测试完整的用户场景（飞书发消息 → agent 处理 → 回复到飞书）

### 前车之鉴

- 参考微信 channel 的测试方式
- 参考 nanobot 飞书实现的测试方式

## Out of Scope

1. **多个飞书 bot 对应多个 agent**：复杂度太高，不做
2. **飞书端和本地端的消息历史同步**：飞书端的历史由飞书维护，本地端的历史由 agents-hub 维护，不需要同步
3. **媒体处理的完整实现**：图片/文件上传下载作为可选/分期功能
4. **飞书开放平台的应用创建和配置**：需要用户自行在飞书开放平台创建应用并配置权限

## Further Notes

### 技术风险

1. **lark-oapi SDK 线程安全**：WebSocket 在独立线程运行，需要正确桥接到 asyncio，参考 nanobot 的 `run_ws()` 实现
2. **CardKit API 限流**：流式更新可能触发 API 限流，使用 0.5 秒节流间隔
3. **消息去重**：飞书可能重复推送消息，使用 OrderedDict 缓存 message_id
4. **异步回调**：当前 GroupChatService 不支持异步回调，需要新增事件订阅机制

### 实现建议

1. **Phase 1：基础连接**：WebSocket 连接、消息接收、基础发送
2. **Phase 2：群聊对接**：Session 映射、消息路由、@Mention 解析
3. **Phase 3：流式输出**：CardKit 流式卡片、缓冲区管理、节流
4. **Phase 4：异步通知**：事件订阅机制、实时推送
5. **Phase 5：测试与优化**：集成测试、性能优化、错误处理

### 参考实现

- nanobot 飞书实现：`D:\desktop\软件开发\nanobot\nanobot\channels\feishu.py`
- 微信 channel 实现：`D:\desktop\软件开发\agents-hub\agents_hub\channels\wechat\`
- 飞书调研报告：`D:\desktop\软件开发\agents-hub\docs\temp\docs\feishu-channel-research.md`
