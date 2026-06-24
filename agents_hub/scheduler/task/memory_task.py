"""记忆更新任务

负责单个群聊的记忆收集执行。
通过 agent_platform_client.execute 调用记忆助手 Agent。
执行完成后裁剪 history.jsonl 保留最近 1000 条。
"""

import logging
from pathlib import Path

from agents_hub.agent_bridge import agent_platform_client
from agents_hub.config.config import config
from agents_hub.roles import RoleManager

logger = logging.getLogger(__name__)

HISTORY_MAX_LINES = 1000


def trim_history_jsonl(history_path: Path, max_lines: int = HISTORY_MAX_LINES) -> None:
    """裁剪 history.jsonl，保留最近 max_lines 条记录

    Args:
        history_path: history.jsonl 文件路径
        max_lines: 最大保留行数
    """
    if not history_path.exists():
        return

    try:
        lines = history_path.read_text(encoding="utf-8").strip().splitlines()
        if len(lines) > max_lines:
            trimmed = lines[-max_lines:]
            history_path.write_text("\n".join(trimmed) + "\n", encoding="utf-8")
            logger.info("history.jsonl 已裁剪: %d → %d 条", len(lines), max_lines)
    except OSError as e:
        logger.warning("裁剪 history.jsonl 失败: %s", e)


def _build_memory_prompt(group_chat_id: str, last_updated: str | None) -> str:
    """构建记忆助手的 prompt

    Args:
        group_chat_id: 群聊ID
        last_updated: 上次更新时间（ISO 8601 格式）

    Returns:
        构建好的 prompt 字符串
    """
    task = f"请处理群聊 {group_chat_id} 的记忆收集。"
    if last_updated:
        task += f"上次更新时间：{last_updated}"
    else:
        task += "这是首次执行，需要处理所有历史消息。"
    return f"{task}\n\n[系统提示] 你的 agent token 是: {config.assistant_token}"


class MemoryTask:
    """记忆更新任务"""

    def __init__(self) -> None:
        self._role_manager = RoleManager()

    async def execute(self, group_chat_id: str, last_updated: str | None) -> str:
        """执行单个群聊的记忆更新

        Args:
            group_chat_id: 群聊ID
            last_updated: 上次更新时间（ISO 8601 格式）

        Returns:
            执行结果文本（成功时为成功消息，失败时为错误描述）

        Raises:
            不抛出异常，内部捕获并返回错误描述
        """
        logger.info("开始执行记忆收集: group_chat_id=%s", group_chat_id)
        try:
            # 1. 获取记忆助手的 RoleConfig
            role = self._role_manager.get_role(config.default_memory_assistant_name)
            role_config = role.get_role_config()

            # 2. 构建 prompt
            prompt = _build_memory_prompt(group_chat_id, last_updated)

            # 3. 执行记忆助手（非流式）
            result = await agent_platform_client.execute(
                prompt=prompt,
                config=role_config,
            )

            logger.info("记忆收集完成: group_chat_id=%s", group_chat_id)

            # 裁剪 history.jsonl
            history_path = config.memory_path / "agents_hub_history" / "history.jsonl"
            trim_history_jsonl(history_path)

            return result.text

        except Exception as e:
            logger.error("群聊 %s 记忆收集失败: %s", group_chat_id, str(e), exc_info=True)
            return f"执行失败: {str(e)}"
