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
from agents_hub.core.foundation import GroupChatNotFoundError
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
from agents_hub.roles import RoleManager
from agents_hub.utils import get_logger

logger = get_logger(__name__)

# 常量
MESSAGE_TIMEOUT_SECONDS = 120.0  # 消息等待超时时间

HELP_TEXT = """欢迎使用 Agents Hub！

可用命令：
/help - 显示帮助
/a 或 /assistant - 进入助手模式
/agents - 列出所有 agent
/ag <名称或序号> - 进入 agent 单聊 (快捷方式)
/groups - 列出所有群聊
/g <名称或序号> - 进入群聊 (快捷方式)
/default <名称> - 设置群聊默认对话对象 (仅群聊模式)
/status - 显示当前状态
/back - 返回命令面板

提示：可使用序号快速选择，如 /g 1 或 /ag 2"""


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
            "/a": lambda: self._cmd_assistant(chat_id),
            "/assistant": lambda: self._cmd_assistant(chat_id),
            "/agents": lambda: self._cmd_agents(),
            "/ag": lambda: self._cmd_agent(chat_id, arg),  # 快捷方式
            "/agent": lambda: self._cmd_agent(chat_id, arg),
            "/groups": lambda: self._cmd_groups(),
            "/g": lambda: self._cmd_group(chat_id, arg),  # 快捷方式
            "/group": lambda: self._cmd_group(chat_id, arg),
            "/default": lambda: self._cmd_default(chat_id, arg),
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

    async def _cmd_assistant(self, chat_id: str) -> str:
        """进入助手模式。"""
        state = self._session_manager.get_or_create_state(chat_id)

        # 如果已经在助手模式，提示用户
        if state.session_type == "assistant":
            return "已经在助手模式中\n\n直接发送消息即可与助手对话"

        # 切换到助手模式
        self._session_manager.switch_to_assistant(chat_id)
        self._session_manager.save()
        logger.info("已切换到助手模式: chat_id=%s", chat_id)
        return "已进入助手模式\n\n直接发送消息即可与助手对话\n发送 /back 返回命令面板"

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
            return "请指定群聊名称或序号，如: /g my-team 或 /g 1"

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

    async def _cmd_agent(self, chat_id: str, name_or_idx: str) -> str:
        """切换到单聊模式。"""
        if not name_or_idx:
            return "请指定 agent 名称或序号，如: /ag pm 或 /ag 1"

        # 获取所有 agent
        roles = self._role_manager.list_roles()
        if not roles:
            return "当前没有可用的 agent"

        agent_name = None

        # 按序号匹配
        if name_or_idx.isdigit():
            idx = int(name_or_idx) - 1
            if 0 <= idx < len(roles):
                agent_name = roles[idx].name
            else:
                return f"序号 {name_or_idx} 超出范围，共 {len(roles)} 个 agent"
        else:
            # 按名称匹配
            if name_or_idx in [r.name for r in roles]:
                agent_name = name_or_idx
            else:
                names = [r.name for r in roles]
                return f"Agent '{name_or_idx}' 不存在。可用: {', '.join(names)}"

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
        return f"已进入与 {agent_name} 的单聊模式\n发送 /back 返回命令面板"

    async def _cmd_default(self, chat_id: str, agent_name: str) -> str:
        """设置群聊默认对话 Agent。"""
        if not agent_name:
            return "请指定 agent 名称，如: /default pm"

        state = self._session_manager.get_or_create_state(chat_id)

        # 检查是否在群聊状态
        if state.session_type != "group_chat":
            return "此命令仅在群聊模式下可用\n\n请先使用 /group <名称> 进入群聊"

        # 检查 agent 是否存在
        roles = self._role_manager.list_roles()
        valid_names = [r.name for r in roles]
        if agent_name not in valid_names:
            return f"Agent '{agent_name}' 不存在。可用: {', '.join(valid_names)}"

        # 设置默认 agent
        state.default_agent = agent_name
        self._session_manager.save()

        logger.info("已设置默认 agent: chat_id=%s, agent=%s", chat_id, agent_name)
        return f"已设置默认对话对象: {agent_name}\n\n后续消息将默认发送给 {agent_name}"

    async def _cmd_status(self, chat_id: str) -> str:
        """显示当前状态。"""
        state = self._session_manager.get_or_create_state(chat_id)
        type_map = {
            "idle": "命令面板",
            "assistant": "助手模式",
            "single_chat": "单聊模式",
            "group_chat": "群聊模式",
        }
        type_text = type_map.get(state.session_type, state.session_type)

        if state.session_type == "idle":
            return f"当前模式: {type_text}\n\n发送命令选择模式，如 /a 进入助手"

        name_text = state.session_name or state.session_id
        return f"当前模式: {type_text}\n当前对话: {name_text}"

    async def _cmd_back(self, chat_id: str) -> str:
        """返回命令面板。"""
        state = self._session_manager.get_or_create_state(chat_id)
        state.session_type = "idle"
        state.session_id = ""
        state.session_name = ""
        # 保留 single_chat_id，避免重复创建单聊
        self._session_manager.save()
        logger.info("已返回命令面板: chat_id=%s", chat_id)
        return "已返回命令面板\n\n" + HELP_TEXT

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

        if state.session_type == "idle":
            # 空闲模式：显示命令面板
            return HELP_TEXT
        elif state.session_type == "assistant":
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

        try:
            # 获取群聊成员
            group_chat = await group_chat_manager.load_group_chat(state.session_id)
        except GroupChatNotFoundError:
            logger.warning("群聊已删除: group_chat_id=%s, 重置状态为 idle", state.session_id)
            state.session_type = "idle"
            state.session_id = ""
            state.session_name = ""
            self._session_manager.save()
            return f"群聊 '{state.session_name or state.session_id}' 已删除\n\n已返回命令面板\n\n{HELP_TEXT}"

        member_dicts = group_chat.runtime.get_member_dicts()
        members = [m["name"] for m in member_dicts]

        # 使用默认 agent 或默认发送给 manager
        default_agent = state.default_agent if state.default_agent else "manager"

        logger.info(
            "转发消息到群聊: group_chat_id=%s, members=%s, default_agent=%s",
            state.session_id,
            members,
            default_agent,
        )

        # 发送消息并等待回复
        result = await self._group_chat_service.send_message_and_wait(
            group_chat_id=state.session_id,
            content=content,
            members=members,
            timeout=MESSAGE_TIMEOUT_SECONDS,
        )

        # 添加群聊信息
        group_info = f"\n\n---\n当前默认对话对象: {default_agent}\n群聊成员: {', '.join(members)}"
        result_with_info = f"{result}{group_info}"

        logger.info("消息转发完成: group_chat_id=%s", state.session_id)
        return result_with_info

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
                event_type = event.get("type")

                # 调试日志：记录所有事件类型
                logger.debug(
                    "收到流式事件: type=%s, content_keys=%s",
                    event_type,
                    list(event.get("content", {}).keys())
                    if isinstance(event.get("content"), dict)
                    else "not_dict",
                )

                if event_type == "text_delta":
                    text = event.get("content", {}).get("text", "")
                    if text:
                        parts.append(text)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("解析流式事件失败: %s", e)

        result = "".join(parts) if parts else "Agent 未返回内容"
        logger.info("流式响应收集完成: single_chat_id=%s, length=%d", single_chat_id, len(result))
        return result
