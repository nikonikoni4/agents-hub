"""飞书命令系统

复用微信的命令逻辑，支持 /help, /agents, /groups, /bind, /back 命令。
"""

from __future__ import annotations

from typing import Any

from agents_hub.channels.feishu.session import FeishuSessionManager
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
from agents_hub.roles import RoleManager
from agents_hub.utils import get_logger

logger = get_logger(__name__)

HELP_TEXT = """可用命令：
/help - 显示帮助
/agents - 列出所有 agent
/groups - 列出所有群聊
/bind <群聊名称> - 绑定飞书群到 agents-hub 群聊
/back - 退出当前对话"""


class FeishuCommander:
    """飞书命令处理

    负责解析和执行用户命令，以及转发消息到群聊。

    使用方式：
        commander = FeishuCommander(session_manager, group_chat_service)
        response = await commander.handle(user_id, content, chat_id)
    """

    def __init__(self, session_manager: FeishuSessionManager, group_chat_service: Any = None):
        self._session_manager = session_manager
        self._role_manager = RoleManager()
        self._group_chat_service = group_chat_service

    async def handle(self, user_id: str, content: str, chat_id: str) -> str:
        """处理命令或消息。

        Args:
            user_id: 用户 ID
            content: 消息内容
            chat_id: 飞书群 ID

        Returns:
            响应文本
        """
        if content.startswith("/"):
            return await self._dispatch_command(user_id, content, chat_id)
        return await self._forward_message(user_id, content, chat_id)

    # ==================== 命令分发 ====================

    async def _dispatch_command(self, user_id: str, content: str, chat_id: str) -> str:
        """分发命令。"""
        parts = content.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        handlers = {
            "/help": lambda: self._cmd_help(),
            "/agents": lambda: self._cmd_agents(),
            "/groups": lambda: self._cmd_groups(),
            "/bind": lambda: self._cmd_bind(chat_id, arg),
            "/back": lambda: self._cmd_back(),
        }

        handler = handlers.get(cmd)
        if handler:
            return await handler()
        return f"未知命令: {cmd}\n\n{HELP_TEXT}"

    # ==================== 基础命令 ====================

    @staticmethod
    async def _cmd_help() -> str:
        """显示帮助信息。"""
        return HELP_TEXT

    async def _cmd_agents(self) -> str:
        """列出所有 agent。"""
        roles = self._role_manager.list_roles()
        if not roles:
            return "当前没有可用的 agent"
        lines = ["可用 Agent："]
        for i, r in enumerate(roles, 1):
            desc = f" - {r.description}" if r.description else ""
            lines.append(f"  {i}. {r.name} [{r.platform.value}]{desc}")
        return "\n".join(lines)

    async def _cmd_groups(self) -> str:
        """列出所有群聊。"""
        groups = group_chat_manager.list_all_group_chats()
        if not groups:
            return "当前没有群聊"
        lines = ["群聊列表："]
        for i, g in enumerate(groups, 1):
            status = "活跃" if g["is_active"] else "未激活"
            lines.append(f"  {i}. {g['group_chat_name']} [{status}]")
            lines.append(f"     ID: {g['group_chat_id']}")
        return "\n".join(lines)

    async def _cmd_bind(self, chat_id: str, group_chat_name: str) -> str:
        """绑定飞书群到 agents-hub 群聊。

        Args:
            chat_id: 飞书群 ID
            group_chat_name: agents-hub 群聊名称
        """
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
        self._session_manager.bind(chat_id, target["group_chat_id"], target["group_chat_name"])
        self._session_manager.save()

        return f"已绑定到群聊: {target['group_chat_name']}"

    @staticmethod
    async def _cmd_back() -> str:
        """退出当前对话。"""
        return "已退出当前对话\n\n发送 /help 查看可用命令"

    # ==================== 消息转发 ====================

    async def _forward_message(self, user_id: str, content: str, chat_id: str) -> str:
        """转发消息到绑定的群聊。

        Args:
            user_id: 用户 ID
            content: 消息内容
            chat_id: 飞书群 ID
        """
        # 检查是否已绑定
        mapping = self._session_manager.get_mapping(chat_id)
        if not mapping:
            return "请先绑定群聊\n\n发送 /help 查看可用命令"

        # 检查 group_chat_service 是否可用
        if not self._group_chat_service:
            logger.error("GroupChatService 未注入，无法转发消息")
            return "消息转发服务不可用"

        # 获取群聊成员
        group_chat = await group_chat_manager.load_group_chat(mapping.group_chat_id)
        member_dicts = group_chat.runtime.get_member_dicts()
        members = [m["name"] for m in member_dicts]

        # 转发消息
        return await self._group_chat_service.send_message_and_wait(
            group_chat_id=mapping.group_chat_id,
            content=content,
            members=members,
            timeout=120.0,
        )
