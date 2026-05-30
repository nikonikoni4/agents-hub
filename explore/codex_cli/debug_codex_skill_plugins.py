"""调试 Codex skill/plugins 相关功能"""
import asyncio

from agents_hub.agent_bridge import AgentBridge
from agents_hub.roles import RoleManager
from agents_hub.config.types import AgentPlatform, RoleType

# 通过 RoleManager 创建 role，再获取 RoleConfig
role_manager = RoleManager()
role_manager.create_role(
    "codex_test_plugins",
    AgentPlatform.CODEX,
    type=RoleType.TEAM_MEMBER,
    description="用于测试 codex skill/plugins 的角色",
)
role = role_manager.get_role("codex_test_plugins")
test_config = role.get_role_config()

# 创建 AgentBridge 实例
agent_bridge = AgentBridge()

# 导出 exec 实例
llm_codex_test_plugins = agent_bridge


async def test_basic_exec():
    """测试基本的 exec 调用"""
    prompt = "你目前加载的skill列表有哪些内容？只需要skill列表不需要工具，和mcp。是否有deep-answer skill?"

    print("=== 基本调用 ===")
    result = await agent_bridge.execute(prompt, test_config)
    print(f"  结果: {result}")


async def main():
    await test_basic_exec()


if __name__ == "__main__":
    asyncio.run(main())
