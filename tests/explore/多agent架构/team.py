# 创建team
from enum import Enum
from agents_hub.roles import Role,RoleManager,RoleType, role_manager
from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.roles.models import RoleConfig
from agents_hub.agent_bridge import AgentBridge, AgentResult
from pydantic import BaseModel, field_validator
from uuid import uuid4
from pathlib import Path
import asyncio
from dataclasses import dataclass,field
from datetime import datetime
# 物理存储路径
LOCAL_DATA_PATH = 'local_data'
"""
local_data/
agents/ <role_name> / <work_rook>
teams/ <team_name> / team.json # 存放小组成员
teams / <team_name> / <project_path> / <group_chat_id> / <group_chat_id>.jsonl # 存放group_chat的上下文
teams / <team_name> / <project_path> / <group_chat_id> / agent_session_id.json # 存放group_chat的上下文
teams / <team_name> / <project_path> / <group_chat_id> / memory / user_memory.md (暂不实现)
teams / <team_name> / <project_path> / <group_chat_id> / memory / compact_history.jsonl  

<group_chat_id>.jsonl 

{
    _type : "meta_data", last_compact_loc : ,create_at:,updata_at:
}
{
    agent_name : , content : ,timestamp:
}

agent_session_id.json:
{
    <agent_name> : {
        "main_session" : <session_id>,
        "btw_session" [<btw_session_id>] # by the way session , 可以是fork原会话或开启新的会话
    }
}

<project_path> 解析规则，传入的project_path str 将/ : \\ 转化为 -

"""
"""
compact_history.jsonl  
{create_at:,content : {summary : 对这段内容的一个简短内容说明 , <agentA> : 针对于agentA应该关注的信息的提取},<agentB>:针对于agentB应该关注的信息的提取...}
当前群聊历史的compact机制说明：1. summary是对于每个agent共有的 2. <agentA>是针对于于每个在compact存在的时候的专门压缩 3. 每次压缩只压缩从last_compact_loc 到最新的内容，不包括之前的内容
"""




"""
teams.json
[
    {
        team_name : "",
        members_list : ['',''] # 不包含manager，manager在一个团队中总是预定义的
    }
]

"""
import tiktoken,json
from typing import Any
# 暂时的辅助函数
def estimate_prompt_tokens(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> int:
    """Estimate prompt tokens with tiktoken.

    Counts all fields that providers send to the LLM: content, tool_calls,
    reasoning_content, tool_call_id, name, plus per-message framing overhead.
    """
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        parts: list[str] = []
        for msg in messages:
            content = msg.get("content")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        txt = part.get("text", "")
                        if txt:
                            parts.append(txt)

            tc = msg.get("tool_calls")
            if tc:
                parts.append(json.dumps(tc, ensure_ascii=False))

            rc = msg.get("reasoning_content")
            if isinstance(rc, str) and rc:
                parts.append(rc)

            for key in ("name", "tool_call_id"):
                value = msg.get(key)
                if isinstance(value, str) and value:
                    parts.append(value)

        if tools:
            parts.append(json.dumps(tools, ensure_ascii=False))

        per_message_overhead = len(messages) * 4
        return len(enc.encode("\n".join(parts))) + per_message_overhead
    except Exception:
        return 0

# ============================= 常量 ========================================
MAX_TOKEN = 1000



# ===========================团队设置（暂时），后续应该增加团队管理类=============
class Team(BaseModel):
    team_members_name : list[str]
    team_name : str = "default_team"  # 设置默认值
    @field_validator('team_members_name')
    @classmethod
    def validate_team_members(cls, team_members_name):
        if not team_members_name:
            raise ValueError('team_members 不能为空')
        # 验证role_name成立
        # 获取role 
        role_manager = RoleManager()
        role_info_list = role_manager.list_role_names()
        for role in team_members_name:
            if role not in role_info_list:
                raise ValueError(f"错误的role_name {role}")
        return team_members_name

# ========================== 消息传递 ========================================
# 采用方法每个agent一个私有消息队列，设置一个environment类记录每个agent的私有队列地址
class SessionType(Enum) :
    MAIN = "main"
    BTW = "btw"

@dataclass
class AgentsMessage:
    content : str
    send_from : str
    send_to : str
    session_type : SessionType = SessionType.MAIN
    timestamp : datetime = field(default_factory=datetime.now)

class MessageRouter:
    """用于agent之间，系统(user)与agent之间发送消息"""
    def __init__(self):
        self._agents_queue: dict[str, asyncio.Queue] = {}

    def register(self, name: str, queue: asyncio.Queue):
        self._agents_queue[name] = queue

    def unregister(self, name: str):
        self._agents_queue.pop(name, None)

    def send_message(self, send_from: str, send_to: str, content: str):
        message = AgentsMessage(
            content = content,
            send_from = send_from,
            send_to = send_to
        )
        self._validate_message(message)
        self._agents_queue[send_to].put_nowait(message)

    def _validate_message(self, message: AgentsMessage):
        if not message.content or not message.content.strip():
            raise ValueError("消息内容不能为空")
        if message.send_from not in self._agents_queue:
            raise ValueError(f"发送者 '{message.send_from}' 不在已注册的agent列表中")
        if message.send_to not in self._agents_queue:
            raise ValueError(f"接收者 '{message.send_to}' 不在已注册的agent列表中")
# ===========================针对于某个团队的群聊===============================

class GroupChatType(Enum):
    SEQUENCE_EXECUTE = "sequence_excute" # 流水线顺序执行
    MANAGER_ORCHESTRATE = "manager_orchestrate" # 由Team manager动态决定安排

# GroupChat
class GroupChat:
    """
    每个team可以创建多个群聊，这个群聊应该管理：
    1. session_id，管理与每个team member的session_id，并且这个session_id在整个会话期间不变
    2. 初始化各个member的状态，在群聊中回复
    3. 管理group_chat的内容 
    4. 先制作编排-子agent模式，workflow先不做
    """
    def __init__(self, team:Team, group_type:str,project_path:str,group_chat_id : str = str(uuid4())):
        self.members_session_id :dict ={} # members_session_id['role_name']
        self.group_chat_id = group_chat_id
        self.team_members_name = team.team_members_name
        self.works = {}
        self.manager = None
        self.project_path = None
        self.group_chat_context = GroupChatContext(group_chat_id,project_path)
        self.message_router = MessageRouter()
    async def _initialize_new_members(self):
        """
        初始化新成员（第一次进入群聊的成员）

        检查哪些成员没有 session_id，对这些成员执行初始化流程（打招呼）。

        注意：
        - 只在 GroupChat 初始化时通过 start() 调用
        - 如果项目已经启动一段时间后再添加新的 worker，不会自动执行此操作
        - 需要手动调用此方法来初始化新加入的成员
        """
        import asyncio

        # 获取需要初始化的成员（没有 session_id 的成员）
        new_members = []

        # 检查 manager 是否需要初始化
        if self.manager and self.manager.name not in self.group_chat_context.agent_session_id:
            new_members.append(self.manager)

        # 检查 workers 是否需要初始化
        for name, worker in self.works.items():
            if name not in self.group_chat_context.agent_session_id:
                new_members.append(worker)

        # 如果没有新成员，直接返回
        if not new_members:
            return

        # 定义打招呼函数
        async def start_conversation(agent:Agent):
            if agent.role_type == RoleType.LEADER:
                return await agent.execute(
                    f"你好，我是这个团队的boss,当前团队成员有{self.team_members_name},你将指挥他们完成我的任务。你使用一句话简单介绍一下自己"
                )
            else:
                other_members = [name for name in self.team_members_name if name != agent.name]
                return await agent.execute(
                    f"你好，我是这个团队的boss，当前团队有成员有{other_members},你的直属领导是{self.manager.name},你使用一句话简单介绍一下自己"
                )
        
        # 并发执行所有新成员的初始化
        results: list[AgentResult] = await asyncio.gather(
            *[start_conversation(member) for member in new_members]
        )

        # 保存结果
        for result in results:
            self.group_chat_context.update_agent_session_id(result)
            self.group_chat_context.group_chat_session.add_message(result)

        self.group_chat_context.save_agent_session_id()
        self.group_chat_context.save_group_chat_session()

    async def start(self):
        """
        启动群聊

        1. 初始化 manager
        2. 初始化所有 workers
        3. 对第一次进入群聊的成员执行初始化（打招呼）

        注意：此方法只在 GroupChat 创建时调用一次
        """
        # 1. 初始化team manager
        self.manager = Manager()

        # 2. 初始化team worker
        if not self.team_members_name:
            print("warning : 无团队成员")
            return

        role_manager = RoleManager()
        for role in self.team_members_name:
            self.works[role] = Worker(role_manager.get_role(role))

        # 3. 注册所有agent到message_router
        self.manager.message_router = self.message_router
        self.message_router.register(self.manager.name, self.manager.message_queue)
        for worker in self.works.values():
            worker.message_router = self.message_router
            self.message_router.register(worker.name, worker.message_queue)

        # 3. 初始化新成员（第一次会话的成员）
        await self._initialize_new_members()

    async def compact_history(self):
        """
        压缩群聊历史消息

        将未压缩的消息进行压缩，生成摘要和针对每个 agent 的专门信息
        """
        # 构建 agent 信息字典 {agent_name: work_scope}
        agent_info = {}

        # 添加 manager 信息
        if self.manager:
            manager_role = RoleManager().get_role(self.manager.name)
            agent_info[self.manager.name] = manager_role.get_role_config().description or "团队领导"

        # 添加 workers 信息
        role_manager = RoleManager()
        for name in self.works.keys():
            worker_role = role_manager.get_role(name)
            agent_info[name] = worker_role.get_role_config().description or "团队成员"

        await self.group_chat_context.compact_messages(agent_info)

    def get_agent_context(self, agent_name: str) -> str:
        """
        获取特定 agent 的上下文

        Args:
            agent_name: agent 名称

        Returns:
            格式化的上下文字符串，包括压缩历史和最新消息
        """
        return self.group_chat_context.get_agent_context(agent_name)

@dataclass
class AgentSessionInfo:
    """Agent 的会话信息"""
    main_session: str = ""  # 主会话 ID
    btw_session: list[str] = field(default_factory=list)  # by the way session 列表

@dataclass
class GroupChatSession:
    """用户管理群聊，对于每个agent的单聊和具体的内容由各自的平台管理"""
    group_chat_id : str = field(default_factory=lambda: str(uuid4()))
    name : str = field(default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d%H%M')}")
    messages : list[dict[str]] = field(default_factory=list)
    created_at : datetime = field(default_factory=datetime.now)
    updated_at : datetime = field(default_factory=datetime.now)
    last_compacted_loc : int = 0 # 上一次compact的位置

    def add_message(self, agent_result: AgentResult):
        self.messages.append({
            "agent_name" : agent_result.agent_name,"content":agent_result.text,"timestamp":agent_result.timestamp,"platform":agent_result.platform.value
        })
    def get_uncompact_messages(self):
        return self.messages[self.last_compacted_loc:]

class GroupChatContext:
    """
    负责
    1. 群聊对话保存
    2. 上下文压缩和群聊公共记忆提取，作为每个member运行时上下文加载的内容
    """
    def __init__(self,group_chat_id : str,project_path:str):
        self.group_chat_id = group_chat_id
        self.agent_session_id: dict[str, AgentSessionInfo] = {}  # agent_name -> AgentSessionInfo
        # 获取当前的聊天历史路径
        sanitized_path = self.sanitize_project_path(project_path)
        self.group_chat_session_path = f"{LOCAL_DATA_PATH}/teams/{sanitized_path}/{group_chat_id}"
        self.messages_file = f"{self.group_chat_session_path}/{group_chat_id}.jsonl"
        self.session_file = f"{self.group_chat_session_path}/agent_session_id.json" # agent_name : {main_session: , btw_session}
        self.compact_history_file = f"{self.group_chat_session_path}/memory/compact_history.jsonl"
        self.agent_session_id = self.get_agent_session_id()
        self.group_chat_session = self.load_group_chat_session()

    def load_group_chat_session(self)->GroupChatSession:
        """
        从文件加载群聊会话

        Returns:
            GroupChatSession: 加载的会话对象
        """
        import json
        import os

        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 如果文件不存在，返回新的会话
        if not os.path.exists(self.messages_file):
            return GroupChatSession(group_chat_id=self.group_chat_id)

        # 读取 jsonl 文件
        messages = []
        meta_data = None

        with open(self.messages_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    if data.get('_type') == 'meta_data':
                        meta_data = data
                    else:
                        messages.append(data)

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
        import json
        import os

        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 更新时间戳
        self.group_chat_session.updated_at = datetime.now()

        # 写入 jsonl 文件
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

    def get_agent_session_id(self) -> dict[str, AgentSessionInfo]:
        """
        获取 agent session id 映射

        Returns:
            dict: {agent_name: AgentSessionInfo}
        """
        import json
        import os

        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 如果文件不存在，返回空 dict
        if not os.path.exists(self.session_file):
            return {}

        # 读取 session 文件
        with open(self.session_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

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
        import json
        import os

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
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_agent_session_id(self, agent_result: AgentResult):
        """
        根据 AgentResult 更新 agent session id

        如果 agent 不存在，创建新的 AgentSessionInfo
        如果 session_id 不同于 main_session，添加到 btw_session

        Args:
            agent_result: Agent 执行结果
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

    async def compact_messages(self, agent_info: dict[str, str]):
        """
        压缩群聊消息历史

        从 last_compacted_loc 到最新的消息进行压缩，生成：
        1. summary: 所有 agent 共享的简短内容说明
        2. 为每个 agent 生成专门的压缩信息

        Args:
            agent_info: agent 信息字典，格式为 {agent_name: agent_work_scope}
        """
        import json
        import os

        # 获取未压缩的消息
        uncompacted_messages = self.group_chat_session.get_uncompact_messages()

        # 如果没有未压缩的消息，直接返回
        if not uncompacted_messages:
            return

        # 估算 token 数量
        token_count = estimate_prompt_tokens(uncompacted_messages)

        # 如果 token 数量小于 1000，不进行压缩
        if token_count < MAX_TOKEN:
            print(f"未压缩消息 token 数量为 {token_count}，小于阈值 {MAX_TOKEN}，跳过压缩")
            return

        print(f"未压缩消息 token 数量为 {token_count}，开始压缩...")

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
        compact_prompt = f"""请总结下面的对话记录，请严格按照要求输出 JSON。 对话记录： <message_list> {messages_text} </message_list> 参与者职责： {agent_descriptions} 任务：将上述对话总结为 JSON 格式，包含：1. summary: 整体对话的1-2句话总结 2. agent_specific: 为每个参与者提取与其职责相关的2-3句话关键信息 输出格式（只输出这个 JSON，不要有任何其他内容）： {{"summary": "...", "agent_specific": {{"{list(agent_info.keys())[0] if agent_info else 'agent_name'}": "...", ...}}}}"""

        # 调用 llm_call 进行压缩
        print(f"input prompt : {compact_prompt}")
        compact_result = await llm_call.execute(compact_prompt)
        compact_result_codex = await llm_call_codex.execute(compact_prompt)
        print(f"claude llm call : {compact_result}")
        print(f"codex llm call : {compact_result_codex}")
        # 解析 JSON 结果
        try:
            # 尝试提取 JSON（可能包含在 markdown 代码块中）
            result_text = compact_result.text.strip()
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()

            compact_data = json.loads(result_text)
            summary = compact_data.get("summary", "")
            agent_specific = compact_data.get("agent_specific", {})
        except json.JSONDecodeError as e:
            print(f"解析压缩结果失败: {e}")
            print(f"原始结果: {compact_result.text}")
            return

        # 构建压缩记录
        compact_record = {
            "create_at": datetime.now().isoformat(),
            "content": {
                "summary": summary,
                **agent_specific
            }
        }

        # 保存到 compact_history.jsonl
        os.makedirs(os.path.dirname(self.compact_history_file), exist_ok=True)

        with open(self.compact_history_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(compact_record, ensure_ascii=False) + '\n')

        # 更新 last_compacted_loc
        self.group_chat_session.last_compacted_loc = len(self.group_chat_session.messages)
        self.save_group_chat_session()

        print(f"压缩完成，已压缩 {len(uncompacted_messages)} 条消息")

    def load_compact_history(self) -> list[dict]:
        """
        加载压缩历史记录

        Returns:
            压缩历史记录列表
        """
        import json
        import os

        if not os.path.exists(self.compact_history_file):
            return []

        compact_history = []
        with open(self.compact_history_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    compact_history.append(json.loads(line))

        return compact_history

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
        import re
        # 将 / : \\ 替换为 -
        sanitized = re.sub(r'[/:\\]', '-', project_path)
        # 移除开头和结尾的 -
        sanitized = sanitized.strip('-')
        # 将连续的 - 合并为单个 -
        sanitized = re.sub(r'-+', '-', sanitized)
        return sanitized

# ============================= AgentContext 先不实现==================================
class AgentContext:
    """
    为Agent每次调用提供上下文
    主要实现对于groupchatsession有选择的作为agentcontext
    """
    def __init__(self,agent_name:str,group_chat_context:GroupChatContext):
        pass

# ============================= LLM / Agent调用 ==============================
agent_platform_client = AgentBridge()
def create_defaute_role():
    role_manager = RoleManager()
    role_manager.create_role(
            "Leader",
            AgentPlatform.CLAUDE,
            type=RoleType.LEADER,
            description="团队领导，负责任务分配、进度跟踪和技术决策"
        )
    role_manager.create_role(
            "llm_call",
            AgentPlatform.CLAUDE,
            type=RoleType.LEADER
        )
    role_manager.create_role(
            "llm_call_codex",
            AgentPlatform.CODEX,
            type=RoleType.LEADER
        )

create_defaute_role()


# ============================= LLM / Agent调用 ==============================

class Agent:
    def __init__(self,role:Role,group_chat_context:GroupChatContext | None = None):
        """"""
        self.role_config = role.get_role_config()
        self.name = self.role_config.name # 这里很奇怪，这些信息应该都直接作为类成员比较好啊，先不优化，role和agentbriged之后在优化
        self.role_type = self.role_config.role_type
        self.message_queue = asyncio.Queue() # 私有队列, 用户存放消息
        self.group_chat_context = group_chat_context
        self.agent_context = AgentContext(self.name , group_chat_context) # 暂时没有实现
        self.message_router: MessageRouter | None = None
        self._run = True
    def set_run(self,run:bool):
        """设置该agent是否工作，"""
        # 这个可能与后续性能优化有关，先不管
        self._run = run

    def send_message(self,send_to:str,content:str):
        self.message_router.send_message(self.name,send_to,content)    

    async def execute(self, prompt)->AgentResult: 
        """执行主会话（群聊）
        args : 
            prompt 发送给claude / codex 的信息
        """
        return await agent_platform_client.execute(prompt, self.role_config,self.main_session_id)
    
    async def btw_execute(self, prompt, session: str | None = None)->AgentResult:
        """执行单聊（by the way）"""
        print(f"Info : {self.name} 执行单聊 content:{prompt[:20]}")
        return await agent_platform_client.execute(prompt, self.role_config,session)
    
    @property
    def main_session_id(self):
        if self.group_chat_context.agent_session_id.get(self.name):
            if self.group_chat_context.agent_session_id[self.name].main_session:
                return self.group_chat_context.agent_session_id[self.name].main_session
            else:
                print(f"warning : {self.name}在当前群聊中无历史记录") # 这里的print 需要替换为具体的logger
        else :
            print(f"warning : 当前群聊无{self.name}的main session记录 [ 如果是初始化会话 忽略改警告]")
        return None
    async def _process_message(self,msg:AgentsMessage)->AgentResult:
        """
        处理消息
        args:
            msg : AgentsMessage 
        """
        if msg.session_type == SessionType.MAIN:
            return await self.execute(msg.content)
        else:
            return await self.btw_execute(msg.content)
    async def run(self):
      """持续监听私有队列，处理收到的消息"""
      while self._run:
        msg = await self.message_queue.get()
        result = await self._process_message(msg)
        # 处理 result，比如发回群聊或触发下一步是
       

class Manager(Agent):
    def __init__(self):
        super().__init__(RoleManager().get_role("Leader"))
        pass
    pass
class Worker(Agent):
    pass

class LLMCall(Agent):
    def __init__(self):
        # 暂时这么写临时的非角色的llm调用，llm_call不进入groupchat,可临时用于需要llm调用的场景
        super().__init__(RoleManager().get_role("llm_call"))
        pass
llm_call = LLMCall()
llm_call_codex = Agent(RoleManager().get_role("llm_call_codex"))


# =============================== TooL ==========================
# 【架构说明】agents之间如何交流（call_agent 是跨 agent 通信的核心入口）
#
# 完整调用链路：
#   Agent A 的 LLM（claude/codex）
#     → tool_use: call_agent(send_from="A", send_to="B", content="...")
#       → agentshub MCP Server 接收 tool call
#         → call_agent()
#           → MessageRouter.send_message()
#             → 投递到目标 Agent B 的私有 message_queue
#               → Agent B 的 run loop 取出消息并处理
#
# 【设计要点】
# 1. call_agent 是 LLM 可调用的工具（MCP tool），不是代码层面的 API
#    - Agent 的 LLM 决定何时调用、发给谁、发什么内容
#    - 类似 CrewAI 的 DelegateWorkTool、AutoGen 的 handoff、deer-flow 的 task_tool
#
# 2. MessageRouter 负责路由，不关心消息内容
#    - 验证 send_from/send_to 是否已注册
#    - 投递到目标队列
#    - 未来可扩展：topic 广播、消息过滤、优先级等
#
# 3. group_chat 参数的传递方式（当前是探索版本，正式版本需要调整）
#    - 当前：作为参数显式传入
#    - 正式版本建议：通过全局注册表（如 GroupChatRegistry）按 group_chat_id 获取
#      因为 MCP tool 调用时无法直接传入对象实例，需要通过 ID 查找
#
# 【正式版本 TODO】
# - group_chat 参数改为 group_chat_id，从全局注册表查找
# - call_agent 需要注册为 MCP tool（在 agents_hub MCP server 中声明 tool schema）
# - 返回值需要适配 MCP tool 的响应格式（当前返回 str 是简化版本）

def call_agent(send_from: str, send_to: str, content: str, group_chat: GroupChat) -> str:
    """
    call_agent将会作为agentshub MCP工具的一个部分，用于codex/claude code可以通过agentshub与别的agent对话

    args：
        send_from : 填写发送者的名称
        send_to : 你要发送给谁
        content : 发送的内容，可以是询问的问题，也可以是委派的任务
        group_chat : 当前群聊实例（正式版本改为 group_chat_id，从注册表获取）
    """
    router = group_chat.message_router
    try:
        router.send_message(send_from, send_to, content)
        return f"消息已发送: {send_from} -> {send_to}"
    except ValueError as e:
        return f"发送失败: {e}"
    


async def main():
    role_manager = RoleManager()
    role_manager.create_role("小李",AgentPlatform.CLAUDE,type = RoleType.TEAM_MEMBER)
    role_manager.create_role("小赵",AgentPlatform.CODEX,type = RoleType.TEAM_MEMBER)
    role_manager.create_role("Leader",AgentPlatform.CLAUDE,type = RoleType.LEADER)
    role_manager.create_role("llm_call",AgentPlatform.CODEX,type = RoleType.LEADER)
    team_member_list = ["小李","小赵"]
    team = Team(team_name= "测试",team_members_name=team_member_list)
    group_chat = GroupChat(team,GroupChatType.MANAGER_ORCHESTRATE,project_path='D:/desktop/软件开发/agents-hub')
    await group_chat.start()

if __name__ == "__main__":
    asyncio.run(main())
