"""测试 AgentMember 的 use_docker 字段"""

from agents_hub.core.context.group_chat_session import AgentMember


def test_agent_session_info_default_use_docker():
    """测试 use_docker 默认值为 False"""
    info = AgentMember()
    assert info.use_docker is False


def test_agent_session_info_with_use_docker():
    """测试设置 use_docker"""
    info = AgentMember(use_docker=True)
    assert info.use_docker is True
