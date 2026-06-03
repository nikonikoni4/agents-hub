import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from agents_hub.config.types import AgentPlatform, RoleType
from agents_hub.roles.models import RoleConfig


# 角色名称映射：config.default_manager_name -> 实际显示名
_MANAGER_DISPLAY_NAME = "Leader"


def _make_mock_role(name: str) -> MagicMock:
    """创建带有正确 name 和 role_config 属性的 mock Role"""
    role = MagicMock()
    role.name = name
    role.get_role_config.return_value = RoleConfig(
        name=name,
        platform=AgentPlatform.CLAUDE,
        role_type=RoleType.TEAM_MEMBER if name != _MANAGER_DISPLAY_NAME else RoleType.LEADER,
    )
    return role


def _make_mock_agent_result(agent_name: str = "test_agent", session_id: str = "test_session") -> MagicMock:
    """创建带有正确属性的 mock AgentResult"""
    result = MagicMock()
    result.agent_name = agent_name
    result.session_id = session_id
    result.text = "mock response"
    result.is_error = False
    result.error = None
    result.timestamp = "2026-06-03T10:00:00"
    result.platform = AgentPlatform.CLAUDE
    return result


@pytest.fixture(autouse=True)
def _mock_team_validation():
    """跳过 Team 的 RoleManager 验证，允许任意 role_name"""
    mock_role_manager = MagicMock()
    mock_role_manager.list_role_names.return_value = [
        "小王", "小李", _MANAGER_DISPLAY_NAME, "Worker1", "manager",
    ]

    def _get_role(name):
        # 当通过 config.default_manager_name ("manager") 查找时，返回 Leader 角色
        if name == "manager":
            return _make_mock_role(_MANAGER_DISPLAY_NAME)
        return _make_mock_role(name)

    mock_role_manager.get_role.side_effect = _get_role

    def _execute_side_effect(prompt, config=None, session_id=None, cwd=None):
        return _make_mock_agent_result(
            agent_name=session_id or "unknown",
            session_id=session_id or "mock_session",
        )

    mock_bridge = MagicMock()
    mock_bridge.execute = AsyncMock(side_effect=_execute_side_effect)

    with patch(
        "agents_hub.core.orchestration.team.RoleManager",
        return_value=mock_role_manager,
    ), patch(
        "agents_hub.core.orchestration.group_chat.RoleManager",
        return_value=mock_role_manager,
    ), patch(
        "agents_hub.core.agent.base_agent.agent_platform_client",
        mock_bridge,
    ):
        yield
