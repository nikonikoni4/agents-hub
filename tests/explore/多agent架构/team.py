# 创建team
from enum import Enum
from agents_hub.roles import Role,RoleManager,RoleType, role_manager
from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.roles.models import RoleConfig
from agents_hub.agent_bridge import AgentBridge,AgentEvent
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
teams / <team_name> / <project_path> / <group_chat_id> / memory / # （暂定，先不实现）存放会话短期压缩记忆和记录

<group_chat_id>.jsonl 

{
    _type : "meta_data", last_compact_loc : ,create_at:,updata_at
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
teams.json
[
    {
        team_name : "",
        members_list : ['',''] # 不包含manager，manager在一个团队中总是预定义的
    }
]

"""


# Team
# Team类存在的意义是什么？目前能想到的就算一个team成员的检验器，可以从json文档中加载

class Team(BaseModel):
    team_members_name : list[str]
    team_name : str
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

    async def start(self):
        # 1. 初始化team manager
        self.manager = Manager()
        # 2. 初始化team worker
        
        if not self.team_members_name:
            print("warning : 无团队成员")
            return
        role_manager = RoleManager()
        for role in self.team_members_name:
            
            self.works[role] = Worker(role_manager.get_role(role)) # 关于角色这部分，可能有优化的地方，每次都需要读取文件夹

        import asyncio
        # 向manager和worker发送信息，获取session_id以及将每个成员的消息返回到群聊中
        async def start_conversation(agent : Agent):
            if agent.role_type == RoleType.LEADER:
                return await agent.execute(f"你好，我是这个团队的boss,当前团队成员有{self.team_members_name},你将指挥他们完成我的任务。你使用一句话简单介绍一下自己")
            else:
                other_members = [name for name in self.team_members_name if name != agent.name]
                return await agent.execute(f"你好，我是这个团队的boss，当前团队有成员有{other_members},你的直属领导是{self.manager.name},你使用一句话简单介绍一下自己")
        result:list[AgentEvent] = await asyncio.gather(
            start_conversation(self.manager)
            ,*[
            start_conversation(work) for _,work in self.works.items()
        ])
@dataclass
class GroupChatSession:
    group_chat_id : str = field(default_factory=lambda: str(uuid4()))
    name : str = field(default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d%H%M')}")
    messages : list[dict[str]] = field(default_factory=list)
    created_at : datetime = field(default_factory=datetime.now)
    updated_at : datetime = field(default_factory=datetime.now)
    last_compacted_loc : int = 0 # 上一次compact的位置 

    def add_message(self,agent_event:AgentEvent):
        pass


class GroupChatContext:
    """
    负责
    1. 群聊对话保存
    2. 上下文压缩和群聊公共记忆提取，作为每个member运行时上下文加载的内容
    """
    def __init__(self,group_chat_id : str,project_path:str):
        self.group_chat_id = group_chat_id
        self.agent_session_id = {} # agent_name : <session_id>
        # 获取当前的聊天历史路径
        sanitized_path = self.sanitize_project_path(project_path)
        self.group_chat_session_path = f"{LOCAL_DATA_PATH}/teams/{sanitized_path}/{group_chat_id}"
        self.messages_file = f"{self.group_chat_session_path}/{group_chat_id}.jsonl"
        self.session_file = f"{self.group_chat_session_path}/agent_session_id.json"
        self.agent_session_id = self.get_agent_session_id()
        self.messages = self.get_group_chat_messages()
        self.last_compact_loc = 0

    def get_group_chat_messages(self)->list[dict]:
        """
        获取群聊消息列表

        Returns:
            消息列表，每条消息是一个 dict
        """
        import json
        import os

        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)

        # 如果文件不存在，返回空列表
        if not os.path.exists(self.messages_file):
            return []

        # 读取 jsonl 文件
        messages = []
        with open(self.messages_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
        return messages

    def get_agent_session_id(self)->dict:
        """
        获取 agent session id 映射

        Returns:
            dict: {agent_name: {main_session: str, btw_session: [str]}}
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
            return json.load(f)

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

    def add_message(self,agent_event:AgentEvent):
        self.messages.append()

agent_platform_client = AgentBridge()
class Agent:
    def __init__(self,role:Role):
        self.role_config = role.get_role_config()
        self.name = self.role_config.name # 这里很奇怪，这些信息应该都直接作为类成员比较好啊，先不优化，role和agentbriged之后在优化
        self.role_type = role.get_info().type
        pass
    async def execute(self, prompt, session: str | None = None):
        return await agent_platform_client.execute(prompt, self.role_config)
class Manager(Agent):
    def __init__(self):
        super().__init__(RoleManager().get_role("Leader"))
        pass
        
    pass

class Worker(Agent):
    pass

async def main():
    role_manager = RoleManager()
    role_manager.create_role("小李",AgentPlatform.CLAUDE,type = RoleType.TEAM_MEMBER)
    role_manager.create_role("小赵",AgentPlatform.CODEX,type = RoleType.TEAM_MEMBER)
    role_manager.create_role("Leader",AgentPlatform.CLAUDE,type = RoleType.LEADER)
    team_member_list = ["小李","小赵"]
    team = Team(team_members_name=team_member_list)
    group_chat = GroupChat(team,GroupChatType.MANAGER_ORCHESTRATE,project_path='D:/desktop/软件开发/agents-hub')
    await group_chat.start()

if __name__ == "__main__":
    asyncio.run(main())
