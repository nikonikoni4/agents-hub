"""
Foundation 层单元测试

契约：
1. models.py: 枚举值正确
2. message.py: AgentMessage 默认值自动填充
3. exceptions.py: 异常继承链、构造器、to_mcp_response
4. renderer.py: wrap_xml, render_for_llm, render_for_chat, parse_chat_input
5. constants.py: 常量值正确
"""

import pytest

from agents_hub.core.foundation.constants import LOCAL_DATA_PATH, MAX_TOKEN
from agents_hub.core.foundation.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    AgentsHubError,
    AgentTimeoutError,
    CompactionError,
    FileSystemError,
    GroupChatNotFoundError,
    InvalidMessageError,
    MessageDeliveryError,
)
from agents_hub.core.foundation.message import AgentMessage
from agents_hub.core.foundation.models import CallStatus, GroupChatType, MessageType, SessionType
from agents_hub.core.foundation.renderer import (
    Tag,
    parse_chat_input,
    render_for_chat,
    render_for_llm,
    wrap_xml,
)

# ==================== models.py ====================


class TestModels:
    """测试枚举值定义"""

    def test_session_type_values(self):
        """契约：SessionType 包含 MAIN 和 BTW"""
        assert SessionType.MAIN.value == "main"
        assert SessionType.BTW.value == "btw"

    def test_message_type_values(self):
        """契约：MessageType 包含 TASK 和 NOTIFICATION"""
        assert MessageType.TASK.value == "task"
        assert MessageType.NOTIFICATION.value == "notification"

    def test_call_status_values(self):
        """契约：CallStatus 包含完整状态机"""
        assert CallStatus.PENDING.value == "pending"
        assert CallStatus.RUNNING.value == "running"
        assert CallStatus.COMPLETED.value == "completed"
        assert CallStatus.FAILED.value == "failed"
        assert CallStatus.TIMEOUT.value == "timeout"

    def test_group_chat_type_values(self):
        """契约：GroupChatType 包含 SEQUENCE_EXECUTE 和 MANAGER_ORCHESTRATE"""
        assert GroupChatType.SEQUENCE_EXECUTE.value == "sequence_execute"
        assert GroupChatType.MANAGER_ORCHESTRATE.value == "manager_orchestrate"


# ==================== message.py ====================


class TestAgentMessage:
    """测试 AgentMessage 数据类"""

    def test_default_timestamp(self):
        """契约：创建时自动填充 timestamp 默认值"""
        msg = AgentMessage(
            call_id="c1", content="hi", send_from="a", send_to="b"
        )
        assert msg.timestamp is not None

    def test_default_session_type(self):
        """契约：session_type 默认为 MAIN"""
        msg = AgentMessage(
            call_id="c1", content="hi", send_from="a", send_to="b"
        )
        assert msg.session_type == SessionType.MAIN

    def test_default_message_type(self):
        """契约：message_type 默认为 NOTIFICATION"""
        msg = AgentMessage(
            call_id="c1", content="hi", send_from="a", send_to="b"
        )
        assert msg.message_type == MessageType.NOTIFICATION


# ==================== exceptions.py ====================


class TestExceptions:
    """测试异常类"""

    def test_agents_hub_error_to_mcp_response(self):
        """契约：to_mcp_response 返回标准错误格式"""
        err = AgentsHubError(
            message="test error",
            error_code="TEST_ERROR",
            details={"key": "val"},
        )
        resp = err.to_mcp_response()
        assert resp["success"] is False
        assert resp["error_code"] == "TEST_ERROR"
        assert resp["message"] == "test error"
        assert resp["details"] == {"key": "val"}

    def test_agents_hub_error_details_default_empty(self):
        """契约：details 默认为空 dict"""
        err = AgentsHubError(message="m", error_code="E")
        assert err.details == {}

    def test_agents_hub_error_is_exception(self):
        """契约：AgentsHubError 继承 Exception"""
        assert issubclass(AgentsHubError, Exception)

    def test_all_subclasses_inherit_agents_hub_error(self):
        """契约：所有子类继承 AgentsHubError"""
        subclasses = [
            AgentNotFoundError,
            GroupChatNotFoundError,
            MessageDeliveryError,
            AgentExecutionError,
            AgentTimeoutError,
            InvalidMessageError,
            FileSystemError,
            CompactionError,
        ]
        for cls in subclasses:
            assert issubclass(cls, AgentsHubError), f"{cls.__name__} 不是 AgentsHubError 子类"

    def test_agent_not_found_error_details(self):
        """契约：AgentNotFoundError 填充 agent_name 到 details"""
        err = AgentNotFoundError("my_agent")
        assert err.error_code == "AGENT_NOT_FOUND"
        assert err.details["agent_name"] == "my_agent"
        assert "my_agent" in str(err)

    def test_group_chat_not_found_error_details(self):
        """契约：GroupChatNotFoundError 填充 group_chat_id 到 details"""
        err = GroupChatNotFoundError("gc_123")
        assert err.error_code == "GROUP_CHAT_NOT_FOUND"
        assert err.details["group_chat_id"] == "gc_123"

    def test_message_delivery_error_details(self):
        """契约：MessageDeliveryError 填充 send_from, send_to, reason"""
        err = MessageDeliveryError(reason="queue full", send_from="a", send_to="b")
        assert err.error_code == "MESSAGE_DELIVERY_FAILED"
        assert err.details["send_from"] == "a"
        assert err.details["send_to"] == "b"
        assert err.details["reason"] == "queue full"

    def test_agent_execution_error_details(self):
        """契约：AgentExecutionError 填充 agent_name, reason"""
        err = AgentExecutionError(
            agent_name="agent1", reason="crash", session_id="s1", platform="claude"
        )
        assert err.error_code == "AGENT_EXECUTION_FAILED"
        assert err.details["agent_name"] == "agent1"
        assert err.details["reason"] == "crash"

    def test_agent_timeout_error_details(self):
        """契约：AgentTimeoutError 填充 agent_name, timeout_seconds"""
        err = AgentTimeoutError(agent_name="agent1", timeout_seconds=30)
        assert err.error_code == "AGENT_TIMEOUT"
        assert err.details["agent_name"] == "agent1"
        assert err.details["timeout_seconds"] == 30

    def test_invalid_message_error_details(self):
        """契约：InvalidMessageError 填充 reason"""
        err = InvalidMessageError(reason="empty content")
        assert err.error_code == "INVALID_MESSAGE"
        assert err.details["reason"] == "empty content"

    def test_file_system_error_details(self):
        """契约：FileSystemError 填充 operation, path, reason"""
        err = FileSystemError(operation="read", path="/tmp/f", reason="not found")
        assert err.error_code == "FILE_SYSTEM_ERROR"
        assert err.details["operation"] == "read"
        assert err.details["path"] == "/tmp/f"

    def test_compaction_error_details(self):
        """契约：CompactionError 填充 reason"""
        err = CompactionError(reason="LLM failed")
        assert err.error_code == "COMPACTION_FAILED"
        assert err.details["reason"] == "LLM failed"


# ==================== renderer.py ====================


class TestRenderer:
    """测试渲染函数"""

    def test_wrap_xml_basic(self):
        """契约：wrap_xml 用 XML 标签包裹内容"""
        result = wrap_xml("tag", "content")
        assert result == "<tag>\ncontent\n</tag>"

    def test_wrap_xml_multiline(self):
        """契约：wrap_xml 正确包裹多行内容"""
        result = wrap_xml("t", "line1\nline2")
        assert result == "<t>\nline1\nline2\n</t>"

    def test_render_for_llm_format(self):
        """契约：render_for_llm 输出 <incoming_message> 包裹的格式，含平台标识"""
        msg = AgentMessage(
            call_id="c1",
            content="hello",
            send_from="agent_a",
            send_to="agent_b",
        )
        result = render_for_llm(msg)
        assert result.startswith("<incoming_message>")
        assert result.endswith("</incoming_message>")
        assert "[Agents Hub 平台消息]" in result
        assert "来自：agent_a" in result
        assert "发送给：agent_b（你）" in result
        assert "内容：hello" in result

    def test_render_for_chat_format(self):
        """契约：render_for_chat 输出 @send_to content"""
        result = render_for_chat("from_agent", "to_agent", "hello")
        assert result == "@to_agent hello"

    def test_parse_chat_input_valid(self):
        """契约：parse_chat_input 正确解析 @xxx content"""
        send_to, content = parse_chat_input("@agent hello world")
        assert send_to == "agent"
        assert content == "hello world"

    def test_parse_chat_input_no_content(self):
        """契约：parse_chat_input 解析 @xxx（无内容）"""
        send_to, content = parse_chat_input("@agent")
        assert send_to == "agent"
        assert content == ""

    def test_parse_chat_input_no_at_raises(self):
        """契约：无 @ 前缀抛 InvalidMessageError"""
        with pytest.raises(InvalidMessageError):
            parse_chat_input("hello world")

    def test_parse_chat_input_empty_at_raises(self):
        """契约：@ 后无名称抛 InvalidMessageError"""
        with pytest.raises(InvalidMessageError):
            parse_chat_input("@ hello")

    def test_tag_constants(self):
        """契约：Tag 常量值正确"""
        assert Tag.GROUP_HISTORY == "group_chat_history"
        assert Tag.RECENT_MESSAGES == "recent_messages"
        assert Tag.INCOMING_MESSAGE == "incoming_message"
        assert Tag.SUMMARY_OVERALL == "overall_summary"
        assert Tag.SUMMARY_FOR_YOU == "summary_for_you"


# ==================== constants.py ====================


class TestConstants:
    """测试常量值"""

    def test_max_token_value(self):
        """契约：MAX_TOKEN 为 1000"""
        assert MAX_TOKEN == 1000

    def test_local_data_path_value(self):
        """契约：LOCAL_DATA_PATH 为 'local_data'"""
        assert LOCAL_DATA_PATH == "local_data"
