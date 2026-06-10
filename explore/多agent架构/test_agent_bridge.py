"""测试通过 AgentBridge 调用，模拟实际场景"""

import asyncio
import sys

sys.path.insert(0, "D:/desktop/软件开发/agents-hub")

from agents_hub.roles import RoleManager
from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.roles.models import RoleType
from tests.explore.多agent架构.team import Agent


async def test_agent_bridge_call():
    """通过 AgentBridge 调用，使用 llm_call_codex"""

    # 获取 llm_call_codex 角色
    role_manager = RoleManager()
    llm_call_codex_role = role_manager.get_role("llm_call_codex")
    llm_call_codex = Agent(llm_call_codex_role)

    print("=" * 70)
    print("测试通过 AgentBridge 调用（使用 llm_call_codex）")
    print("=" * 70)
    print(f"角色配置:")
    print(f"  name: {llm_call_codex.role_config.name}")
    print(f"  platform: {llm_call_codex.role_config.platform}")
    print(f"  work_root: {llm_call_codex.role_config.work_root}")
    print("=" * 70)

    prompt = """请总结以下对话内容，并以 JSON 格式输出。对话内容：[Leader]: 你好！我是你的AI助手，将协助你指挥小李、小赵和小王三位团队成员，高效完成你分配的各项任务。[小李]: 你好！我是这个多智能体团队中的一名AI助手，主要负责协助团队成员进行软件开发、代码维护和技术研究等工作。[小赵]: 我会先加载会话要求的基础技能说明，确认本轮应遵守的工作方式。我是 Codex，负责在当前 workspace 里协助团队完成代码、文档和工程验证工作，会遵守 Leader 的安排并和小李、小王协同推进任务。[小王]: 你好！我是AI编程助手，擅长代码编写、调试和架构设计，由Leader直接指导工作，随时准备为团队提供技术支持。[Leader]: 大家好！我们接到一个新项目：开发一个电商平台的用户管理系统。这个系统需要支持用户注册、登录、个人信息管理、订单历史查询等功能。预计开发周期是3周。[Leader]: 小李，你负责前端部分，需要设计用户友好的界面。小赵，你负责后端API和数据库设计。小王，你负责制定测试计划和执行测试。大家有什么问题吗？[小李]: 收到！我有几个问题：1. 这个系统需要支持移动端吗？2. UI设计风格有什么要求？3. 需要支持第三方登录（如微信、支付宝）吗？[小赵]: 我也有一些技术问题：1. 用户量预期是多少？这关系到数据库设计。2. 需要支持分布式部署吗？3. 对于用户密码，我们使用什么加密方式？参与者及其职责：Leader-团队领导负责任务分配进度跟踪和技术决策，小李-负责前端开发和UI设计擅长React和Vue框架，小赵-负责后端开发和数据库设计擅长Python和PostgreSQL，小王-负责测试和质量保证擅长自动化测试和性能优化。请输出 JSON 格式，包含 summary 字段（对整体对话的简短总结1到2句话）和 agent_specific 字段（为每个参与者提取与其职责最相关的信息2到3句话），只输出 JSON 不要有其他文字。"""

    # 通过 llm_call_codex.execute 调用（内部使用 AgentBridge）
    result = await llm_call_codex.execute(prompt)

    print("\n返回结果:")
    print(result.text)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(test_agent_bridge_call())
