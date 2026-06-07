"""
Agent Pin 消息注入功能测试

测试契约：
1. Agent._get_pinned_messages_prompt() - 读取 pins.json 并生成提示词
2. Agent._process_message() - 将 Pin 消息注入到 MAIN 会话的提示词中
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents_hub.core.agent.base_agent import Agent
from agents_hub.core.foundation import AgentMessage, MessageType, SessionType


# ==================== 辅助函数 ====================


def create_mock_agent(session_path: Path) -> Agent:
    """创建用于测试的 Mock Agent

    Args:
        session_path: 群聊会话路径（包含 pins.json）

    Returns:
        配置好的 Mock Agent
    """
    # Mock Role
    mock_role = MagicMock()
    mock_role.get_role_config.return_value = MagicMock(
        name="TestAgent",
        role_type=MagicMock(value="worker"),
        work_root=None,
    )

    # Mock GroupChatContext
    mock_context = MagicMock()
    mock_context.repository.group_chat_session_path = str(session_path)
    mock_context.agent_member_info = {}
    mock_context.group_chat_id = "test-chat-id"

    # Mock Dependencies
    mock_call_manager = MagicMock()
    mock_message_router = MagicMock()

    agent = Agent(
        role=mock_role,
        group_chat_context=mock_context,
        agent_call_manager=mock_call_manager,
        message_router=mock_message_router,
    )

    return agent


# ==================== _get_pinned_messages_prompt() 测试 ====================


class TestGetPinnedMessagesPrompt:
    """Agent._get_pinned_messages_prompt() 契约测试"""

    @pytest.mark.asyncio
    async def test_returns_empty_when_pins_file_not_exists(self):
        """
        契约：当 pins.json 不存在时，返回空字符串

        验证方式：
        1. 创建临时目录（不创建 pins.json）
        2. 调用 _get_pinned_messages_prompt()
        3. 验证返回空字符串

        如果失败，说明：Agent 没有正确处理文件不存在的情况
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            agent = create_mock_agent(session_path)

            result = await agent._get_pinned_messages_prompt()

            assert result == "", "pins.json 不存在时应返回空字符串"

    @pytest.mark.asyncio
    async def test_returns_empty_when_pins_file_is_empty(self):
        """
        契约：当 pins.json 为空或无有效数据时，返回空字符串

        验证方式：
        1. 创建临时目录和空的 pins.json
        2. 调用 _get_pinned_messages_prompt()
        3. 验证返回空字符串

        如果失败，说明：Agent 没有正确处理空文件的情况
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"
            pins_path.write_text("[]", encoding="utf-8")

            agent = create_mock_agent(session_path)

            result = await agent._get_pinned_messages_prompt()

            assert result == "", "pins.json 为空时应返回空字符串"

    @pytest.mark.asyncio
    async def test_generates_prompt_with_single_pin(self):
        """
        契约：当有 Pin 消息时，生成 XML 格式的提示词

        验证方式：
        1. 创建包含单条 Pin 消息的 pins.json
        2. 调用 _get_pinned_messages_prompt()
        3. 验证返回的提示词包含 XML 标签和消息内容

        如果失败，说明：提示词生成逻辑有问题
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"

            pins = [
                {
                    "speaker": "user",
                    "content": "规则：所有代码必须添加类型注解",
                    "pinned_at": "2026-06-07T10:00:00",
                }
            ]
            pins_path.write_text(json.dumps(pins, ensure_ascii=False), encoding="utf-8")

            agent = create_mock_agent(session_path)

            result = await agent._get_pinned_messages_prompt()

            # 验证包含必要的结构
            assert "<pinned_messages>" in result, "缺少开始标签"
            assert "</pinned_messages>" in result, "缺少结束标签"
            assert "以下是用户置顶的重要消息" in result, "缺少说明文字"
            assert "[user]: 规则：所有代码必须添加类型注解" in result, "缺少消息内容"

    @pytest.mark.asyncio
    async def test_sorts_pins_by_pinned_at_ascending(self):
        """
        契约：Pin 消息按 pinned_at 升序排列（最早 pin 的在前）

        验证方式：
        1. 创建包含多条 Pin 消息的 pins.json（时间乱序）
        2. 调用 _get_pinned_messages_prompt()
        3. 验证返回的提示词中消息按时间排序

        如果失败，说明：排序逻辑有问题
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"

            # 故意乱序
            pins = [
                {
                    "speaker": "Manager",
                    "content": "第二条规则",
                    "pinned_at": "2026-06-07T11:00:00",
                },
                {
                    "speaker": "user",
                    "content": "第一条规则",
                    "pinned_at": "2026-06-07T10:00:00",
                },
                {
                    "speaker": "Worker",
                    "content": "第三条规则",
                    "pinned_at": "2026-06-07T12:00:00",
                },
            ]
            pins_path.write_text(json.dumps(pins, ensure_ascii=False), encoding="utf-8")

            agent = create_mock_agent(session_path)

            result = await agent._get_pinned_messages_prompt()

            # 验证顺序：通过索引位置判断
            idx_first = result.index("第一条规则")
            idx_second = result.index("第二条规则")
            idx_third = result.index("第三条规则")

            assert idx_first < idx_second < idx_third, "Pin 消息应按时间升序排列"

    @pytest.mark.asyncio
    async def test_returns_empty_on_file_read_error(self):
        """
        契约：当读取文件失败时，返回空字符串（异常处理）

        验证方式：
        1. Mock aiofiles.open 抛出异常
        2. 调用 _get_pinned_messages_prompt()
        3. 验证返回空字符串（不崩溃）

        如果失败，说明：异常处理不完善
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"
            pins_path.write_text("[]", encoding="utf-8")

            agent = create_mock_agent(session_path)

            # Mock aiofiles.open 抛出异常
            with patch("aiofiles.open", side_effect=IOError("Mock read error")):
                result = await agent._get_pinned_messages_prompt()

                assert result == "", "文件读取失败时应返回空字符串"


# ==================== _process_message() Pin 注入测试 ====================


class TestProcessMessagePinInjection:
    """Agent._process_message() 中 Pin 消息注入的契约测试"""

    @pytest.mark.asyncio
    async def test_injects_pins_into_main_session_prompt(self):
        """
        契约：在 MAIN 会话中，Pin 消息会被注入到提示词中

        验证方式：
        1. 创建包含 Pin 消息的 pins.json
        2. Mock Agent.execute() 捕获传入的 prompt
        3. 调用 _process_message()（MAIN 会话）
        4. 验证传入的 prompt 包含 Pin 消息内容

        如果失败，说明：Pin 注入逻辑未正确触发
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"

            pins = [
                {
                    "speaker": "user",
                    "content": "重要规则：必须测试",
                    "pinned_at": "2026-06-07T10:00:00",
                }
            ]
            pins_path.write_text(json.dumps(pins, ensure_ascii=False), encoding="utf-8")

            agent = create_mock_agent(session_path)

            # Mock 依赖
            agent.agent_context.get_context = AsyncMock(return_value="")
            agent.execute = AsyncMock(return_value=MagicMock(text="done"))
            agent.agent_call_manager.update_status = MagicMock()

            # 构造消息
            msg = AgentMessage(
                call_id="test-call",
                send_from="user",
                send_to="TestAgent",
                content="执行任务",
                session_type=SessionType.MAIN,
                message_type=MessageType.TASK,
            )

            await agent._process_message(msg, "执行任务")

            # 验证 execute 被调用，且 prompt 包含 Pin 消息
            agent.execute.assert_called_once()
            called_prompt = agent.execute.call_args[0][0]

            assert "<pinned_messages>" in called_prompt, "MAIN 会话的 prompt 应包含 Pin 消息"
            assert "重要规则：必须测试" in called_prompt, "Pin 消息内容应被注入"

    @pytest.mark.asyncio
    async def test_does_not_inject_pins_into_btw_session(self):
        """
        契约：在 BTW（单聊）会话中，不注入 Pin 消息

        验证方式：
        1. 创建包含 Pin 消息的 pins.json
        2. Mock Agent.btw_execute() 捕获传入的 prompt
        3. 调用 _process_message()（BTW 会话）
        4. 验证传入的 prompt 不包含 Pin 消息内容

        如果失败，说明：Pin 注入逻辑作用范围错误
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"

            pins = [
                {
                    "speaker": "user",
                    "content": "这条不应该出现在单聊中",
                    "pinned_at": "2026-06-07T10:00:00",
                }
            ]
            pins_path.write_text(json.dumps(pins, ensure_ascii=False), encoding="utf-8")

            agent = create_mock_agent(session_path)

            # Mock 依赖
            agent.btw_execute = AsyncMock(return_value=MagicMock(text="done"))
            agent.agent_call_manager.update_status = MagicMock()

            # 构造 BTW 消息
            msg = AgentMessage(
                call_id="test-call",
                send_from="user",
                send_to="TestAgent",
                content="单聊任务",
                session_type=SessionType.BTW,
                message_type=MessageType.NOTIFICATION,
            )

            await agent._process_message(msg, "单聊任务")

            # 验证 btw_execute 被调用，且 prompt 不包含 Pin 消息
            agent.btw_execute.assert_called_once()
            called_prompt = agent.btw_execute.call_args[0][0]

            assert "<pinned_messages>" not in called_prompt, "BTW 会话不应注入 Pin 消息"
