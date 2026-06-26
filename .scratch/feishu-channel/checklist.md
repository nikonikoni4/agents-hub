# 飞书 Channel 集成 Checklist

## 架构设计关键点

### 1. 群聊修改（阶段 1）

- [ ] **修改位置**：`agents_hub/core/context/group_chat_runtime.py`
- [ ] **修改内容**：`broadcast_group_chat_refresh()` 函数添加可选 `message` 参数
- [ ] **向后兼容**：不传 message 时行为不变
- [ ] **调用方式**：在 `add_message()` 中调用扩展后的广播方法

**设计决策**：
- 选择合并方案（消息添加和状态刷新共用一个广播函数）
- 原因：当前场景下两者紧密相关，分开反而增加复杂度
- 后续如需拆分，可以再重构

### 2. 飞书 Channel 监听机制

- [ ] **连接方式**：飞书 Channel 在 agents-hub 进程内，直接调用 WebSocketManager
- [ ] **房间加入**：启动时加入对应 group_chat_id 的房间
- [ ] **广播过滤**：只处理有消息的广播，忽略纯状态刷新

**关键实现**：
```python
async def on_broadcast(self, group_chat_id: str, signal: dict):
    """处理广播信号"""
    # 过滤：只处理有消息的广播
    if "message" not in signal:
        return  # 忽略纯状态刷新
    
    # 提取消息内容
    message = signal["message"]
    
    # 推送到飞书群
    await self.send_to_feishu(
        chat_id=self._get_feishu_chat_id(group_chat_id),
        content=message["content"],
        agent_name=message["send_from"],
    )
```

### 3. 飞书 Channel 耦合点

- [ ] **WebSocket 监听**：主动加入房间，不需要改群聊代码
- [ ] **配置模块**：添加飞书配置项（app_id, app_secret）
- [ ] **GroupChatService**：复用 `send_message_and_wait()` API
- [ ] **GroupChatManager**：复用群聊查询 API

### 4. 消息格式

- [ ] **发送格式**：`**[agent_name]** : 消息内容`
- [ ] **成员列表**：消息末尾附带当前群聊 agent 列表
- [ ] **@解析**：复用本地 `_resolve_send_to()` 逻辑

### 5. 连接关系

```
WebSocket 1：本地前端 ↔ agents-hub
- 用于：前端接收刷新信号
- 端点：ws://localhost:8000/api/v1/ws/group_chat/{id}

WebSocket 2：飞书 Channel ↔ 飞书服务器
- 用于：接收飞书用户消息、发送回复到飞书群
- 通过 lark-oapi SDK 建立

进程内调用：飞书 Channel ↔ agents-hub
- 用于：监听广播、调用 API
- 不需要 WebSocket
```

### 6. 流式输出

- [ ] **决策**：砍掉流式输出，先做基础功能
- [ ] **原因**：前端修改量较大，需要重构消息展示逻辑
- [ ] **后续**：作为优化项，后续再考虑

### 7. 风险与缓解

- [ ] **lark-oapi SDK 线程安全**：参考 nanobot 的 run_ws() 实现
- [ ] **消息去重**：使用 OrderedDict 缓存 message_id
- [ ] **CardKit API 限流**：使用 0.5 秒节流间隔（流式输出砍掉后不需要）
- [ ] **异步回调机制**：通过广播机制解决（阶段 1）

## 切片设计

### 切片 1：广播机制扩展（AFK，无阻塞）

**目标**：扩展广播机制，支持携带消息内容

**修改内容**：
- 修改 `realtime/dependencies.py` 的 `broadcast_group_chat_refresh()` 函数
- 修改 `core/context/group_chat_runtime.py` 的 `add_message()` 方法
- 保持向后兼容

**验收标准**：
- [ ] `broadcast_group_chat_refresh()` 支持可选 `message` 参数
- [ ] `add_message()` 调用时传递消息内容
- [ ] 不传 message 时行为不变
- [ ] 单元测试通过

### 切片 2：飞书 Channel 基础框架（AFK，无阻塞）

**目标**：创建飞书 Channel 模块基础结构

**创建内容**：
- `agents_hub/channels/feishu/__init__.py`
- `agents_hub/channels/feishu/config.py`（FeishuConfig 配置模型）
- `agents_hub/channels/feishu/exceptions.py`（异常定义）
- `agents_hub/channels/feishu/client.py`（lark-oapi SDK 封装）

**验收标准**：
- [ ] 目录结构创建完成
- [ ] FeishuConfig 配置模型定义
- [ ] 异常类定义
- [ ] Client 基础封装（连接、断开）

### 切片 3：飞书消息接收与解析（AFK，阻塞：切片 2）

**目标**：实现飞书消息接收和解析

**实现内容**：
- `agents_hub/channels/feishu/message.py`（消息解析、@Mention 检测）
- `agents_hub/channels/feishu/channel.py` 的 `on_message()` 方法
- 消息去重逻辑（OrderedDict 缓存）

**验收标准**：
- [ ] 能够接收飞书消息
- [ ] 正确解析 @Mention
- [ ] 正确解析 @agent_name
- [ ] 消息去重有效

### 切片 4：飞书消息发送（AFK，阻塞：切片 2）

**目标**：实现飞书消息发送

**实现内容**：
- `agents_hub/channels/feishu/channel.py` 的 `send_to_feishu()` 方法
- 消息格式化：`**[agent_name]** : 消息内容` + 成员列表
- 广播监听：过滤只处理有消息的广播

**验收标准**：
- [ ] 能够发送消息到飞书群
- [ ] 消息格式正确
- [ ] 广播监听有效
- [ ] 过滤逻辑正确（忽略纯状态刷新）

### 切片 5：Session 映射管理（AFK，阻塞：切片 2）

**目标**：实现飞书群到 agents-hub 群聊的映射

**实现内容**：
- `agents_hub/channels/feishu/session.py`（映射关系持久化）
- `/bind <group_chat_name>` 命令
- 启动时加载映射关系

**验收标准**：
- [ ] 映射关系能够持久化
- [ ] `/bind` 命令正常工作
- [ ] 启动时自动加载映射

### 切片 6：命令系统集成（AFK，阻塞：切片 3、4、5）

**目标**：集成命令系统

**实现内容**：
- `agents_hub/channels/feishu/commander.py`（复用微信命令）
- 集成到 `channel.py`

**验收标准**：
- [ ] /help 命令正常工作
- [ ] /agents 命令正常工作
- [ ] /groups 命令正常工作
- [ ] /bind 命令正常工作
- [ ] /back 命令正常工作

### 切片 7：端到端集成测试（AFK，阻塞：切片 1-6）

**目标**：完整流程测试

**测试内容**：
- 飞书发消息 → Agent 处理 → 回复到飞书
- 命令系统测试
- 断线重连测试

**验收标准**：
- [ ] 完整流程正常工作
- [ ] 命令系统正常工作
- [ ] 断线重连正常工作

## 相关文档

- [PRD 文件](.scratch/feishu-channel/PRD.md)
- [架构约束文件](.scratch/feishu-channel/architecture.md)
- [core-context spec](docs/specs/2026-05-31-core-context.md)
- [realtime spec](docs/specs/2026-06-06-realtime.md)
- [websocket-backend spec](docs/specs/2026-06-03-websocket-backend.md)
