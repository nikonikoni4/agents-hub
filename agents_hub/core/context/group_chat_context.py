"""
群聊上下文

负责群聊对话保存、上下文压缩和群聊公共记忆提取。
"""
import json
import os
import re
from datetime import datetime

from agents_hub.core.foundation import LOCAL_DATA_PATH, MAX_TOKEN, FileSystemError
from .group_chat_session import GroupChatSession, AgentSessionInfo


class GroupChatContext:
    """
    群聊上下文管理器

    职责：
    1. 群聊对话保存
    2. 上下文压缩和群聊公共记忆提取
    3. 作为每个 member 运行时上下文加载的内容
    """

    def __init__(self, group_chat_id: str, project_path: str):
        self.group_chat_id = group_chat_id
        self.agent_session_id: dict[str, AgentSessionInfo] = {}  # agent_name -> AgentSessionInfo

        # 获取当前的聊天历史路径
        sanitized_path = self.sanitize_project_path(project_path)
        self.group_chat_session_path = f"{LOCAL_DATA_PATH}/teams/{sanitized_path}/{group_chat_id}"
        self.messages_file = f"{self.group_chat_session_path}/{group_chat_id}.jsonl"
        self.session_file = f"{self.group_chat_session_path}/agent_session_id.json"
        self.compact_history_file = f"{self.group_chat_session_path}/memory/compact_history.jsonl"

        # 加载数据
        self.agent_session_id = self.get_agent_session_id()
        self.group_chat_session = self.load_group_chat_session()

    # ==================== 文件路径处理 ====================

    @staticmethod
    def sanitize_project_path(project_path: str) -> str:
        """
        将 project_path 转换为安全的存储路径名称。
        将 / : \\ 等 Windows 文件夹命名非法字符转化为 -

        Args:
            project_path: 原始项目路径字符串

        Returns:
            转换后的安全路径名称
        """
        # 将 / : \\ 替换为 -
        sanitized = re.sub(r'[/:\\]', '-', project_path)
        # 移除开头和结尾的 -
        sanitized = sanitized.strip('-')
        # 将连续的 - 合并为单个 -
        sanitized = re.sub(r'-+', '-', sanitized)
        return sanitized

    # ==================== GroupChatSession 持久化 ====================

    def load_group_chat_session(self) -> GroupChatSession:
        """
        从文件加载群聊会话

        Returns:
            GroupChatSession: 加载的会话对象
        """
        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 如果文件不存在，返回新的会话
        if not os.path.exists(self.messages_file):
            return GroupChatSession(group_chat_id=self.group_chat_id)

        # 读取 jsonl 文件
        messages = []
        meta_data = None

        try:
            with open(self.messages_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        if data.get('_type') == 'meta_data':
                            meta_data = data
                        else:
                            messages.append(data)
        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=self.messages_file,
                reason=str(e)
            )

        # 构建 GroupChatSession
        session = GroupChatSession(group_chat_id=self.group_chat_id)
        session.messages = messages

        if meta_data:
            session.last_compacted_loc = meta_data.get('last_compact_loc', 0)
            if 'created_at' in meta_data:
                session.created_at = datetime.fromisoformat(meta_data['created_at'])
            if 'updated_at' in meta_data:
                session.updated_at = datetime.fromisoformat(meta_data['updated_at'])
            if 'name' in meta_data:
                session.name = meta_data['name']

        return session

    def save_group_chat_session(self):
        """将 GroupChatSession 保存到 <group_chat_id>.jsonl"""
        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 更新时间戳
        self.group_chat_session.updated_at = datetime.now()

        # 写入 jsonl 文件
        try:
            with open(self.messages_file, 'w', encoding='utf-8') as f:
                # 写入 meta_data
                meta_data = {
                    '_type': 'meta_data',
                    'last_compact_loc': self.group_chat_session.last_compacted_loc,
                    'created_at': self.group_chat_session.created_at.isoformat(),
                    'updated_at': self.group_chat_session.updated_at.isoformat(),
                    'name': self.group_chat_session.name
                }
                f.write(json.dumps(meta_data, ensure_ascii=False) + '\n')

                # 写入消息
                for msg in self.group_chat_session.messages:
                    f.write(json.dumps(msg, ensure_ascii=False) + '\n')
        except OSError as e:
            raise FileSystemError(
                operation="write",
                path=self.messages_file,
                reason=str(e)
            )

    # ==================== Agent Session ID 管理 ====================

    def get_agent_session_id(self) -> dict[str, AgentSessionInfo]:
        """
        获取 agent session id 映射

        Returns:
            dict: {agent_name: AgentSessionInfo}
        """
        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 如果文件不存在，返回空 dict
        if not os.path.exists(self.session_file):
            return {}

        # 读取 session 文件
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=self.session_file,
                reason=str(e)
            )

        # 转换为 AgentSessionInfo 对象
        result = {}
        for agent_name, session_data in data.items():
            result[agent_name] = AgentSessionInfo(
                main_session=session_data.get('main_session', ''),
                btw_session=session_data.get('btw_session', [])
            )
        return result

    def save_agent_session_id(self):
        """
        保存 agent session id 映射到文件

        将 self.agent_session_id 保存到 agent_session_id.json
        """
        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 转换为可序列化的字典
        data = {}
        for agent_name, session_info in self.agent_session_id.items():
            data[agent_name] = {
                'main_session': session_info.main_session,
                'btw_session': session_info.btw_session
            }

        # 写入文件
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            raise FileSystemError(
                operation="write",
                path=self.session_file,
                reason=str(e)
            )

    def update_agent_session_id(self, agent_result):
        """
        根据 AgentResult 更新 agent session id

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
                main_session=session_id,
                btw_session=[]
            )
        else:
            session_info = self.agent_session_id[agent_name]

            # 如果是第一次设置 main_session
            if not session_info.main_session:
                session_info.main_session = session_id
            # 如果 session_id 不同于 main_session，且不在 btw_session 中
            elif session_id != session_info.main_session and session_id not in session_info.btw_session:
                session_info.btw_session.append(session_id)

    # ==================== 压缩历史管理 ====================

    def load_compact_history(self) -> list[dict]:
        """
        加载压缩历史记录

        Returns:
            压缩历史记录列表
        """
        if not os.path.exists(self.compact_history_file):
            return []

        compact_history = []
        try:
            with open(self.compact_history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        compact_history.append(json.loads(line))
        except OSError as e:
            raise FileSystemError(
                operation="read",
                path=self.compact_history_file,
                reason=str(e)
            )

        return compact_history

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
        from agents_hub.core.foundation import CompactionError

        # 获取未压缩的消息
        uncompacted_messages = self.group_chat_session.get_uncompact_messages()

        # 如果没有未压缩的消息，直接返回
        if not uncompacted_messages:
            return

        # 估算 token 数量
        # TODO: 需要实现 estimate_prompt_tokens 函数
        # 暂时使用简单的字符数估算
        total_chars = sum(len(msg.get('content', '')) for msg in uncompacted_messages)
        estimated_tokens = total_chars // 4  # 粗略估算：4 个字符 ≈ 1 token

        # 如果 token 数量小于阈值，不进行压缩
        if estimated_tokens < MAX_TOKEN:
            print(f"未压缩消息估算 token 数量为 {estimated_tokens}，小于阈值 {MAX_TOKEN}，跳过压缩")
            return

        print(f"未压缩消息估算 token 数量为 {estimated_tokens}，开始压缩...")

        # 构建消息历史文本
        messages_text = "\n".join([
            f"[{msg['agent_name']}]: {msg['content']}"
            for msg in uncompacted_messages
        ])

        # 构建 agent 信息描述
        agent_descriptions = "\n".join([
            f"- {name}: {scope}"
            for name, scope in agent_info.items()
        ])

        # 一次性生成 summary 和所有 agent 的专门信息
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
{{"summary": "...", "agent_specific": {{"{list(agent_info.keys())[0] if agent_info else 'agent_name'}": "...", ...}}}}"""

        # TODO: 调用 LLM 进行压缩
        # 这里需要依赖 agent 层的 LLMCall，但会造成循环依赖
        # 解决方案：将 compact_messages 的 LLM 调用部分移到 orchestration 层
        # 或者通过依赖注入的方式传入 LLM 调用函数
        raise CompactionError(
            reason="compact_messages 需要 LLM 调用，但会造成循环依赖。"
                   "需要将此方法移到 orchestration 层或使用依赖注入。"
        )

    # ==================== 上下文获取 ====================

    def get_agent_context(self, agent_name: str) -> str:
        """
        获取特定 agent 的上下文

        包括：
        1. 所有压缩历史的 summary
        2. 该 agent 的专门压缩信息
        3. 未压缩的最新消息

        Args:
            agent_name: agent 名称

        Returns:
            格式化的上下文字符串
        """
        context_parts = []

        # 1. 加载压缩历史
        compact_history = self.load_compact_history()

        if compact_history:
            context_parts.append("=== 历史消息摘要 ===")
            for record in compact_history:
                content = record['content']
                context_parts.append(f"\n[总体]: {content['summary']}")
                if agent_name in content:
                    context_parts.append(f"[针对你]: {content[agent_name]}")

        # 2. 添加未压缩的最新消息
        uncompacted_messages = self.group_chat_session.get_uncompact_messages()
        if uncompacted_messages:
            context_parts.append("\n=== 最新消息 ===")
            for msg in uncompacted_messages:
                context_parts.append(f"[{msg['agent_name']}]: {msg['content']}")

        return "\n".join(context_parts)

