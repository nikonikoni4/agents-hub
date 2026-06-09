"""OpenCode 集成测试

直接调用 OpenCode CLI 进行测试，验证端到端流程。
"""

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.agent_bridge.models import AgentEventType
from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.roles.models import RoleConfig


@pytest.fixture
def bridge():
    return AgentBridge()


@pytest.fixture
def opencode_config():
    """创建 OpenCode 角色配置"""
    return RoleConfig(
        name="nico",
        platform=AgentPlatform.OPENCODE,
        role_type=RoleType.TEAM_MEMBER,
        work_root="D:\\测试",
    )


class TestOpenCodeIntegration:
    """OpenCode 集成测试"""

    @pytest.mark.asyncio
    async def test_opencode_non_stream_execute(self, bridge, opencode_config):
        """
        契约：使用 AgentBridge 非流式调用 OpenCode

        验证方式：
        1. 创建 OpenCode 角色配置
        2. 调用 bridge.execute
        3. 验证返回 AgentResult
        4. 验证文本内容不为空
        5. 验证 session_id 被正确返回

        如果失败，说明：OpenCode 集成存在问题
        """
        result = await bridge.execute(
            prompt="你的名字是什么？用一句话回答",
            config=opencode_config,
            system_prompt="nico",
        )

        # 验证结果
        assert result is not None
        assert result.text, "返回文本不应为空"
        assert result.agent_name == "nico"
        assert result.platform == AgentPlatform.OPENCODE
        assert result.role_type == RoleType.TEAM_MEMBER
        assert result.session_id, "session_id 不应为空"

        # 验证包含 nico 关键词（因为 agent 文件内容是"你的名字是nico"）
        assert "nico" in result.text.lower(), f"回答应包含 'nico'，实际回答: {result.text}"

        print(f"\n[测试结果] Agent 回答: {result.text}")
        print(f"[测试结果] Session ID: {result.session_id}")

    @pytest.mark.asyncio
    async def test_opencode_stream_execute(self, bridge, opencode_config):
        """
        契约：使用 AgentBridge 流式调用 OpenCode

        验证方式：
        1. 创建 OpenCode 角色配置
        2. 调用 bridge.execute_stream
        3. 验证返回事件流
        4. 验证包含 text_delta 事件

        如果失败，说明：OpenCode 流式输出存在问题
        """
        events = []
        async for event in bridge.execute_stream(
            prompt="你的名字是什么？用一句话回答",
            config=opencode_config,
            system_prompt="nico",
        ):
            events.append(event)
            print(f"\n[测试结果] 事件类型: {event.type}, 内容: {event.content}")

        # 验证事件
        assert len(events) > 0, "应至少返回一个事件"

        # 验证包含 text_delta 事件
        text_events = [e for e in events if e.type == AgentEventType.TEXT_DELTA]
        assert len(text_events) > 0, "应包含 text_delta 事件"

        # 验证文本内容
        full_text = "".join(e.content.get("text", "") for e in text_events)
        assert "nico" in full_text.lower(), f"回答应包含 'nico'，实际回答: {full_text}"

        # 验证事件属性
        for event in events:
            assert event.agent_name == "nico"
            assert event.platform == AgentPlatform.OPENCODE
            assert event.role_type == RoleType.TEAM_MEMBER

        print(f"\n[测试结果] 完整文本: {full_text}")
        print(f"[测试结果] 事件数量: {len(events)}")

    @pytest.mark.asyncio
    async def test_opencode_with_different_agent(self, bridge):
        """
        契约：使用不同的 agent 名称调用 OpenCode

        验证方式：
        1. 创建配置，使用 asdfgh agent
        2. 调用 bridge.execute
        3. 验证返回正确的 agent 名称

        如果失败，说明：agent 名称传递存在问题
        """
        config = RoleConfig(
            name="asdfgh",
            platform=AgentPlatform.OPENCODE,
            role_type=RoleType.TEAM_MEMBER,
            work_root="D:\\测试",
        )

        result = await bridge.execute(
            prompt="你的名字是什么？用一句话回答",
            config=config,
            system_prompt="asdfgh",
        )

        # 验证结果
        assert result is not None
        assert result.text, "返回文本不应为空"
        assert "asdfgh" in result.text.lower(), f"回答应包含 'asdfgh'，实际回答: {result.text}"

        print(f"\n[测试结果] Agent 回答: {result.text}")
