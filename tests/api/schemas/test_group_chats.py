import pytest
from datetime import datetime
from pydantic import ValidationError
from agents_hub.api.schemas.group_chats import (
    GroupChatCreate,
    GroupChatInfo,
    GroupChatSummary,
    GroupChatMember,
)


def test_group_chat_create_valid():
    """测试有效的创建请求"""
    data = {
        "team_members": ["Leader", "Worker1"],
        "project_path": "/path/to/project",
        "group_chat_name": "My Team",
    }
    schema = GroupChatCreate(**data)
    assert schema.team_members == ["Leader", "Worker1"]
    assert schema.project_path == "/path/to/project"
    assert schema.group_chat_name == "My Team"


def test_group_chat_create_without_name():
    """测试创建请求可以不提供群聊名"""
    data = {
        "team_members": ["Leader"],
        "project_path": "/path/to/project",
    }
    schema = GroupChatCreate(**data)
    assert schema.group_chat_name is None


def test_group_chat_create_empty_members_fails():
    """测试空成员列表应该失败"""
    data = {
        "team_members": [],
        "project_path": "/path/to/project",
    }
    with pytest.raises(ValidationError) as exc_info:
        GroupChatCreate(**data)
    assert "at least 1 item" in str(exc_info.value).lower()


def test_group_chat_info_valid():
    """测试群聊详细信息响应"""
    data = {
        "group_chat_id": "gc_123",
        "group_chat_name": "Test Group",
        "project_path": "/path/to/project",
        "created_at": datetime(2026, 6, 3, 10, 0, 0),
        "group_type": "MANAGER_ORCHESTRATE",
        "is_active": True,
    }
    schema = GroupChatInfo(**data)
    assert schema.group_chat_id == "gc_123"
    assert schema.is_active is True


def test_group_chat_summary_valid():
    """测试群聊摘要响应"""
    data = {
        "group_chat_id": "gc_123",
        "group_chat_name": "Test Group",
        "project_path": "/path/to/project",
        "is_active": False,
        "created_at": datetime(2026, 6, 3, 10, 0, 0),
    }
    schema = GroupChatSummary(**data)
    assert schema.project_path == "/path/to/project"


def test_group_chat_member_valid():
    """测试群聊成员响应"""
    data = {
        "name": "Leader",
        "main_session": "session_123",
        "btw_session": ["btw_1", "btw_2"],
        "cwd": "/path/to/project",
        "use_docker": False,
    }
    schema = GroupChatMember(**data)
    assert schema.name == "Leader"
    assert len(schema.btw_session) == 2


def test_group_chat_member_optional_fields():
    """测试成员可选字段"""
    data = {
        "name": "Worker1",
        "main_session": None,
        "btw_session": [],
        "cwd": None,
    }
    schema = GroupChatMember(**data)
    assert schema.use_docker is False  # 默认值
    assert schema.main_session is None
