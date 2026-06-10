"""GroupChatSession 测试

测试 add_message 的可选字段透传逻辑。
"""

from unittest.mock import MagicMock

from agents_hub.config.types import AgentPlatform
from agents_hub.core.context.group_chat_session import GroupChatSession


def _make_agent_result(**overrides):
    """构造最小可用的 mock AgentResult"""
    defaults = {
        "agent_name": "TestAgent",
        "text": "hello",
        "timestamp": "2026-06-09T10:00:00",
        "platform": AgentPlatform.CLAUDE,
        "cwd": None,
        "modified_files": None,
        "git_diff_range": None,
        "permission_request": None,
        "web_preview": None,
    }
    defaults.update(overrides)
    result = MagicMock()
    for k, v in defaults.items():
        setattr(result, k, v)
    return result


def test_add_message_includes_web_preview():
    """
    契约：add_message 将 web_preview 透传到消息 dict

    验证方式：
    1. 构造包含 web_preview 的 AgentResult
    2. 调用 add_message
    3. 验证消息 dict 包含 web_preview 字段

    如果失败，说明：add_message 未透传 web_preview
    """
    session = GroupChatSession()
    result = _make_agent_result(web_preview={"url": "http://localhost:3000", "title": "预览"})

    session.add_message(result)

    assert len(session.messages) == 1
    msg = session.messages[0]
    assert "web_preview" in msg
    assert msg["web_preview"]["url"] == "http://localhost:3000"
    assert msg["web_preview"]["title"] == "预览"


def test_add_message_omits_web_preview_when_none():
    """
    契约：add_message 在 web_preview 为 None 时不写入消息 dict

    验证方式：
    1. 构造 web_preview=None 的 AgentResult
    2. 调用 add_message
    3. 验证消息 dict 不包含 web_preview 字段

    如果失败，说明：add_message 未正确过滤 None 值
    """
    session = GroupChatSession()
    result = _make_agent_result(web_preview=None)

    session.add_message(result)

    assert len(session.messages) == 1
    msg = session.messages[0]
    assert "web_preview" not in msg


def test_add_message_web_preview_coexists_with_permission_request():
    """
    契约：web_preview 与 permission_request 可以共存

    验证方式：
    1. 构造同时包含 web_preview 和 permission_request 的 AgentResult
    2. 调用 add_message
    3. 验证两个字段都正确透传

    如果失败，说明：多个可选字段透传存在冲突
    """
    session = GroupChatSession()
    result = _make_agent_result(
        web_preview={"url": "http://localhost:3000", "title": "预览"},
        permission_request={
            "request_id": "r1",
            "title": "权限",
            "content": "请求",
            "status": "pending",
            "requested_by": "agent",
        },
    )

    session.add_message(result)

    msg = session.messages[0]
    assert "web_preview" in msg
    assert "permission_request" in msg
