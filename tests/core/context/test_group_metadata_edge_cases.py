"""测试 GroupMetadata 的边界情况和异常处理"""

import asyncio
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from agents_hub.core.context.group_chat_repository import GroupChatRepository
from agents_hub.core.context.group_metadata import GroupMetadata
from agents_hub.core.foundation import FileSystemError, GroupChatPaths


class TestGroupMetadataConcurrency:
    """测试 metadata 的并发控制"""

    @pytest.mark.asyncio
    async def test_concurrent_metadata_writes(self):
        """
        契约：多个并发写入操作不会导致数据损坏

        验证方式：
        1. 创建 repository
        2. 并发执行多个 save_group_metadata 操作
        3. 验证最后一次写入的数据可以正确读取

        如果失败，说明：_metadata_lock 没有正确保护文件写入
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            group_chat_id = "test-concurrent"
            repository = GroupChatRepository(group_chat_id, temp_dir)

            # 创建多个不同的 metadata
            metadatas = [
                GroupMetadata(
                    group_chat_id=group_chat_id,
                    group_chat_name=f"群聊-{i}",
                    project_path=temp_dir,
                    created_at=datetime.now(),
                    group_type="MANAGER_ORCHESTRATE",
                )
                for i in range(10)
            ]

            # 并发保存
            await asyncio.gather(
                *[repository.save_group_metadata(m) for m in metadatas]
            )

            # 加载并验证文件没有损坏
            loaded = await repository.load_group_metadata()
            assert loaded is not None
            assert loaded.group_chat_id == group_chat_id
            # 验证 group_chat_name 是其中一个有效值
            assert loaded.group_chat_name in [f"群聊-{i}" for i in range(10)]


class TestGroupMetadataErrorHandling:
    """测试 metadata 的异常处理"""

    @pytest.mark.asyncio
    async def test_save_metadata_io_error(self):
        """
        契约：保存 metadata 时发生 IO 错误应抛出 FileSystemError

        验证方式：
        1. Mock aiofiles.open 抛出 OSError
        2. 调用 save_group_metadata
        3. 验证抛出 FileSystemError

        如果失败，说明：没有正确处理 IO 异常
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = GroupChatRepository("test-io-error", temp_dir)
            metadata = GroupMetadata(
                group_chat_id="test-io-error",
                group_chat_name="测试",
                project_path=temp_dir,
                created_at=datetime.now(),
                group_type="MANAGER_ORCHESTRATE",
            )

            # Mock aiofiles.open 抛出 OSError
            with patch("aiofiles.open", side_effect=OSError("磁盘空间不足")):
                with pytest.raises(FileSystemError) as exc_info:
                    await repository.save_group_metadata(metadata)

                # 验证异常信息
                assert exc_info.value.details["operation"] == "write"
                assert "磁盘空间不足" in exc_info.value.details["reason"]

    @pytest.mark.asyncio
    async def test_load_metadata_io_error(self):
        """
        契约：加载 metadata 时发生 IO 错误应抛出 FileSystemError

        验证方式：
        1. 先保存一个 metadata
        2. Mock aiofiles.open 抛出 OSError
        3. 调用 load_group_metadata
        4. 验证抛出 FileSystemError

        如果失败，说明：没有正确处理读取异常
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = GroupChatRepository("test-read-error", temp_dir)

            # 先保存一个 metadata
            metadata = GroupMetadata(
                group_chat_id="test-read-error",
                group_chat_name="测试",
                project_path=temp_dir,
                created_at=datetime.now(),
                group_type="MANAGER_ORCHESTRATE",
            )
            await repository.save_group_metadata(metadata)

            # Mock aiofiles.open 抛出 OSError
            with patch("aiofiles.open", side_effect=OSError("权限不足")):
                with pytest.raises(FileSystemError) as exc_info:
                    await repository.load_group_metadata()

                # 验证异常信息
                assert exc_info.value.details["operation"] == "read"
                assert "权限不足" in exc_info.value.details["reason"]

    @pytest.mark.asyncio
    async def test_load_metadata_corrupted_json(self):
        """
        契约：加载损坏的 JSON 文件应抛出异常

        验证方式：
        1. 创建 metadata 文件，写入无效 JSON
        2. 调用 load_group_metadata
        3. 验证抛出异常

        如果失败，说明：没有正确处理 JSON 解析错误
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            repository = GroupChatRepository("test-corrupted", temp_dir)

            # 确保目录存在
            os.makedirs(repository.group_chat_session_path, exist_ok=True)

            # 写入无效 JSON
            with open(repository.metadata_file, "w", encoding="utf-8") as f:
                f.write("{ invalid json }")

            # 加载应该抛出异常
            with pytest.raises(Exception):  # json.JSONDecodeError
                await repository.load_group_metadata()


class TestGroupMetadataDeserialization:
    """测试 metadata 的反序列化边界情况"""

    def test_from_dict_missing_required_fields(self):
        """
        契约：缺少必填字段时应抛出 KeyError

        验证方式：
        1. 构造缺少必填字段的字典
        2. 调用 from_dict
        3. 验证抛出 KeyError

        如果失败，说明：没有正确验证必填字段
        """
        # 缺少 group_chat_id
        data_missing_id = {
            "group_chat_name": "测试",
            "project_path": "/test",
            "created_at": "2026-06-02T10:30:00",
        }

        with pytest.raises(KeyError):
            GroupMetadata.from_dict(data_missing_id)

        # 缺少 project_path
        data_missing_path = {
            "group_chat_id": "test-id",
            "group_chat_name": "测试",
            "created_at": "2026-06-02T10:30:00",
        }

        with pytest.raises(KeyError):
            GroupMetadata.from_dict(data_missing_path)

    def test_from_dict_invalid_datetime(self):
        """
        契约：无效的日期格式应抛出 ValueError

        验证方式：
        1. 构造包含无效日期的字典
        2. 调用 from_dict
        3. 验证抛出 ValueError

        如果失败，说明：没有正确验证日期格式
        """
        data = {
            "group_chat_id": "test-id",
            "group_chat_name": "测试",
            "project_path": "/test",
            "created_at": "invalid-date",
            "group_type": "MANAGER_ORCHESTRATE",
        }

        with pytest.raises(ValueError):
            GroupMetadata.from_dict(data)

    def test_from_dict_with_optional_group_type(self):
        """
        契约：group_type 字段缺失时应使用默认值

        验证方式：
        1. 构造不包含 group_type 的字典
        2. 调用 from_dict
        3. 验证 group_type 为默认值

        如果失败，说明：默认值逻辑不正确
        """
        data = {
            "group_chat_id": "test-id",
            "group_chat_name": "测试",
            "project_path": "/test",
            "created_at": "2026-06-02T10:30:00",
        }

        metadata = GroupMetadata.from_dict(data)
        assert metadata.group_type == "MANAGER_ORCHESTRATE"


class TestGroupChatPathsMetadata:
    """测试 GroupChatPaths.metadata_file() 方法"""

    def test_metadata_file_path_format(self):
        """
        契约：metadata_file() 返回正确的文件路径格式

        验证方式：
        1. 调用 metadata_file() 生成路径
        2. 验证路径格式为：<base_dir>/<group_chat_id>/group_metadata.json

        如果失败，说明：路径格式不正确
        """
        paths = GroupChatPaths()
        group_chat_id = "test-group-123"
        project_path = "/workspace/project-a"

        result = paths.metadata_file(group_chat_id, project_path)

        # 验证路径包含正确的组件
        assert "group_metadata.json" in str(result)
        assert group_chat_id in str(result)

    def test_metadata_file_path_consistency(self):
        """
        契约：相同参数多次调用应返回相同路径

        验证方式：
        1. 使用相同参数调用 metadata_file() 两次
        2. 验证返回的路径相同

        如果失败，说明：路径生成不是幂等的
        """
        paths = GroupChatPaths()
        group_chat_id = "test-group-456"
        project_path = "/workspace/project-b"

        path1 = paths.metadata_file(group_chat_id, project_path)
        path2 = paths.metadata_file(group_chat_id, project_path)

        assert path1 == path2

    def test_metadata_file_different_groups(self):
        """
        契约：不同 group_chat_id 应返回不同路径

        验证方式：
        1. 使用不同 group_chat_id 调用 metadata_file()
        2. 验证返回的路径不同

        如果失败，说明：路径生成没有区分不同群聊
        """
        paths = GroupChatPaths()
        project_path = "/workspace/project-c"

        path1 = paths.metadata_file("group-1", project_path)
        path2 = paths.metadata_file("group-2", project_path)

        assert path1 != path2
        assert "group-1" in str(path1)
        assert "group-2" in str(path2)
