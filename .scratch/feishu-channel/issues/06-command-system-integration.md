---
labels: [ready-for-agent]
---

# Issue 6：命令系统集成

## Parent

无

## What to build

实现飞书 Channel 的命令系统，复用微信的命令逻辑。

**实现内容**：
1. `agents_hub/channels/feishu/commander.py` - 命令处理
   - 复用微信的命令系统
   - 命令路由：/help, /agents, /groups, /bind, /back
2. 集成到 `channel.py`

**命令列表**：
```python
HELP_TEXT = """可用命令：
/help - 显示帮助
/agents - 列出所有 agent
/groups - 列出所有群聊
/bind <群聊名称> - 绑定飞书群到 agents-hub 群聊
/back - 退出当前对话"""
```

**核心功能**：
```python
class FeishuCommander:
    """飞书命令处理"""
    
    def __init__(self, session_manager: FeishuSessionManager):
        self._session_manager = session_manager
        self._role_manager = RoleManager()
        self._group_chat_service = GroupChatService(group_chat_manager)
    
    async def handle(self, user_id: str, content: str, chat_id: str) -> str:
        """处理命令或消息"""
        if content.startswith("/"):
            return await self._dispatch_command(user_id, content, chat_id)
        return await self._forward_message(user_id, content, chat_id)
    
    async def _dispatch_command(self, user_id: str, content: str, chat_id: str) -> str:
        """分发命令"""
        parts = content.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        handlers = {
            "/help": lambda: self._cmd_help(),
            "/agents": lambda: self._cmd_agents(),
            "/groups": lambda: self._cmd_groups(),
            "/bind": lambda: self._cmd_bind(chat_id, arg),
            "/back": lambda: self._cmd_back(user_id),
        }
        
        handler = handlers.get(cmd)
        if handler:
            return await handler()
        return f"未知命令: {cmd}\n\n{HELP_TEXT}"
    
    async def _cmd_bind(self, chat_id: str, group_chat_name: str) -> str:
        """绑定飞书群到 agents-hub 群聊"""
        if not group_chat_name:
            return "请指定群聊名称，如: /bind my-team"
        
        # 查找群聊
        groups = group_chat_manager.list_all_group_chats()
        target = None
        for g in groups:
            if g["group_chat_name"] == group_chat_name:
                target = g
                break
        
        if not target:
            return f"未找到群聊 '{group_chat_name}'"
        
        # 绑定
        self._session_manager.bind(
            chat_id,
            target["group_chat_id"],
            target["group_chat_name"]
        )
        self._session_manager.save()
        
        return f"已绑定到群聊: {target['group_chat_name']}"
```

## Acceptance criteria

- [ ] `FeishuCommander` 类实现
- [ ] `/help` 命令正常工作
- [ ] `/agents` 命令正常工作
- [ ] `/groups` 命令正常工作
- [ ] `/bind` 命令正常工作
- [ ] `/back` 命令正常工作
- [ ] 消息转发正常工作
- [ ] 集成到 `channel.py`
- [ ] 单元测试通过

## Blocked by

- Issue 3：飞书消息接收与解析
- Issue 4：飞书消息发送与广播监听
- Issue 5：Session 映射与同步状态管理

## 相关文件

- `agents_hub/channels/feishu/commander.py`
- `agents_hub/channels/feishu/channel.py`

## 参考文档

- [架构约束文件](../architecture.md)
- [Checklist](../checklist.md)
- `agents_hub/channels/wechat/commander.py` - 微信命令系统参考
