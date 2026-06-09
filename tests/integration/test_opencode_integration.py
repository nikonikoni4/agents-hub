"""OpenCode 集成测试

通过 RoleManager 创建角色，写入提示词，然后使用 AgentBridge 进行测试。
"""

import pytest

from agents_hub.agent_bridge.bridge import AgentBridge
from agents_hub.agent_bridge.models import AgentEventType
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.role_manager import RoleManager


@pytest.fixture
def bridge():
    return AgentBridge()


@pytest.fixture
def role_manager():
    return RoleManager()


@pytest.fixture
def opencode_role(role_manager):
    """创建 OpenCode 角色"""
    role_name = "test_opencode_agent"
    try:
        # 先删除已存在的测试角色
        role_manager.delete_role(role_name)
    except Exception:
        pass

    # 创建角色
    role = role_manager.create_role(
        name=role_name,
        platform=AgentPlatform.OPENCODE,
        description="测试用 OpenCode 角色",
    )

    # 写入 agent 提示词文件
    work_root = role._work_root
    agents_dir = work_root / "agents"
    agents_dir.mkdir(exist_ok=True)

    # 创建 agent 提示词文件
    agent_md = agents_dir / "test_agent.md"
    agent_md.write_text("你的名字是TestAgent，你是一个测试助手。", encoding="utf-8")

    yield role

    # 清理：删除测试角色
    try:
        role_manager.delete_role(role_name)
    except Exception:
        pass


class TestOpenCodeIntegration:
    """OpenCode 集成测试"""

    @pytest.mark.asyncio
    async def test_opencode_non_stream_execute(self, bridge, opencode_role):
        """
        契约：使用 RoleManager 创建角色，通过 AgentBridge 非流式调用 OpenCode

        验证方式：
        1. 通过 RoleManager 创建 OpenCode 角色
        2. 写入 agent 提示词文件
        3. 调用 bridge.execute
        4. 验证返回 AgentResult
        5. 验证文本内容不为空

        如果失败，说明：OpenCode 集成存在问题
        """
        config = opencode_role.get_role_config()
        result = await bridge.execute(
            prompt="你的名字是什么？用一句话回答",
            config=config,
            system_prompt="test_agent",
        )

        # 验证结果
        assert result is not None
        assert result.text, "返回文本不应为空"
        assert result.agent_name == "test_opencode_agent"
        assert result.platform == AgentPlatform.OPENCODE
        assert result.session_id, "session_id 不应为空"

        # 验证包含 TestAgent 关键词
        assert "testagent" in result.text.lower(), (
            f"回答应包含 'TestAgent'，实际回答: {result.text}"
        )

        print(f"\n[测试结果] Agent 回答: {result.text}")
        print(f"[测试结果] Session ID: {result.session_id}")

    @pytest.mark.asyncio
    async def test_opencode_stream_execute(self, bridge, opencode_role):
        """
        契约：使用 RoleManager 创建角色，通过 AgentBridge 流式调用 OpenCode

        验证方式：
        1. 通过 RoleManager 创建 OpenCode 角色
        2. 写入 agent 提示词文件
        3. 调用 bridge.execute_stream
        4. 验证返回事件流
        5. 验证包含 text_delta 事件

        如果失败，说明：OpenCode 流式输出存在问题
        """
        config = opencode_role.get_role_config()
        events = []
        async for event in bridge.execute_stream(
            prompt="你的名字是什么？用一句话回答",
            config=config,
            system_prompt="test_agent",
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
        assert "testagent" in full_text.lower(), f"回答应包含 'TestAgent'，实际回答: {full_text}"

        # 验证事件属性
        for event in events:
            assert event.agent_name == "test_opencode_agent"
            assert event.platform == AgentPlatform.OPENCODE

        print(f"\n[测试结果] 完整文本: {full_text}")
        print(f"[测试结果] 事件数量: {len(events)}")

    @pytest.mark.asyncio
    async def test_opencode_create_role_and_execute(self, bridge, role_manager):
        """
        契约：完整流程测试 - 创建角色、写入提示词、执行

        验证方式：
        1. 创建新的 OpenCode 角色
        2. 写入自定义提示词
        3. 执行调用
        4. 验证结果符合提示词
        5. 清理角色

        如果失败，说明：完整流程存在问题
        """
        role_name = "test_custom_agent"
        try:
            # 先删除已存在的测试角色
            role_manager.delete_role(role_name)
        except Exception:
            pass

        try:
            # 创建角色
            role = role_manager.create_role(
                name=role_name,
                platform=AgentPlatform.OPENCODE,
                description="自定义测试角色",
            )

            # 写入自定义提示词
            work_root = role._work_root
            agents_dir = work_root / "agents"
            agents_dir.mkdir(exist_ok=True)

            agent_md = agents_dir / "custom_agent.md"
            agent_md.write_text(
                "你是CustomBot，一个专业的编程助手。回答问题时要简洁。",
                encoding="utf-8",
            )

            # 执行调用
            config = role.get_role_config()
            result = await bridge.execute(
                prompt="你是谁？用一句话回答",
                config=config,
                system_prompt="custom_agent",
            )

            # 验证结果
            assert result is not None
            assert result.text, "返回文本不应为空"
            assert "custombot" in result.text.lower(), (
                f"回答应包含 'CustomBot'，实际回答: {result.text}"
            )

            print(f"\n[测试结果] Agent 回答: {result.text}")

        finally:
            # 清理
            try:
                role_manager.delete_role(role_name)
            except Exception:
                pass
