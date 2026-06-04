"""测试 GroupChat 与 GroupMetadata 的集成"""

import os
import tempfile

import pytest

from agents_hub.core.context.group_chat_repository import GroupChatRepository
from agents_hub.core.context.group_chat_session import AgentMember
from agents_hub.core.foundation import GroupChatType


class TestGroupChatMetadataIntegration:
    """测试 GroupChat 与 GroupMetadata 的集成"""

    @pytest.mark.asyncio
    async def test_metadata_and_agent_cwd_workflow(self):
        """测试 metadata 保存和 agent cwd 设置的完整流程"""
        with tempfile.TemporaryDirectory() as temp_dir:
            group_chat_id = "test-group-1"
            repository = GroupChatRepository(group_chat_id, temp_dir)

            # 模拟 GroupChat.start() 的流程

            # 1. 保存 metadata
            from datetime import datetime

            from agents_hub.core.context.group_metadata import GroupMetadata

            metadata = GroupMetadata(
                group_chat_id=group_chat_id,
                group_chat_name=group_chat_id,
                project_path=temp_dir,
                created_at=datetime.now(),
                group_type=GroupChatType.MANAGER_ORCHESTRATE.value,
            )
            await repository.save_group_metadata(metadata)

            # 验证 metadata 文件存在
            assert os.path.exists(repository.metadata_file)

            # 2. 模拟 _generate_and_register_tokens() 的逻辑
            # 读取 metadata 获取 project_path 作为默认 cwd
            loaded_metadata = await repository.load_group_metadata()
            default_cwd = loaded_metadata.project_path if loaded_metadata else ""

            # 创建 agent_session_id
            agent_session_id = {}
            agent_session_id["Leader"] = AgentMember(
                token="token_leader",
                cwd=default_cwd,
            )
            agent_session_id["Worker1"] = AgentMember(
                token="token_worker1",
                cwd=default_cwd,
            )

            # 保存 agent session state
            await repository.save_agent_member(agent_session_id)

            # 3. 验证：重新加载，确认 cwd 正确
            loaded_state = await repository.load_agent_member()
            assert loaded_state["Leader"].cwd == temp_dir
            assert loaded_state["Worker1"].cwd == temp_dir

    @pytest.mark.asyncio
    async def test_agent_cwd_fallback_when_empty(self):
        """测试当 agent cwd 为空时，使用 project_path 填充"""
        with tempfile.TemporaryDirectory() as temp_dir:
            group_chat_id = "test-group-2"
            repository = GroupChatRepository(group_chat_id, temp_dir)

            # 保存 metadata
            from datetime import datetime

            from agents_hub.core.context.group_metadata import GroupMetadata

            metadata = GroupMetadata(
                group_chat_id=group_chat_id,
                group_chat_name=group_chat_id,
                project_path=temp_dir,
                created_at=datetime.now(),
                group_type=GroupChatType.MANAGER_ORCHESTRATE.value,
            )
            await repository.save_group_metadata(metadata)

            # 模拟已存在的 agent，但 cwd 为空
            agent_session_id = {}
            agent_session_id["Leader"] = AgentMember(
                token="token_leader",
                cwd="",  # 空 cwd
            )

            # 模拟 _generate_and_register_tokens() 的逻辑
            loaded_metadata = await repository.load_group_metadata()
            default_cwd = loaded_metadata.project_path if loaded_metadata else ""

            # 如果 cwd 为空，则填充 default_cwd
            if not agent_session_id["Leader"].cwd:
                agent_session_id["Leader"].cwd = default_cwd

            # 验证 cwd 被填充
            assert agent_session_id["Leader"].cwd == temp_dir

    @pytest.mark.asyncio
    async def test_metadata_persistence_across_restarts(self):
        """测试 metadata 在重启后保持一致"""
        with tempfile.TemporaryDirectory() as temp_dir:
            group_chat_id = "test-group-3"

            # 第一次：创建并保存 metadata
            from datetime import datetime

            from agents_hub.core.context.group_metadata import GroupMetadata

            repository1 = GroupChatRepository(group_chat_id, temp_dir)
            metadata = GroupMetadata(
                group_chat_id=group_chat_id,
                group_chat_name="测试群聊",
                project_path=temp_dir,
                created_at=datetime(2026, 6, 2, 10, 30, 0),
                group_type=GroupChatType.MANAGER_ORCHESTRATE.value,
            )
            await repository1.save_group_metadata(metadata)

            # 第二次：模拟重启，重新创建 repository 并加载
            repository2 = GroupChatRepository(group_chat_id, temp_dir)
            loaded_metadata = await repository2.load_group_metadata()

            assert loaded_metadata is not None
            assert loaded_metadata.group_chat_id == group_chat_id
            assert loaded_metadata.group_chat_name == "测试群聊"
            assert loaded_metadata.project_path == temp_dir
            assert loaded_metadata.group_type == GroupChatType.MANAGER_ORCHESTRATE.value

    @pytest.mark.asyncio
    async def test_metadata_created_independently_of_messages(self):
        """测试 metadata 独立于消息历史创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            group_chat_id = "test-group-4"
            repository = GroupChatRepository(group_chat_id, temp_dir)

            # 保存 metadata
            from datetime import datetime

            from agents_hub.core.context.group_metadata import GroupMetadata

            metadata = GroupMetadata(
                group_chat_id=group_chat_id,
                group_chat_name=group_chat_id,
                project_path=temp_dir,
                created_at=datetime.now(),
                group_type=GroupChatType.MANAGER_ORCHESTRATE.value,
            )
            await repository.save_group_metadata(metadata)

            # metadata 文件存在
            assert os.path.exists(repository.metadata_file)

            # 消息文件不存在（延迟创建）
            assert not os.path.exists(repository.messages_file)

            # 即使没有消息，metadata 也可以独立加载
            loaded_metadata = await repository.load_group_metadata()
            assert loaded_metadata is not None
            assert loaded_metadata.project_path == temp_dir

    @pytest.mark.asyncio
    async def test_group_chat_exposes_runtime_metadata_after_start(self, monkeypatch, tmp_path):
        """测试 GroupChat 在 start 后通过 runtime 暴露 metadata"""
        from agents_hub.core.orchestration import GroupChat
        from agents_hub.core.orchestration.team import Team
        from agents_hub.utils.logger import setup_logging

        # 初始化日志系统
        setup_logging(log_dir=tmp_path / "logs")

        team = Team.model_construct(team_members_name=["Leader"])
        group_chat = GroupChat(
            team=team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=str(tmp_path),
            group_chat_id="gc_runtime_metadata",
            group_chat_name="Runtime Metadata",
        )

        async def fake_init_agents():
            group_chat.manager = None
            group_chat.workers = {}

        async def fake_generate_tokens():
            return None

        async def fake_initialize_members():
            return None

        monkeypatch.setattr(group_chat, "_init_agents", fake_init_agents)
        monkeypatch.setattr(group_chat, "_generate_and_register_tokens", fake_generate_tokens)
        monkeypatch.setattr(group_chat, "_initialize_new_members", fake_initialize_members)
        monkeypatch.setattr(group_chat, "_start_agent_tasks", lambda: None)

        await group_chat.start()

        info = group_chat.runtime.get_info_dict(is_active=True)
        assert info["group_chat_id"] == "gc_runtime_metadata"
        assert info["group_chat_name"] == "Runtime Metadata"
        assert info["project_path"] == str(tmp_path)

