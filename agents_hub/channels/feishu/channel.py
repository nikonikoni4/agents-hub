"""飞书 Channel 主类

负责消息接收、解析、去重和命令处理。
"""

from __future__ import annotations

from typing import Any

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

    负责消息接收、解析、去重和命令处理。

    使用方式：
        channel = FeishuChannel(config)
        await channel.start()
        # ... 接收消息时调用 on_message(event)
        await channel.stop()
    """

    name = "feishu"

    def __init__(self, config: FeishuConfig):
        self.config = config
        self._deduplicator = MessageDeduplicator()
        self._commander: Any = None  # 延迟初始化
        self._members: list[str] = []  # 群聊成员列表

    async def start(self) -> None:
        """启动 channel"""
        # 延迟导入避免循环依赖
        from agents_hub.channels.feishu.commander import Commander

        self._commander = Commander()
        logger.info("飞书 channel 已启动")

    async def stop(self) -> None:
        """停止 channel"""
        self._commander = None
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
