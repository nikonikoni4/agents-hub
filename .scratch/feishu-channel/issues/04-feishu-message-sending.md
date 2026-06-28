---
labels: [ready-for-agent]
---

# Issue 4：飞书消息发送与广播监听

## Parent

无

## What to build

实现飞书消息发送功能，并注册回调监听群聊广播。

**实现内容**：
1. `agents_hub/channels/feishu/channel.py`
   - `send_to_feishu()` - 发送消息到飞书群
   - `_on_broadcast()` - 处理广播回调
   - `start()` - 启动时注册回调
2. 消息格式化：`**[agent_name]** : 消息内容` + 成员列表

**消息发送格式**：
```python
async def send_to_feishu(self, chat_id: str, content: str, 
                          agent_name: str, members: list[str]) -> None:
    """发送消息到飞书群"""
    # 格式化消息
    formatted_content = f"**[{agent_name}]** : {content}"
    
    # 添加成员列表
    if members:
        member_list = ", ".join(members)
        formatted_content += f"\n\n---\n群聊成员: {member_list}"
    
    # 发送到飞书
    await self._client.send_message(chat_id, formatted_content)
```

**广播监听**：
```python
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
    
    # 获取绑定的飞书群 ID
    feishu_chat_id = self._get_feishu_chat_id(group_chat_id)
    if not feishu_chat_id:
        return  # 未绑定，跳过
    
    # 增量同步：只处理新消息
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

## Acceptance criteria

- [ ] `send_to_feishu()` 正确格式化并发送消息
- [ ] 消息格式正确：`**[agent_name]** : 消息内容` + 成员列表
- [ ] `_on_broadcast()` 正确处理广播回调
- [ ] 广播过滤有效：只处理有消息的广播
- [ ] 回调注册正常工作
- [ ] 单元测试通过

## Blocked by

- Issue 2：飞书 Channel 基础框架

## 相关文件

- `agents_hub/channels/feishu/channel.py`
- `agents_hub/realtime/dependencies.py`

## 参考文档

- [架构约束文件](../architecture.md)
- [Checklist](../checklist.md)
- `agents_hub/channels/wechat/channel.py` - 微信 Channel 参考
