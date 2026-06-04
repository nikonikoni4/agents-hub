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
teams / <team_name> / <project_path> / <group_chat_id> / agent_member.json # 存放group_chat的上下文
teams / <team_name> / <project_path> / <group_chat_id> / memory / user_memory.md (暂不实现)
teams / <team_name> / <project_path> / <group_chat_id> / memory / compact_history.jsonl  

<group_chat_id>.jsonl 

{
    _type : "meta_data", last_compact_loc : ,create_at:,updata_at:
}
{
    agent_name : , content : ,timestamp:
}

agent_member.json:
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

class MessageType(Enum):
    """message传递的类型，会依据这个类型来判断agent会不会默认回复"""
    TASK = "task"           # 需要回复的任务
    NOTIFICATION = "notification"  # 不需要回复的通知

@dataclass
class AgentMessage:
    content : str
    send_from : str
    send_to : str
    session_type : SessionType = SessionType.MAIN # 用于判断是单聊还是群聊
    message_type : MessageType = MessageType.NOTIFICATION # 用于判读系统是否需要自动回复被调用agent回复的信息
    timestamp : datetime = field(default_factory=datetime.now)


class MessageRouter:
    """用于agent之间，系统(user)与agent之间发送消息"""
    def __init__(self):
        self._agents_queue: dict[str, asyncio.Queue] = {}

    def register(self, name: str, queue: asyncio.Queue):
        self._agents_queue[name] = queue

    def unregister(self, name: str):
        self._agents_queue.pop(name, None)

    def send_message(self, message: AgentMessage):
        self._validate_message(message)
        self._agents_queue[message.send_to].put_nowait(message)

    def _validate_message(self, message: AgentMessage):
        if not message.content or not message.content.strip():
            raise ValueError("消息内容不能为空")
        if message.send_from not in self._agents_queue:
            raise ValueError(f"发送者 '{message.send_from}' 不在已注册的agent列表中")
        if message.send_to not in self._agents_queue:
            raise ValueError(f"接收者 '{message.send_to}' 不在已注册的agent列表中")
# ========================== agent call 管理 ========================================
# agent call的生命周期说明，agent call是用来：1. 查询任务状态 2. 记录agent沟通过程 3. 承载需要传递给下游AgentMessage的参数
# 生命周期
# 1. 创建 ： 1） MCP Tool 调用，call_agent时，会创建AgentCall，承载激活另一个agent的参数
#           2）若messageType 是 task类型，在完成任务之后系统主动返回信息给 发送给他任务的agent
#           3） user在群聊种发信息@agent时会创建agent call
# 2. 修改 ： 1. 创建时  pending
#            2. execute 之前 running
#           3. 运行完成之后 判断是否执行成功 ！！[如何判断成功当前先不考虑]，只通过try expect 先暂时用来判断是否成功，因为对于CLI的相关失败处理还不清楚，后续测试的时候再补充这部分内容
#               若try 成功 则 COMPLETED
#               若 进入expect 则FAILED
#               若执行时间超过，预定的timetout阈值，则TIMEOUT
#                调用这个的agent手动停止，则 STOP
# 3. 删除    为了减小内存占用，需要删除无用的调用信息 [删除如何判断为未确认，先不实现]
#            删除依赖于messageType

class CallStatus(Enum):
    """agent调用状态跟踪"""
    PENDING = "pending"      # 已创建，等待执行
    RUNNING = "running"      # 正在执行
    COMPLETED = "completed"  # 执行完成
    FAILED = "failed"        # 执行失败
    TIMEOUT = "timeout"      # 执行超时
    # STOP = "stop"           # [stop]标志位暂时不实现，未来可能需要调用方手动停止被调用方的工作，现在不增加这个机制

@dataclass
class AgentCall:
    send_from: str
    send_to: str
    content: str
    message_type: MessageType
    call_id: str = field(default_factory=lambda: str(uuid4())[:8])
    status: CallStatus = CallStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: AgentResult | None = None  # 执行结果
    error: str | None = None           # 错误信息
    business_task_id: str | None = None  # 关联的业务任务 ID（可选）
    timeout_seconds :int| None = None  # 考虑到agent平台执行比较慢的原因，所以默认是无timeout

    def is_timeout(self) -> bool:
        """判断是否超时"""
        if self.status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT):
            return False
        
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.timeout_seconds
    
    def can_be_deleted(self) -> bool:
        # TODO，未确认删除逻辑
        return False


class AgentCallManager:
    """统一管理所有跨 Agent 的异步调用"""
    
    def __init__(self):
        self._calls: dict[str, AgentCall] = {}  # call_id -> AgentCall
        # TODO
        # 1. 与util统一的logger，但是agentCall单独保存一份，需要一个logger的变体类独立用于AgentCallManager
        # 2. 轮询线程，用于判断是否需要删除已经完成的AgentCall
    
    def create_call(self, send_from: str, send_to: str, content: str, message_type:MessageType,timeout_seconds:int,
                    business_task_id: str | None = None) -> AgentCall:
        """创建新调用，返回 call_id"""
        call = AgentCall(
            send_from=send_from,
            send_to=send_to,
            content=content,
            message_type=message_type,
            business_task_id=business_task_id
        )
        self._calls[call.call_id] = call
        return call
    

    def get_call(self, call_id: str) -> AgentCall | None:
        """获取调用详情"""
        return self._calls.get(call_id)
    
    def update_status(self, call_id: str, status: CallStatus):
        """更新调用状态"""
        if call := self._calls.get(call_id):
            call.status = status
            if status == CallStatus.RUNNING:
                call.started_at = datetime.now()
            elif status in (CallStatus.COMPLETED, CallStatus.FAILED):
                call.completed_at = datetime.now()
    
    def set_result(self, call_id: str, result: AgentResult):
        """设置调用结果"""
        if call := self._calls.get(call_id):
            call.result = result
            call.status = CallStatus.COMPLETED
            call.completed_at = datetime.now()
    
    def set_error(self, call_id: str, error: str):
        """设置调用错误"""
        if call := self._calls.get(call_id):
            call.error = error
            call.status = CallStatus.FAILED
            call.completed_at = datetime.now()
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
        self.agent_call_manager = AgentCallManager()
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
        self.agent_member_file = f"{self.group_chat_session_path}/agent_member.json" # agent_name : {main_session: , btw_session}
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
        if not os.path.exists(self.agent_member_file):
            return {}

        # 读取 session 文件
        with open(self.agent_member_file, 'r', encoding='utf-8') as f:
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

        将 self.agent_session_id 保存到 agent_member.json
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
        with open(self.agent_member_file, 'w', encoding='utf-8') as f:
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

    def send_message_to_agent(self,send_to:str,content:str):
        message = AgentMessage(
            send_from=self.name, 
            send_to=send_to, 
            content=content,
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION
            )
        self.message_router.send_message(message)

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
    async def _process_message(self,msg:AgentMessage)->AgentResult:
        """
        处理消息
        args:
            msg : AgentMessage 
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

class GroupChatManager:
    """管理GroupChat"""
    _group_chats :dict[str,GroupChat] = {}
    def register(self,group_chat_id :str,group_chat:GroupChat):
        if group_chat_id and isinstance(group_chat_id,str) and group_chat and isinstance(group_chat,GroupChat):
            self._group_chats[group_chat_id] = group_chat
        else:
            raise ValueError(f"无效的 {group_chat_id}或 group_chat")
    def get_group_chat(self,group_chat_id)->GroupChat:
        if self._group_chats.get(group_chat_id):
            return self._group_chats.get(group_chat_id)
        else:
            raise  ValueError(f"无效的 {group_chat_id}")
    def unregister(self,gourp_chat_id):
        pass
group_chat_manager = GroupChatManager()
def call_agent(group_chat_id : str , send_from: str, send_to: str, content: str, need_response:bool,timeout_seconds : int | None  = None) -> str:
    """
    call_agent将会作为agentshub MCP工具的一个部分，用于codex/claude code可以通过agentshub与别的agent对话

    args：
        send_from : 填写发送者的名称
        send_to : 你要发送给谁
        content : 发送的内容，可以是询问的问题，也可以是委派的任务
        need_response : 是否需要被调用的agent回复
        timeout : 超时阈值，单位秒
    """
    
    try:
        # 1. 获取group chat
        group_chat = group_chat_manager.get_group_chat(group_chat_id)
        # 2. 创建AgentCall
        call:AgentCall = group_chat.agent_call_manager.create_call(
            send_from=send_from,
            send_to=send_to,
            content=content,
            message_type=MessageType.TASK if need_response else MessageType.NOTIFICATION,
            timeout_seconds=timeout_seconds
        )
        # 3. 通过MessageRouter发送消息
        group_chat.message_router.send_message(
            AgentMessage(send_from=call.send_from, send_to=call.send_to, content=call.content, message_type=call.message_type)
        )
    except Exception  as e:
        return e # 注意这里是为了方便简单的写法，真实的写法是需要定义专门的exception 在这里捕获，然后返回具体的错误

    


async def main():
    role_manager = RoleManager()
    role_manager.create_role("小李",AgentPlatform.CLAUDE,type = RoleType.TEAM_MEMBER)
    role_manager.create_role("小赵",AgentPlatform.CODEX,type = RoleType.TEAM_MEMBER)
    role_manager.create_role("Leader",AgentPlatform.CLAUDE,type = RoleType.LEADER)
    # role_manager.create_role("llm_call",AgentPlatform.CODEX,type = RoleType.LEADER)
    team_member_list = ["小李","小赵"]
    team = Team(team_name= "测试",team_members_name=team_member_list)
    group_chat = GroupChat(team,GroupChatType.MANAGER_ORCHESTRATE,project_path='D:/desktop/软件开发/agents-hub')
    await group_chat.start()

if __name__ == "__main__":
    asyncio.run(main())


# ================================================================================================
# 未完成内容、潜在问题和需要确认的事项汇总
# ================================================================================================

# ==================== 1. GroupChat 消息添加与 WebSocket 推送 ====================
# 【问题】GroupChat 中缺少消息添加的统一入口和 WebSocket 推送机制
# 【位置】GroupChat 类（第 281-418 行）
# 【说明】
#   - 当前 GroupChat 只在 _initialize_new_members() 中调用了 group_chat_context.group_chat_session.add_message()
#   - 但在正常的消息流转中（Agent.run() 处理消息后），没有统一的地方将消息添加到 GroupChat
#   - 缺少 WebSocket 推送机制：当消息添加到 group_chat 时，应该通过 WebSocket 发送给前端更新显示
# 【需要实现】
#   1. 在 GroupChat 中添加 add_message_and_notify() 方法：
#      - 接收 AgentResult
#      - 调用 self.group_chat_context.group_chat_session.add_message(result)
#      - 调用 self.group_chat_context.save_group_chat_session()
#      - 通过 WebSocket 推送消息给前端（需要 WebSocket 管理器）
#   2. 在 Agent.run() 中调用这个方法（见下方 Agent.run() 的问题）
#   3. 需要实现 WebSocketManager 类来管理 WebSocket 连接和消息推送

# ==================== 2. Agent.run() 方法未完成 ====================
# 【问题】Agent.run() 方法的消息处理逻辑不完整
# 【位置】Agent.run() 方法（第 879-885 行）
# 【当前代码】
#   async def run(self):
#       """持续监听私有队列，处理收到的消息"""
#       while self._run:
#           msg = await self.message_queue.get()
#           result = await self._process_message(msg)
#           # 处理 result，比如发回群聊或触发下一步是
# 【需要补充】
#   1. 将 result 添加到 GroupChat：
#      - 需要调用 self.group_chat_context.group_chat_session.add_message(result)
#      - 或者调用 GroupChat 的统一方法（见上方问题 1）
#   2. 根据 msg.message_type 决定是否需要回复：
#      - 如果是 MessageType.TASK，需要自动回复给发送者
#      - 如果是 MessageType.NOTIFICATION，只处理不回复
#   3. 更新 AgentCall 状态（如果这个消息关联了 AgentCall）：
#      - 调用 agent_call_manager.set_result() 或 set_error()
#   4. 错误处理：
#      - 如果 _process_message() 抛出异常，需要捕获并记录
#      - 更新 AgentCall 状态为 FAILED

# ==================== 3. AgentCallManager 未完成的功能 ====================
# 【问题】AgentCallManager 缺少日志记录和自动清理机制
# 【位置】AgentCallManager 类（第 227-273 行）
# 【注释中提到的 TODO】（第 232-234 行）
#   # TODO
#   # 1. 与util统一的logger，但是agentCall单独保存一份，需要一个logger的变体类独立用于AgentCallManager
#   # 2. 轮询线程，用于判断是否需要删除已经完成的AgentCall
# 【需要实现】
#   1. Logger 集成：
#      - 创建专门的 AgentCallLogger 类
#      - 记录每个 call 的创建、状态变更、完成/失败
#      - 日志应该保存到独立文件，方便调试和审计
#   2. 自动清理机制：
#      - 启动后台线程/任务，定期检查已完成的 AgentCall
#      - 调用 AgentCall.can_be_deleted() 判断是否可删除
#      - 删除逻辑需要明确（见下方 AgentCall.can_be_deleted() 的问题）
#   3. 超时检查：
#      - 定期调用 AgentCall.is_timeout() 检查超时
#      - 将超时的 call 状态更新为 TIMEOUT

# ==================== 4. AgentCall.can_be_deleted() 删除逻辑未确认 ====================
# 【问题】AgentCall 的删除逻辑未定义
# 【位置】AgentCall.can_be_deleted() 方法（第 222-224 行）
# 【当前代码】
#   def can_be_deleted(self) -> bool:
#       # TODO，未确认删除逻辑
#       return False
# 【需要确认】
#   1. 删除条件应该是什么？
#      - 已完成且超过一定时间（如 1 小时）？
#      - NOTIFICATION 类型的消息完成后立即删除？
#      - TASK 类型的消息需要保留更久？
#   2. 是否需要考虑业务任务关联？
#      - 如果有 business_task_id，可能需要保留更久
#   3. 是否需要持久化到磁盘？
#      - 当前 AgentCall 只在内存中，重启后丢失
#      - 是否需要保存到文件以便审计和恢复？

# ==================== 5. AgentCall.is_timeout() 的空指针风险 ====================
# 【问题】is_timeout() 方法在 timeout_seconds 为 None 时会抛出异常
# 【位置】AgentCall.is_timeout() 方法（第 214-220 行）
# 【当前代码】
#   def is_timeout(self) -> bool:
#       """判断是否超时"""
#       if self.status in (CallStatus.COMPLETED, CallStatus.FAILED, CallStatus.TIMEOUT):
#           return False
#
#       elapsed = (datetime.now() - self.created_at).total_seconds()
#       return elapsed > self.timeout_seconds  # ← 如果 timeout_seconds 是 None，这里会报错
# 【修复建议】
#   if self.timeout_seconds is None:
#       return False  # 无超时限制
#   elapsed = (datetime.now() - self.created_at).total_seconds()
#   return elapsed > self.timeout_seconds

# ==================== 6. call_agent() 函数的返回值和错误处理 ====================
# 【问题】call_agent() 的返回值设计不完整
# 【位置】call_agent() 函数（第 952-979 行）
# 【当前代码】
#   except Exception as e:
#       return e  # 注意这里是为了方便简单的写法，真实的写法是需要定义专门的exception 在这里捕获，然后返回具体的错误
# 【需要实现】
#   1. 定义专门的异常类：
#      - AgentNotFoundError
#      - GroupChatNotFoundError
#      - MessageDeliveryError
#   2. 返回值应该是结构化的：
#      - 成功：返回 call_id（用于查询状态）
#      - 失败：返回错误信息（符合 MCP tool 的响应格式）
#   3. 当前返回 str，但注释说"正式版本需要适配 MCP tool 的响应格式"
#      - 需要确认 MCP tool 的响应格式是什么
#      - 可能需要返回 JSON 或特定的数据结构

# ==================== 7. call_agent() 缺少异步执行机制 ====================
# 【问题】call_agent() 是同步函数，但消息处理是异步的
# 【位置】call_agent() 函数（第 952-979 行）
# 【说明】
#   - call_agent() 只是将消息放入队列就返回了
#   - 如果 need_response=True，调用者如何获取响应？
#   - 当前没有等待机制，也没有回调机制
# 【需要实现】
#   1. 如果 need_response=False：
#      - 当前逻辑 OK，直接返回 call_id
#   2. 如果 need_response=True：
#      - 需要等待 AgentCall 完成
#      - 可以通过 asyncio.Event 或 Future 实现
#      - 或者返回 call_id，让调用者通过 get_call_status() 轮询
#   3. 超时处理：
#      - 如果设置了 timeout_seconds，需要在超时后返回 TIMEOUT 状态

# ==================== 8. MessageRouter 缺少错误处理和日志 ====================
# 【问题】MessageRouter.send_message() 缺少错误处理
# 【位置】MessageRouter 类（第 154-175 行）
# 【当前代码】
#   def send_message(self, message: AgentMessage):
#       self._validate_message(message)
#       self._agents_queue[message.send_to].put_nowait(message)
# 【潜在问题】
#   1. put_nowait() 可能抛出 asyncio.QueueFull 异常（如果队列有大小限制）
#   2. 没有日志记录，无法追踪消息流转
#   3. 如果 _validate_message() 抛出异常，调用者需要处理
# 【建议】
#   1. 添加 try-except 捕获 QueueFull
#   2. 添加日志记录每条消息的发送
#   3. 考虑返回值（成功/失败）而不是抛出异常

# ==================== 9. GroupChat.start() 中的注册顺序问题 ====================
# 【问题】注册顺序可能导致初始化时消息路由失败
# 【位置】GroupChat.start() 方法（第 353-383 行）
# 【当前代码】
#   # 3. 注册所有agent到message_router
#   self.manager.message_router = self.message_router
#   self.message_router.register(self.manager.name, self.manager.message_queue)
#   for worker in self.works.values():
#       worker.message_router = self.message_router
#       self.message_router.register(worker.name, worker.message_queue)
#
#   # 3. 初始化新成员（第一次会话的成员）
#   await self._initialize_new_members()
# 【潜在问题】
#   - _initialize_new_members() 中调用 agent.execute()，可能会触发 agent 之间的消息发送
#   - 但此时 agent.run() 还没有启动，消息会堆积在队列中
#   - 如果初始化过程中需要 agent 互相通信，会卡住
# 【建议】
#   1. 在 start() 中启动所有 agent 的 run() 任务
#   2. 或者确保初始化过程不需要 agent 互相通信

# ==================== 10. Agent 缺少 run() 任务的启动和停止机制 ====================
# 【问题】Agent.run() 方法定义了，但没有地方启动它
# 【位置】Agent.run() 方法（第 879-885 行）
# 【说明】
#   - Agent.run() 是一个 async 方法，需要通过 asyncio.create_task() 启动
#   - 当前代码中没有看到启动 run() 的地方
#   - 也没有停止机制（虽然有 set_run() 方法）
# 【需要实现】
#   1. 在 GroupChat.start() 中启动所有 agent 的 run() 任务：
#      self.manager_task = asyncio.create_task(self.manager.run())
#      self.worker_tasks = [asyncio.create_task(w.run()) for w in self.works.values()]
#   2. 添加 GroupChat.stop() 方法：
#      - 调用所有 agent 的 set_run(False)
#      - 等待所有任务完成（await task）
#      - 清理资源

# ==================== 11. GroupChatContext 缺少并发安全保护 ====================
# 【问题】多个 agent 并发写入文件可能导致数据损坏
# 【位置】GroupChatContext 类（第 442-784 行）
# 【说明】
#   - save_group_chat_session() 和 save_agent_session_id() 直接写文件
#   - 如果多个 agent 同时调用，可能导致文件损坏或数据丢失
#   - compact_messages() 也有同样的问题
# 【建议】
#   1. 添加 asyncio.Lock 保护文件写入：
#      self._save_lock = asyncio.Lock()
#   2. 在所有写文件的方法中使用：
#      async with self._save_lock:
#          # 写文件操作
#   3. 或者使用队列 + 单独的写入任务来串行化写操作

# ==================== 12. compact_messages() 的 LLM 调用未处理失败情况 ====================
# 【问题】如果 LLM 调用失败或返回格式错误，压缩会中断
# 【位置】GroupChatContext.compact_messages() 方法（第 616-704 行）
# 【当前代码】
#   try:
#       # 解析 JSON
#       compact_data = json.loads(result_text)
#       # ...
#   except json.JSONDecodeError as e:
#       print(f"解析压缩结果失败: {e}")
#       print(f"原始结果: {compact_result.text}")
#       return  # ← 直接返回，last_compacted_loc 没有更新
# 【潜在问题】
#   1. 如果 LLM 返回格式错误，压缩失败，但 last_compacted_loc 没有更新
#   2. 下次调用 compact_messages() 会重新尝试压缩相同的消息
#   3. 如果 LLM 持续返回错误格式，会陷入死循环
# 【建议】
#   1. 添加重试机制（最多 3 次）
#   2. 如果重试失败，记录错误日志，但更新 last_compacted_loc 避免死循环
#   3. 或者将失败的消息标记为"无法压缩"，跳过它们

# ==================== 13. compact_messages() 中的调试代码需要清理 ====================
# 【问题】代码中有调试用的 print 和重复的 LLM 调用
# 【位置】GroupChatContext.compact_messages() 方法（第 663-667 行）
# 【当前代码】
#   print(f"input prompt : {compact_prompt}")
#   compact_result = await llm_call.execute(compact_prompt)
#   compact_result_codex = await llm_call_codex.execute(compact_prompt)  # ← 为什么调用两次？
#   print(f"claude llm call : {compact_result}")
#   print(f"codex llm call : {compact_result_codex}")
# 【需要确认】
#   1. 为什么同时调用 claude 和 codex？是为了对比测试吗？
#   2. 正式版本应该只调用一个，或者有明确的选择逻辑
#   3. print 应该替换为 logger

# ==================== 14. Manager 和 Worker 类几乎是空的 ====================
# 【问题】Manager 和 Worker 类没有实现任何特殊逻辑
# 【位置】Manager 类（第 887-891 行）、Worker 类（第 892-893 行）
# 【当前代码】
#   class Manager(Agent):
#       def __init__(self):
#           super().__init__(RoleManager().get_role("Leader"))
#           pass
#       pass
#   class Worker(Agent):
#       pass
# 【需要确认】
#   1. Manager 是否需要特殊的任务分配逻辑？
#      - 根据 GroupChatType.MANAGER_ORCHESTRATE，Manager 应该动态决定任务分配
#      - 当前没有实现这个逻辑
#   2. Worker 是否需要特殊的任务执行逻辑？
#   3. 如果不需要特殊逻辑，这两个类可以删除，直接使用 Agent

# ==================== 15. GroupChatType.SEQUENCE_EXECUTE 未实现 ====================
# 【问题】定义了 SEQUENCE_EXECUTE 类型，但没有实现
# 【位置】GroupChatType 枚举（第 276-278 行）
# 【说明】
#   - 定义了两种类型：SEQUENCE_EXECUTE（流水线顺序执行）和 MANAGER_ORCHESTRATE（管理者编排）
#   - 但 GroupChat 中没有根据类型实现不同的逻辑
#   - group_type 参数在 __init__ 中接收，但没有使用
# 【需要实现】
#   1. 在 GroupChat 中根据 group_type 实现不同的消息路由逻辑
#   2. SEQUENCE_EXECUTE：按照预定义的顺序依次调用 agent
#   3. MANAGER_ORCHESTRATE：由 Manager 动态决定调用哪个 agent

# ==================== 16. AgentContext 类完全未实现 ====================
# 【问题】AgentContext 类只有空壳
# 【位置】AgentContext 类（第 787-793 行）
# 【当前代码】
#   class AgentContext:
#       """
#       为Agent每次调用提供上下文
#       主要实现对于groupchatsession有选择的作为agentcontext
#       """
#       def __init__(self,agent_name:str,group_chat_context:GroupChatContext):
#           pass
# 【需要实现】
#   1. 根据注释，应该"有选择的"提供上下文
#      - 可能需要根据 agent 的角色、任务类型等过滤上下文
#   2. 提供方法获取格式化的上下文字符串
#   3. 或者直接删除这个类，使用 GroupChatContext.get_agent_context()

# ==================== 17. 缺少 WebSocketManager 类 ====================
# 【问题】代码中多处提到需要 WebSocket 推送，但没有实现
# 【位置】多处（见问题 1）
# 【需要实现】
#   1. WebSocketManager 类：
#      - 管理所有 WebSocket 连接（按 group_chat_id 或 user_id）
#      - 提供 send_message() 方法推送消息给前端
#      - 处理连接/断开事件
#   2. 消息格式定义：
#      - 定义前端期望的消息格式（JSON schema）
#      - 包括消息类型、发送者、内容、时间戳等
#   3. 集成到 GroupChat：
#      - 在 GroupChat.__init__() 中初始化 WebSocketManager
#      - 在 add_message_and_notify() 中调用 WebSocketManager.send_message()

# ==================== 18. 缺少团队管理类 ====================
# 【问题】注释中提到"后续应该增加团队管理类"
# 【位置】Team 类注释（第 116 行）
# 【当前代码】
#   # ===========================团队设置（暂时），后续应该增加团队管理类=============
#   class Team(BaseModel):
#       # ...
# 【需要实现】
#   1. TeamManager 类：
#      - 管理所有团队（类似 RoleManager）
#      - 提供 create_team()、get_team()、list_teams() 等方法
#      - 持久化团队信息到 teams.json（见第 54-62 行的注释）
#   2. 团队成员管理：
#      - 添加/删除成员
#      - 验证成员是否存在
#   3. 与 GroupChat 集成：
#      - GroupChat 应该通过 team_name 获取 Team，而不是直接传入 Team 对象

# ==================== 19. 缺少 GroupChat 的持久化和恢复机制 ====================
# 【问题】GroupChat 对象本身没有持久化
# 【位置】GroupChat 类（第 281-418 行）
# 【说明】
#   - GroupChatContext 持久化了消息和 session_id
#   - 但 GroupChat 的配置（team、group_type、members 等）没有持久化
#   - 如果程序重启，无法恢复 GroupChat 对象
# 【需要实现】
#   1. 在 GroupChat.__init__() 中保存配置到文件（如 group_chat_config.json）
#   2. 提供 GroupChat.load() 类方法从文件恢复
#   3. 或者通过 GroupChatManager 统一管理持久化

# ==================== 20. 缺少错误恢复机制 ====================
# 【问题】如果 agent 执行失败，没有重试或降级机制
# 【位置】Agent._process_message() 方法（第 869-878 行）
# 【说明】
#   - 如果 execute() 或 btw_execute() 抛出异常，消息会丢失
#   - 没有重试机制
#   - 没有降级方案（如切换到备用 agent）
# 【建议】
#   1. 在 Agent.run() 中添加 try-except 捕获异常
#   2. 记录失败的消息到日志
#   3. 根据错误类型决定是否重试（如网络错误可以重试）
#   4. 如果重试失败，通知发送者（如果是 TASK 类型）

# ==================== 21. 缺少性能监控和统计 ====================
# 【问题】没有性能监控和统计功能
# 【建议】
#   1. 记录每个 agent 的调用次数、平均响应时间、成功率
#   2. 记录消息队列的长度、等待时间
#   3. 记录压缩操作的频率、耗时
#   4. 提供 get_stats() 方法返回统计信息

# ==================== 22. 缺少测试用例 ====================
# 【问题】这是一个复杂的多 agent 系统，但没有测试用例
# 【建议】
#   1. 单元测试：
#      - MessageRouter 的消息路由
#      - AgentCallManager 的状态管理
#      - GroupChatContext 的持久化和压缩
#   2. 集成测试：
#      - 完整的消息流转（user → manager → worker → user）
#      - 并发场景（多个 agent 同时发送消息）
#      - 错误场景（agent 失败、超时、队列满）
#   3. 性能测试：
#      - 大量消息的处理速度
#      - 压缩操作的性能

# ==================== 23. main() 函数的测试代码不完整 ====================
# 【问题】main() 函数只初始化了 GroupChat，但没有测试消息流转
# 【位置】main() 函数（第 983-995 行）
# 【当前代码】
#   async def main():
#       # ... 创建 team 和 group_chat
#       await group_chat.start()
#       # ← 没有后续操作
# 【建议】
#   1. 添加测试消息发送：
#      - 模拟 user 发送任务给 manager
#      - manager 分配任务给 worker
#      - worker 完成任务并回复
#   2. 测试压缩功能：
#      - 发送足够多的消息触发压缩
#      - 验证压缩结果
#   3. 测试 call_agent() 工具：
#      - 模拟 agent 之间的互相调用

# ==================== 24. 缺少配置管理 ====================
# 【问题】硬编码的配置散落在代码中
# 【位置】多处（如 MAX_TOKEN、LOCAL_DATA_PATH）
# 【建议】
#   1. 创建 Config 类或配置文件（如 config.yaml）
#   2. 集中管理所有配置：
#      - 文件路径
#      - 超时阈值
#      - 压缩阈值
#      - LLM 模型选择
#   3. 支持环境变量覆盖配置

# ==================== 25. 缺少文档和使用示例 ====================
# 【问题】代码复杂度高，但缺少使用文档
# 【建议】
#   1. 添加 README.md 说明：
#      - 架构概述
#      - 核心概念（Team、GroupChat、Agent、MessageRouter 等）
#      - 使用示例
#   2. 添加 API 文档（docstring）
#   3. 添加架构图（如消息流转图、状态机图）

# ==================== 26. 缺少完善的错误处理体系 ====================
# 【问题】当前错误处理过于简化，没有统一的错误分类和处理机制
# 【位置】多处（如 call_agent 第 978 行、MessageRouter._validate_message 第 169-175 行等）
# 【当前问题】
#   1. 错误处理不统一：
#      - 有些地方直接 raise ValueError
#      - 有些地方 return Exception 对象（如 call_agent）
#      - 有些地方只是 print 错误信息
#   2. 缺少错误分类：
#      - 没有区分哪些错误需要发送给 Agent
#      - 哪些错误需要系统报错
#      - 哪些错误需要记录日志但不中断流程
#   3. MCP Tool 的错误返回格式不明确：
#      - Agent 通过 MCP 调用 call_agent 时，需要返回结构化的错误信息
#      - 不同类型的错误，返回给 Agent 的提示词应该不同
#
# 【需要设计的错误分类体系】
#   1. 系统级错误（SystemError）- 需要立即中断并报警：
#      - 文件系统错误（无法写入、磁盘满）
#      - 数据库连接失败
#      - 内存不足
#      处理方式：抛出异常，记录错误日志，通知管理员
#
#   2. 业务级错误（BusinessError）- 需要返回给 Agent 处理：
#      - Agent 不存在（AgentNotFoundError）
#      - 消息格式错误（InvalidMessageError）
#      - 权限不足（PermissionDeniedError）
#      - 超时（TimeoutError）
#      处理方式：返回结构化错误信息给调用方（Agent 或 MCP Tool）
#
#   3. 可恢复错误（RecoverableError）- 需要重试：
#      - 网络临时故障
#      - LLM API 限流
#      - 队列临时满
#      处理方式：自动重试（带退避策略），记录警告日志
#
#   4. 验证错误（ValidationError）- 需要明确提示：
#      - 参数缺失或格式错误
#      - 数据不符合约束
#      处理方式：返回详细的错误信息，帮助调用方修正
#
# 【需要实现的错误类】
#   # 基础错误类
#   class AgentsHubError(Exception):
#       """所有 agents-hub 错误的基类"""
#       def __init__(self, message: str, error_code: str, details: dict = None):
#           self.message = message
#           self.error_code = error_code  # 用于 MCP Tool 返回
#           self.details = details or {}
#           super().__init__(message)
#
#       def to_mcp_response(self) -> dict:
#           """转换为 MCP Tool 的错误响应格式"""
#           return {
#               "success": False,
#               "error_code": self.error_code,
#               "message": self.message,
#               "details": self.details
#           }
#
#   # 业务错误
#   class AgentNotFoundError(AgentsHubError):
#       """Agent 不存在"""
#       def __init__(self, agent_name: str):
#           super().__init__(
#               message=f"Agent '{agent_name}' 不存在，请检查 agent 名称是否正确",
#               error_code="AGENT_NOT_FOUND",
#               details={"agent_name": agent_name}
#           )
#
#   class GroupChatNotFoundError(AgentsHubError):
#       """GroupChat 不存在"""
#       def __init__(self, group_chat_id: str):
#           super().__init__(
#               message=f"GroupChat '{group_chat_id}' 不存在",
#               error_code="GROUP_CHAT_NOT_FOUND",
#               details={"group_chat_id": group_chat_id}
#           )
#
#   class MessageDeliveryError(AgentsHubError):
#       """消息投递失败"""
#       def __init__(self, reason: str, send_from: str, send_to: str):
#           super().__init__(
#               message=f"消息投递失败: {reason}",
#               error_code="MESSAGE_DELIVERY_FAILED",
#               details={"send_from": send_from, "send_to": send_to, "reason": reason}
#           )
#
#   class AgentExecutionError(AgentsHubError):
#       """Agent 执行失败"""
#       def __init__(self, agent_name: str, reason: str):
#           super().__init__(
#               message=f"Agent '{agent_name}' 执行失败: {reason}",
#               error_code="AGENT_EXECUTION_FAILED",
#               details={"agent_name": agent_name, "reason": reason}
#           )
#
#   class AgentTimeoutError(AgentsHubError):
#       """Agent 执行超时"""
#       def __init__(self, agent_name: str, timeout_seconds: int):
#           super().__init__(
#               message=f"Agent '{agent_name}' 执行超时（{timeout_seconds}秒）",
#               error_code="AGENT_TIMEOUT",
#               details={"agent_name": agent_name, "timeout_seconds": timeout_seconds}
#           )
#
#   # 验证错误
#   class InvalidMessageError(AgentsHubError):
#       """消息格式错误"""
#       def __init__(self, reason: str):
#           super().__init__(
#               message=f"消息格式错误: {reason}",
#               error_code="INVALID_MESSAGE",
#               details={"reason": reason}
#           )
#
#   # 系统错误
#   class FileSystemError(AgentsHubError):
#       """文件系统错误"""
#       def __init__(self, operation: str, path: str, reason: str):
#           super().__init__(
#               message=f"文件系统错误: {operation} '{path}' 失败 - {reason}",
#               error_code="FILE_SYSTEM_ERROR",
#               details={"operation": operation, "path": path, "reason": reason}
#           )
#
#   class CompactionError(AgentsHubError):
#       """压缩失败"""
#       def __init__(self, reason: str):
#           super().__init__(
#               message=f"消息压缩失败: {reason}",
#               error_code="COMPACTION_FAILED",
#               details={"reason": reason}
#           )
#
# 【需要修改的地方】
#   1. call_agent() 函数（第 952-979 行）：
#      当前代码：
#        except Exception as e:
#            return e
#      修改为：
#        except AgentNotFoundError as e:
#            return e.to_mcp_response()
#        except GroupChatNotFoundError as e:
#            return e.to_mcp_response()
#        except MessageDeliveryError as e:
#            return e.to_mcp_response()
#        except Exception as e:
#            # 未预期的错误，记录日志并返回通用错误
#            logger.error(f"call_agent 发生未预期错误: {e}", exc_info=True)
#            return {
#                "success": False,
#                "error_code": "INTERNAL_ERROR",
#                "message": "内部错误，请联系管理员",
#                "details": {}
#            }
#
#   2. MessageRouter._validate_message() 方法（第 169-175 行）：
#      当前代码：
#        if not message.content or not message.content.strip():
#            raise ValueError("消息内容不能为空")
#      修改为：
#        if not message.content or not message.content.strip():
#            raise InvalidMessageError("消息内容不能为空")
#        if message.send_from not in self._agents_queue:
#            raise AgentNotFoundError(message.send_from)
#        if message.send_to not in self._agents_queue:
#            raise AgentNotFoundError(message.send_to)
#
#   3. MessageRouter.send_message() 方法（第 165-167 行）：
#      当前代码：
#        def send_message(self, message: AgentMessage):
#            self._validate_message(message)
#            self._agents_queue[message.send_to].put_nowait(message)
#      修改为：
#        def send_message(self, message: AgentMessage):
#            try:
#                self._validate_message(message)
#                self._agents_queue[message.send_to].put_nowait(message)
#            except asyncio.QueueFull:
#                raise MessageDeliveryError(
#                    reason="目标 Agent 的消息队列已满",
#                    send_from=message.send_from,
#                    send_to=message.send_to
#                )
#            except (AgentNotFoundError, InvalidMessageError):
#                raise  # 直接向上传递
#            except Exception as e:
#                raise MessageDeliveryError(
#                    reason=f"未知错误: {str(e)}",
#                    send_from=message.send_from,
#                    send_to=message.send_to
#                )
#
#   4. Agent._process_message() 方法（第 869-878 行）：
#      需要捕获执行错误并转换为 AgentExecutionError：
#        async def _process_message(self, msg: AgentMessage) -> AgentResult:
#            try:
#                if msg.session_type == SessionType.MAIN:
#                    return await self.execute(msg.content)
#                else:
#                    return await self.btw_execute(msg.content)
#            except Exception as e:
#                raise AgentExecutionError(
#                    agent_name=self.name,
#                    reason=str(e)
#                )
#
#   5. GroupChatContext.compact_messages() 方法（第 616-704 行）：
#      当前代码：
#        except json.JSONDecodeError as e:
#            print(f"解析压缩结果失败: {e}")
#            print(f"原始结果: {compact_result.text}")
#            return
#      修改为：
#        except json.JSONDecodeError as e:
#            raise CompactionError(
#                reason=f"LLM 返回的 JSON 格式错误: {str(e)}"
#            )
#        except Exception as e:
#            raise CompactionError(
#                reason=f"压缩过程发生错误: {str(e)}"
#            )
#
#   6. GroupChatContext 的文件操作方法：
#      需要捕获文件系统错误：
#        def save_group_chat_session(self):
#            try:
#                os.makedirs(self.group_chat_session_path, exist_ok=True)
#                with open(self.messages_file, 'w', encoding='utf-8') as f:
#                    # ... 写入操作
#            except OSError as e:
#                raise FileSystemError(
#                    operation="write",
#                    path=self.messages_file,
#                    reason=str(e)
#                )
#
# 【错误处理的最佳实践】
#   1. 在边界处捕获错误：
#      - MCP Tool 入口（call_agent）：捕获所有错误，返回结构化响应
#      - Agent.run() 循环：捕获执行错误，记录日志，继续处理下一条消息
#      - 文件操作：捕获 IO 错误，转换为 FileSystemError
#
#   2. 错误传播原则：
#      - 底层函数：抛出具体的错误类（如 AgentNotFoundError）
#      - 中间层：传递错误或包装为更高层的错误
#      - 顶层（MCP Tool）：捕获所有错误，转换为 MCP 响应格式
#
#   3. 日志记录：
#      - 所有错误都应该记录日志（包括堆栈信息）
#      - 区分错误级别：ERROR（系统错误）、WARNING（业务错误）、INFO（验证错误）
#      - 记录上下文信息（agent_name、group_chat_id、message 等）
#
#   4. 用户友好的错误信息：
#      - 返回给 Agent 的错误信息应该清晰、可操作
#      - 包含错误原因和建议的解决方案
#      - 例如："Agent 'worker1' 不存在，请使用 list_agents 查看可用的 agent 列表"
#
#   5. 错误恢复策略：
#      - 可恢复错误：自动重试（带指数退避）
#      - 业务错误：返回错误信息，让调用方决定如何处理
#      - 系统错误：记录日志，通知管理员，可能需要人工介入
#
# 【MCP Tool 的错误响应格式】
#   所有 MCP Tool 应该返回统一的格式：
#   成功：
#   {
#       "success": True,
#       "data": {
#           "call_id": "abc123",
#           "status": "pending"
#       }
#   }
#
#   失败：
#   {
#       "success": False,
#       "error_code": "AGENT_NOT_FOUND",
#       "message": "Agent 'worker1' 不存在，请检查 agent 名称是否正确",
#       "details": {
#           "agent_name": "worker1",
#           "available_agents": ["小李", "小赵", "Leader"]
#       }
#   }
#
# 【优先级】
#   这是一个高优先级问题，因为：
#   1. 影响系统的稳定性和可维护性
#   2. 影响 Agent 的使用体验（错误信息不清晰会导致 Agent 无法正确处理）
#   3. 影响调试效率（没有统一的错误处理，很难定位问题）
#   建议在实现核心功能后，立即完善错误处理体系

# ================================================================================================
# 总结：优先级排序
# ================================================================================================
# 【高优先级】必须实现才能运行：
#   1. Agent.run() 的完整实现（问题 2）
#   2. 启动 Agent.run() 任务（问题 10）
#   3. call_agent() 的异步执行机制（问题 7）
#   4. AgentCall.is_timeout() 的空指针修复（问题 5）
#
# 【中优先级】影响功能完整性：
#   5. GroupChat 消息添加与 WebSocket 推送（问题 1）
#   6. AgentCallManager 的日志和清理机制（问题 3）
#   7. GroupChatContext 的并发安全（问题 11）
#   8. compact_messages() 的错误处理（问题 12）
#   9. Manager 的任务分配逻辑（问题 14）
#   10. SEQUENCE_EXECUTE 类型的实现（问题 15）
#
# 【低优先级】优化和完善：
#   11. WebSocketManager 实现（问题 17）
#   12. 团队管理类（问题 18）
#   13. GroupChat 持久化（问题 19）
#   14. 错误恢复机制（问题 20）
#   15. 性能监控（问题 21）
#   16. 测试用例（问题 22）
#   17. 配置管理（问题 24）
#   18. 文档和示例（问题 25）
#
# 【清理项】代码质量：
#   19. 调试代码清理（问题 13）
#   20. AgentContext 实现或删除（问题 16）
#   21. MessageRouter 错误处理（问题 8）
#   22. call_agent() 返回值设计（问题 6）
#   23. AgentCall.can_be_deleted() 逻辑（问题 4）
#   24. GroupChat.start() 注册顺序（问题 9）
#   25. main() 测试代码（问题 23）
# ================================================================================================
