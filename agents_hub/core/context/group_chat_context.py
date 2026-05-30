"""
群聊上下文

负责群聊业务逻辑：消息管理、session 管理、上下文压缩。
"""

from datetime import datetime

from agents_hub.agent_bridge import agent_platform_client
from agents_hub.core.foundation import MAX_TOKEN, StateError

from .group_chat_repository import GroupChatRepository
from .group_chat_session import AgentSessionInfo, GroupChatSession


class GroupChatContext:
    """
    群聊上下文管理器

    职责：
    1. 业务逻辑：消息管理、session 管理、上下文压缩
    2. 调用 Repository 进行持久化
    """

    def __init__(self, group_chat_id: str, project_path: str):
        self.group_chat_id = group_chat_id
        self.repository = GroupChatRepository(group_chat_id, project_path)

        # 数据
        self.group_chat_session: GroupChatSession | None = None
        self.agent_session_id: dict[str, AgentSessionInfo] = {}

    async def load(self):
        """加载数据"""
        self.group_chat_session = await self.repository.load_group_chat_session()
        self.agent_session_id = await self.repository.load_agent_session_state()

    # ==================== 消息管理 ====================

    async def add_message(self, agent_result):
        """
        添加消息并保存

        Args:
            agent_result: Agent 执行结果（AgentResult）
                需要包含: agent_name, text, timestamp, platform
        """
        if self.group_chat_session is None:
            raise StateError("GroupChatSession 未加载，请先调用 load()")
        self.group_chat_session.add_message(agent_result)
        # TODO 调用websocket,让前端更新显示
        await self.repository.save_group_chat_session(self.group_chat_session)

    # ==================== Agent Session 管理 ====================

    async def update_agent_session_id(self, agent_result):
        """
        根据 AgentResult 更新 agent session id 并保存

        如果 agent 不存在，创建新的 AgentSessionInfo
        如果 session_id 不同于 main_session，添加到 btw_session

        Args:
            agent_result: Agent 执行结果（AgentResult）
                需要包含: agent_name, session_id
        """
        agent_name = agent_result.agent_name
        session_id = agent_result.session_id

        # 如果 agent 不存在，创建新的
        if agent_name not in self.agent_session_id:
            self.agent_session_id[agent_name] = AgentSessionInfo(
                main_session=session_id, btw_session=[]
            )
        else:
            session_info = self.agent_session_id[agent_name]

            # 如果是第一次设置 main_session
            if not session_info.main_session:
                session_info.main_session = session_id
            # 如果 session_id 不同于 main_session，且不在 btw_session 中
            elif (
                session_id != session_info.main_session
                and session_id not in session_info.btw_session
            ):
                session_info.btw_session.append(session_id)

        # 保存到文件
        await self.repository.save_agent_session_state(self.agent_session_id)

    # ==================== 压缩历史管理 ====================

    async def load_compact_history(self) -> list[dict]:
        """
        加载压缩历史记录

        Returns:
            压缩历史记录列表
        """
        return await self.repository.load_compact_history()

    async def compact_messages(self, agent_info: dict[str, str]):
        """
        压缩群聊消息历史

        从 last_compacted_loc 到最新的消息进行压缩，生成：
        1. summary: 所有 agent 共享的简短内容说明
        2. 为每个 agent 生成专门的压缩信息

        Args:
            agent_info: agent 信息字典，格式为 {agent_name: agent_work_scope}

        Raises:
            CompactionError: 压缩失败
        """
        import json as _json

        from agents_hub.core.foundation import CompactionError

        # 获取未压缩的消息
        if self.group_chat_session is None:
            raise StateError("GroupChatSession 未加载，请先调用 load()")
        uncompacted_messages = self.group_chat_session.get_uncompact_messages()

        # 如果没有未压缩的消息，直接返回
        if not uncompacted_messages:
            return

        # 估算 token 数量（粗略：4 个字符 ≈ 1 token）
        total_chars = sum(len(msg.get("content", "")) for msg in uncompacted_messages)
        estimated_tokens = total_chars // 4

        if estimated_tokens < MAX_TOKEN:
            print(f"未压缩消息估算 token 数量为 {estimated_tokens}，小于阈值 {MAX_TOKEN}，跳过压缩")
            return

        print(f"未压缩消息估算 token 数量为 {estimated_tokens}，开始压缩...")

        # 构建消息历史文本
        messages_text = "\n".join(
            [f"[{msg['agent_name']}]: {msg['content']}" for msg in uncompacted_messages]
        )

        # 构建 agent 信息描述
        agent_descriptions = "\n".join([f"- {name}: {scope}" for name, scope in agent_info.items()])

        # 一次性生成 summary 和所有 agent 的专门信息
        first_agent = list(agent_info.keys())[0] if agent_info else "agent_name"
        compact_prompt = f"""请总结下面的对话记录，请严格按照要求输出 JSON。

对话记录：
<message_list>
{messages_text}
</message_list>

参与者职责：
{agent_descriptions}

任务：将上述对话总结为 JSON 格式，包含：
1. summary: 整体对话的1-2句话总结
2. agent_specific: 为每个参与者提取与其职责相关的2-3句话关键信息

输出格式（只输出这个 JSON，不要有任何其他内容）：
{{"summary": "...", "agent_specific": {{"{first_agent}": "...", ...}}}}"""

        # 调用 bare_claude_call 进行压缩
        try:
            result = await agent_platform_client.bare_claude_call(compact_prompt)
        except Exception as e:
            raise CompactionError(reason=f"LLM 调用失败: {e}") from e

        # 解析 JSON 响应
        try:
            # 提取 JSON（LLM 可能会在 JSON 前后添加其他文本）
            text = result.text.strip()
            # 尝试直接解析
            compact_data = _json.loads(text)
        except _json.JSONDecodeError:
            # 尝试从文本中提取 JSON
            import re

            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                try:
                    compact_data = _json.loads(json_match.group())
                except _json.JSONDecodeError as e:
                    raise CompactionError(reason=f"LLM 返回的 JSON 解析失败: {e}") from e
            else:
                raise CompactionError(reason=f"LLM 返回中未找到 JSON: {text[:200]}") from None

        # 构建压缩记录（对齐 compact_history.jsonl 格式）
        content = {"summary": compact_data.get("summary", "")}
        content.update(compact_data.get("agent_specific", {}))
        compact_record = {
            "create_at": datetime.now().isoformat(),
            "content": content,
        }

        # 加载已有压缩历史，追加新记录，保存
        compact_history = await self.repository.load_compact_history()
        compact_history.append(compact_record)
        await self.repository.save_compact_history(compact_history)

        # 更新 last_compacted_loc
        self.group_chat_session.last_compacted_loc = len(self.group_chat_session.messages)
        await self.repository.save_group_chat_session(self.group_chat_session)
