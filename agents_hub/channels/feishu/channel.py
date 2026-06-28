"""飞书 Channel 主类

负责消息接收、解析、去重、命令处理和消息发送。
"""

from __future__ import annotations

from pathlib import Path
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
        channel = FeishuChannel(config, data_path, group_chat_service)
        await channel.start()
        # ... 接收消息时调用 on_message(event)
        await channel.stop()
    """

    name = "feishu"

    def __init__(self, config: FeishuConfig, data_path: Path, group_chat_service: Any):
        self.config = config
        self._data_path = data_path
        self._group_chat_service = group_chat_service
        self._client: FeishuClient | None = None
        self._deduplicator = MessageDeduplicator()
        self._commander: Any = None  # 延迟初始化
        self._members: list[str] = []  # 群聊成员列表

    async def start(self) -> None:
        """启动 channel：初始化客户端 -> 注册回调"""
        # 延迟导入避免循环依赖
        from agents_hub.channels.feishu.commander import FeishuCommander
        from agents_hub.channels.feishu.session import feishu_session_manager
        from agents_hub.realtime.dependencies import register_channel_callback

        # 初始化客户端
        self._client = FeishuClient(self.config)

        # 设置消息回调（在 connect 之前）
        self._client.on_message = self._on_ws_message

        await self._client.connect()

        # 加载全局 session manager
        feishu_session_manager.load()

        # 注册飞书机器人名称为保留角色名
        if self.config.bot_names:
            from agents_hub.roles.role_manager import RoleManager

            RoleManager.reserved_role_names.update(self.config.bot_names)
            logger.info("已注册机器人保留名称: %s", self.config.bot_names)

        # 初始化 commander（不再传递 session_manager）
        self._commander = FeishuCommander(self._group_chat_service)

        # 注册广播回调
        register_channel_callback(self._on_broadcast)

        # 补偿重启期间错过的消息
        await self._sync_missed_messages()

        logger.info("飞书 channel 已启动")

    async def _sync_missed_messages(self) -> None:
        """补偿重启期间错过的消息。

        遍历所有已绑定的群聊 session，查询群聊历史中 id > last_message_id 的消息并补发。
        """
        from agents_hub.channels.feishu.session import feishu_session_manager
        from agents_hub.core.foundation import GroupChatNotFoundError
        from agents_hub.core.orchestration.group_chat_manager import group_chat_manager

        synced_count = 0
        for state in feishu_session_manager.iter_states():
            if state.session_type != "group_chat":
                continue

            try:
                group_chat = await group_chat_manager.load_group_chat(state.session_id)
                messages = group_chat.runtime.get_message_dicts(limit=0)  # 获取全部消息

                # 过滤出错过的消息
                missed = [m for m in messages if m.get("id", 0) > state.last_message_id]
                if not missed:
                    continue

                logger.info(
                    "补偿消息: feishu_chat_id=%s, group_chat_id=%s, missed=%d",
                    state.feishu_chat_id,
                    state.session_id,
                    len(missed),
                )

                # 逐条补发
                for msg in missed:
                    await self.send_to_feishu(
                        chat_id=state.feishu_chat_id,
                        content=msg.get("content", ""),
                        agent_name=msg.get("speaker", "unknown"),
                    )
                    state.last_message_id = msg.get("id", 0)
                    synced_count += 1

            except GroupChatNotFoundError:
                logger.warning(
                    "群聊已删除，重置状态为 idle: feishu_chat_id=%s, group_chat_id=%s",
                    state.feishu_chat_id,
                    state.session_id,
                )
                state.session_type = "idle"
                state.session_id = ""
                state.session_name = ""

            except Exception as e:
                logger.error(
                    "补偿消息失败: feishu_chat_id=%s, group_chat_id=%s, error=%s",
                    state.feishu_chat_id,
                    state.session_id,
                    e,
                    exc_info=True,
                )

        if synced_count > 0:
            from agents_hub.channels.feishu.session import feishu_session_manager

            feishu_session_manager.save()
            logger.info("消息补偿完成: synced=%d", synced_count)

    async def _on_ws_message(self, event: dict[str, Any]) -> None:
        """处理 WebSocket 接收到的消息事件。

        飞书 SDK 返回的是 P2ImMessageReceiveV1Data 对象，需要转换为字典格式。
        """
        try:
            # 提取消息和发送者
            message = event.get("message")
            sender = event.get("sender")

            if not message or not sender:
                logger.warning("飞书消息格式异常: %s", str(event)[:200])
                return

            # 提取 sender_id
            sender_id_obj = getattr(sender, "sender_id", None)
            sender_id = ""
            sender_type = ""
            if sender_id_obj:
                sender_id = getattr(sender_id_obj, "user_id", "") or ""
            sender_type = getattr(sender, "sender_type", "") or ""

            # 提取消息内容
            message_id = getattr(message, "message_id", "") or ""
            chat_id = getattr(message, "chat_id", "") or ""
            content_str = getattr(message, "content", "{}") or "{}"
            msg_type = getattr(message, "message_type", "text") or "text"

            # 解析 content JSON
            import json

            try:
                content_obj = json.loads(content_str)
                content = content_obj.get("text", "")
            except (json.JSONDecodeError, TypeError):
                content = content_str

            # 解析 mentions
            raw_mentions = getattr(message, "mentions", None) or []
            mentions = []
            for m in raw_mentions:
                mention_id_obj = getattr(m, "id", None)
                mention_id = ""
                if mention_id_obj:
                    mention_id = getattr(mention_id_obj, "user_id", "") or ""
                mentions.append(
                    {
                        "key": getattr(m, "key", "") or "",
                        "id": mention_id,
                        "name": getattr(m, "name", "") or "",
                    }
                )

            # 构造标准化的事件字典
            parsed_event = {
                "message": {
                    "message_id": message_id,
                    "chat_id": chat_id,
                    "content": json.dumps({"text": content}),
                    "message_type": msg_type,
                    "sender": {
                        "sender_id": {"user_id": sender_id},
                        "sender_type": sender_type,
                    },
                    "mentions": [
                        {"key": m["key"], "id": {"user_id": m["id"]}, "name": m["name"]}
                        for m in mentions
                    ],
                }
            }

            logger.info(
                "飞书 WebSocket 收到消息: message_id=%s, chat_id=%s, sender=%s",
                message_id,
                chat_id,
                sender_id,
            )
            await self.on_message(parsed_event)
        except Exception as e:
            logger.error("处理飞书 WebSocket 消息失败: %s", e, exc_info=True)

    async def stop(self) -> None:
        """停止 channel：断开连接 -> 清理资源"""
        if self._client:
            await self._client.disconnect()
            self._client = None

        self._commander = None
        # 注意：不再清理 _session_manager，因为使用全局单例
        logger.info("飞书 channel 已停止")

    async def on_message(self, event: dict[str, Any]) -> None:
        """处理接收到的消息。

        Args:
            event: 飞书事件对象，包含 message 字段
        """
        # 1. 解析消息
        parsed = parse_message(event)
        message_id = parsed["message_id"]
        chat_id = parsed["chat_id"]
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

        # 4.5 过滤机器人名称：去除行首的 @bot_name
        import re

        for bot_name in self.config.bot_names:
            content = re.sub(rf"^@?\s*{re.escape(bot_name)}\s+", "", content)

        # 5. 【优先级1】判断是否为命令消息（以 / 开头）
        #    命令消息直接交给 commander 处理，不解析 agent_name
        if content.strip().startswith("/"):
            logger.info(
                "收到飞书命令: message_id=%s, chat_id=%s, sender=%s, command=%s",
                message_id,
                chat_id,
                sender_id,
                content.split()[0] if content.split() else content,
            )

            if self._commander:
                response = await self._commander.handle(sender_id, content.strip(), chat_id)

                if response:
                    await self.send_to_feishu(
                        chat_id=chat_id,
                        content=response,
                        agent_name="Agents Hub",
                    )
                    logger.info(
                        "已发送命令响应到飞书: chat_id=%s, length=%d", chat_id, len(response)
                    )
            return

        # 6. 【优先级2】解析目标 agent（非命令消息）
        agent_name, clean_content = parse_agent_name(content, self._members)

        logger.info(
            "收到飞书消息: message_id=%s, chat_id=%s, sender=%s, target=%s",
            message_id,
            chat_id,
            sender_id,
            agent_name,
        )

        # 7. 调用 commander 处理并获取响应
        if self._commander:
            response = await self._commander.handle(sender_id, clean_content, chat_id)

            # 8. 发送响应回飞书
            if response:
                await self.send_to_feishu(
                    chat_id=chat_id,
                    content=response,
                    agent_name="Agents Hub",  # 统一使用平台名称
                )
                logger.info("已发送响应到飞书: chat_id=%s, length=%d", chat_id, len(response))

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

        Raises:
            FeishuAPIError: API 调用失败
            FeishuAuthError: 认证失败
        """
        if not self._client:
            return

        # 安全过滤：移除泄露的 feishu_chat_id
        import re

        content = re.sub(r"oc_[a-zA-Z0-9]+", "[已隐藏]", content)

        # 格式化消息
        formatted_content = f"**[{agent_name}]** : {content}"

        # 添加成员列表
        if members:
            member_list = ", ".join(members)
            formatted_content += f"\n\n---\n群聊成员: {member_list}"

        # 飞书 API 要求 content 是 JSON 格式
        import json

        content_json = json.dumps({"text": formatted_content}, ensure_ascii=False)

        # 发送到飞书（异常由调用方处理）
        await self._client.send_message(chat_id, content_json)
        logger.info("消息已发送到飞书: chat_id=%s, agent=%s", chat_id, agent_name)

    async def _on_broadcast(self, group_chat_id: str, message: dict[str, Any] | None) -> None:
        """处理广播回调（支持新状态结构）。

        Args:
            group_chat_id: 群聊 ID
            message: 消息内容（可选）

        Raises:
            FeishuAPIError: 飞书 API 调用失败
            FeishuAuthError: 飞书认证失败
        """
        from agents_hub.channels.feishu.session import feishu_session_manager

        # 过滤：只处理有消息的广播
        if not message:
            return

        synced = False

        # 查找所有绑定到此 group_chat_id 的飞书群
        for state in feishu_session_manager.iter_states():
            # 只同步群聊模式且匹配 group_chat_id 的状态
            if state.session_type != "group_chat" or state.session_id != group_chat_id:
                continue

            # 增量同步检查
            if message.get("id", 0) <= state.last_message_id:
                continue

            # 推送到飞书群（异常由调用方处理）
            await self.send_to_feishu(
                chat_id=state.feishu_chat_id,
                content=message.get("content", ""),
                agent_name=message.get("send_from", "unknown"),
            )

            # 更新同步状态
            feishu_session_manager.update_sync_state(state.feishu_chat_id, message.get("id", 0))
            synced = True

        # 仅在有状态变更时持久化
        if synced:
            feishu_session_manager.save()
