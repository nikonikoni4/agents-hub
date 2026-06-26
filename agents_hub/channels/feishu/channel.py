"""飞书 Channel 主类

负责消息接收、解析、去重、命令处理和消息发送。
"""

from __future__ import annotations

from typing import Any

from agents_hub.channels.feishu.client import FeishuClient
from agents_hub.channels.feishu.config import FeishuConfig
from agents_hub.channels.feishu.message import (
    MessageDeduplicator,
    parse_agent_name,
    parse_mentions,
    parse_message,
)
from agents_hub.utils import get_logger

logger = get_logger(__name__)


class FeishuChannel:
    """飞书 Channel 主类

    负责消息接收、解析、去重、命令处理和消息发送。

    使用方式：
        channel = FeishuChannel(config)
        await channel.start()
        # ... 接收消息时调用 on_message(event)
        await channel.stop()
    """

    name = "feishu"

    def __init__(self, config: FeishuConfig):
        self.config = config
        self._client: FeishuClient | None = None
        self._deduplicator = MessageDeduplicator()
        self._commander: Any = None  # 延迟初始化
        self._session_manager: Any = None  # 延迟初始化
        self._members: list[str] = []  # 群聊成员列表

    async def start(self) -> None:
        """启动 channel：初始化客户端 -> 注册回调"""
        # 延迟导入避免循环依赖
        from agents_hub.channels.feishu.commander import Commander
        from agents_hub.channels.feishu.session import FeishuSessionManager
        from agents_hub.realtime.dependencies import register_channel_callback

        # 初始化客户端
        self._client = FeishuClient(self.config)
        await self._client.connect()

        # 初始化 commander
        self._commander = Commander()

        # 初始化 session manager
        self._session_manager = FeishuSessionManager()
        self._session_manager.load()

        # 注册广播回调
        register_channel_callback(self._on_broadcast)

        logger.info("飞书 channel 已启动")

    async def stop(self) -> None:
        """停止 channel：断开连接 -> 清理资源"""
        if self._client:
            await self._client.disconnect()
            self._client = None

        self._commander = None
        self._session_manager = None
        logger.info("飞书 channel 已停止")

    async def on_message(self, event: dict[str, Any]) -> None:
        """处理接收到的消息。

        Args:
            event: 飞书事件对象，包含 message 字段
        """
        try:
            # 1. 解析消息
            parsed = parse_message(event)
            message_id = parsed["message_id"]
            content = parsed["content"]
            sender_id = parsed["sender_id"]

            # 2. 消息去重
            if self._deduplicator.is_duplicate(message_id):
                logger.debug("消息已处理，跳过: message_id=%s", message_id)
                return

            # 3. 跳过空内容
            if not content.strip():
                return

            # 4. 解析 mention 占位符
            mentions = parsed.get("mentions", [])
            if mentions:
                content = parse_mentions(content, mentions)

            # 5. 解析目标 agent
            agent_name, clean_content = parse_agent_name(content, self._members)

            logger.info(
                "收到飞书消息: message_id=%s, sender=%s, target=%s",
                message_id,
                sender_id,
                agent_name,
            )

            # 6. 调用 commander 处理
            if self._commander:
                await self._commander.handle(sender_id, clean_content)

        except Exception:
            logger.error("处理飞书消息失败", exc_info=True)

    async def send_to_feishu(
        self,
        chat_id: str,
        content: str,
        agent_name: str,
        members: list[str] | None = None,
    ) -> None:
        """发送消息到飞书群。

        Args:
            chat_id: 飞书群 ID
            content: 消息内容
            agent_name: 发送消息的 agent 名称
            members: 群聊成员列表（可选）
        """
        if not self._client:
            return

        try:
            # 格式化消息
            formatted_content = f"**[{agent_name}]** : {content}"

            # 添加成员列表
            if members:
                member_list = ", ".join(members)
                formatted_content += f"\n\n---\n群聊成员: {member_list}"

            # 发送到飞书
            await self._client.send_message(chat_id, formatted_content)
            logger.info("消息已发送到飞书: chat_id=%s, agent=%s", chat_id, agent_name)

        except Exception:
            logger.error("发送飞书消息失败: chat_id=%s", chat_id, exc_info=True)

    async def _on_broadcast(self, group_chat_id: str, message: dict[str, Any] | None) -> None:
        """处理广播回调。

        Args:
            group_chat_id: 群聊 ID
            message: 消息内容（可选）
        """
        # 过滤：只处理有消息的广播
        if not message:
            return

        try:
            # 获取绑定的飞书群 ID
            if not self._session_manager:
                return

            mapping = self._session_manager.get_mapping(group_chat_id)
            if not mapping:
                return  # 未绑定，跳过

            feishu_chat_id = mapping.feishu_chat_id

            # 增量同步：只处理新消息
            sync_state = self._session_manager.get_sync_state(feishu_chat_id)
            if message.get("id", 0) <= sync_state.last_message_id:
                return  # 已同步过，跳过

            # 推送到飞书群
            await self.send_to_feishu(
                chat_id=feishu_chat_id,
                content=message.get("content", ""),
                agent_name=message.get("send_from", "unknown"),
            )

            # 更新同步状态
            self._session_manager.update_sync_state(feishu_chat_id, message.get("id", 0))

        except Exception:
            logger.error("处理广播回调失败: group_chat_id=%s", group_chat_id, exc_info=True)
