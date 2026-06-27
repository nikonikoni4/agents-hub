"""飞书命令系统

支持会话状态管理，包括群聊、单聊和助手模式的切换。
命令精简为 3 个核心命令：/start、/back、/default
"""

from __future__ import annotations

import json
from typing import Any

from agents_hub.api.schemas.single_chat import CreateSingleChatRequest, SingleChatType
from agents_hub.api.services.single_chat_service import single_chat_manager
from agents_hub.channels.feishu.session import FeishuSessionState, feishu_session_manager
from agents_hub.config import config
from agents_hub.core.foundation import GroupChatNotFoundError
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
from agents_hub.roles import RoleManager
from agents_hub.utils import get_logger

logger = get_logger(__name__)

# 常量
MESSAGE_TIMEOUT_SECONDS = 120.0  # 消息等待超时时间
DEFAULT_COMMAND_PREFIX = "/default "  # /default 命令前缀（含空格）

WELCOME_TEXT = """欢迎使用 Agents Hub！

发送 /start 进入助手模式，通过自然语言管理会话。"""


class FeishuCommander:
    """飞书命令处理

    负责解析和执行用户命令，支持群聊、单聊和助手模式的切换。

    使用方式：
        commander = FeishuCommander(group_chat_service)
        response = await commander.handle(user_id, content, chat_id)
    """

    def __init__(self, group_chat_service: Any = None):
        self._role_manager = RoleManager()
        self._group_chat_service = group_chat_service

    async def handle(self, user_id: str, content: str, chat_id: str) -> str:
        """处理命令或消息。

        路由逻辑：
        1. /back 最高优先级，任何状态下返回 idle
        2. idle 状态：/start 进入助手模式，其他返回欢迎文本
        3. assistant 状态：转发到助手，检测状态变化
        4. group_chat 状态：/default 拦截，其他转发到群聊
        5. single_chat 状态：转发到单聊

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

        # 最高优先级：/back 命令
        if content.strip() == "/back":
            return await self._cmd_back(chat_id)

        state = feishu_session_manager.get_or_create_state(chat_id)

        if state.session_type == "idle":
            if content.strip() == "/start":
                return await self._enter_assistant_mode(chat_id, state)
            return WELCOME_TEXT

        elif state.session_type == "assistant":
            response = await self._forward_to_assistant(chat_id, content)
            # 检查状态是否改变（助手调用了 MCP 工具）
            new_state = feishu_session_manager.get_or_create_state(chat_id)
            if new_state.session_type != "assistant":
                return response + f"\n\n已进入{new_state.session_name}\n/back 返回"
            return response

        elif state.session_type == "group_chat":
            if content.startswith(DEFAULT_COMMAND_PREFIX):
                agent_name = content.strip()[len(DEFAULT_COMMAND_PREFIX) :]
                return await self._cmd_default(chat_id, agent_name, state)
            return await self._forward_to_group_chat(state, content)

        elif state.session_type == "single_chat":
            return await self._forward_to_single_chat(state, content)

        return WELCOME_TEXT

    # ==================== 命令处理 ====================

    async def _enter_assistant_mode(self, chat_id: str, state: FeishuSessionState) -> str:
        """进入助手模式。"""
        # 如果已经在助手模式，提示用户
        if state.session_type == "assistant":
            return "已经在助手模式中\n\n直接发送消息即可与助手对话"

        # 切换到助手模式
        feishu_session_manager.switch_to_assistant(chat_id)
        feishu_session_manager.save()
        logger.info("已切换到助手模式: chat_id=%s", chat_id)
        return "已进入助手模式\n\n直接发送消息即可与助手对话\n发送 /back 返回命令面板"

    async def _cmd_back(self, chat_id: str) -> str:
        """返回命令面板。"""
        feishu_session_manager.switch_to_idle(chat_id)
        feishu_session_manager.save()
        logger.info("已返回命令面板: chat_id=%s", chat_id)
        return "已返回命令面板\n/start - 进入助手模式"

    async def _cmd_default(self, chat_id: str, agent_name: str, state: FeishuSessionState) -> str:
        """设置群聊默认对话 Agent。"""
        if not agent_name:
            return "请指定 agent 名称，如: /default pm"

        # 检查 agent 是否存在
        roles = self._role_manager.list_roles()
        valid_names = [r.name for r in roles]
        if agent_name not in valid_names:
            return f"Agent '{agent_name}' 不存在。可用: {', '.join(valid_names)}"

        # 设置默认 agent
        state.default_agent = agent_name
        feishu_session_manager.save()

        logger.info("已设置默认 agent: chat_id=%s, agent=%s", chat_id, agent_name)
        return f"已设置默认对话对象: {agent_name}\n\n后续消息将默认发送给 {agent_name}"

    # ==================== 消息转发 ====================

    async def _forward_to_assistant(self, chat_id: str, content: str) -> str:
        """转发到助手（复用单聊逻辑）。

        Args:
            chat_id: 飞书群 ID
            content: 消息内容

        Returns:
            助手响应文本
        """
        state = feishu_session_manager.get_or_create_state(chat_id)

        # 确保助手单聊存在
        if not state.single_chat_id:
            request = CreateSingleChatRequest(
                type=SingleChatType.NEW,
                single_chat_name=f"feishu-assistant-{state.feishu_chat_id}",
                agent_name=config.default_assistant_name,
            )
            response = await single_chat_manager.create_single_chat(request)
            state.single_chat_id = response.single_chat_id
            feishu_session_manager.save()
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
            return "单聊会话不存在，请重新使用 /start 进入助手模式"

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
            deleted_name = state.session_name or state.session_id
            logger.warning("群聊已删除: group_chat_id=%s, 重置状态为 idle", state.session_id)
            feishu_session_manager.switch_to_idle(state.feishu_chat_id)
            feishu_session_manager.save()
            return f"群聊 '{deleted_name}' 已删除\n\n已返回命令面板\n\n{WELCOME_TEXT}"

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
        """收集单聊流式响应。

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
