"""调试 claude skill/plugins 相关功能"""
import asyncio

from agents_hub.agent_bridge import AgentBridge
from agents_hub.roles import RoleManager
from agents_hub.config.types import AgentPlatform, RoleType

# 通过 RoleManager 创建 role，再获取 RoleConfig
role_manager = RoleManager()
role_manager.create_role(
    "claude_test_plugins",
    AgentPlatform.CLAUDE,
    type=RoleType.TEAM_MEMBER,
    description="用于测试 claude skill/plugins 的角色",
)
role = role_manager.get_role("claude_test_plugins")
test_config = role.get_role_config()

# 创建 AgentBridge 实例
agent_bridge = AgentBridge()

# 导出 exec 实例
llm_claude_test_plugins = agent_bridge


async def test_basic_exec():
    """测试基本的 exec 调用"""
    prompt = "你目前加载的skill列表有哪些内容？只需要skill列表不需要工具，和mcp。是否有deep-answer skill?"
#     结果: AgentResult(text='根据系统提示中的skill列表，当前可用的skill如下：\n\n| Skill名称 | 描述 |\n|-----------|------|\n| **update-config** | 配置Claude Code的settings.json，包括权限、环境变量、hooks等 |\n| **keybindings-help** | 自定义键盘快捷键，修改keybindings.json |\n| **simplify** | 审查代码的复用性、质量和效率，修复发现的问题 |\n| **fewer-permission-prompts** | 扫描常见只读工具调用，添加允许列表减少权限提示 |\n| **loop** | 按固定间隔重复运行提示或斜杠命令 |\n| **claude-api** | 构建、调试和优化Claude API/Anthropic SDK应用 |\n| **init** | 初始化新的CLAUDE.md文件 |\n| **review** | 审查Pull Request |\n| **security-review** | 完成当前分支待更改的安全审查 |\n\n**没有 `deep-answer` skill。**\n\n如果你需要某个特定功能的skill，可以告诉我，我可以帮你确认是否有替代方案或如何实现。', session_id='9f45bd88-9630-4ec2-aa15-ffb6e56cd86e', timestamp='2026-05-28T19:54:13.696032', agent_name='claude_test_plugins', platform=<AgentPlatform.CLAUDE: 'claude'>, role_type=<RoleType.TEAM_MEMBER: 'team_member'>, usage=None)       
# (agentshub_dev_env) PS D:\desktop\软件开发\agents-hub\tests\explore\多agent架构
    prompt = "你目前加载的插件有哪些,superpower是否可用"

    print("=== 基本调用 ===")
    result = await agent_bridge.execute(prompt, test_config)
    print(f"  结果: {result}")


async def main():
    await test_basic_exec()


if __name__ == "__main__":
    asyncio.run(main())
