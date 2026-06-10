"""测试 Claude Executor 两次调用的 input_tokens"""

import asyncio

from agents_hub.agent_bridge.executors.claude import ClaudeExecutor
from agents_hub.agent_bridge.parsers.claude import ClaudeParser
from agents_hub.agent_bridge.models import AgentEventType
from agents_hub.roles import RoleManager


async def test_two_calls():
    executor = ClaudeExecutor()
    parser = ClaudeParser()
    role_manager = RoleManager()

    config = role_manager.get_role("manager").get_role_config()
    cwd = r"D:\desktop\软件开发\agents-hub\.claude\worktrees\task-31-front-polling"

    # 第一次调用（不传 session_id，让 CLI 自动创建）
    print("=== 第一次调用 ===")
    prompt1 = "回复一个字：好"
    usage1 = None
    session_id = None

    async for raw in executor.execute(prompt1, config, cwd=cwd):
        event = parser.parse_event(raw)
        if event:
            if event.session_id and not session_id:
                session_id = event.session_id
                print(f"  session_id: {session_id}")
            if event.type == AgentEventType.TURN_COMPLETE:
                u = event.content.get("usage", {})
                inp = u.get("input_tokens", 0)
                cache = u.get("cache_read_input_tokens", 0)
                if inp > 0 or cache > 0:
                    usage1 = u
                    print(f"  input_tokens: {inp}, cache_read: {cache}, total: {inp + cache}")

    if not session_id:
        print("ERROR: 未获取到 session_id")
        return

    # 第二次调用（同一 session）
    print(f"\n=== 第二次调用 (session={session_id}) ===")
    prompt2 = "再回复一个字：好"
    usage2 = None

    async for raw in executor.execute(prompt2, config, session_id=session_id, cwd=cwd):
        event = parser.parse_event(raw)
        if event and event.type == AgentEventType.TURN_COMPLETE:
            u = event.content.get("usage", {})
            inp = u.get("input_tokens", 0)
            cache = u.get("cache_read_input_tokens", 0)
            if inp > 0 or cache > 0:
                usage2 = u
                print(f"  input_tokens: {inp}, cache_read: {cache}, total: {inp + cache}")

    # 比较
    t1 = (usage1.get("input_tokens", 0) + usage1.get("cache_read_input_tokens", 0)) if usage1 else 0
    t2 = (usage2.get("input_tokens", 0) + usage2.get("cache_read_input_tokens", 0)) if usage2 else 0
    print(f"\n=== 比较 ===")
    print(f"第一次 total tokens: {t1}")
    print(f"第二次 total tokens: {t2}")
    print(f"第二次 >= 第一次: {t2 >= t1}")


if __name__ == "__main__":
    asyncio.run(test_two_calls())
