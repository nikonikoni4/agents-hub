"""RoleService 单元测试 - 契约驱动"""

from unittest.mock import MagicMock

import pytest

from agents_hub.api.schemas.roles import RoleCreateRequest, RoleUpdateRequest
from agents_hub.api.services.role_service import RoleService
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.exceptions import (
    RoleAlreadyExistsError,
    RoleNotFoundError,
    SkillAlreadyExistsError,
    SkillNotFoundError,
)
from agents_hub.roles.models import RoleInfo, RoleType, SkillInfo


@pytest.fixture
def mock_role_manager():
    """Mock RoleManager"""
    return MagicMock()


@pytest.fixture
def service(mock_role_manager):
    """创建 RoleService 实例"""
    return RoleService(role_manager=mock_role_manager)


# ========== create_role ==========


def test_create_role_success(service, mock_role_manager):
    """
    契约：成功创建角色，返回 RoleInfo

    验证方式：
    1. 准备：mock RoleManager.create_role 返回 Role 实例
    2. 执行：调用 service.create_role
    3. 验证：返回正确的 RoleInfo
    """
    # 准备
    mock_role = MagicMock()
    mock_role.get_info.return_value = RoleInfo(
        name="test-role",
        platform=AgentPlatform.CLAUDE,
        avatar=None,
        abilities=[],
        type=RoleType.TEAM_MEMBER,
    )
    mock_role_manager.create_role.return_value = mock_role

    request = RoleCreateRequest(name="test-role", platform="claude")

    # 执行
    result = service.create_role(request)

    # 验证
    assert result.name == "test-role"
    assert result.platform == AgentPlatform.CLAUDE
    mock_role_manager.create_role.assert_called_once()


def test_create_role_already_exists(service, mock_role_manager):
    """
    契约：名称重复时抛出 RoleAlreadyExistsError

    验证方式：
    1. 准备：mock RoleManager.create_role 抛出 RoleAlreadyExistsError
    2. 执行：调用 service.create_role
    3. 验证：抛出 RoleAlreadyExistsError
    """
    # 准备
    mock_role_manager.create_role.side_effect = RoleAlreadyExistsError(
        role_name="test-role"
    )

    request = RoleCreateRequest(name="test-role", platform="claude")

    # 执行 & 验证
    with pytest.raises(RoleAlreadyExistsError):
        service.create_role(request)


def test_create_role_invalid_name(service, mock_role_manager):
    """
    契约：名称不合法时抛出 ValueError

    验证方式：
    1. 准备：mock RoleManager.create_role 抛出 ValueError
    2. 执行：调用 service.create_role
    3. 验证：抛出 ValueError
    """
    # 准备
    mock_role_manager.create_role.side_effect = ValueError("Invalid role name")

    request = RoleCreateRequest(name="invalid name", platform="claude")

    # 执行 & 验证
    with pytest.raises(ValueError):
        service.create_role(request)


# ========== get_role ==========


def test_get_role_success(service, mock_role_manager):
    """
    契约：成功获取角色，返回 RoleInfo

    验证方式：
    1. 准备：mock RoleManager.get_role 返回 Role 实例
    2. 执行：调用 service.get_role
    3. 验证：返回正确的 RoleInfo
    """
    # 准备
    mock_role = MagicMock()
    mock_role.get_info.return_value = RoleInfo(
        name="test-role",
        platform=AgentPlatform.CLAUDE,
        avatar=None,
        abilities=[],
        type=RoleType.TEAM_MEMBER,
    )
    mock_role.list_skills.return_value = []
    mock_role_manager.get_role.return_value = mock_role

    # 执行
    role_info, skills = service.get_role("test-role")

    # 验证
    assert role_info.name == "test-role"
    assert skills == []
    mock_role_manager.get_role.assert_called_once_with("test-role")


def test_get_role_not_found(service, mock_role_manager):
    """
    契约：角色不存在时抛出 RoleNotFoundError

    验证方式：
    1. 准备：mock RoleManager.get_role 抛出 RoleNotFoundError
    2. 执行：调用 service.get_role
    3. 验证：抛出 RoleNotFoundError
    """
    # 准备
    mock_role_manager.get_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    # 执行 & 验证
    with pytest.raises(RoleNotFoundError):
        service.get_role("nonexistent")


# ========== delete_role ==========


def test_delete_role_success(service, mock_role_manager):
    """
    契约：成功删除角色

    验证方式：
    1. 准备：mock RoleManager.delete_role 正常返回
    2. 执行：调用 service.delete_role
    3. 验证：RoleManager.delete_role 被调用
    """
    # 执行
    service.delete_role("test-role")

    # 验证
    mock_role_manager.delete_role.assert_called_once_with("test-role")


def test_delete_role_not_found(service, mock_role_manager):
    """
    契约：角色不存在时抛出 RoleNotFoundError

    验证方式：
    1. 准备：mock RoleManager.delete_role 抛出 RoleNotFoundError
    2. 执行：调用 service.delete_role
    3. 验证：抛出 RoleNotFoundError
    """
    # 准备
    mock_role_manager.delete_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    # 执行 & 验证
    with pytest.raises(RoleNotFoundError):
        service.delete_role("nonexistent")


# ========== update_role ==========


def test_update_role_success(service, mock_role_manager):
    """
    契约：成功更新角色信息

    验证方式：
    1. 准备：mock RoleManager.get_role 返回 Role 实例
    2. 执行：调用 service.update_role
    3. 验证：返回更新后的 RoleInfo
    """
    # 准备
    mock_role = MagicMock()
    mock_role.get_info.return_value = RoleInfo(
        name="test-role",
        platform=AgentPlatform.CLAUDE,
        avatar="new-avatar.png",
        abilities=["coding"],
        type=RoleType.TEAM_MEMBER,
    )
    mock_role.list_skills.return_value = []
    mock_role_manager.get_role.return_value = mock_role

    request = RoleUpdateRequest(avatar="new-avatar.png", abilities=["coding"])

    # 执行
    role_info, skills = service.update_role("test-role", request)

    # 验证
    assert role_info.avatar == "new-avatar.png"
    assert role_info.abilities == ["coding"]
    assert skills == []
    mock_role.update_avatar.assert_called_once_with("new-avatar.png")
    mock_role.update_abilities.assert_called_once_with(["coding"])


def test_update_role_not_found(service, mock_role_manager):
    """
    契约：角色不存在时抛出 RoleNotFoundError

    验证方式：
    1. 准备：mock RoleManager.get_role 抛出 RoleNotFoundError
    2. 执行：调用 service.update_role
    3. 验证：抛出 RoleNotFoundError
    """
    # 准备
    mock_role_manager.get_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    request = RoleUpdateRequest(avatar="new-avatar.png")

    # 执行 & 验证
    with pytest.raises(RoleNotFoundError):
        service.update_role("nonexistent", request)


# ========== list_role_skills ==========


def test_list_role_skills_success(service, mock_role_manager):
    """
    契约：成功列出角色的 skills

    验证方式：
    1. 准备：mock Role 实例的 list_skills 返回 SkillInfo 列表
    2. 执行：调用 service.list_role_skills
    3. 验证：返回正确的 SkillInfo 列表
    """
    # 准备
    mock_role = MagicMock()
    mock_role.list_skills.return_value = [
        SkillInfo(id="skill-1", name="Skill 1", description="Description 1"),
        SkillInfo(id="skill-2", name="Skill 2", description="Description 2"),
    ]
    mock_role_manager.get_role.return_value = mock_role

    # 执行
    result = service.list_role_skills("test-role")

    # 验证
    assert len(result) == 2
    assert result[0].id == "skill-1"
    assert result[1].id == "skill-2"


# ========== add_role_skill ==========


def test_add_role_skill_success(service, mock_role_manager):
    """
    契约：成功添加 skill

    验证方式：
    1. 准备：mock Role 实例的 add_skill 正常返回，list_skills 返回添加的 skill
    2. 执行：调用 service.add_role_skill
    3. 验证：返回添加的 SkillInfo
    """
    # 准备
    mock_role = MagicMock()
    mock_role.list_skills.return_value = [
        SkillInfo(id="skill-1", name="Skill 1", description="Description 1"),
    ]
    mock_role_manager.get_role.return_value = mock_role

    # 执行
    result = service.add_role_skill("test-role", "skill-1")

    # 验证
    assert result.id == "skill-1"
    mock_role.add_skill.assert_called_once_with("skill-1")


def test_add_role_skill_not_found(service, mock_role_manager):
    """
    契约：skill 不存在时抛出 SkillNotFoundError

    验证方式：
    1. 准备：mock Role 实例的 add_skill 抛出 SkillNotFoundError
    2. 执行：调用 service.add_role_skill
    3. 验证：抛出 SkillNotFoundError
    """
    # 准备
    mock_role = MagicMock()
    mock_role.add_skill.side_effect = SkillNotFoundError(skill_id="nonexistent")
    mock_role_manager.get_role.return_value = mock_role

    # 执行 & 验证
    with pytest.raises(SkillNotFoundError):
        service.add_role_skill("test-role", "nonexistent")


def test_add_role_skill_already_exists(service, mock_role_manager):
    """
    契约：skill 已存在时抛出 SkillAlreadyExistsError

    验证方式：
    1. 准备：mock Role 实例的 add_skill 抛出 SkillAlreadyExistsError
    2. 执行：调用 service.add_role_skill
    3. 验证：抛出 SkillAlreadyExistsError
    """
    # 准备
    mock_role = MagicMock()
    mock_role.add_skill.side_effect = SkillAlreadyExistsError(
        skill_id="skill-1", role_name="test-role"
    )
    mock_role_manager.get_role.return_value = mock_role

    # 执行 & 验证
    with pytest.raises(SkillAlreadyExistsError):
        service.add_role_skill("test-role", "skill-1")


# ========== remove_role_skill ==========


def test_remove_role_skill_success(service, mock_role_manager):
    """
    契约：成功移除 skill

    验证方式：
    1. 准备：mock Role 实例的 remove_skill 正常返回
    2. 执行：调用 service.remove_role_skill
    3. 验证：Role.remove_skill 被调用
    """
    # 准备
    mock_role = MagicMock()
    mock_role_manager.get_role.return_value = mock_role

    # 执行
    service.remove_role_skill("test-role", "skill-1")

    # 验证
    mock_role.remove_skill.assert_called_once_with("skill-1")


def test_remove_role_skill_not_found(service, mock_role_manager):
    """
    契约：skill 不存在时抛出 SkillNotFoundError

    验证方式：
    1. 准备：mock Role 实例的 remove_skill 抛出 SkillNotFoundError
    2. 执行：调用 service.remove_role_skill
    3. 验证：抛出 SkillNotFoundError
    """
    # 准备
    mock_role = MagicMock()
    mock_role.remove_skill.side_effect = SkillNotFoundError(skill_id="nonexistent")
    mock_role_manager.get_role.return_value = mock_role

    # 执行 & 验证
    with pytest.raises(SkillNotFoundError):
        service.remove_role_skill("test-role", "nonexistent")
