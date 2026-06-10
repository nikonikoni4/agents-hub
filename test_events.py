"""测试：打印所有原始事件，查看 message_delta 和 result 的 usage 差异"""

import asyncio
import json

from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
from agents_hub.agent_bridge.parsers.claude import ClaudeParser
from agents_hub.agent_bridge.models import AgentEventType
from agents_hub.roles import RoleManager


async def test():
    executor = ClaudeExecutor()
    parser = ClaudeParser()
    role_manager = RoleManager()
    config = role_manager.get_role("manager").get_role_config()
    cwd = r"D:\desktop\软件开发\agents-hub\.claude\worktrees\task-31-front-polling"

    # 第一次调用
    print("=== 第一次调用 ===")
    session_id = None
    async for raw in executor.execute("回复一个字：好", config, cwd=cwd):
        event = parser.parse_event(raw)
        if event:
            if event.session_id and not session_id:
                session_id = event.session_id
            if event.type == AgentEventType.TURN_COMPLETE:
                u = event.content.get("usage", {})
                print(
                    f"  TURN_COMPLETE: input={u.get('input_tokens', 0)}, cache_read={u.get('cache_read_input_tokens', 0)}"
                )

    # 第二次调用
    print(f"\n=== 第二次调用 ===")
    async for raw in executor.execute("再回复一个字：好", config, session_id=session_id, cwd=cwd):
        event = parser.parse_event(raw)
        if event and event.type == AgentEventType.TURN_COMPLETE:
            u = event.content.get("usage", {})
            print(
                f"  TURN_COMPLETE: input={u.get('input_tokens', 0)}, cache_read={u.get('cache_read_input_tokens', 0)}"
            )


asyncio.run(test())
