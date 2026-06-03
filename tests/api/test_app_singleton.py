"""测试 GroupChatManager 单例初始化"""

from agents_hub.api.app import get_group_chat_manager
from agents_hub.core.orchestration import GroupChatManager


def test_get_group_chat_manager_returns_instance():
    """测试 get_group_chat_manager 返回 GroupChatManager 实例"""
    manager = get_group_chat_manager()
    assert isinstance(manager, GroupChatManager)


def test_get_group_chat_manager_returns_same_instance():
    """测试多次调用返回同一个实例（单例）"""
    manager1 = get_group_chat_manager()
    manager2 = get_group_chat_manager()
    assert manager1 is manager2
