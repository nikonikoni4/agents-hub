---
labels: [ready-for-agent]
---

# Issue 8：群聊消息逐条发送（增量回复）

## Parent

无

## What to build

修改飞书群聊消息发送逻辑，将 agent 的回复改为逐条发送，而不是聚拢成一条消息。

**当前行为**：
- 用户在飞书群发消息后，`_forward_to_group_chat` 调用 `send_message_and_wait`
- `send_message_and_wait` 等待所有 agent 回复完成，用 `"\n"` 连接所有回复
- 最终发送一条很长的消息到飞书群

**期望行为**：
- 用户在飞书群发消息后，只发送用户消息到群聊
- Agent 的回复通过 `_on_broadcast` 逐条推送到飞书群
- 每条 agent 回复单独显示，格式为 `**[agent_name]** : 消息内容`

**实现方案**：
修改 `_forward_to_group_chat` 方法：
1. 只调用 `send_message`（不等待回复）
2. 返回空字符串或简单的确认消息
3. Agent 的回复由 `_on_broadcast` 负责逐条推送

```python
async def _forward_to_group_chat(self, state: FeishuSessionState, content: str) -> str:
    """转发到群聊。"""
    # ... 获取群聊成员、检查群聊是否存在 ...

    # 发送消息到群聊（不等待回复）
    await self._group_chat_service.send_message(
        group_chat_id=state.session_id,
        content=content,
        members=members,
    )

    # Agent 的回复将通过 _on_broadcast 逐条推送到飞书群
    return ""  # 返回空字符串，不发送额外消息
```

## Acceptance criteria

- [ ] 用户在飞书群发消息后，只发送用户消息到群聊
- [ ] Agent 的回复通过 `_on_broadcast` 逐条推送到飞书群
- [ ] 每条 agent 回复单独显示，格式为 `**[agent_name]** : 消息内容`
- [ ] 消息底部显示群聊信息（默认对话对象、成员列表）
- [ ] 不会出现重复发送（`_forward_to_group_chat` 和 `_on_broadcast` 不冲突）

## Blocked by

- None - 可以立即开始

## 相关文件

- `agents_hub/channels/feishu/commander.py` - `_forward_to_group_chat` 方法
- `agents_hub/channels/feishu/channel.py` - `_on_broadcast` 方法
- `agents_hub/api/services/group_chat_service.py` - `send_message` 和 `send_message_and_wait` 方法

## 参考文档

- [Checklist](../checklist.md)
- [PRD](../PRD.md)
