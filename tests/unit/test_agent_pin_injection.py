"""
Agent Pin 消息注入功能测试

测试契约：
1. Agent._get_pinned_messages_content() - 读取 pins.json 并生成 XML 片段（用于 runtime 注入）
2. Agent._generate_runtime_content() - 将 Pin 消息包含在 runtime 内容中
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents_hub.core.agent.base_agent import Agent

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


# ==================== _get_pinned_messages_content() 测试 ====================


class TestGetPinnedMessagesContent:
    """Agent._get_pinned_messages_content() 契约测试"""

    def test_returns_empty_when_pins_file_not_exists(self):
        """
        契约：当 pins.json 不存在时，返回空字符串
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            agent = create_mock_agent(session_path)

            result = agent._get_pinned_messages_content()

            assert result == "", "pins.json 不存在时应返回空字符串"

    def test_returns_empty_when_pins_file_is_empty(self):
        """
        契约：当 pins.json 为空或无有效数据时，返回空字符串
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"
            pins_path.write_text("[]", encoding="utf-8")

            agent = create_mock_agent(session_path)

            result = agent._get_pinned_messages_content()

            assert result == "", "pins.json 为空时应返回空字符串"

    def test_generates_content_with_single_pin(self):
        """
        契约：当有 Pin 消息时，生成 XML 格式的内容片段
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

            result = agent._get_pinned_messages_content()

            # 验证包含必要的结构
            assert "<pinned_messages>" in result, "缺少开始标签"
            assert "</pinned_messages>" in result, "缺少结束标签"
            assert "以下是用户置顶的重要消息" in result, "缺少说明文字"
            assert "[user]: 规则：所有代码必须添加类型注解" in result, "缺少消息内容"

    def test_sorts_pins_by_pinned_at_ascending(self):
        """
        契约：Pin 消息按 pinned_at 升序排列（最早 pin 的在前）
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

            result = agent._get_pinned_messages_content()

            # 验证顺序：通过索引位置判断
            idx_first = result.index("第一条规则")
            idx_second = result.index("第二条规则")
            idx_third = result.index("第三条规则")

            assert idx_first < idx_second < idx_third, "Pin 消息应按时间升序排列"

    def test_returns_empty_on_file_read_error(self):
        """
        契约：当读取文件失败时，返回空字符串（异常处理）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"
            pins_path.write_text("[]", encoding="utf-8")

            agent = create_mock_agent(session_path)

            with patch("builtins.open", side_effect=OSError("Mock read error")):
                result = agent._get_pinned_messages_content()

                assert result == "", "文件读取失败时应返回空字符串"


# ==================== runtime 注入 Pin 消息测试 ====================


class TestRuntimePinInjection:
    """Agent._generate_runtime_content() 中 Pin 消息注入的契约测试"""

    def test_pins_included_in_runtime_content(self):
        """
        契约：Pin 消息被包含在 _generate_runtime_content() 输出中

        验证方式：
        1. 创建包含 Pin 消息的 pins.json
        2. 调用 _generate_runtime_content()
        3. 验证输出包含 pinned_messages 标签和内容
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

            result = agent._generate_runtime_content()

            assert "<pinned_messages>" in result, "runtime 内容应包含 pinned_messages 标签"
            assert "重要规则：必须测试" in result, "Pin 消息内容应出现在 runtime 中"

    def test_no_pins_section_when_empty(self):
        """
        契约：无 Pin 消息时，runtime 内容不包含 pinned_messages 标签
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            agent = create_mock_agent(session_path)

            result = agent._generate_runtime_content()

            assert "<pinned_messages>" not in result, "无 Pin 时不应出现 pinned_messages 标签"


# ==================== 幂等性测试 ====================


class TestPinInjectionIdempotency:
    """Pin 消息注入的幂等性测试"""

    def test_runtime_content_idempotent_across_calls(self):
        """
        契约：多次调用 _generate_runtime_content() 返回相同结果

        验证方式：
        1. 创建包含 Pin 消息的 pins.json
        2. 连续调用 _generate_runtime_content() 多次
        3. 验证每次返回内容一致
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"

            pins = [
                {
                    "speaker": "user",
                    "content": "幂等性测试规则",
                    "pinned_at": "2026-06-07T10:00:00",
                }
            ]
            pins_path.write_text(json.dumps(pins, ensure_ascii=False), encoding="utf-8")

            agent = create_mock_agent(session_path)

            result1 = agent._generate_runtime_content()
            result2 = agent._generate_runtime_content()
            result3 = agent._generate_runtime_content()

            assert result1 == result2 == result3, "多次调用应返回一致结果"

    def test_pinned_messages_content_idempotent(self):
        """
        契约：多次调用 _get_pinned_messages_content() 返回相同结果
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"

            pins = [
                {
                    "speaker": "user",
                    "content": "规则A",
                    "pinned_at": "2026-06-07T10:00:00",
                },
                {
                    "speaker": "Manager",
                    "content": "规则B",
                    "pinned_at": "2026-06-07T11:00:00",
                },
            ]
            pins_path.write_text(json.dumps(pins, ensure_ascii=False), encoding="utf-8")

            agent = create_mock_agent(session_path)

            result1 = agent._get_pinned_messages_content()
            result2 = agent._get_pinned_messages_content()

            assert result1 == result2, "多次调用应返回一致结果"
            assert result1 != "", "有 pin 时不应返回空字符串"

    def test_inject_runtime_idempotent(self):
        """
        契约：多次调用 _inject_runtime_to_files() 后文件内容一致

        验证方式：
        1. 创建包含 Pin 消息的 pins.json 和 CLAUDE.md
        2. 多次调用 _inject_runtime_to_files()
        3. 验证文件内容一致（不会累积重复）
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = Path(tmpdir)
            pins_path = session_path / "pins.json"

            pins = [
                {
                    "speaker": "user",
                    "content": "注入幂等性测试",
                    "pinned_at": "2026-06-07T10:00:00",
                }
            ]
            pins_path.write_text(json.dumps(pins, ensure_ascii=False), encoding="utf-8")

            agent = create_mock_agent(session_path)
            agent.role_config.work_root = tmpdir

            # 创建带标记的 CLAUDE.md
            claude_md = Path(tmpdir) / "CLAUDE.md"
            claude_md.write_text(
                "# Test\n\n<AGENT_RUNTIME>\nold content\n</AGENT_RUNTIME>\n",
                encoding="utf-8",
            )

            # 多次注入
            agent._inject_runtime_to_files()
            content_after_first = claude_md.read_text(encoding="utf-8")

            agent._inject_runtime_to_files()
            content_after_second = claude_md.read_text(encoding="utf-8")

            agent._inject_runtime_to_files()
            content_after_third = claude_md.read_text(encoding="utf-8")

            assert content_after_first == content_after_second == content_after_third, (
                "多次注入后文件内容应一致（不会累积重复）"
            )
            assert "注入幂等性测试" in content_after_first, "Pin 内容应被注入"
            assert content_after_first.count("<pinned_messages>") == 1, "pinned_messages 标签应只出现一次"
