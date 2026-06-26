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
| 流式输出 | CardKit 流式卡片 | 飞书原生支持，体验好 |
| 命令系统 | 复用微信命令 | 保持一致性，降低开发成本 |

## 2. 模块职责边界

### 2.1 阶段 1：广播机制修改

**修改文件**：`agents_hub/core/context/group_chat_runtime.py`

**修改内容**：
- 扩展 `broadcast_group_chat_refresh()` 函数签名，添加可选的 `message` 参数
- 在 `add_message()` 方法中调用扩展后的广播方法，附加消息内容
- 保持向后兼容：前端继续使用现有的刷新逻辑

**接口变更**：
```python
# realtime/dependencies.py
async def broadcast_group_chat_refresh(
    group_chat_id: str,
    manager: WebSocketManager | None = None,
    message: dict | None = None,  # 新增参数
):
    """广播群聊刷新信号（可选携带消息内容）"""
    ...
```

**调用链路**：
```
add_message(agent_result)
  → _notify_change()
    → on_change(group_chat_id)
      → broadcast_group_chat_refresh(group_chat_id, message=...)
```

### 2.2 阶段 2：飞书 Channel 模块

**新增目录**：`agents_hub/channels/feishu/`

**文件结构**：

| 文件 | 职责 | 依赖 |
|------|------|------|
| `__init__.py` | 模块导出 | - |
| `channel.py` | 主 channel 类，WebSocket 连接管理、消息接收/发送 | client, message, commander, session |
| `config.py` | 配置模型（app_id, app_secret 等） | - |
| `client.py` | lark-oapi 封装，API 调用 | config |
| `message.py` | 消息解析，@Mention 检测，@agent_name 解析 | - |
| `streaming.py` | CardKit 流式输出，缓冲区管理 | client |
| `commander.py` | 命令处理，复用微信的命令系统 | - |
| `session.py` | Session 映射，chat_id 到 group_chat_id 的持久化 | - |
| `exceptions.py` | 异常定义 | - |

**依赖关系**：
```
channel.py
  ├── client.py (API 调用)
  ├── message.py (消息解析)
  ├── commander.py (命令处理)
  └── session.py (Session 映射)
      └── streaming.py (流式输出)
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

### 4.3 Session 映射接口

```python
class FeishuSessionManager:
    """飞书 Session 映射管理"""
    
    def __init__(self, data_path: Path):
        self.mapping_file = data_path / "channels" / "feishu" / "session_mapping.json"
        self._mappings: dict[str, str] = {}  # feishu_chat_id -> group_chat_id
    
    def bind(self, feishu_chat_id: str, group_chat_id: str) -> None:
        """绑定飞书群到 agents-hub 群聊"""
        
    def unbind(self, feishu_chat_id: str) -> None:
        """解绑飞书群"""
        
    def get_group_chat_id(self, feishu_chat_id: str) -> str | None:
        """获取绑定的 group_chat_id"""
        
    def save(self) -> None:
        """持久化映射关系"""
        
    def load(self) -> None:
        """加载映射关系"""
```

## 5. 关键实现细节

### 5.1 lark-oapi SDK 线程安全

**问题**：lark-oapi SDK 的 WebSocket 在独立线程运行，需要桥接到 asyncio。

**解决方案**：参考 nanobot 的 `run_ws()` 实现：
```python
async def start(self) -> None:
    """启动飞书 WebSocket 连接"""
    loop = asyncio.get_event_loop()
    # 在独立线程中运行 lark-oapi WebSocket
    await loop.run_in_executor(None, self._run_ws_sync)

def _run_ws_sync(self) -> None:
    """同步方式运行 WebSocket（在独立线程）"""
    # lark-oapi 的 WebSocket 客户端
    ws_client = lark.ws.Client(
        app_id=self.config.app_id,
        app_secret=self.config.app_secret,
        event_handler=self._create_event_handler(),
    )
    ws_client.start()
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
| CardKit API | - | 流式卡片输出 |

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
    streaming: bool = True       # 启用 CardKit 流式输出
```

## 8. 测试策略

### 8.1 单元测试

| 模块 | 测试点 |
|------|--------|
| message.py | @agent_name 解析、mention 占位符替换 |
| session.py | 映射关系持久化、加载 |
| streaming.py | 节流逻辑、缓冲区管理 |
| commander.py | 命令路由、参数解析 |

### 8.2 集成测试

| 场景 | 测试点 |
|------|--------|
| 消息接收 | 飞书消息 → agents-hub 群聊 |
| 消息发送 | agents-hub 群聊 → 飞书群 |
| 流式输出 | CardKit 卡片更新 |
| Session 映射 | bind/unbind/get |

### 8.3 端到端测试

| 场景 | 测试点 |
|------|--------|
| 完整流程 | 飞书发消息 → Agent 处理 → 回复到飞书 |
| 命令系统 | /help, /agents, /groups, /bind |
| 断线重连 | WebSocket 断开 → 自动重连 |

## 9. 风险与缓解

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| lark-oapi SDK 线程安全 | 中 | 参考 nanobot 的 run_ws() 实现，使用独立线程 |
| CardKit API 限流 | 低 | 使用 0.5 秒节流间隔 |
| 消息去重 | 中 | 使用 OrderedDict 缓存 message_id |
| 异步回调机制 | 高 | 需要新增事件订阅机制（阶段 1 解决） |

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
