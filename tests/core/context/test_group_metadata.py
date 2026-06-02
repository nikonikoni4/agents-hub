"""测试 GroupMetadata 持久化"""

import os
import tempfile
from datetime import datetime

import pytest

from agents_hub.core.context.group_chat_repository import GroupChatRepository
from agents_hub.core.context.group_metadata import GroupMetadata


class TestGroupMetadata:
    """测试 GroupMetadata 的保存和加载"""

    @pytest.mark.asyncio
    async def test_save_and_load_metadata(self):
        """测试保存和加载群聊元数据"""
        with tempfile.TemporaryDirectory() as temp_dir:
            group_chat_id = "test-group-1"
            repository = GroupChatRepository(group_chat_id, temp_dir)

            # 创建元数据
            metadata = GroupMetadata(
                group_chat_id=group_chat_id,
                group_chat_name="测试群聊",
                project_path=temp_dir,
                created_at=datetime(2026, 6, 2, 10, 30, 0),
                group_type="MANAGER_ORCHESTRATE",
            )

            # 保存
            await repository.save_group_metadata(metadata)

            # 验证文件存在
            assert os.path.exists(repository.metadata_file)

            # 加载
            loaded = await repository.load_group_metadata()

            # 验证
            assert loaded is not None
            assert loaded.group_chat_id == group_chat_id
            assert loaded.group_chat_name == "测试群聊"
            assert loaded.project_path == temp_dir
            assert loaded.created_at == datetime(2026, 6, 2, 10, 30, 0)
            assert loaded.group_type == "MANAGER_ORCHESTRATE"

    @pytest.mark.asyncio
    async def test_load_nonexistent_metadata(self):
        """测试加载不存在的元数据文件"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = GroupChatRepository("test-group-2", temp_dir)

            # 加载不存在的文件
            loaded = await repository.load_group_metadata()

            # 应该返回 None
            assert loaded is None

    @pytest.mark.asyncio
    async def test_metadata_file_path(self):
        """测试元数据文件路径正确"""
        with tempfile.TemporaryDirectory() as temp_dir:
            group_chat_id = "test-group-3"
            repository = GroupChatRepository(group_chat_id, temp_dir)

            metadata = GroupMetadata(
                group_chat_id=group_chat_id,
                group_chat_name="路径测试",
                project_path=temp_dir,
                created_at=datetime.now(),
                group_type="MANAGER_ORCHESTRATE",
            )

            await repository.save_group_metadata(metadata)

            # 验证文件路径格式
            expected_path = os.path.join(
                repository.group_chat_session_path, "group_metadata.json"
            )
            assert repository.metadata_file == expected_path
            assert os.path.exists(expected_path)

    @pytest.mark.asyncio
    async def test_metadata_default_group_type(self):
        """测试 group_type 的默认值"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = GroupChatRepository("test-group-4", temp_dir)

            # 创建元数据时省略 group_type
            metadata = GroupMetadata(
                group_chat_id="test-group-4",
                group_chat_name="默认类型测试",
                project_path=temp_dir,
                created_at=datetime.now(),
            )

            await repository.save_group_metadata(metadata)
            loaded = await repository.load_group_metadata()

            # 验证默认值
            assert loaded is not None
            assert loaded.group_type == "MANAGER_ORCHESTRATE"

    @pytest.mark.asyncio
    async def test_metadata_to_dict_and_from_dict(self):
        """测试元数据的序列化和反序列化"""
        metadata = GroupMetadata(
            group_chat_id="test-id",
            group_chat_name="测试名称",
            project_path="/test/path",
            created_at=datetime(2026, 6, 2, 15, 45, 30),
            group_type="CUSTOM_TYPE",
        )

        # 序列化
        data = metadata.to_dict()
        assert data["group_chat_id"] == "test-id"
        assert data["group_chat_name"] == "测试名称"
        assert data["project_path"] == "/test/path"
        assert data["created_at"] == "2026-06-02T15:45:30"
        assert data["group_type"] == "CUSTOM_TYPE"

        # 反序列化
        restored = GroupMetadata.from_dict(data)
        assert restored.group_chat_id == metadata.group_chat_id
        assert restored.group_chat_name == metadata.group_chat_name
        assert restored.project_path == metadata.project_path
        assert restored.created_at == metadata.created_at
        assert restored.group_type == metadata.group_type
