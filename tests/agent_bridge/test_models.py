"""AgentResult 模型测试

验证 AgentResult 数据模型的字段定义和验证。
"""

from agents_hub.agent_bridge.models import AgentResult
from agents_hub.config.types import AgentPlatform, RoleType


def test_agent_result_with_file_fields():
    """测试 AgentResult 包含文件相关字段"""
    result = AgentResult(
        text="任务完成",
        session_id="session_1",
        timestamp="2026-06-07T10:00:00",
        agent_name="TestAgent",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
        cwd="/path/to/project",
        modified_files=[
            {
                "path": "test.py",
                "status": "modified",
                "additions": 10,
                "deletions": 5,
                "snapshot_id": "call_123_0",
                "diff_available": True,
                "diff_error": None
            }
        ],
        git_diff_range="abc123..def456"
    )

    assert result.cwd == "/path/to/project"
    assert len(result.modified_files) == 1
    assert result.modified_files[0]["path"] == "test.py"
    assert result.git_diff_range == "abc123..def456"


def test_agent_result_without_file_fields():
    """测试 AgentResult 不包含文件字段"""
    result = AgentResult(
        text="任务完成",
        session_id="session_1",
        timestamp="2026-06-07T10:00:00",
        agent_name="TestAgent",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER
    )

    assert result.cwd is None
    assert result.modified_files is None
    assert result.git_diff_range is None
