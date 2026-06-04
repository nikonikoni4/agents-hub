import pytest
from datetime import datetime
from pydantic import ValidationError
from agents_hub.api.schemas.group_chats import (
    GroupChatCreate,
    GroupChatInfo,
    GroupChatMember,
)
from agents_hub.core.foundation.models import GroupChatType


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
        "group_type": GroupChatType.MANAGER_ORCHESTRATE,
        "is_active": True,
    }
    schema = GroupChatInfo(**data)
    assert schema.group_chat_id == "gc_123"
    assert schema.is_active is True
    assert schema.group_type == GroupChatType.MANAGER_ORCHESTRATE


def test_group_chat_info_all_group_types():
    """测试所有合法的 group_type 值"""
    base_data = {
        "group_chat_id": "gc_123",
        "group_chat_name": "Test Group",
        "project_path": "/path/to/project",
        "created_at": datetime(2026, 6, 3, 10, 0, 0),
        "is_active": True,
    }

    # 测试 SEQUENCE_EXECUTE
    data_seq = {**base_data, "group_type": GroupChatType.SEQUENCE_EXECUTE}
    schema_seq = GroupChatInfo(**data_seq)
    assert schema_seq.group_type == GroupChatType.SEQUENCE_EXECUTE

    # 测试 MANAGER_ORCHESTRATE
    data_mgr = {**base_data, "group_type": GroupChatType.MANAGER_ORCHESTRATE}
    schema_mgr = GroupChatInfo(**data_mgr)
    assert schema_mgr.group_type == GroupChatType.MANAGER_ORCHESTRATE


def test_group_chat_info_invalid_group_type():
    """测试非法的 group_type 值应该失败"""
    data = {
        "group_chat_id": "gc_123",
        "group_chat_name": "Test Group",
        "project_path": "/path/to/project",
        "created_at": datetime(2026, 6, 3, 10, 0, 0),
        "group_type": "INVALID_TYPE",
        "is_active": True,
    }
    with pytest.raises(ValidationError) as exc_info:
        GroupChatInfo(**data)
    assert "group_type" in str(exc_info.value).lower()


def test_group_chat_info_list_valid():
    """测试群聊列表信息响应"""
    data = {
        "group_chat_id": "gc_123",
        "group_chat_name": "Test Group",
        "project_path": "/path/to/project",
        "created_at": datetime(2026, 6, 3, 10, 0, 0),
        "group_type": GroupChatType.MANAGER_ORCHESTRATE,
        "is_active": False,
    }
    schema = GroupChatInfo(**data)
    assert schema.project_path == "/path/to/project"
    assert schema.group_type == GroupChatType.MANAGER_ORCHESTRATE


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
