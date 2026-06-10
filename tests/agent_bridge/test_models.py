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
                "diff_error": None,
            }
        ],
        git_diff_range="abc123..def456",
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
        role_type=RoleType.TEAM_MEMBER,
    )

    assert result.cwd is None
    assert result.modified_files is None
    assert result.git_diff_range is None


def test_agent_result_with_web_preview():
    """
    契约：AgentResult 支持 web_preview 可选字段

    验证方式：
    1. 构造包含 web_preview 的 AgentResult
    2. 验证字段正确存储

    如果失败，说明：AgentResult 缺少 web_preview 字段定义
    """
    result = AgentResult(
        text="网页已生成",
        session_id="session_1",
        timestamp="2026-06-09T10:00:00",
        agent_name="TestAgent",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
        web_preview={"url": "http://localhost:3000", "title": "预览页面"},
    )

    assert result.web_preview is not None
    assert result.web_preview["url"] == "http://localhost:3000"
    assert result.web_preview["title"] == "预览页面"


def test_agent_result_without_web_preview():
    """
    契约：AgentResult 不传 web_preview 时默认为 None

    验证方式：
    1. 构造不包含 web_preview 的 AgentResult
    2. 验证字段为 None

    如果失败，说明：web_preview 默认值不是 None
    """
    result = AgentResult(
        text="任务完成",
        session_id="session_1",
        timestamp="2026-06-09T10:00:00",
        agent_name="TestAgent",
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER,
    )

    assert result.web_preview is None
