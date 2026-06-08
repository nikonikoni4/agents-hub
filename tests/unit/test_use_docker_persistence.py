"""use_docker 持久化单元测试

契约：
1. save_agent_member 序列化 use_docker 字段
2. load_agent_member_infos 反序列化 use_docker 字段
3. use_docker=False 正确 round-trip
"""

import json

import pytest

from agents_hub.core.context.group_chat_repository import GroupChatRepository
from agents_hub.core.context.group_chat_session import AgentMemberInfo


@pytest.fixture
def repo(tmp_path):
    """创建临时目录的 GroupChatRepository"""
    return GroupChatRepository(group_chat_id="test_gc", project_path=str(tmp_path))


async def test_save_and_load_use_docker_round_trip(repo):
    """
    契约：use_docker=True 正确序列化/反序列化

    验证方式：
    1. 构造 AgentMemberInfo(use_docker=True)
    2. save_agent_member 写入文件
    3. load_agent_member_infos 读取
    4. 断言 use_docker=True
    """
    state = {
        "agent1": AgentMemberInfo(
            main_session="sess_1",
            use_docker=True,
        ),
    }

    await repo.save_agent_member(state)
    loaded = await repo.load_agent_member_infos()

    assert "agent1" in loaded
    assert loaded["agent1"].use_docker is True


async def test_save_use_docker_false_round_trip(repo):
    """
    契约：use_docker=False 正确 round-trip（不会被过滤掉）

    验证方式：
    1. 构造 AgentMemberInfo(use_docker=False)
    2. save → load
    3. 断言 use_docker=False 且字段存在于 JSON
    """
    state = {
        "agent1": AgentMemberInfo(
            main_session="sess_1",
            use_docker=False,
        ),
    }

    await repo.save_agent_member(state)

    # 验证 JSON 文件中显式包含 use_docker 字段
    with open(repo.agent_member_file, encoding="utf-8") as f:
        raw = json.load(f)
    assert "use_docker" in raw["agent1"]
    assert raw["agent1"]["use_docker"] is False

    loaded = await repo.load_agent_member_infos()
    assert loaded["agent1"].use_docker is False


async def test_load_missing_use_docker_defaults_false(repo):
    """
    契约：旧数据无 use_docker 字段时默认 False（向后兼容）

    验证方式：
    1. 写入不含 use_docker 的 JSON
    2. load_agent_member_infos
    3. 断言 use_docker=False
    """
    import os

    os.makedirs(repo.group_chat_session_path, exist_ok=True)
    old_data = {
        "agent1": {
            "main_session": "sess_1",
            "btw_session": [],
            "context_state": {"last_loaded_compact_index": 0, "last_loaded_message_index": 0},
            "token": "tok_123",
            "cwd": "/workspace",
        }
    }
    with open(repo.agent_member_file, "w", encoding="utf-8") as f:
        json.dump(old_data, f)

    loaded = await repo.load_agent_member_infos()

    assert loaded["agent1"].use_docker is False
