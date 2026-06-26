"""飞书命令系统

支持会话状态管理，包括群聊、单聊和助手模式的切换。
"""

from __future__ import annotations

import json
from typing import Any

from agents_hub.api.schemas.single_chat import CreateSingleChatRequest, SingleChatType
from agents_hub.api.services.single_chat_service import single_chat_manager
from agents_hub.channels.feishu.session import FeishuSessionManager, FeishuSessionState
from agents_hub.config import config
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
from agents_hub.roles import RoleManager
from agents_hub.utils import get_logger

logger = get_logger(__name__)

# 常量
MESSAGE_TIMEOUT_SECONDS = 120.0  # 消息等待超时时间

HELP_TEXT = """可用命令：
/help - 显示帮助
/agents - 列出所有 agent
/groups - 列出所有群聊
/group <名称或序号> - 进入群聊模式
/agent <名称> - 进入单聊模式
/status - 显示当前状态
/back - 返回助手模式"""


class FeishuCommander:
    """飞书命令处理

    负责解析和执行用户命令，支持群聊、单聊和助手模式的切换。

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
        logger.info(
            "处理飞书消息: user=%s, chat_id=%s, content=%s", user_id, chat_id, content[:100]
        )
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
            "/group": lambda: self._cmd_group(chat_id, arg),
            "/agent": lambda: self._cmd_agent(chat_id, arg),
            "/status": lambda: self._cmd_status(chat_id),
            "/back": lambda: self._cmd_back(chat_id),
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
        return "\n".join(lines)

    async def _cmd_group(self, chat_id: str, name_or_idx: str) -> str:
        """切换到群聊模式。"""
        if not name_or_idx:
            return "请指定群聊名称、序号或 ID，如: /group my-team 或 /group 1"

        groups = group_chat_manager.list_all_group_chats()
        if not groups:
            return "当前没有群聊"

        target = None

        # 按序号匹配
        if name_or_idx.isdigit():
            idx = int(name_or_idx) - 1
            if 0 <= idx < len(groups):
                target = groups[idx]
            else:
                return f"序号 {name_or_idx} 超出范围，共 {len(groups)} 个群聊"
        else:
            # 按 ID 匹配（UUID 格式）
            id_matches = [g for g in groups if g["group_chat_id"] == name_or_idx]
            if id_matches:
                target = id_matches[0]
            else:
                # 按名称匹配
                name_matches = [g for g in groups if g["group_chat_name"] == name_or_idx]
                if not name_matches:
                    names = [g["group_chat_name"] for g in groups]
                    return f"未找到群聊 '{name_or_idx}'。可用: {', '.join(names)}"
                target = name_matches[0]

        # 获取成员列表
        group_chat = await group_chat_manager.load_group_chat(target["group_chat_id"])
        member_dicts = group_chat.runtime.get_member_dicts()
        members = [m["name"] for m in member_dicts]

        # 切换状态
        self._session_manager.switch_to_group_chat(
            chat_id, target["group_chat_id"], target["group_chat_name"]
        )
        self._session_manager.save()

        logger.info("已切换到群聊: chat_id=%s, group=%s", chat_id, target["group_chat_name"])
        return (
            f"已进入群聊: {target['group_chat_name']}\n"
            f"成员: {', '.join(members)}\n"
            f"消息将默认发送给 manager，用 @名称 指定目标\n"
            f"发送 /back 返回助手模式"
        )

    async def _cmd_agent(self, chat_id: str, agent_name: str) -> str:
        """切换到单聊模式。"""
        if not agent_name:
            return "请指定 agent 名称，如: /agent pm"

        # 验证 agent 存在
        try:
            self._role_manager.get_role(agent_name)
        except Exception:
            available = self._role_manager.list_role_names()
            return f"Agent '{agent_name}' 不存在。可用: {', '.join(available)}"

        # 创建单聊会话
        request = CreateSingleChatRequest(
            type=SingleChatType.NEW,
            single_chat_name=f"feishu-{chat_id}-{agent_name}",
            agent_name=agent_name,
        )
        response = await single_chat_manager.create_single_chat(request)

        # 切换状态
        self._session_manager.switch_to_single_chat(chat_id, agent_name, response.single_chat_id)
        self._session_manager.save()

        logger.info("已切换到单聊: chat_id=%s, agent=%s", chat_id, agent_name)
        return f"已进入与 {agent_name} 的单聊模式\n发送 /back 返回助手模式"

    async def _cmd_status(self, chat_id: str) -> str:
        """显示当前状态。"""
        state = self._session_manager.get_or_create_state(chat_id)
        type_map = {
            "assistant": "助手模式",
            "single_chat": "单聊模式",
            "group_chat": "群聊模式",
        }
        type_text = type_map.get(state.session_type, state.session_type)
        name_text = state.session_name or state.session_id
        return f"当前模式: {type_text}\n当前对话: {name_text}"

    async def _cmd_back(self, chat_id: str) -> str:
        """返回助手模式。"""
        self._session_manager.switch_to_assistant(chat_id)
        self._session_manager.save()
        logger.info("已返回助手模式: chat_id=%s", chat_id)
        return "已返回助手模式\n\n发送 /help 查看可用命令"

    # ==================== 消息转发 ====================

    async def _forward_message(self, user_id: str, content: str, chat_id: str) -> str:
        """转发消息到当前会话（助手/单聊/群聊）。

        Args:
            user_id: 用户 ID
            content: 消息内容
            chat_id: 飞书群 ID

        Returns:
            响应文本
        """
        logger.info("转发消息: user=%s, chat_id=%s, content=%s", user_id, chat_id, content[:100])

        # 自动创建状态（首次消息）
        state = self._session_manager.get_or_create_state(chat_id)

        if state.session_type == "assistant":
            return await self._forward_to_assistant(state, content)
        elif state.session_type == "single_chat":
            return await self._forward_to_single_chat(state, content)
        elif state.session_type == "group_chat":
            return await self._forward_to_group_chat(state, content)
        else:
            return "请先设置会话类型\n\n发送 /help 查看可用命令"

    async def _forward_to_assistant(self, state: FeishuSessionState, content: str) -> str:
        """转发到助手（复用单聊逻辑）。"""
        # 确保助手单聊存在
        if not state.single_chat_id:
            request = CreateSingleChatRequest(
                type=SingleChatType.NEW,
                single_chat_name=f"feishu-assistant-{state.feishu_chat_id}",
                agent_name=config.default_assistant_name,
            )
            response = await single_chat_manager.create_single_chat(request)
            state.single_chat_id = response.single_chat_id
            self._session_manager.save()
            logger.info(
                "创建助手单聊: chat_id=%s, single_chat_id=%s",
                state.feishu_chat_id,
                response.single_chat_id,
            )

        # 发送消息并收集流式响应
        return await self._collect_stream_response(state.single_chat_id, content)

    async def _forward_to_single_chat(self, state: FeishuSessionState, content: str) -> str:
        """转发到单聊 agent。"""
        if not state.single_chat_id:
            logger.error("单聊状态缺少 single_chat_id: %s", state.feishu_chat_id)
            return "单聊会话不存在，请重新使用 /agent 命令"

        return await self._collect_stream_response(state.single_chat_id, content)

    async def _forward_to_group_chat(self, state: FeishuSessionState, content: str) -> str:
        """转发到群聊。"""
        if not self._group_chat_service:
            logger.error("GroupChatService 未注入")
            return "消息转发服务不可用"

        # 获取群聊成员
        group_chat = await group_chat_manager.load_group_chat(state.session_id)
        member_dicts = group_chat.runtime.get_member_dicts()
        members = [m["name"] for m in member_dicts]

        logger.info(
            "转发消息到群聊: group_chat_id=%s, members=%s",
            state.session_id,
            members,
        )

        # 发送消息并等待回复
        result = await self._group_chat_service.send_message_and_wait(
            group_chat_id=state.session_id,
            content=content,
            members=members,
            timeout=MESSAGE_TIMEOUT_SECONDS,
        )

        logger.info("消息转发完成: group_chat_id=%s", state.session_id)
        return result

    async def _collect_stream_response(self, single_chat_id: str, content: str) -> str:
        """收集单聊流式响应（参考微信实现）。

        Args:
            single_chat_id: 单聊会话 ID
            content: 消息内容

        Returns:
            完整响应文本
        """
        parts = []
        async for event_json in single_chat_manager.send_message_stream(single_chat_id, content):
            try:
                event = json.loads(event_json)
                if event.get("type") == "text_delta":
                    text = event.get("content", {}).get("text", "")
                    if text:
                        parts.append(text)
            except (json.JSONDecodeError, KeyError):
                pass

        return "".join(parts) if parts else "Agent 未返回内容"
