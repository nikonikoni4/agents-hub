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

- [ ] **连接方式**：飞书 Channel 在 agents-hub 进程内，通过回调订阅机制监听
- [ ] **回调注册**：启动时调用 `register_channel_callback()` 注册回调
- [ ] **广播过滤**：只处理有消息的广播，忽略纯状态刷新

**关键实现**：
```python
class FeishuChannel:
    async def start(self):
        """启动飞书 Channel"""
        # 1. 连接到飞书服务器
        self._connect_to_feishu()
        
        # 2. 注册回调到 broadcast_group_chat_refresh
        from agents_hub.realtime.dependencies import register_channel_callback
        register_channel_callback(self._on_broadcast)
        
        # 3. 加载 Session 映射和同步状态
        self._session_manager.load()
    
    async def _on_broadcast(self, group_chat_id: str, message: dict | None):
        """处理广播回调"""
        # 过滤 1：只处理有消息的广播
        if not message:
            return
        
        # 获取绑定的飞书群 ID
        feishu_chat_id = self._get_feishu_chat_id(group_chat_id)
        if not feishu_chat_id:
            return  # 未绑定，跳过
        
        # 过滤 2：增量同步，只处理新消息
        sync_state = self._session_manager.get_sync_state(feishu_chat_id)
        if message["id"] <= sync_state.last_message_id:
            return  # 已同步过，跳过
        
        # 推送到飞书群
        await self.send_to_feishu(
            chat_id=feishu_chat_id,
            content=message["content"],
            agent_name=message["send_from"],
        )
        
        # 更新同步状态
        self._session_manager.update_sync_state(feishu_chat_id, message["id"])
```

**审核发现的问题**：
1. ✅ **已解决**：`WebSocketManager` 不支持非 WebSocket 连接加入房间
   - 解决方案：使用回调订阅机制，飞书 Channel 注册回调到 `broadcast_group_chat_refresh`
2. ✅ **已解决**：`on_change` 回调签名不支持传递消息内容
   - 解决方案：扩展 `_notify_change()` 和 `on_change` 签名，添加可选 `message` 参数

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

### 6. Session 与同步状态

- [ ] **Session 映射**：飞书群 ↔ agents-hub 群聊的绑定关系（持久化）
- [ ] **同步状态**：记录每个飞书群最后同步到哪条消息（持久化）
- [ ] **增量同步**：重启后从上次位置开始同步，避免重复发送
- [ ] **飞书 chat_id 稳定性**：oc_xxx 创建后不变，绑定关系长期有效

**同步时机**：
- **启动时**：`channel.start()` 中调用 `_sync_missed_messages()`，遍历所有 `session_type == "group_chat"` 的 session，查询群聊历史中 `id > last_message_id` 的消息并补发
- **运行时**：通过广播机制实时推送（`_on_broadcast()`）
- **单聊暂不实现**：单聊数据不在 agents-hub 中存储，后续待存储方案确定后再实现

**数据模型**：
```python
@dataclass
class FeishuSessionMapping:
    """飞书群绑定关系（持久化）"""
    feishu_chat_id: str          # 飞书群 ID（oc_xxx，创建后不变）
    group_chat_id: str           # agents-hub 群聊 ID
    group_chat_name: str         # agents-hub 群聊名称（便于显示）
    bound_at: str                # 绑定时间

@dataclass
class FeishuSyncState:
    """同步状态（持久化）"""
    feishu_chat_id: str          # 飞书群 ID
    last_message_id: int         # 最后同步的消息 ID
    last_sync_at: str            # 最后同步时间
```

### 7. 流式输出

- [ ] **决策**：砍掉流式输出，先做基础功能
- [ ] **原因**：前端修改量较大，需要重构消息展示逻辑
- [ ] **后续**：作为优化项，后续再考虑

### 8. 风险与缓解

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

### 切片 5：Session 映射与同步状态管理（AFK，阻塞：切片 2）

**目标**：实现飞书群到 agents-hub 群聊的映射，支持增量同步

**实现内容**：
- `agents_hub/channels/feishu/session.py`
  - `FeishuSessionMapping`：绑定关系（持久化）
  - `FeishuSyncState`：同步状态（持久化）
  - 增量同步逻辑：重启后从上次位置开始同步
- `/bind <group_chat_name>` 命令
- 启动时加载映射关系和同步状态

**验收标准**：
- [ ] 映射关系能够持久化
- [ ] 同步状态能够持久化
- [ ] `/bind` 命令正常工作
- [ ] 启动时自动加载映射和同步状态
- [ ] 增量同步逻辑正确（重启后不重复发送）

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
