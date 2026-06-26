# 飞书 Channel 实现研究报告

> 基于 nanobot 仓库的飞书实现分析，为 agents-hub 飞书 channel 提供技术参考

## 目录

- [1. 概述](#1-概述)
- [2. SDK 与连接模型](#2-sdk-与连接模型)
- [3. 配置模型](#3-配置模型)
- [4. 消息接收流程](#4-消息接收流程)
- [5. 消息发送流程](#5-消息发送流程)
- [6. 群聊与单聊处理](#6-群聊与单聊处理)
- [7. 流式输出实现](#7-流式输出实现)
- [8. 媒体处理](#8-媒体处理)
- [9. 与 agents-hub 架构对比](#9-与-agents-hub-架构对比)
- [10. 实现建议](#10-实现建议)
- [附录: 关键代码路径](#附录-关键代码路径)

---

## 1. 概述

### 1.1 nanobot 飞书实现特点

- **单文件实现**：`feishu.py` 约 2357 行，包含完整的飞书 channel 功能
- **WebSocket 长连接**：使用 `lark-oapi` SDK 的 WebSocket 模式，无需公网 IP
- **支持群聊和单聊**：通过 `chat_type` 字段区分 (`"group"` / `"p2p"`)
- **流式输出**：使用 CardKit API 实现打字机效果
- **QR 码注册**：支持扫码创建 bot 应用

### 1.2 关键依赖

```
lark-oapi >= 1.0.0  # 飞书官方 SDK
httpx               # HTTP 客户端
pydantic            # 配置验证
```

---

## 2. SDK 与连接模型

### 2.1 SDK 选择

**文件**: `nanobot/channels/feishu.py:35`

```python
FEISHU_AVAILABLE = importlib.util.find_spec("lark_oapi") is not None
```

使用官方 `lark-oapi` SDK，支持：
- REST API 调用
- WebSocket 长连接（推荐）
- 事件订阅

### 2.2 连接模式

**WebSocket 长连接模式**（推荐）：

| 特性 | 说明 |
|------|------|
| 公网 IP | 不需要 |
| 防火墙 | 无需配置 |
| 重连机制 | SDK 内置自动重连 |
| 延迟 | 较低 |

**文件**: `nanobot/channels/feishu.py:734-770`

```python
# 创建 WebSocket 客户端
self._ws_client = lark.ws.Client(
    self.config.app_id,
    self.config.app_secret,
    domain=domain,
    event_handler=event_handler,
    log_level=lark.LogLevel.INFO,
)

# 在独立线程中运行，带自动重连
def run_ws():
    while self._running:
        try:
            self._ws_client.start()
        except Exception as e:
            self.logger.warning("WebSocket error: {}", e)
        if self._running:
            time.sleep(5)  # 重连间隔

self._ws_thread = threading.Thread(target=run_ws, daemon=True)
self._ws_thread.start()
```

### 2.3 事件注册

**文件**: `nanobot/channels/feishu.py:701-731`

```python
builder = lark.EventDispatcherHandler.builder(
    self.config.encrypt_key or "",
    self.config.verification_token or "",
).register_p2_im_message_receive_v1(self._on_message_sync)

# 可选事件处理器
builder = self._register_optional_event(
    builder, "register_p2_im_message_reaction_created_v1", self._on_reaction_created
)
builder = self._register_optional_event(
    builder, "register_p2_im_message_reaction_deleted_v1", self._on_reaction_deleted
)
# ... 更多可选事件
```

**必须注册的事件**：
- `p2_im_message_receive_v1` - 接收消息

**可选事件**：
- `p2_im_message_reaction_created_v1` - 表情回复添加
- `p2_im_message_reaction_deleted_v1` - 表情回复删除
- `p2_im_message_message_read_v1` - 消息已读
- `p2_im_chat_access_event_bot_p2p_chat_entered_v1` - 用户打开 bot 聊天
- `p2_im_chat_member_bot_added_v1` - bot 被添加到群组
- `p2_im_chat_member_bot_deleted_v1` - bot 被移出群组

### 2.4 Bot Open ID 获取

**文件**: `nanobot/channels/feishu.py:802-825`

```python
def _fetch_bot_open_id(self) -> str | None:
    """获取 bot 自身的 open_id，用于 @mention 检测"""
    request = (
        lark.BaseRequest.builder()
        .http_method(lark.HttpMethod.GET)
        .uri("/open-apis/bot/v3/info")
        .token_types({lark.AccessTokenType.APP})
        .build()
    )
    response = self._client.request(request)
    if response.success():
        data = json.loads(response.raw.content)
        bot = (data.get("data") or data).get("bot") or data.get("bot") or {}
        return bot.get("open_id")
    return None
```

---

## 3. 配置模型

### 3.1 配置字段

**文件**: `nanobot/channels/feishu.py:341-357`

```python
class FeishuConfig(Base):
    """飞书 channel 配置"""

    enabled: bool = False                    # 启用/禁用
    app_id: str = ""                         # 飞书 App ID
    app_secret: str = ""                     # 飞书 App Secret
    encrypt_key: str = ""                    # 事件加密密钥（可选）
    verification_token: str = ""             # 验证 token（可选）
    allow_from: list[str] = []               # 允许的发送者 open_id 列表
    react_emoji: str = "THUMBSUP"            # 处理中表情
    done_emoji: str | None = None            # 完成表情（如 "DONE", "OK"）
    tool_hint_prefix: str = "🔧"             # 工具提示前缀
    group_policy: Literal["open", "mention"] = "mention"  # 群聊响应策略
    reply_to_message: bool = False           # 是否引用回复用户消息
    streaming: bool = True                   # 启用 CardKit 流式输出
    domain: Literal["feishu", "lark"] = "feishu"  # 国内版/国际版
    topic_isolation: bool = True             # 群聊话题隔离
```

### 3.2 配置说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `app_id` | 飞书开放平台应用 ID | 必填 |
| `app_secret` | 飞书开放平台应用 Secret | 必填 |
| `group_policy` | `"open"` 响应所有群消息，`"mention"` 只响应 @bot | `"mention"` |
| `topic_isolation` | `True` 时每个话题/thread 独立 session | `True` |
| `domain` | `"feishu"` 国内版，`"lark"` 国际版 | `"feishu"` |

---

## 4. 消息接收流程

### 4.1 整体流程

```
WebSocket 事件
    ↓
_on_message_sync() [WebSocket 线程]
    ↓ (asyncio.run_coroutine_threadsafe)
_on_message() [主事件循环]
    ↓
消息解析 & 权限检查
    ↓
_handle_message() [BaseChannel]
    ↓
MessageBus.inbound 队列
```

### 4.2 消息入口

**文件**: `nanobot/channels/feishu.py:2111-2117`

```python
def _on_message_sync(self, data: Any) -> None:
    """同步处理器（WebSocket 线程调用），调度到主事件循环"""
    if self._loop and self._loop.is_running():
        asyncio.run_coroutine_threadsafe(self._on_message(data), self._loop)
```

### 4.3 消息处理核心逻辑

**文件**: `nanobot/channels/feishu.py:2119-2283`

```python
async def _on_message(self, data: P2ImMessageReceiveV1) -> None:
    event = data.event
    message = event.message
    sender = event.sender

    # 1. 跳过 bot 消息
    if sender.sender_type == "bot":
        return

    # 2. 获取基础信息
    sender_id = sender.sender_id.open_id
    chat_id = message.chat_id
    chat_type = message.chat_type  # "group" 或 "p2p"
    msg_type = message.message_type

    # 3. 群聊策略检查
    if chat_type == "group" and not self._is_group_message_for_bot(message):
        return

    # 4. 去重检查
    if message_id in self._processed_message_ids:
        return

    # 5. 权限检查
    if not self.is_allowed(sender_id):
        if chat_type == "p2p":
            # DM 发送配对码
            await self._handle_message(sender_id=sender_id, ...)
        return

    # 6. 添加处理中表情（非阻塞）
    asyncio.create_task(self._add_reaction(message_id, self.config.react_emoji))

    # 7. 解析消息内容
    content_parts = []
    media_paths = []

    if msg_type == "text":
        text = content_json.get("text", "")
        text = self._strip_leading_bot_mention(text, mentions)
        text = self._resolve_mentions(text, mentions)
        content_parts.append(text)

    elif msg_type == "post":
        # 富文本处理
        text, image_keys = _extract_post_content(content_json)
        ...

    elif msg_type in ("image", "audio", "file", "media"):
        # 媒体文件处理
        file_path, content_text = await self._download_and_save_media(...)
        ...

    # 8. 构建 session key
    if chat_type == "group":
        if self.config.topic_isolation:
            session_key = f"feishu:{chat_id}:{root_id or message_id}"
        else:
            session_key = f"feishu:{chat_id}"
    else:
        session_key = None

    # 9. 转发到消息总线
    await self._handle_message(
        sender_id=sender_id,
        chat_id=reply_to,
        content=content,
        media=media_paths,
        metadata={...},
        session_key=session_key,
        is_dm=chat_type == "p2p",
    )
```

### 4.4 消息类型处理

| 消息类型 | 处理方式 |
|----------|----------|
| `text` | 提取文本，解析 @mention，移除 bot mention |
| `post` | 富文本提取，下载内嵌图片 |
| `image` | 下载图片 |
| `audio` | 下载音频，转录（Whisper） |
| `file` | 下载文件 |
| `share_chat` | 提取分享的群组信息 |
| `share_user` | 提取分享的用户信息 |
| `interactive` | 提取卡片内容 |
| `system` | 系统消息 |
| `merge_forward` | 合并转发消息 |

---

## 5. 消息发送流程

### 5.1 发送入口

**文件**: `nanobot/channels/feishu.py:1955-2109`

```python
async def send(self, msg: OutboundMessage) -> None:
    # 确定接收者类型
    receive_id_type = "chat_id" if msg.chat_id.startswith("oc_") else "open_id"

    # 处理工具提示消息
    if msg.metadata.get("_tool_hint"):
        # 内联到流式卡片或单独发送
        ...

    # 处理媒体文件
    for file_path in msg.media:
        if ext in self._IMAGE_EXTS:
            key = await loop.run_in_executor(None, self._upload_image_sync, file_path)
            await loop.run_in_executor(None, _do_send, "image", ...)
        else:
            key = await loop.run_in_executor(None, self._upload_file_sync, file_path)
            await loop.run_in_executor(None, _do_send, media_type, ...)

    # 处理文本内容
    if msg.content and msg.content.strip():
        fmt = self._detect_msg_format(msg.content)

        if fmt == "text":
            # 短文本 -> 普通文本消息
            text_body = json.dumps({"text": msg.content.strip()})
            await loop.run_in_executor(None, _do_send, "text", text_body)

        elif fmt == "post":
            # 中等内容 -> 富文本
            post_body = self._markdown_to_post(msg.content)
            await loop.run_in_executor(None, _do_send, "post", post_body)

        else:
            # 复杂/长内容 -> 交互式卡片
            elements = self._build_card_elements(msg.content)
            for chunk in self._split_elements_by_table_limit(elements):
                card = {"config": {"wide_screen_mode": True}, "elements": chunk}
                await loop.run_in_executor(None, _do_send, "interactive", ...)
```

### 5.2 消息格式智能检测

**文件**: `nanobot/channels/feishu.py:1208-1250`

```python
def _detect_msg_format(self, content: str) -> str:
    """智能检测消息格式"""
    # 复杂 markdown -> 卡片
    if self._COMPLEX_MD_RE.search(content):
        return "card"

    # 简单 markdown -> 卡片
    if self._SIMPLE_MD_RE.search(content):
        return "card"

    # 链接 -> 富文本
    if self._MD_LINK_RE.search(content):
        return "post"

    # 短文本 -> 普通文本
    if len(content) <= 200:
        return "text"

    # 中等长度 -> 富文本
    if len(content) <= 2000:
        return "post"

    # 长文本 -> 卡片
    return "card"
```

### 5.3 发送 API 调用

**文件**: `nanobot/channels/feishu.py:1608-1642`

```python
def _send_message_sync(
    self, receive_id_type: str, receive_id: str, msg_type: str, content: str
) -> str | None:
    """发送单条消息"""
    request = (
        CreateMessageRequest.builder()
        .receive_id_type(receive_id_type)
        .request_body(
            CreateMessageRequestBody.builder()
            .receive_id(receive_id)
            .msg_type(msg_type)
            .content(content)
            .build()
        )
        .build()
    )
    response = self._client.im.v1.message.create(request)
    if not response.success():
        self.logger.error("Failed to send {} message: code={}, msg={}", ...)
        return None
    return response.data.message_id
```

### 5.4 回复消息

**文件**: `nanobot/channels/feishu.py:1558-1591`

```python
def _reply_message_sync(
    self, parent_message_id: str, msg_type: str, content: str,
    *, reply_in_thread: bool = False
) -> bool:
    """回复已有消息"""
    body_builder = ReplyMessageRequestBody.builder().msg_type(msg_type).content(content)
    if reply_in_thread:
        body_builder = body_builder.reply_in_thread(True)

    request = (
        ReplyMessageRequest.builder()
        .message_id(parent_message_id)
        .request_body(body_builder.build())
        .build()
    )
    response = self._client.im.v1.message.reply(request)
    return response.success()
```

---

## 6. 群聊与单聊处理

### 6.1 聊天类型检测

**文件**: `nanobot/channels/feishu.py:2137`

```python
chat_type = message.chat_type  # "group" 或 "p2p"
```

### 6.2 群聊策略

**文件**: `nanobot/channels/feishu.py:915-919`

```python
def _is_group_message_for_bot(self, message: Any) -> bool:
    """群聊消息是否应该响应"""
    if self.config.group_policy == "open":
        return True  # 响应所有群消息
    return self._is_bot_mentioned(message)  # 只响应 @bot
```

### 6.3 @Mention 检测

**文件**: `nanobot/channels/feishu.py:904-913`

```python
def _is_bot_mentioned(self, message: Any) -> bool:
    """检查是否 @了 bot"""
    raw_content = message.content or ""

    # @_all 也算 @bot
    if "@_all" in raw_content:
        return True

    # 检查 mentions 列表
    for mention in getattr(message, "mentions", None) or []:
        if self._is_bot_mention_event(mention):
            return True
    return False
```

### 6.4 @Mention 解析

**文件**: `nanobot/channels/feishu.py:828-859`

```python
@staticmethod
def _resolve_mentions(text: str, mentions: list[MentionEvent] | None) -> str:
    """将 @_user_n 占位符替换为实际用户信息"""
    for mention in mentions:
        key = mention.key  # 如 "@_user_1"
        open_id = mention.id.open_id
        user_id = mention.id.user_id
        name = mention.name or key

        # 替换为 @姓名 (open_id, user_id: xxx)
        pattern = rf"{re.escape(key)}(?![A-Za-z0-9_])"
        text = re.sub(pattern, f"@{name} ({open_id}, user_id: {user_id})", text)

    return text
```

### 6.5 移除 Bot Mention

**文件**: `nanobot/channels/feishu.py:884-900`

```python
def _strip_leading_bot_mention(self, text: str, mentions: list[MentionEvent] | None) -> str:
    """移除开头的 bot @mention，让 agent 收到干净的输入"""
    if not mentions:
        return text

    for mention in mentions:
        if self._is_bot_mention_event(mention):
            key = mention.key
            if key and text.startswith(key):
                stripped = text[len(key):].strip()
                return stripped or text

    return text
```

### 6.6 Session 隔离

**文件**: `nanobot/channels/feishu.py:2258-2264`

```python
# Session key 构建
if chat_type == "group":
    if self.config.topic_isolation:
        # 每个话题/thread 独立 session
        session_key = f"feishu:{chat_id}:{root_id or message_id}"
    else:
        # 整个群共享 session
        session_key = f"feishu:{chat_id}"
else:
    # 单聊：使用默认 session key
    session_key = None
```

### 6.7 回复线程处理

**文件**: `nanobot/channels/feishu.py:1593-1606`

```python
def _should_use_reply_in_thread(self, metadata: dict[str, Any]) -> bool:
    """群聊回复是否创建话题/thread"""
    return metadata.get("chat_type", "group") == "group" and self.config.reply_to_message

def _thread_reply_target(self, metadata: dict[str, Any]) -> str | None:
    """返回应该接收回复的 message_id"""
    if metadata.get("chat_type", "group") != "group":
        return None
    message_id = metadata.get("message_id")
    if not message_id:
        return None
    if metadata.get("thread_id") or self.config.reply_to_message:
        return message_id
    return None
```

---

## 7. 流式输出实现

### 7.1 CardKit 流式卡片

**文件**: `nanobot/channels/feishu.py:1644-1707`

```python
def _create_streaming_card_sync(
    self, receive_id_type: str, chat_id: str,
    reply_message_id: str | None = None, *, reply_in_thread: bool = False
) -> str | None:
    """创建 CardKit 流式卡片"""
    card_json = {
        "schema": "2.0",
        "config": {
            "wide_screen_mode": True,
            "update_multi": True,
            "streaming_mode": True  # 启用流式模式
        },
        "body": {
            "elements": [{
                "tag": "markdown",
                "content": "",
                "element_id": _STREAM_ELEMENT_ID
            }]
        },
    }

    request = (
        CreateCardRequest.builder()
        .request_body(
            CreateCardRequestBody.builder()
            .type("card_json")
            .data(json.dumps(card_json))
            .build()
        )
        .build()
    )
    response = self._client.cardkit.v1.card.create(request)
    return response.data.card_id
```

### 7.2 流式更新

**文件**: `nanobot/channels/feishu.py:1709-1741`

```python
def _stream_update_text_sync(self, card_id: str, content: str, sequence: int) -> bool:
    """更新流式卡片内容（打字机效果）"""
    request = (
        ContentCardElementRequest.builder()
        .card_id(card_id)
        .element_id(_STREAM_ELEMENT_ID)
        .request_body(
            ContentCardElementRequestBody.builder()
            .content(content)
            .sequence(sequence)  # 递增序列号
            .build()
        )
        .build()
    )
    response = self._client.cardkit.v1.card_element.content(request)
    return response.success()
```

### 7.3 流式缓冲区

**文件**: `nanobot/channels/feishu.py:1895-1953`

```python
async def send_delta(self, chat_id: str, delta: str, metadata: dict[str, Any] | None = None) -> None:
    """发送流式文本块"""
    stream_key = self._stream_key(chat_id, metadata)
    loop = asyncio.get_running_loop()
    rid_type = "chat_id" if chat_id.startswith("oc_") else "open_id"
    meta = metadata or {}

    # 获取或创建缓冲区
    buf = self._stream_bufs.get(stream_key)
    if buf is None:
        buf = _FeishuStreamBuf()
        self._stream_bufs[stream_key] = buf
    buf.text += delta

    now = time.monotonic()
    if buf.card_id is None:
        # 首次 delta：创建流式卡片
        card_id = await loop.run_in_executor(
            None, lambda: self._create_streaming_card_sync(rid_type, chat_id, ...)
        )
        if card_id:
            ok, sequence = await loop.run_in_executor(
                None, self._stream_update_text_with_reopen_sync, card_id, buf.text, 1
            )
            if ok:
                buf.card_id = card_id
                buf.sequence = sequence
                buf.last_edit = now

    elif (now - buf.last_edit) >= self._STREAM_EDIT_INTERVAL:
        # 节流更新（0.5 秒间隔）
        ok, buf.sequence = await loop.run_in_executor(
            None, self._stream_update_text_with_reopen_sync,
            buf.card_id, buf.text, buf.sequence + 1,
        )
        if ok:
            buf.last_edit = now
```

### 7.4 流式结束

**文件**: `nanobot/channels/feishu.py:1743-1760`

```python
def _close_streaming_mode_sync(self, card_id: str, sequence: int) -> bool:
    """关闭流式模式"""
    settings_payload = json.dumps({"config": {"streaming_mode": False}})
    request = (
        SettingsCardRequest.builder()
        .card_id(card_id)
        .request_body(
            SettingsCardRequestBody.builder()
            .settings(settings_payload)
            .sequence(sequence)
            .build()
        )
        .build()
    )
    response = self._client.cardkit.v1.card.settings(request)
    return response.success()
```

---

## 8. 媒体处理

### 8.1 图片上传

**文件**: `nanobot/channels/feishu.py` (相关方法)

```python
def _upload_image_sync(self, file_path: str) -> str | None:
    """上传图片，返回 image_key"""
    request = (
        CreateImageRequest.builder()
        .request_body(
            CreateImageRequestBody.builder()
            .image_type("message")
            .image(open(file_path, "rb"))
            .build()
        )
        .build()
    )
    response = self._client.im.v1.image.create(request)
    return response.data.image_key if response.success() else None
```

### 8.2 文件上传

```python
def _upload_file_sync(self, file_path: str) -> str | None:
    """上传文件，返回 file_key"""
    request = (
        CreateFileRequest.builder()
        .request_body(
            CreateFileRequestBody.builder()
            .file_type(self._get_file_type(file_path))
            .file_name(os.path.basename(file_path))
            .file(open(file_path, "rb"))
            .build()
        )
        .build()
    )
    response = self._client.im.v1.file.create(request)
    return response.data.file_key if response.success() else None
```

### 8.3 媒体下载

```python
async def _download_and_save_media(
    self, msg_type: str, content_json: dict, message_id: str
) -> tuple[str | None, str]:
    """下载并保存媒体文件"""
    if msg_type == "image":
        image_key = content_json.get("image_key")
        request = GetMessageResourceRequest.builder()...
    elif msg_type == "file":
        file_key = content_json.get("file_key")
        request = GetMessageResourceRequest.builder()...

    response = self._client.im.v1.message_resource.get(request)
    if response.success():
        # 保存到本地
        file_path = get_media_dir() / f"{message_id}_{safe_filename(...)}"
        with open(file_path, "wb") as f:
            f.write(response.file.read())
        return str(file_path), f"[{msg_type}]"

    return None, f"[{msg_type}: download failed]"
```

---

## 9. 与 agents-hub 架构对比

### 9.1 nanobot vs agents-hub Channel 架构

| 特性 | nanobot | agents-hub (wechat) |
|------|---------|---------------------|
| **基类** | `BaseChannel` (ABC) | 无基类，独立实现 |
| **消息总线** | `MessageBus` 异步队列 | 无，直接处理 |
| **配置模型** | Pydantic `Base` | dataclass |
| **连接模式** | WebSocket 长连接 | HTTP 长轮询 |
| **流式输出** | CardKit 支持 | 不支持 |
| **群聊支持** | 完整支持 | 不支持 |

### 9.2 agents-hub 微信 Channel 结构

**文件**: `agents_hub/channels/wechat/channel.py`

```python
class WechatChannel:
    name = "wechat"

    def __init__(self, config: WechatConfig, data_path: Path):
        self.config = config
        self.client: WechatClient | None = None
        self.auth: WechatAuth | None = None
        self.commander = Commander()

    async def start(self) -> None:
        """启动 channel：初始化客户端 -> 登录 -> 启动轮询"""
        ...

    async def stop(self) -> None:
        """停止 channel"""
        ...

    async def _poll_loop(self) -> None:
        """长轮询消息循环"""
        ...

    async def _handle_message(self, raw_msg: dict) -> None:
        """处理单条消息"""
        ...
```

### 9.3 关键差异

1. **消息流转**：
   - nanobot: Channel → MessageBus → Agent
   - agents-hub: Channel → Commander → 直接回复

2. **配置管理**：
   - nanobot: 统一的 Pydantic 配置模型
   - agents-hub: 独立的 dataclass

3. **异步处理**：
   - nanobot: 完整的 asyncio 支持
   - agents-hub: 基础的 asyncio 支持

---

## 10. 实现建议

### 10.1 目录结构

```
agents_hub/channels/feishu/
├── __init__.py
├── channel.py      # 主 channel 类
├── config.py       # 配置模型
├── client.py       # lark-oapi 封装
├── message.py      # 消息解析
├── streaming.py    # 流式输出
└── exceptions.py   # 异常定义
```

### 10.2 核心实现步骤

1. **配置模型** (`config.py`)
   - 使用 dataclass，与现有风格一致
   - 包含 app_id, app_secret, group_policy 等

2. **客户端封装** (`client.py`)
   - 封装 lark-oapi SDK
   - 提供 WebSocket 连接管理
   - 处理重连逻辑

3. **消息处理** (`message.py`)
   - 解析各种消息类型
   - @mention 检测和解析
   - 群聊/单聊区分

4. **Channel 主类** (`channel.py`)
   - 实现 start/stop 生命周期
   - 集成消息处理
   - 支持群聊和单聊

5. **流式输出** (`streaming.py`)
   - CardKit 流式卡片
   - 缓冲区管理
   - 节流更新

### 10.3 与现有架构集成

参考微信 channel 的实现模式：

```python
class FeishuChannel:
    name = "feishu"

    def __init__(self, config: FeishuConfig, data_path: Path):
        self.config = config
        self.client: FeishuClient | None = None
        self._running = False

    async def start(self) -> None:
        """启动飞书 channel"""
        self.client = FeishuClient(self.config)
        await self.client.connect()
        self._running = True
        # 启动消息监听...

    async def stop(self) -> None:
        """停止飞书 channel"""
        self._running = False
        if self.client:
            await self.client.disconnect()
```

### 10.4 关键注意事项

1. **线程安全**：
   - lark-oapi SDK 在独立线程运行 WebSocket
   - 需要 `asyncio.run_coroutine_threadsafe()` 桥接到主事件循环

2. **去重机制**：
   - 使用 `OrderedDict` 缓存已处理的 message_id
   - 限制缓存大小（如 1000 条）

3. **错误处理**：
   - WebSocket 断连自动重连
   - API 调用失败重试
   - 异常日志记录

4. **资源管理**：
   - 及时关闭文件句柄
   - 清理临时媒体文件
   - 限制流式缓冲区大小

---

## 附录: 关键代码路径

### nanobot 飞书实现

| 功能 | 文件路径 | 行号 |
|------|----------|------|
| 配置模型 | `nanobot/channels/feishu.py` | 341-357 |
| SDK 懒加载 | `nanobot/channels/feishu.py` | 39-67 |
| WebSocket 连接 | `nanobot/channels/feishu.py` | 671-789 |
| 事件注册 | `nanobot/channels/feishu.py` | 701-731 |
| Bot Open ID | `nanobot/channels/feishu.py` | 802-825 |
| @Mention 检测 | `nanobot/channels/feishu.py` | 904-919 |
| @Mention 解析 | `nanobot/channels/feishu.py` | 828-859 |
| 消息接收 | `nanobot/channels/feishu.py` | 2119-2283 |
| 消息发送 | `nanobot/channels/feishu.py` | 1955-2109 |
| 流式卡片创建 | `nanobot/channels/feishu.py` | 1644-1707 |
| 流式更新 | `nanobot/channels/feishu.py` | 1709-1741 |
| 流式发送 | `nanobot/channels/feishu.py` | 1895-1953 |
| 消息格式检测 | `nanobot/channels/feishu.py` | 1208-1250 |
| 回复消息 | `nanobot/channels/feishu.py` | 1558-1591 |
| Session 隔离 | `nanobot/channels/feishu.py` | 2258-2264 |

### agents-hub 微信 Channel

| 功能 | 文件路径 |
|------|----------|
| Channel 主类 | `agents_hub/channels/wechat/channel.py` |
| 配置模型 | `agents_hub/channels/wechat/config.py` |
| 客户端 | `agents_hub/channels/wechat/client.py` |
| 认证 | `agents_hub/channels/wechat/auth.py` |
| 消息处理 | `agents_hub/channels/wechat/message.py` |
| 命令处理 | `agents_hub/channels/wechat/commander.py` |

### nanobot 基础设施

| 功能 | 文件路径 |
|------|----------|
| BaseChannel | `nanobot/channels/base.py` |
| InboundMessage | `nanobot/bus/events.py` |
| OutboundMessage | `nanobot/bus/events.py` |
| MessageBus | `nanobot/bus/queue.py` |
| ChannelManager | `nanobot/channels/manager.py` |

---

## 参考资料

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [lark-oapi Python SDK](https://github.com/larksuite/oapi-sdk-python)
- [nanobot 飞书实现](D:\desktop\软件开发\nanobot\nanobot\channels\feishu.py)
- [agents-hub 微信实现](D:\desktop\软件开发\agents-hub\agents_hub\channels\wechat\channel.py)
