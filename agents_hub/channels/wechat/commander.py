import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from agents_hub.api.schemas.single_chat import (
    CreateSingleChatRequest,
    SingleChatType,
)
from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.api.services.single_chat_service import single_chat_manager
from agents_hub.config.config import config
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
from agents_hub.roles import RoleManager

logger = logging.getLogger(__name__)

ASSISTANT_AGENT_NAME = "Agents-Hub-Assistant"

HELP_TEXT = """可用命令：
/help - 显示帮助
/agents - 列出所有 agent
/groups - 列出所有群聊
/agent <名称> - 选择 agent 进入单聊
/group <名称或序号> - 选择群聊
/create-group - 创建群聊（通过助手）
/create-role - 创建角色（通过助手）
/back - 退出当前对话"""


@dataclass
class UserSession:
    """单个微信用户的会话状态"""

    mode: str = "idle"  # "idle" | "agent_chat" | "group_chat" | "wait_create_group" | "wait_create_role"
    target: str = ""  # agent name 或 group_chat_id
    single_chat_id: str = ""  # 单聊会话 ID（agent_chat 模式）
    assistant_chat_id: str = ""  # 与助手的单聊 ID（create 模式）
    group_members: list[str] = field(default_factory=list)  # 群聊成员列表（group_chat 模式）


class Commander:
    """微信消息命令解析与执行"""

    def __init__(self):
        self._sessions: dict[str, UserSession] = {}
        self._role_manager = RoleManager()
        self._group_chat_service = GroupChatService(group_chat_manager)

    def _get_session(self, user_id: str) -> UserSession:
        if user_id not in self._sessions:
            self._sessions[user_id] = UserSession()
        return self._sessions[user_id]

    async def handle(self, user_id: str, content: str) -> str:
        """入口：根据内容分发到命令处理或消息转发"""
        session = self._get_session(user_id)

        # 处于等待创建状态时，非命令文本当作参数
        if session.mode == "wait_create_group" and not content.startswith("/"):
            return await self._handle_create_group_input(user_id, content)
        if session.mode == "wait_create_role" and not content.startswith("/"):
            return await self._handle_create_role_input(user_id, content)

        if content.startswith("/"):
            return await self._dispatch_command(user_id, content)

        return await self._forward_message(user_id, content)

    # ==================== 命令分发 ====================

    async def _dispatch_command(self, user_id: str, content: str) -> str:
        parts = content.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        handlers = {
            "/help": lambda: self._cmd_help(),
            "/agents": lambda: self._cmd_agents(),
            "/groups": lambda: self._cmd_groups(),
            "/back": lambda: self._cmd_back(user_id),
            "/agent": lambda: self._cmd_agent(user_id, arg),
            "/group": lambda: self._cmd_group(user_id, arg),
            "/create-group": lambda: self._cmd_create_group(user_id),
            "/create-role": lambda: self._cmd_create_role(user_id),
        }

        handler = handlers.get(cmd)
        if handler:
            return await handler()
        return f"未知命令: {cmd}\n\n{HELP_TEXT}"

    # ==================== 基础命令 ====================

    @staticmethod
    async def _cmd_help() -> str:
        return HELP_TEXT

    async def _cmd_agents(self) -> str:
        roles = self._role_manager.list_roles()
        if not roles:
            return "当前没有可用的 agent"
        lines = ["可用 Agent："]
        for i, r in enumerate(roles, 1):
            desc = f" - {r.description}" if r.description else ""
            lines.append(f"  {i}. {r.name} [{r.platform.value}]{desc}")
        return "\n".join(lines)

    async def _cmd_groups(self) -> str:
        groups = group_chat_manager.list_all_group_chats()
        if not groups:
            return "当前没有群聊"
        lines = ["群聊列表："]
        for i, g in enumerate(groups, 1):
            status = "活跃" if g["is_active"] else "未激活"
            lines.append(f"  {i}. {g['group_chat_name']} [{status}]")
            lines.append(f"     ID: {g['group_chat_id']}")
        return "\n".join(lines)

    async def _cmd_back(self, user_id: str) -> str:
        session = self._get_session(user_id)
        if session.mode == "idle":
            return "当前没有在对话中"
        old_mode = session.mode
        session.mode = "idle"
        session.target = ""
        session.single_chat_id = ""
        session.assistant_chat_id = ""
        session.group_members.clear()
        return f"已退出 {old_mode} 模式"

    # ==================== Agent 单聊 ====================

    async def _cmd_agent(self, user_id: str, name: str) -> str:
        if not name:
            return "请指定 agent 名称，如: /agent nico"

        # 验证 agent 存在
        try:
            self._role_manager.get_role(name)
        except Exception:
            available = self._role_manager.list_role_names()
            return f"Agent '{name}' 不存在。可用: {', '.join(available)}"

        # 创建单聊
        request = CreateSingleChatRequest(
            type=SingleChatType.NEW,
            single_chat_name=f"wechat-{user_id}-{name}",
            agent_name=name,
        )
        response = await single_chat_manager.create_single_chat(request)

        session = self._get_session(user_id)
        session.mode = "agent_chat"
        session.target = name
        session.single_chat_id = response.single_chat_id

        return f"已进入与 {name} 的单聊模式\n发送 /back 退出"

    # ==================== 群聊 ====================

    async def _cmd_group(self, user_id: str, name_or_idx: str) -> str:
        if not name_or_idx:
            return "请指定群聊名称、序号或 ID，如: /group my-team 或 /group 1"

        groups = group_chat_manager.list_all_group_chats()
        if not groups:
            return "当前没有群聊"

        # 按序号匹配
        if name_or_idx.isdigit():
            idx = int(name_or_idx) - 1
            if 0 <= idx < len(groups):
                target = groups[idx]
            else:
                return f"序号 {name_or_idx} 超出范围，共 {len(groups)} 个群聊"
        else:
            # 按 ID 匹配（UUID 格式）
            id_matches = [g for g in groups if g["group_chat_id"] == name_or_idx]
            if id_matches:
                target = id_matches[0]
            else:
                # 按名称匹配
                name_matches = [g for g in groups if g["group_chat_name"] == name_or_idx]
                if not names := [g["group_chat_name"] for g in groups]:
                    return f"未找到群聊 '{name_or_idx}'"
                if not name_matches:
                    return f"未找到群聊 '{name_or_idx}'。可用: {', '.join(names)}"
                target = name_matches[0]

        # 获取成员列表
        group_chat = await group_chat_manager.load_group_chat(target["group_chat_id"])
        member_dicts = group_chat.runtime.get_member_dicts()
        members = [m["name"] for m in member_dicts]

        session = self._get_session(user_id)
        session.mode = "group_chat"
        session.target = target["group_chat_id"]
        session.group_members = members

        return (
            f"已进入群聊: {target['group_chat_name']}\n"
            f"成员: {', '.join(members)}\n"
            f"消息将默认发送给 manager，用 @名称 指定目标\n"
            f"发送 /back 退出"
        )

    # ==================== 创建群聊/角色（通过助手） ====================

    async def _cmd_create_group(self, user_id: str) -> str:
        session = self._get_session(user_id)
        session.mode = "wait_create_group"
        session.assistant_chat_id = ""
        return "请输入群聊信息，格式：\n群聊名称 成员1 成员2 ...\n\n例如: my-team nico architect"

    async def _cmd_create_role(self, user_id: str) -> str:
        session = self._get_session(user_id)
        session.mode = "wait_create_role"
        session.assistant_chat_id = ""
        return "请输入角色信息，格式：\n角色名称 平台 描述\n\n例如: my-agent claude 代码审查专家"

    async def _ensure_assistant_chat(self, session: UserSession) -> str:
        """确保与助手的单聊存在，返回 single_chat_id"""
        if session.assistant_chat_id:
            return session.assistant_chat_id
        request = CreateSingleChatRequest(
            type=SingleChatType.NEW,
            single_chat_name="wechat-assistant-create",
            agent_name=ASSISTANT_AGENT_NAME,
        )
        response = await single_chat_manager.create_single_chat(request)
        session.assistant_chat_id = response.single_chat_id
        return response.single_chat_id

    async def _ask_assistant(self, session: UserSession, prompt: str) -> str:
        """发送消息给助手并收集完整回复"""
        chat_id = await self._ensure_assistant_chat(session)
        parts = []
        async for event_json in single_chat_manager.send_message_stream(chat_id, prompt):
            try:
                event = json.loads(event_json)
                if event.get("type") == "text_delta":
                    text = event.get("content", {}).get("text", "")
                    if text:
                        parts.append(text)
            except (json.JSONDecodeError, KeyError):
                pass
        return "".join(parts) if parts else "助手未返回内容"

    async def _handle_create_group_input(self, user_id: str, content: str) -> str:
        session = self._get_session(user_id)

        prompt = f"请帮我创建一个群聊，信息如下：{content}"
        reply = await self._ask_assistant(session, prompt)

        # 自动进入助手单聊模式
        session.mode = "agent_chat"
        session.target = ASSISTANT_AGENT_NAME
        session.single_chat_id = session.assistant_chat_id

        return f"[创建群聊]\n{reply}\n\n已进入与助手的单聊，可继续对话。发送 /back 退出"

    async def _handle_create_role_input(self, user_id: str, content: str) -> str:
        session = self._get_session(user_id)

        prompt = f"请帮我创建一个角色，信息如下：{content}"
        reply = await self._ask_assistant(session, prompt)

        # 自动进入助手单聊模式
        session.mode = "agent_chat"
        session.target = ASSISTANT_AGENT_NAME
        session.single_chat_id = session.assistant_chat_id

        return f"[创建角色]\n{reply}\n\n已进入与助手的单聊，可继续对话。发送 /back 退出"

    # ==================== 消息转发 ====================

    async def _forward_message(self, user_id: str, content: str) -> str:
        session = self._get_session(user_id)

        if session.mode == "agent_chat":
            return await self._forward_to_agent(session, content)

        if session.mode == "group_chat":
            return await self._forward_to_group(session, content)

        return f"请先选择对话目标\n\n{HELP_TEXT}"

    async def _forward_to_agent(self, session: UserSession, content: str) -> str:
        """转发消息到单聊 agent，收集流式响应"""
        parts = []
        async for event_json in single_chat_manager.send_message_stream(
            session.single_chat_id, content
        ):
            try:
                event = json.loads(event_json)
                if event.get("type") == "text_delta":
                    text = event.get("content", {}).get("text", "")
                    if text:
                        parts.append(text)
            except (json.JSONDecodeError, KeyError):
                pass

        return "".join(parts) if parts else "Agent 未返回内容"

    async def _forward_to_group(self, session: UserSession, content: str) -> str:
        """转发消息到群聊并等待 agent 回复"""
        return await self._group_chat_service.send_message_and_wait(
            group_chat_id=session.target,
            content=content,
            members=session.group_members,
            timeout=120.0,
        )
