---
labels: [ready-for-agent]
---

# Issue 3：飞书消息接收与解析

## Parent

无

## What to build

实现飞书消息的接收和解析功能，包括消息去重、@Mention 检测和 @agent_name 解析。

**实现内容**：
1. `agents_hub/channels/feishu/message.py` - 消息解析
   - `parse_message()` - 解析飞书消息事件
   - `parse_agent_name()` - 解析 @agent_name
   - `parse_mentions()` - 解析 mention 占位符
2. `agents_hub/channels/feishu/channel.py` - `on_message()` 方法
   - 消息去重（OrderedDict 缓存 message_id）
   - 调用 `commander.handle()` 处理消息

**消息解析逻辑**：
```python
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

## Acceptance criteria

- [ ] `parse_message()` 正确解析飞书消息事件
- [ ] `parse_agent_name()` 正确解析 @agent_name
- [ ] `parse_mentions()` 正确解析 mention 占位符
- [ ] 消息去重有效（使用 OrderedDict 缓存 message_id）
- [ ] `on_message()` 方法正常工作
- [ ] 单元测试通过

## Blocked by

- Issue 2：飞书 Channel 基础框架

## 相关文件

- `agents_hub/channels/feishu/message.py`
- `agents_hub/channels/feishu/channel.py`

## 参考文档

- [架构约束文件](../architecture.md)
- [Checklist](../checklist.md)
- `agents_hub/channels/wechat/message.py` - 微信消息解析参考
