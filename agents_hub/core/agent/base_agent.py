"""
Agent 基类

所有 Agent 的基类，包含消息处理、执行逻辑。

渲染分工（参见 foundation/renderer.py）：
- 入站 LLM prompt：render_for_llm（msg.content 始终为原始内容，不被改写）
- 出口 A 写群聊：render_for_chat
- 出口 B 投递回复：传 result.text 原文，不预渲染
"""
import asyncio
from contextlib import asynccontextmanager

from agents_hub.core.foundation import (
    AgentMessage,
    MessageType,
    AgentResult,
    Role,
    RoleConfig,
    SessionType,
    CallStatus,
    AgentExecutionError,
    render_for_llm,
    render_for_chat,
)

from agents_hub.core.communication import MessageRouter, AgentCallManager, AgentCall
from agents_hub.core.context import GroupChatContext, AgentContext
from agents_hub.agent_bridge import agent_platform_client


class Agent:
    def __init__(self, role: Role, group_chat_context: GroupChatContext, agent_call_manager: AgentCallManager):
        self.role_config: RoleConfig = role.get_role_config()
        self.name = self.role_config.name
        self.role_type = self.role_config.role_type
        self.message_queue = asyncio.Queue()  # 私有队列, 用于存放消息
        self.group_chat_context = group_chat_context
        self.agent_context = AgentContext(self.name, group_chat_context)
        self.message_router: MessageRouter | None = None
        self.agent_call_manager = agent_call_manager
        self._run = True

    def set_run(self, run: bool):
        """设置该agent是否工作"""
        # TODO 后续使用，暂时占位
        self._run = run

    def send_message_to_agent(self, call_id: str, send_to: str, content: str):
        """投递消息给指定 agent。

        约束：content 必须是原始内容（不预渲染包络），
        渲染由接收方 run() 通过 render_for_llm 统一处理。
        """
        message = AgentMessage(
            call_id=call_id,
            send_from=self.name,
            send_to=send_to,
            content=content,
            session_type=SessionType.MAIN,
            message_type=MessageType.NOTIFICATION,
        )
        self.message_router.send_message(message)

    async def execute(self, prompt) -> AgentResult:
        """执行主会话（群聊）

        Args:
            prompt: 渲染好的 LLM prompt 字符串
        """
        return await agent_platform_client.execute(prompt, self.role_config, self.main_session_id)

    async def btw_execute(self, prompt, session: str | None = None) -> AgentResult:
        """执行单聊（by the way）"""
        print(f"Info : {self.name} 执行单聊 content:{prompt[:20]}")
        return await agent_platform_client.execute(prompt, self.role_config, session)

    @property
    def main_session_id(self):
        if self.group_chat_context.agent_session_id.get(self.name):
            if self.group_chat_context.agent_session_id[self.name].main_session:
                return self.group_chat_context.agent_session_id[self.name].main_session
            else:
                print(f"warning : {self.name}在当前群聊中无历史记录")  # TODO 替换为 logger
        else:
            print(f"warning : 当前群聊无{self.name}的main session记录 [ 如果是初始化会话 忽略该警告]")
        return None

    async def _process_message(self, msg: AgentMessage, prompt: str) -> AgentResult:
        """处理一条入站消息。

        Args:
            msg: 原始 AgentMessage（content 不可变）
            prompt: 已通过 render_for_llm 渲染好的 LLM 输入字符串
        """
        self.agent_call_manager.update_status(msg.call_id, CallStatus.RUNNING)
        try:
            if msg.session_type == SessionType.MAIN:
                history = await self.agent_context.get_context()
                full_prompt = f"{history}\n{prompt}" if history else prompt
                result = await self.execute(full_prompt)
            else:
                result = await self.btw_execute(prompt)
            self.agent_call_manager.update_status(msg.call_id, CallStatus.COMPLETED)
            return result
        except Exception as e:
            self.agent_call_manager.update_status(msg.call_id, CallStatus.FAILED)
            self.agent_call_manager.set_error(msg.call_id, str(e))
            raise AgentExecutionError(
                agent_name=self.name,
                reason=str(e),
                session_id=self.main_session_id if msg.session_type == SessionType.MAIN else None,
                platform=self.role_config.platform,
            )

    async def run(self):
        """持续监听私有队列，处理收到的消息"""
        while self._run:
            # 1. 从队列中取回消息
            msg: AgentMessage = await self.message_queue.get()

            # 2. 渲染 LLM prompt（不写回 msg.content）
            prompt = render_for_llm(msg)
            result = await self._process_message(msg, prompt)

            # 3. 出口 A：写回群聊（@发起者 result.text）
            self.group_chat_context.add_message(
                render_for_chat(self.name, msg.send_from, result.text)
            )

            # 4. 出口 B：如果是 TASK 且发起者不是 user，投递回复
            if msg.message_type == MessageType.TASK and msg.send_from != "user":
                response_call = self.agent_call_manager.create_call(
                    send_from=self.name,
                    send_to=msg.send_from,
                    content=result.text,
                    message_type=MessageType.NOTIFICATION,
                )
                self.send_message_to_agent(
                    response_call.call_id, msg.send_from, result.text
                )
