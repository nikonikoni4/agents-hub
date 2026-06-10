"""调试 llm_call 的问题 - 异步测试版本"""

import asyncio
from team import llm_call_codex


async def test_with_newlines():
    """测试带换行符的 prompt"""
    prompt = """请直接回复我下面的内容：111111
22222
"""
    print("=== 带换行符 ===")
    result = await llm_call_codex.execute(prompt)
    print(f"结果: {result}")


async def test_without_newlines():
    """测试不带换行符的 prompt"""
    prompt = "请直接回复我下面的内容：11111122222"
    print("=== 无换行符 ===")
    result = await llm_call_codex.execute(prompt)
    print(f"结果: {result}")


async def test_stripped_newlines():
    """测试去掉换行符后的 prompt"""
    prompt = """请直接回复我下面的内容：111111
22222
"""
    prompt = prompt.replace("\n", "")
    print("=== 去掉换行符 ===")
    result = await llm_call_codex.execute(prompt)
    print(f"结果: {result}")


async def main():
    await test_with_newlines()
    await test_without_newlines()
    await test_stripped_newlines()


if __name__ == "__main__":
    asyncio.run(main())

#     === 带换行符 ===
# 结果: AgentResult(text='111111', session_id='019e6e4d-2318-7be2-a65a-cff443dbdc1d', timestamp='2026-05-28T19:17:05.417098', agent_name='llm_call_codex', platform=<AgentPlatform.CODEX: 'codex'>, role_type=<RoleType.TEAM_MEMBER: 'team_member'>, usage={'input_tokens': 26883, 'cached_input_tokens': 12927, 'output_tokens': 222, 'reasoning_output_tokens': 0})
# === 无换行符 ===
# 结果: AgentResult(text='11111122222', session_id='019e6e4d-61f5-7d20-8d85-32764d973462', timestamp='2026-05-28T19:17:28.625151', agent_name='llm_call_codex', platform=<AgentPlatform.CODEX: 'codex'>, role_type=<RoleType.TEAM_MEMBER: 'team_member'>, usage={'input_tokens': 27275, 'cached_input_tokens': 12929, 'output_tokens': 172, 'reasoning_output_tokens': 0})
# === 去掉换行符 ===
# 结果: AgentResult(text='11111122222', session_id='019e6e4d-bc85-7372-94f7-24a607720bc4', timestamp='2026-05-28T19:17:44.364429', agent_name='llm_call_codex', platform=<AgentPlatform.CODEX: 'codex'>, role_type=<RoleType.TEAM_MEMBER: 'team_member'>, usage={'input_tokens': 27270, 'cached_input_tokens': 12929, 'output_tokens': 133, 'reasoning_output_tokens': 0})
