# 架构约束文件：飞书 Channel 集成

## 版本信息

- 创建时间：2026-06-26
- PRD 文件：.scratch/feishu-channel/PRD.md
- 状态：设计中

## 1. 架构概述

### 1.1 系统定位

飞书 Channel 是 agents-hub 的外部渠道适配模块，与微信 Channel 平级，位于 `agents_hub/channels/feishu/` 目录。

```
agents_hub/
├── channels/
│   ├── wechat/          # 微信渠道（已有）
│   └── feishu/          # 飞书渠道（新增）
```

### 1.2 核心设计决策

| 决策项 | 选择 | 原因 |
|--------|------|------|
| Bot 数量 | 一个 bot 代理整个群聊 | 降低复杂度，避免多 bot 管理 |
| 连接方式 | WebSocket 长连接 | 飞书原生支持，无需公网 IP |
| 消息格式 | `[agent_name] : 内容` | 清晰标识发言者 |
| 命令系统 | 复用微信命令 | 保持一致性，降低开发成本 |
| Channel 监听 | 回调订阅机制 | 飞书 Channel 是进程内组件，无法直接加入 WebSocket 房间 |

## 2. 模块职责边界

### 2.1 阶段 1：广播机制修改

**修改文件**：
- `agents_hub/core/context/group_chat_runtime.py`
- `agents_hub/realtime/dependencies.py`

**修改内容**：
1. 扩展 `on_change` 回调签名，支持传递消息内容
2. 扩展 `_notify_change()` 方法，添加可选的 `message` 参数
3. 扩展 `broadcast_group_chat_refresh()` 函数，添加可选的 `message` 参数
4. 添加回调订阅机制，支持飞书 Channel 注册回调

**接口变更**：
```python
# realtime/dependencies.py
# 新增：回调订阅列表
_channel_callbacks: list[Callable] = []

def register_channel_callback(callback: Callable):
    """注册 Channel 回调"""
    _channel_callbacks.append(callback)

async def broadcast_group_chat_refresh(
    group_chat_id: str,
    manager: WebSocketManager | None = None,
    message: dict | None = None,  # 新增参数
):
    """广播群聊刷新信号（可选携带消息内容）"""
    # 1. WebSocket 广播（前端）
    realtime_manager = manager or get_realtime_manager()
    signal = make_refresh_signal(group_chat_id)
    if message:
        signal["message"] = message
    await realtime_manager.broadcast(group_chat_id, signal.model_dump(mode="json"))
    
    # 2. 回调通知（飞书 Channel 等进程内组件）
    for callback in _channel_callbacks:
        try:
            await callback(group_chat_id, message)
        except Exception:
            logger.warning("Channel 回调失败", exc_info=True)
```

**调用链路**：
```
add_message(agent_result)
  → _notify_change(message=...)
    → on_change(group_chat_id, message=...)
      → broadcast_group_chat_refresh(group_chat_id, message=...)
        → WebSocket 广播（前端）
        → 回调通知（飞书 Channel）
```

### 2.2 阶段 2：飞书 Channel 模块

**新增目录**：`agents_hub/channels/feishu/`

**文件结构**：

| 文件 | 职责 | 依赖 |
|------|------|------|
| `__init__.py` | 模块导出 | - |
| `channel.py` | 主 channel 类，WebSocket 连接管理、消息接收/发送、回调注册 | client, message, commander, session |
| `config.py` | 配置模型（app_id, app_secret 等） | - |
| `client.py` | lark-oapi 封装，API 调用 | config |
| `message.py` | 消息解析，@Mention 检测，@agent_name 解析 | - |
| `commander.py` | 命令处理，复用微信的命令系统 | - |
| `session.py` | Session 映射与同步状态管理 | - |
| `exceptions.py` | 异常定义 | - |

**依赖关系**：
```
channel.py
  ├── client.py (API 调用)
  ├── message.py (消息解析)
  ├── commander.py (命令处理)
  └── session.py (Session 映射 + 同步状态)
```

**飞书 Channel 监听机制**：
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
        # 过滤：只处理有消息的广播
        if not message:
            return
        
        # 增量同步：只处理新消息
        feishu_chat_id = self._get_feishu_chat_id(group_chat_id)
        if not feishu_chat_id:
            return  # 未绑定，跳过
        
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

## 3. 数据流设计

### 3.1 消息接收链路（飞书 → agents-hub）

```
飞书用户发送消息
  → 飞书服务器推送 WebSocket 事件
    → FeishuChannel.on_message() 接收
      → FeishuMessage.parse_message() 解析
        → 检测 @bot 或 @agent_name
          → Commander.handle() 处理命令/转发
            → GroupChatService.send_message_and_wait()
              → GroupChat.send_message_to_agent()
                → Agent 处理
```

### 3.2 消息发送链路（agents-hub → 飞书）

```
Agent 完成任务
  → GroupChatRuntime.add_message()
    → _notify_change()
      → broadcast_group_chat_refresh(group_chat_id, message)
        → WebSocketManager.broadcast()
          → 飞书 Channel 监听广播
            → FeishuReplyChannel.send()
              → CardKit API 更新卡片
```

### 3.3 流式输出链路

```
Agent 执行中产生 delta
  → AgentBridge 流式事件
    → 检查 message.reply_channel
      → FeishuReplyChannel.send_delta()
        → 节流缓冲（0.5s）
          → CardKit API 更新卡片内容
```

## 4. 接口契约

### 4.1 FeishuChannel 接口

```python
class FeishuChannel:
    """飞书 Channel 主类"""
    
    name = "feishu"
    
    async def start(self) -> None:
        """启动 channel：初始化客户端 -> WebSocket 连接 -> 监听消息"""
        
    async def stop(self) -> None:
        """停止 channel：断开连接 -> 清理资源"""
        
    async def on_message(self, event: dict) -> None:
        """处理接收到的消息"""
        
    async def send_to_feishu(self, chat_id: str, content: str, 
                              agent_name: str, members: list[str]) -> None:
        """发送消息到飞书群"""
```

### 4.2 FeishuReplyChannel 接口

```python
class FeishuReplyChannel:
    """飞书回复通道，支持流式输出"""
    
    def __init__(self, client: FeishuClient, chat_id: str, message_id: str):
        self.client = client
        self.chat_id = chat_id
        self.message_id = message_id
        self._buffer = ""
        self._last_update = 0.0
    
    async def send_delta(self, delta: str) -> None:
        """发送流式增量（带节流）"""
        
    async def send(self, final_content: str) -> None:
        """发送最终内容"""
```

### 4.3 Session 映射与同步状态接口

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

class FeishuSessionManager:
    """飞书 Session 映射与同步状态管理"""
    
    def __init__(self, data_path: Path):
        self.mapping_file = data_path / "channels" / "feishu" / "session_mapping.json"
        self.sync_state_file = data_path / "channels" / "feishu" / "sync_state.json"
        self._mappings: dict[str, FeishuSessionMapping] = {}  # feishu_chat_id -> mapping
        self._sync_states: dict[str, FeishuSyncState] = {}    # feishu_chat_id -> sync_state
    
    def bind(self, feishu_chat_id: str, group_chat_id: str, group_chat_name: str) -> None:
        """绑定飞书群到 agents-hub 群聊"""
        
    def unbind(self, feishu_chat_id: str) -> None:
        """解绑飞书群"""
        
    def get_mapping(self, feishu_chat_id: str) -> FeishuSessionMapping | None:
        """获取绑定关系"""
        
    def get_sync_state(self, feishu_chat_id: str) -> FeishuSyncState:
        """获取同步状态（不存在则创建）"""
        
    def update_sync_state(self, feishu_chat_id: str, last_message_id: int) -> None:
        """更新同步状态"""
        
    def save(self) -> None:
        """持久化映射关系和同步状态"""
        
    def load(self) -> None:
        """加载映射关系和同步状态"""
```

## 5. 关键实现细节

### 5.1 lark-oapi SDK 线程安全与事件循环冲突

**问题**：lark-oapi SDK 的 WebSocket 客户端在 Windows 环境下与我们的异步架构不兼容。

**根本原因**：
1. lark-oapi SDK 使用**模块级全局 loop 变量**（`loop = asyncio.get_event_loop()`），在 import 时就固化了
2. `start()` 方法内部多次调用 `loop.run_until_complete()`，但这个 loop 是主线程的事件循环
3. 即使在独立线程中创建新事件循环，SDK 仍使用旧的全局 loop
4. Windows ProactorEventLoop 环境下，在已运行的事件循环中调用 `run_until_complete()` 会抛出 `RuntimeError`

**解决方案**（三重修复）：

```python
def _start_ws(self):
    """在后台线程中启动 WebSocket 连接（阻塞）。"""
    import asyncio

    # 1. 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # 2. 应用 nest_asyncio 允许嵌套事件循环（关键！）
    import nest_asyncio
    nest_asyncio.apply(loop)

    # 3. Hack: 替换 lark_oapi.ws.client 模块中的全局 loop 变量
    import lark_oapi.ws.client as ws_client_module
    ws_client_module.loop = loop

    # 4. 启动 WebSocket（阻塞调用）
    self._ws_client.start()
```

**依赖要求**：
- 必须添加 `nest-asyncio>=1.5.0` 到 `pyproject.toml`
- nest_asyncio 通过 monkey-patch asyncio 实现嵌套循环支持

**相关 Bug**：
- `docs/history-bugs/2026-06-27-feishu-websocket-event-loop-conflict.md` - 完整的根因分析和修复过程

**替代方案（未采用）**：
- 方案 A：放弃 WebSocket，改用 HTTP 轮询 → 性能差、延迟高
- 方案 B：fork lark-oapi SDK 修改源码 → 维护成本高
- 方案 C：独立进程运行飞书 channel → 架构复杂度过高


### 5.2 广播过滤与增量同步

**问题**：飞书 Channel 监听广播时，需要过滤纯状态刷新，并支持增量同步。

**解决方案**：
```python
async def _on_broadcast(self, group_chat_id: str, message: dict | None):
    """处理广播回调（通过 register_channel_callback 注册）"""
    # 过滤 1：只处理有消息的广播
    if not message:
        return  # 忽略纯状态刷新
    
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

### 5.2 消息去重

**问题**：飞书可能重复推送消息。

**解决方案**：使用 OrderedDict 缓存 message_id：
```python
from collections import OrderedDict

class MessageDeduplicator:
    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, bool] = OrderedDict()
        self._max_size = max_size
    
    def is_duplicate(self, message_id: str) -> bool:
        if message_id in self._cache:
            return True
        self._cache[message_id] = True
        self._cache.move_to_end(message_id)
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
        return False
```

### 5.3 CardKit 流式输出节流

**问题**：频繁更新卡片可能触发 API 限流。

**解决方案**：0.5 秒节流间隔：
```python
class FeishuReplyChannel:
    def __init__(self, ...):
        self._buffer = ""
        self._last_update = 0.0
        self._throttle_interval = 0.5  # 0.5 秒
    
    async def send_delta(self, delta: str) -> None:
        self._buffer += delta
        now = time.time()
        if now - self._last_update >= self._throttle_interval:
            await self._update_card()
            self._last_update = now
```

### 5.4 @agent_name 解析

**复用逻辑**：复用本地 `_resolve_send_to()` 逻辑。

```python
# message.py
def parse_agent_name(content: str, members: list[str]) -> tuple[str, str]:
    """
    解析消息中的 @agent_name
    
    Returns:
        (target_agent, clean_content)
    """
    # 匹配 @agent_name 格式
    match = re.match(r'^@(\w+)\s+(.+)', content, re.DOTALL)
    if match:
        agent_name = match.group(1)
        clean_content = match.group(2)
        if agent_name in members:
            return agent_name, clean_content
    
    # 默认发送给 manager
    return "manager", content
```

## 6. 依赖关系图

### 6.1 模块依赖

```
飞书 Channel (agents_hub/channels/feishu/)
  ↓
Core 层
  ├── GroupChatService (消息发送)
  ├── GroupChatManager (群聊管理)
  └── GroupChatRuntime (广播监听)
  ↓
Realtime 层
  └── WebSocketManager (广播机制)
```

### 6.2 外部依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| lark-oapi | >= 1.0.0 | 飞书官方 SDK |
| 飞书开放平台 | - | 创建应用、配置权限 |

## 7. 配置模型

```python
@dataclass
class FeishuConfig:
    app_id: str                  # 飞书开放平台应用 ID
    app_secret: str              # 飞书开放平台应用 Secret
    encrypt_key: str = ""        # 事件加密密钥（可选）
    verification_token: str = "" # 验证 token（可选）
    group_policy: str = "mention"  # "open" / "mention"
    domain: str = "feishu"       # "feishu" / "lark"
```

## 8. 测试策略

### 8.1 单元测试

| 模块 | 测试点 |
|------|--------|
| message.py | @agent_name 解析、mention 占位符替换 |
| session.py | 映射关系持久化、同步状态持久化、增量同步逻辑 |
| commander.py | 命令路由、参数解析 |

### 8.2 集成测试

| 场景 | 测试点 |
|------|--------|
| 消息接收 | 飞书消息 → agents-hub 群聊 |
| 消息发送 | agents-hub 群聊 → 飞书群 |
| 广播过滤 | 只处理有消息的广播，忽略状态刷新 |
| Session 映射 | bind/unbind/get |
| 增量同步 | 重启后从上次位置开始同步 |

### 8.3 端到端测试

| 场景 | 测试点 |
|------|--------|
| 完整流程 | 飞书发消息 → Agent 处理 → 回复到飞书 |
| 命令系统 | /help, /agents, /groups, /bind |
| 断线重连 | WebSocket 断开 → 自动重连 |
| 增量同步 | 重启后不重复发送历史消息 |

## 9. 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| lark-oapi SDK 线程安全 | 中 | 参考 nanobot 的 run_ws() 实现，使用独立线程 |
| 消息去重 | 中 | 使用 OrderedDict 缓存 message_id |
| 广播过滤 | 低 | 检查广播中是否包含 message 字段 |
| 增量同步 | 低 | 持久化 last_message_id，重启后从上次位置开始 |

## 10. 相关文档

### Spec 文档
- [core-context](../../docs/specs/2026-05-31-core-context.md) - GroupChatRuntime 和广播机制
- [realtime](../../docs/specs/2026-06-06-realtime.md) - WebSocketManager 和广播机制
- [websocket-backend](../../docs/specs/2026-06-03-websocket-backend.md) - WebSocket 端点

### Flow 文档
- [message-lifecycle](../../docs/flows/message-lifecycle.md) - 消息生命周期
- [group-chat-lifecycle](../../docs/flows/group-chat-lifecycle.md) - 群聊生命周期

### 参考实现
- 微信 Channel：`agents_hub/channels/wechat/`
- nanobot 飞书实现：`D:\desktop\软件开发\nanobot\nanobot\channels\feishu.py`
