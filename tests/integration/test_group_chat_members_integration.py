"""群成员管理功能集成测试

验证添加成员的完整流程，特别是崩溃恢复场景。
"""

import asyncio

import pytest

from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.core.orchestration.group_chat_manager import group_chat_manager
from agents_hub.utils.logger import setup_logging


@pytest.fixture
def temp_project_path(tmp_path):
    """临时项目路径"""
    # 初始化日志系统
    setup_logging(log_dir=tmp_path / "logs")

    project_path = tmp_path / "test_project"
    project_path.mkdir()
    return str(project_path)


@pytest.mark.asyncio
class TestGroupChatMembersIntegration:
    """群成员管理集成测试"""

    async def test_add_member_crash_recovery(self, temp_project_path):
        """验证添加成员后立即崩溃，重启后能否恢复"""
        service = GroupChatService(group_chat_manager)

        # 1. 创建群聊（使用 mock 的角色名）
        group_chat_info = await service.create_group_chat(
            group_chat_name="test_group",
            project_path=temp_project_path,
            team_members=["Worker1"],
        )
        group_chat_id = group_chat_info.group_chat_id  # ✅ 提取 group_chat_id

        # 2. 添加新成员（使用 mock 的角色名）
        await service.add_group_chat_members(group_chat_id, ["小李"])

        # 3. 模拟崩溃：清空内存，重新加载
        group_chat_manager._group_chats.clear()
        group_chat = await group_chat_manager.load_group_chat_from_disk(group_chat_id)

        # 4. 验证新成员存在
        assert "小李" in group_chat.team_members_name
        assert "小李" in group_chat.workers

        # 5. 验证持久化（agent_member.json 包含新成员）
        agent_member_infos = group_chat.runtime.state.agent_member_infos
        assert "小李" in agent_member_infos

    async def test_add_member_while_processing(self, temp_project_path):
        """验证添加成员时，旧消息不丢失"""
        service = GroupChatService(group_chat_manager)

        # 1. 创建并激活群聊（使用 mock 的角色名）
        group_chat_info = await service.create_group_chat(
            group_chat_name="test_group",
            project_path=temp_project_path,
            team_members=["Worker1"],
        )
        group_chat_id = group_chat_info.group_chat_id  # ✅ 提取 group_chat_id
        await service.activate_group_chat(group_chat_id)

        # 2. 发送消息给 Manager，但不立即处理
        await service.send_message(group_chat_id, "task1", ["manager", "Worker1"])
        await asyncio.sleep(0.1)  # 短暂等待消息入队

        # 3. 添加新成员（使用 mock 的角色名）
        await service.add_group_chat_members(group_chat_id, ["小李"])

        # 4. 等待消息处理完成
        await asyncio.sleep(5)

        # 5. 验证消息被处理（检查消息历史）
        messages = await service.get_messages(group_chat_id)
        assert any("task1" in m.content for m in messages)

    async def test_new_member_access_history(self, temp_project_path):
        """验证新成员能否访问历史消息"""
        service = GroupChatService(group_chat_manager)

        # 1. 创建群聊（使用 mock 的角色名）
        group_chat_info = await service.create_group_chat(
            group_chat_name="test_group",
            project_path=temp_project_path,
            team_members=["Worker1"],
        )
        group_chat_id = group_chat_info.group_chat_id  # ✅ 提取 group_chat_id
        await service.activate_group_chat(group_chat_id)

        # 2. 发送几条消息，形成历史
        await service.send_message(group_chat_id, "历史消息1", ["manager", "Worker1"])
        await asyncio.sleep(2)

        # 3. 添加新成员（使用 mock 的角色名）
        await service.add_group_chat_members(group_chat_id, ["小李"])

        # 4. 发送消息给新成员
        await service.send_message(group_chat_id, "@小李 你好", ["manager", "Worker1", "小李"])
        await asyncio.sleep(5)

        # 5. 验证新成员能访问历史（检查 agent_member_info 的 context_state）
        group_chat = await group_chat_manager.load_group_chat(group_chat_id)
        tester_info = group_chat.runtime.state.agent_member_infos.get("小李")
        assert tester_info is not None
        # 新成员首次执行后，last_loaded_message_index 应该 > 0（加载了历史）
        assert tester_info.context_state.last_loaded_message_index > 0
