"""
Agent 基类

所有 Agent 的基类，包含消息处理、执行逻辑。
"""
import asyncio
from agents_hub.core.foundation import AgentMessage, MessageType,AgentResult,Role,RoleConfig,SessionType
from agents_hub.core.communication import MessageRouter, AgentCallManager, AgentCall
from agents_hub.core.context import GroupChatContext,AgentContext
from agents_hub.agent_bridge import agent_platform_client
class Agent:
    def __init__(self,role:Role,group_chat_context:GroupChatContext):
        """"""
        self.role_config :RoleConfig= role.get_role_config()
        self.name = self.role_config.name
        self.role_type = self.role_config.role_type
        self.message_queue = asyncio.Queue() # 私有队列, 用户存放消息
        self.group_chat_context = group_chat_context
        self.agent_context = AgentContext(self.name , group_chat_context) # 暂时没有实现
        self.message_router: MessageRouter | None = None
        self._run = True
    def set_run(self,run:bool):
        """设置该agent是否工作，"""
        # TODO 后续使用，暂时占位
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
        self.group_chat_context.add_message(result)