"""
测试 GroupChat 的 token 生命周期管理
"""

import pytest

from agents_hub.core.foundation import GroupChatType
from agents_hub.core.orchestration import GroupChat
from agents_hub.core.orchestration.group_chat_manager import GroupChatManager
from agents_hub.core.orchestration.team import Team
from agents_hub.utils.logger import setup_logging


@pytest.fixture
def temp_project_path(tmp_path):
    """创建临时项目路径"""
    # 初始化日志系统
    setup_logging(log_dir=tmp_path / "logs")
    return str(tmp_path)


@pytest.fixture
def team():
    """创建测试 team"""
    return Team(team_members_name=["小王", "小李"])


@pytest.fixture
def group_chat(team, temp_project_path):
    """创建测试 GroupChat"""
    return GroupChat(
        team=team,
        group_type=GroupChatType.SEQUENCE_EXECUTE,
        project_path=temp_project_path,
        group_chat_id="test_chat_001",
    )


class TestGroupChatTokenLifecycle:
    """测试 GroupChat 的 token 生命周期管理"""

    @pytest.mark.asyncio
    async def test_start_generates_and_registers_tokens(self, group_chat):
        """测试 start() 时生成并注册 token"""
        from agents_hub.core.orchestration.group_chat_manager import group_chat_manager

        # 启动群聊
        await group_chat.start()

        # 验证 manager 的 token 已注册
        manager_session = group_chat.group_chat_context.agent_session_id.get("Leader")
        assert manager_session is not None
        assert manager_session.token != ""

        manager_token = manager_session.token
        result = group_chat_manager.resolve_token(manager_token)
        assert result is not None
        assert result == ("Leader", "test_chat_001")

        # 验证 workers 的 token 已注册
        for worker_name in ["小王", "小李"]:
            worker_session = group_chat.group_chat_context.agent_session_id.get(worker_name)
            assert worker_session is not None
            assert worker_session.token != ""

            worker_token = worker_session.token
            result = group_chat_manager.resolve_token(worker_token)
            assert result is not None
            assert result == (worker_name, "test_chat_001")

        # 清理
        await group_chat.cleanup()

    @pytest.mark.asyncio
    async def test_load_restores_and_registers_tokens(self, group_chat, temp_project_path):
        """测试 load() 时恢复并注册 token"""
        from agents_hub.core.orchestration.group_chat_manager import group_chat_manager

        # 第一次启动，生成 token
        await group_chat.start()

        # 获取生成的 token
        manager_token = group_chat.group_chat_context.agent_session_id["Leader"].token
        worker_token = group_chat.group_chat_context.agent_session_id["小王"].token

        # 清理
        await group_chat.cleanup()

        # 创建新的 GroupChat 实例并 load
        from agents_hub.core.orchestration.team import Team

        new_team = Team(team_members_name=["小王", "小李"])
        new_group_chat = GroupChat(
            team=new_team,
            group_type=GroupChatType.SEQUENCE_EXECUTE,
            project_path=temp_project_path,
            group_chat_id="test_chat_001",
        )

        await new_group_chat.load()

        # 验证 token 已恢复并注册
        result = group_chat_manager.resolve_token(manager_token)
        assert result is not None
        assert result == ("Leader", "test_chat_001")

        result = group_chat_manager.resolve_token(worker_token)
        assert result is not None
        assert result == ("小王", "test_chat_001")

        # 清理
        await new_group_chat.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_unregisters_tokens(self, group_chat):
        """测试 cleanup() 时注销 token"""
        from agents_hub.core.orchestration.group_chat_manager import group_chat_manager

        # 启动群聊
        await group_chat.start()

        # 获取生成的 token
        manager_token = group_chat.group_chat_context.agent_session_id["Leader"].token
        worker_token = group_chat.group_chat_context.agent_session_id["小王"].token

        # 验证 token 已注册
        assert group_chat_manager.resolve_token(manager_token) is not None
        assert group_chat_manager.resolve_token(worker_token) is not None

        # 清理
        await group_chat.cleanup()

        # 验证 token 已注销
        assert group_chat_manager.resolve_token(manager_token) is None
        assert group_chat_manager.resolve_token(worker_token) is None
