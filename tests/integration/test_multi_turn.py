"""AgentBridge 多轮对话集成测试

测试 Claude 和 Codex 的上下文记忆能力：
1. 第一轮：让 agent 给出一个名字
2. 第二轮：让 agent 回忆第一轮给出的名字

需要实际调用 CLI，未安装则测试失败。
"""

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.agent_bridge.models import AgentPlatform
from agents_hub.roles.models import RoleConfig


@pytest.fixture
def bridge():
    return AgentBridge()


@pytest.fixture
def claude_config():
    return RoleConfig(
        name="test_claude",
        platform=AgentPlatform.CLAUDE,
    )


@pytest.fixture
def codex_config():
    return RoleConfig(
        name="test_codex",
        platform=AgentPlatform.CODEX,
        work_root="D:/desktop/软件开发/test-codex/role-xiaoli",
    )


async def _multi_turn_test(bridge: AgentBridge, config: RoleConfig):
    """通用多轮对话测试逻辑"""
    # 第一轮：自我介绍
    first_result = await bridge.execute("你好，我是nico", config)
    first_text = first_result.text.strip()
    assert first_text, "第一轮回复不应为空"

    # 提取 session_id
    session_id = first_result.session_id
    assert session_id, f"第一轮应返回 session_id，实际: '{session_id}'"

    # 第二轮：询问名字
    second_result = await bridge.execute("我的名字是什么？", config, session_id=session_id)
    second_text = second_result.text.strip()
    assert second_text, "第二轮回复不应为空"

    # 验证上下文记忆：第二轮应回答 "nico"
    assert "nico" in second_text.lower(), (
        f"上下文记忆失败：第二轮未记住名字\n  第一轮: 你好，我是nico\n  第二轮回复: {second_text}"
    )


@pytest.mark.asyncio
async def test_claude_multi_turn(bridge, claude_config):
    """测试 Claude 多轮对话上下文记忆"""
    await _multi_turn_test(bridge, claude_config)


@pytest.mark.asyncio
async def test_codex_multi_turn(bridge, codex_config):
    """测试 Codex 多轮对话上下文记忆"""
    await _multi_turn_test(bridge, codex_config)
