"""
测试 GroupChatManager 增强功能

测试三个新增方法：
1. list_all_group_chats() - 列出所有群聊
2. load_group_chat_from_disk() - 从磁盘加载群聊
3. create_group_chat() - 创建新群聊
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from agents_hub.core.context import GroupMetadata
from agents_hub.core.foundation import GroupChatType
from agents_hub.core.foundation.paths import group_chat_paths
from agents_hub.core.orchestration import GroupChat, GroupChatManager


@pytest.fixture
def test_base_path(tmp_path):
    """测试用的临时基础路径"""
    from agents_hub.utils.logger import setup_logging

    # 初始化日志系统
    setup_logging(log_dir=tmp_path / "logs")

    base = tmp_path / "test_teams"
    base.mkdir()
    return base


@pytest.fixture
def sample_team():
    """创建测试用的成员列表"""
    return ["Leader", "bare_claude"]


@pytest.fixture
def group_chat_manager():
    """创建 GroupChatManager 实例"""
    GroupChatManager._reset_instance()
    yield GroupChatManager()
    GroupChatManager._reset_instance()


class TestListAllGroupChats:
    """测试 list_all_group_chats() 方法"""

    def test_empty_directory(self, group_chat_manager, test_base_path):
        """测试空目录返回空列表"""
        result = group_chat_manager.list_all_group_chats(str(test_base_path))
        assert result == []

    def test_no_metadata_files(self, group_chat_manager, test_base_path):
        """测试没有 metadata 文件时返回空列表"""
        # 创建目录但不创建 metadata 文件
        (test_base_path / "project1" / "gc1").mkdir(parents=True)
        (test_base_path / "project2" / "gc2").mkdir(parents=True)

        result = group_chat_manager.list_all_group_chats(str(test_base_path))
        assert result == []

    def test_single_group_chat(self, group_chat_manager, test_base_path):
        """测试单个群聊"""
        # 创建 metadata 文件
        project_path = "/test/project1"
        group_chat_id = "gc-001"
        metadata = GroupMetadata(
            group_chat_id=group_chat_id,
            group_chat_name="测试群聊",
            project_path=project_path,
            created_at=datetime(2026, 6, 1, 10, 0, 0),
            group_type="manager_orchestrate",
        )

        metadata_file = test_base_path / "project1" / group_chat_id / "group_metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f)

        # 列出群聊
        result = group_chat_manager.list_all_group_chats(str(test_base_path))

        assert len(result) == 1
        assert result[0]["group_chat_id"] == group_chat_id
        assert result[0]["group_chat_name"] == "测试群聊"
        assert result[0]["project_path"] == project_path
        assert result[0]["created_at"] == "2026-06-01T10:00:00"
        assert result[0]["group_type"] == "manager_orchestrate"
        assert result[0]["is_active"] is False

    def test_multiple_group_chats(self, group_chat_manager, test_base_path):
        """测试多个群聊"""
        # 创建多个 metadata 文件
        metadatas = [
            GroupMetadata(
                group_chat_id="gc-001",
                group_chat_name="群聊1",
                project_path="/project1",
                created_at=datetime(2026, 6, 1, 10, 0, 0),
                group_type="manager_orchestrate",
            ),
            GroupMetadata(
                group_chat_id="gc-002",
                group_chat_name="群聊2",
                project_path="/project2",
                created_at=datetime(2026, 6, 2, 11, 0, 0),
                group_type="manager_orchestrate",
            ),
        ]

        for i, metadata in enumerate(metadatas, 1):
            metadata_file = (
                test_base_path / f"project{i}" / metadata.group_chat_id / "group_metadata.json"
            )
            metadata_file.parent.mkdir(parents=True, exist_ok=True)
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata.to_dict(), f)

        # 列出群聊
        result = group_chat_manager.list_all_group_chats(str(test_base_path))

        assert len(result) == 2
        assert {r["group_chat_id"] for r in result} == {"gc-001", "gc-002"}

    def test_is_active_flag(self, group_chat_manager, test_base_path, sample_team):
        """测试 is_active 标志"""
        # 创建 metadata
        group_chat_id = "gc-001"
        metadata = GroupMetadata(
            group_chat_id=group_chat_id,
            group_chat_name="测试群聊",
            project_path="/test/project",
            created_at=datetime.now(),
            group_type="manager_orchestrate",
        )

        metadata_file = test_base_path / "project" / group_chat_id / "group_metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f)

        # 初始状态：未激活
        result = group_chat_manager.list_all_group_chats(str(test_base_path))
        assert result[0]["is_active"] is False

        # 注册群聊后：激活
        mock_group_chat = GroupChat(
            team_members_name=sample_team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path="/test/project",
            group_chat_id=group_chat_id,
        )
        mock_group_chat._activated = True
        group_chat_manager.register(group_chat_id, mock_group_chat)

        result = group_chat_manager.list_all_group_chats(str(test_base_path))
        assert result[0]["is_active"] is True

    def test_corrupted_metadata_skipped(self, group_chat_manager, test_base_path):
        """测试损坏的 metadata 文件会被跳过"""
        # 创建正常的 metadata
        metadata = GroupMetadata(
            group_chat_id="gc-001",
            group_chat_name="正常群聊",
            project_path="/project1",
            created_at=datetime.now(),
            group_type="manager_orchestrate",
        )
        metadata_file = test_base_path / "project1" / "gc-001" / "group_metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f)

        # 创建损坏的 metadata
        corrupted_file = test_base_path / "project2" / "gc-002" / "group_metadata.json"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("invalid json {{{")

        # 列出群聊（只返回正常的）
        result = group_chat_manager.list_all_group_chats(str(test_base_path))
        assert len(result) == 1
        assert result[0]["group_chat_id"] == "gc-001"


class TestLoadGroupChatFromDisk:
    """测试 load_group_chat_from_disk() 方法"""

    @pytest.mark.asyncio
    async def test_group_chat_not_found(self, group_chat_manager):
        """测试群聊不存在时抛出异常"""
        with pytest.raises(FileNotFoundError, match="找不到GroupChat"):
            await group_chat_manager.load_group_chat_from_disk(
                group_chat_id="non-existent",
            )

    @pytest.mark.asyncio
    async def test_group_chat_id_mismatch(self, group_chat_manager, sample_team, test_base_path):
        """测试 group_chat_id 不一致时抛出异常"""
        from agents_hub.core.utils import sanitize_project_path

        # 创建 metadata（group_chat_id 不匹配）
        # 使用简单的 project_path，避免 sanitize 后路径过长
        project_path = "test_project"
        group_chat_id = "gc-001"
        wrong_id = "gc-999"

        # 创建目录结构: base_path/<sanitized_project>/<group_chat_id>/
        sanitized = sanitize_project_path(project_path)
        group_dir = test_base_path / sanitized / group_chat_id
        group_dir.mkdir(parents=True, exist_ok=True)

        # metadata 中的 group_chat_id 使用 wrong_id（与目录名不匹配）
        # 这会导致 find_project_path_by_group_chat_id 跳过这个目录
        metadata = GroupMetadata(
            group_chat_id=wrong_id,  # 故意不匹配
            group_chat_name="测试群聊",
            project_path=project_path,
            created_at=datetime.now(),
            group_type="manager_orchestrate",
        )

        metadata_file = group_dir / "group_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f)

        # 尝试加载 - 直接传入 base_path
        with pytest.raises(FileNotFoundError, match="找不到GroupChat"):
            await group_chat_manager.load_group_chat_from_disk(
                group_chat_id=group_chat_id,
                base_path=str(test_base_path),
            )

    @pytest.mark.asyncio
    async def test_load_success(self, group_chat_manager, sample_team, test_base_path):
        """测试成功加载群聊"""
        from agents_hub.core.utils import sanitize_project_path

        # 1. 手动创建目录结构和文件
        # 使用简单的 project_path，避免 sanitize 后路径过长
        project_path = "test_project"
        group_chat_id = "gc-001"

        sanitized = sanitize_project_path(project_path)
        group_dir = test_base_path / sanitized / group_chat_id
        group_dir.mkdir(parents=True, exist_ok=True)

        # 创建 metadata
        metadata = GroupMetadata(
            group_chat_id=group_chat_id,
            group_chat_name="测试群聊",
            project_path=project_path,
            created_at=datetime.now(),
            group_type="manager_orchestrate",
        )
        metadata_file = group_dir / "group_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f)

        # 创建 agent_member.json
        session_state = {
            "test_role_1": {"main_session": "sess-1", "btw_session": []},
            "test_role_2": {"main_session": "sess-2", "btw_session": []},
        }
        agent_member_file = group_dir / "agent_member.json"
        with open(agent_member_file, "w", encoding="utf-8") as f:
            json.dump(session_state, f)

        # 2. 从磁盘加载（mock GroupChat.load 以绕过角色验证）
        with (
            patch.object(GroupChat, "load"),
            patch.object(GroupChat, "activate"),
        ):
            loaded_chat = await group_chat_manager.load_group_chat_from_disk(
                group_chat_id=group_chat_id,
                base_path=str(test_base_path),
            )

        # 3. 验证
        assert loaded_chat.group_chat_id == group_chat_id
        assert loaded_chat.group_type == GroupChatType.MANAGER_ORCHESTRATE
        assert group_chat_manager._group_chats.get(group_chat_id) == loaded_chat

        # 清理
        await loaded_chat.cleanup()


class TestGetActiveGroupInfo:
    """测试 get_active_group_info() 方法"""

    def test_get_active_group_info_uses_runtime_query(self, group_chat_manager):
        """测试活动群聊信息从 runtime 查询"""
        mock_runtime = Mock()
        mock_runtime.get_info_dict.return_value = {
            "group_chat_id": "gc-001",
            "group_chat_name": "测试群聊",
            "project_path": "/project1",
            "created_at": datetime(2026, 6, 1, 10, 0, 0),
            "group_type": "manager_orchestrate",
            "is_active": True,
        }
        mock_group_chat = Mock()
        mock_group_chat._activated = True
        mock_group_chat.runtime = mock_runtime
        group_chat_manager._group_chats["gc-001"] = mock_group_chat

        result = group_chat_manager.get_active_group_info("gc-001")

        assert result["group_chat_id"] == "gc-001"
        assert result["is_active"] is True
        mock_runtime.get_info_dict.assert_called_once_with(is_active=True)

    def test_get_active_group_info_returns_none_for_inactive_registry_miss(
        self, group_chat_manager
    ):
        """测试未激活或不存在的群聊返回 None"""
        assert group_chat_manager.get_active_group_info("missing") is None


class TestCreateGroupChat:
    """测试 create_group_chat() 方法"""

    @pytest.mark.asyncio
    async def test_create_with_auto_id(self, group_chat_manager, sample_team, tmp_path):
        """测试使用自动生成的 ID 创建群聊"""
        project_path = str(tmp_path / "project")

        group_chat = await group_chat_manager.create_group_chat(
            team_members_name=sample_team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=project_path,
        )

        # 验证
        assert group_chat.group_chat_id is not None
        assert group_chat_manager._group_chats.get(group_chat.group_chat_id) == group_chat

        # 验证 metadata 已保存
        metadata_file = group_chat_paths.metadata_file(group_chat.group_chat_id, project_path)
        assert metadata_file.exists()

        # 清理
        await group_chat.cleanup()

    @pytest.mark.asyncio
    async def test_create_with_custom_id(self, group_chat_manager, sample_team, tmp_path):
        """测试使用自定义 ID 创建群聊"""
        project_path = str(tmp_path / "project")
        custom_id = "my-custom-gc-id"

        group_chat = await group_chat_manager.create_group_chat(
            team_members_name=sample_team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=project_path,
            group_chat_id=custom_id,
        )

        # 验证
        assert group_chat.group_chat_id == custom_id
        assert group_chat_manager._group_chats.get(custom_id) == group_chat

        # 清理
        await group_chat.cleanup()

    @pytest.mark.asyncio
    async def test_create_with_custom_name(self, group_chat_manager, sample_team, tmp_path):
        """测试使用自定义名称创建群聊"""
        from agents_hub.utils.logger import setup_logging

        # 初始化日志系统
        setup_logging(log_dir=tmp_path / "logs")

        project_path = str(tmp_path / "project")
        custom_name = "我的开发团队"

        group_chat = await group_chat_manager.create_group_chat(
            team_members_name=sample_team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=project_path,
            group_chat_name=custom_name,
        )

        # 验证 metadata 中的名称
        metadata = group_chat.runtime.state.metadata
        assert metadata is not None
        assert metadata.group_chat_name == custom_name

        # 清理
        await group_chat.cleanup()

    @pytest.mark.asyncio
    async def test_create_and_list(self, group_chat_manager, sample_team, tmp_path):
        """测试创建后能在列表中找到"""
        from agents_hub.utils.logger import setup_logging

        # 初始化日志系统
        setup_logging(log_dir=tmp_path / "logs")

        project_path = str(tmp_path / "project")
        custom_name = "测试群聊"

        group_chat = await group_chat_manager.create_group_chat(
            team_members_name=sample_team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=project_path,
            group_chat_name=custom_name,
        )

        # 列出群聊
        base_path = group_chat_paths.base_dir(group_chat.group_chat_id, project_path).parent.parent
        result = group_chat_manager.list_all_group_chats(str(base_path))

        # 验证：找到我们创建的群聊
        our_chat = next((r for r in result if r["group_chat_id"] == group_chat.group_chat_id), None)
        assert our_chat is not None
        assert our_chat["group_chat_name"] == custom_name
        assert our_chat["is_active"] is True

        # 清理
        await group_chat.cleanup()


class TestIntegration:
    """集成测试：完整的生命周期"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, group_chat_manager, sample_team, tmp_path):
        """测试完整的生命周期：创建 -> 注销 -> 加载 -> 列出"""
        from agents_hub.utils.logger import setup_logging

        # 初始化日志系统
        setup_logging(log_dir=tmp_path / "logs")

        project_path = str(tmp_path / "project")
        custom_name = "完整测试群聊"

        # 1. 创建群聊
        group_chat = await group_chat_manager.create_group_chat(
            team_members_name=sample_team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=project_path,
            group_chat_name=custom_name,
        )
        group_chat_id = group_chat.group_chat_id

        # 2. 验证活跃状态
        base_path = group_chat_paths.base_dir(group_chat_id, project_path).parent.parent
        result = group_chat_manager.list_all_group_chats(str(base_path))
        our_chat = next((r for r in result if r["group_chat_id"] == group_chat_id), None)
        assert our_chat is not None
        assert our_chat["is_active"] is True

        # 3. 注销群聊
        await group_chat_manager.unregister(group_chat_id)

        # 4. 验证非活跃状态
        result = group_chat_manager.list_all_group_chats(str(base_path))
        our_chat = next((r for r in result if r["group_chat_id"] == group_chat_id), None)
        assert our_chat is not None
        assert our_chat["is_active"] is False

        # 5. 从磁盘重新加载
        loaded_chat = await group_chat_manager.load_group_chat_from_disk(
            group_chat_id=group_chat_id,
        )

        # 6. 验证重新激活
        result = group_chat_manager.list_all_group_chats(str(base_path))
        our_chat = next((r for r in result if r["group_chat_id"] == group_chat_id), None)
        assert our_chat is not None
        assert our_chat["is_active"] is True
        assert our_chat["group_chat_name"] == custom_name

        # 清理
        await loaded_chat.cleanup()
