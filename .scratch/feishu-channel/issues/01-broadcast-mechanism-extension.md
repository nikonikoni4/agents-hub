---
labels: [ready-for-agent]
---

# Issue 1：广播机制扩展

## Parent

无

## What to build

扩展 `broadcast_group_chat_refresh()` 函数，支持在广播中携带消息内容。这是飞书 Channel 集成的基础，使得飞书 Channel 可以从广播中提取消息内容并推送到飞书群。

**关键修改点**：
1. 扩展 `on_change` 回调签名，支持传递消息内容
2. 扩展 `_notify_change()` 方法，添加可选的 `message` 参数
3. 扩展 `broadcast_group_chat_refresh()` 函数，添加可选的 `message` 参数
4. 添加回调订阅机制，支持飞书 Channel 注册回调

**向后兼容**：不传 message 时行为不变，前端继续使用现有的刷新逻辑。

## Acceptance criteria

- [ ] `broadcast_group_chat_refresh()` 函数支持可选 `message` 参数
- [ ] `_notify_change()` 方法支持传递消息内容
- [ ] `on_change` 回调签名扩展为 `Callable[[str, dict | None], Awaitable[None]]`
- [ ] 添加 `register_channel_callback()` 函数，支持注册回调
- [ ] 回调机制正常工作：消息广播时，注册的回调被调用
- [ ] 不传 message 时行为不变，前端正常工作
- [ ] 单元测试通过

## Blocked by

None - 可以立即开始

## 相关文件

- `agents_hub/core/context/group_chat_runtime.py`
- `agents_hub/realtime/dependencies.py`
- `agents_hub/core/orchestration/group_chat.py`

## 参考文档

- [架构约束文件](../architecture.md)
- [Checklist](../checklist.md)
- [core-context spec](../../../docs/specs/2026-05-31-core-context.md)
- [realtime spec](../../../docs/specs/2026-06-06-realtime.md)
