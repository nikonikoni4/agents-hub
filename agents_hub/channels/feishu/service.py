"""飞书会话管理服务

封装跨模块编排逻辑，保持 feishu_session_manager 职责单一。
"""

from __future__ import annotations

from agents_hub.api.schemas.single_chat import CreateSingleChatRequest, SingleChatType
from agents_hub.api.services.single_chat_service import single_chat_manager
from agents_hub.channels.feishu.session import feishu_session_manager
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
from agents_hub.utils import get_logger

logger = get_logger(__name__)


class FeishuSessionService:
    """飞书会话管理服务

    封装 MCP 工具中的跨模块编排逻辑：
    - 验证外部资源存在（群聊、单聊）
    - 调用 feishu_session_manager 切换状态
    - 抛出领域异常，不返回 error dict

    使用方式：
        from agents_hub.channels.feishu.service import feishu_session_service

        result = await feishu_session_service.bind_to_group_chat("oc_xxx", "group_1")
    """

    async def bind_to_group_chat(self, feishu_chat_id: str, group_chat_id: str) -> dict:
        """将飞书群绑定到 Agent Hub 群聊。

        Args:
            feishu_chat_id: 飞书群 ID
            group_chat_id: Agent Hub 群聊 ID

        Returns:
            {"status": "bound", "group_chat_id": "...", "group_chat_name": "..."}

        Raises:
            GroupChatNotFoundError: 群聊不存在
        """
        logger.info(
            "bind_to_group_chat: feishu_chat_id=%s, group_chat_id=%s",
            feishu_chat_id,
            group_chat_id,
        )
        gc = await group_chat_manager.load_group_chat(group_chat_id)
        gc_name = gc.runtime.get_info_dict(is_active=True).get("group_chat_name", group_chat_id)
        feishu_session_manager.switch_to_group_chat(feishu_chat_id, group_chat_id, gc_name)
        feishu_session_manager.save()
        return {
            "status": "bound",
            "group_chat_id": group_chat_id,
            "group_chat_name": gc_name,
        }

    async def bind_to_single_chat(self, feishu_chat_id: str, session_id: str) -> dict:
        """将飞书群绑定到已有单聊会话。

        Args:
            feishu_chat_id: 飞书群 ID
            session_id: 单聊会话 ID

        Returns:
            {"status": "bound", "session_id": "...", "agent_name": "..."}

        Raises:
            ValueError: 单聊会话不存在
        """
        logger.info(
            "bind_to_single_chat: feishu_chat_id=%s, session_id=%s",
            feishu_chat_id,
            session_id,
        )
        chat = single_chat_manager.get_single_chat(session_id)
        agent_name = chat.agent_name
        feishu_session_manager.switch_to_single_chat(feishu_chat_id, agent_name, session_id)
        feishu_session_manager.save()
        return {
            "status": "bound",
            "session_id": session_id,
            "agent_name": agent_name,
        }

    async def create_single_chat(
        self, feishu_chat_id: str, agent_name: str, cwd: str | None = None
    ) -> dict:
        """为飞书群创建新单聊会话并绑定。

        Args:
            feishu_chat_id: 飞书群 ID
            agent_name: Agent 角色名称
            cwd: Agent 工作目录（可选）

        Returns:
            {"single_chat_id": "...", "agent_name": "...", "status": "created"}

        Raises:
            Exception: 创建失败
        """
        logger.info(
            "create_single_chat: feishu_chat_id=%s, agent_name=%s, cwd=%s",
            feishu_chat_id,
            agent_name,
            cwd,
        )
        request = CreateSingleChatRequest(
            type=SingleChatType.NEW,
            single_chat_name=f"feishu-{feishu_chat_id}-{agent_name}",
            agent_name=agent_name,
            cwd=cwd,
        )
        response = await single_chat_manager.create_single_chat(request)
        feishu_session_manager.add_single_chat_history(
            feishu_chat_id, response.single_chat_id, agent_name, ""
        )
        feishu_session_manager.switch_to_single_chat(
            feishu_chat_id, agent_name, response.single_chat_id
        )
        feishu_session_manager.save()
        return {
            "single_chat_id": response.single_chat_id,
            "agent_name": agent_name,
            "status": "created",
        }


# 全局实例
feishu_session_service = FeishuSessionService()
