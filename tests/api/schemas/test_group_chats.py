from datetime import datetime

import pytest
from pydantic import ValidationError

from agents_hub.api.schemas.group_chats import (
    GroupChatCreate,
    GroupChatInfo,
    GroupChatMember,
    MessageCreate,
    MessageInfo,
    UploadedFileInfo,
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


def test_message_info_with_web_preview():
    """
    契约：MessageInfo 支持 web_preview 可选字段，包含 url 和 title

    验证方式：
    1. 构造包含 web_preview 的 MessageInfo
    2. 验证字段正确解析

    如果失败，说明：MessageInfo 缺少 web_preview 字段定义
    """
    data = {
        "id": 1,
        "speaker": "agent1",
        "content": "网页已生成",
        "timestamp": "2026-06-09T10:00:00",
        "platform": "claude",
        "web_preview": {"url": "http://localhost:3000", "title": "预览页面"},
    }
    schema = MessageInfo(**data)
    assert schema.web_preview is not None
    assert schema.web_preview.url == "http://localhost:3000"
    assert schema.web_preview.title == "预览页面"


def test_message_info_without_web_preview():
    """
    契约：MessageInfo 不传 web_preview 时默认为 None

    验证方式：
    1. 构造不包含 web_preview 的 MessageInfo
    2. 验证字段为 None

    如果失败，说明：web_preview 默认值配置错误
    """
    data = {
        "id": 1,
        "speaker": "agent1",
        "content": "任务完成",
        "timestamp": "2026-06-09T10:00:00",
        "platform": "claude",
    }
    schema = MessageInfo(**data)
    assert schema.web_preview is None


def test_message_info_web_preview_without_title():
    """
    契约：web_preview 的 title 字段可选

    验证方式：
    1. 构造 web_preview 只有 url、没有 title 的 MessageInfo
    2. 验证 url 正确，title 为 None

    如果失败，说明：WebPreviewInfo.title 不是可选字段
    """
    data = {
        "id": 1,
        "speaker": "agent1",
        "content": "网页已生成",
        "timestamp": "2026-06-09T10:00:00",
        "platform": "claude",
        "web_preview": {"url": "http://localhost:3000"},
    }
    schema = MessageInfo(**data)
    assert schema.web_preview.url == "http://localhost:3000"
    assert schema.web_preview.title is None


# --- UploadedFileInfo Tests ---


def test_uploaded_file_info_valid():
    """
    契约：UploadedFileInfo 包含 file_name、file_path、file_type、file_size 四个必填字段

    验证方式：
    1. 构造完整的 UploadedFileInfo
    2. 验证所有字段正确解析

    如果失败，说明：UploadedFileInfo 字段定义错误
    """
    data = {
        "file_name": "photo.jpg",
        "file_path": "uploads/2026/06/10/abc123.jpg",
        "file_type": "image/jpeg",
        "file_size": 102400,
    }
    schema = UploadedFileInfo(**data)
    assert schema.file_name == "photo.jpg"
    assert schema.file_path == "uploads/2026/06/10/abc123.jpg"
    assert schema.file_type == "image/jpeg"
    assert schema.file_size == 102400


def test_uploaded_file_info_missing_field_fails():
    """
    契约：UploadedFileInfo 缺少必填字段时应抛出 ValidationError

    验证方式：
    1. 构造缺少 file_name 的 UploadedFileInfo
    2. 验证抛出 ValidationError

    如果失败，说明：UploadedFileInfo 字段校验缺失
    """
    data = {
        "file_path": "uploads/test.png",
        "file_type": "image/png",
        "file_size": 1024,
    }
    with pytest.raises(ValidationError):
        UploadedFileInfo(**data)


# --- MessageCreate with files Tests ---


def test_message_create_without_files():
    """
    契约：MessageCreate 不传 files 时默认为 None

    验证方式：
    1. 构造不包含 files 的 MessageCreate
    2. 验证 files 字段为 None

    如果失败，说明：files 字段默认值配置错误
    """
    data = {"content": "hello", "members": ["agent1"]}
    schema = MessageCreate(**data)
    assert schema.content == "hello"
    assert schema.members == ["agent1"]
    assert schema.files is None


def test_message_create_with_files():
    """
    契约：MessageCreate 支持 files 可选字段，包含 UploadedFileInfo 列表

    验证方式：
    1. 构造包含 files 的 MessageCreate
    2. 验证 files 列表正确解析

    如果失败，说明：MessageCreate.files 字段定义错误
    """
    data = {
        "content": "看看这张图",
        "members": ["agent1", "agent2"],
        "files": [
            {
                "file_name": "photo.jpg",
                "file_path": "uploads/abc.jpg",
                "file_type": "image/jpeg",
                "file_size": 51200,
            }
        ],
    }
    schema = MessageCreate(**data)
    assert schema.files is not None
    assert len(schema.files) == 1
    assert schema.files[0].file_name == "photo.jpg"
    assert schema.files[0].file_type == "image/jpeg"


def test_message_create_with_multiple_files():
    """
    契约：MessageCreate.files 支持多个文件

    验证方式：
    1. 构造包含多个文件的 MessageCreate
    2. 验证所有文件正确解析

    如果失败，说明：files 列表处理错误
    """
    data = {
        "content": "多张图片",
        "members": ["agent1"],
        "files": [
            {
                "file_name": "a.png",
                "file_path": "uploads/a.png",
                "file_type": "image/png",
                "file_size": 1024,
            },
            {
                "file_name": "b.jpg",
                "file_path": "uploads/b.jpg",
                "file_type": "image/jpeg",
                "file_size": 2048,
            },
        ],
    }
    schema = MessageCreate(**data)
    assert len(schema.files) == 2
    assert schema.files[0].file_name == "a.png"
    assert schema.files[1].file_name == "b.jpg"


def test_message_create_with_empty_files_list():
    """
    契约：MessageCreate.files 传入空列表应正常解析

    验证方式：
    1. 构造 files=[] 的 MessageCreate
    2. 验证 files 为空列表

    如果失败，说明：空列表处理错误
    """
    data = {"content": "无附件", "members": ["agent1"], "files": []}
    schema = MessageCreate(**data)
    assert schema.files is not None
    assert len(schema.files) == 0
