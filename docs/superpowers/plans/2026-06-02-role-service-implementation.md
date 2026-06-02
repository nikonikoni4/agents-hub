# Role Service 和 API 接口实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 roles 模块提供 RESTful API 接口，使前端可以通过 HTTP 调用角色管理功能

**Architecture:** 复用 skills API 的三层结构（route → service → manager），路由层只做参数接收和响应转换，服务层协调 RoleManager，全局异常处理器处理所有错误

**Tech Stack:** FastAPI, Pydantic, pytest

---

## 文件结构

```
agents_hub/api/
├── routes/
│   ├── __init__.py          # 修改：添加 roles router
│   └── roles.py             # 新建：角色 API 路由
├── schemas/
│   └── roles.py             # 新建：角色请求/响应模型
└── services/
    └── role_service.py      # 新建：角色服务层

tests/
├── unit/
│   └── test_role_service.py # 新建：单元测试
└── api/
    └── test_roles_api.py    # 新建：集成测试
```

---

## Task 1: 创建 schemas/roles.py - 请求和响应模型

**Files:**
- Create: `agents_hub/api/schemas/roles.py`

- [ ] **Step 1: 创建 schemas 文件**

```python
"""API schemas for roles."""

from typing import Literal

from pydantic import BaseModel

from agents_hub.roles.models import RoleInfo, SkillInfo


class RoleCreateRequest(BaseModel):
    """创建角色请求"""

    name: str
    platform: Literal["claude", "codex"]
    avatar: str | None = None
    abilities: list[str] = []
    type: Literal["leader", "team_member"] | None = None
    scope: list[str] | None = None
    description: str | None = None


class RoleUpdateRequest(BaseModel):
    """更新角色请求"""

    avatar: str | None = None
    abilities: list[str] | None = None
    description: str | None = None


class RoleSkillRequest(BaseModel):
    """添加角色 skill 请求"""

    skill_id: str


class RoleResponse(BaseModel):
    """角色响应"""

    name: str
    platform: str
    avatar: str | None = None
    abilities: list[str] = []
    type: str | None = None
    scope: list[str] | None = None
    description: str | None = None

    @classmethod
    def from_domain(cls, role_info: RoleInfo) -> "RoleResponse":
        """从领域模型转换"""
        return cls(
            name=role_info.name,
            platform=role_info.platform.value,
            avatar=role_info.avatar,
            abilities=role_info.abilities,
            type=role_info.type.value if role_info.type else None,
            scope=role_info.scope,
            description=role_info.description,
        )


class SkillResponse(BaseModel):
    """Skill 响应"""

    id: str
    name: str
    description: str

    @classmethod
    def from_domain(cls, skill_info: SkillInfo) -> "SkillResponse":
        """从领域模型转换"""
        return cls(
            id=skill_info.id,
            name=skill_info.name,
            description=skill_info.description,
        )
```

- [ ] **Step 2: 验证文件创建成功**

Run: `python -c "from agents_hub.api.schemas.roles import RoleCreateRequest, RoleResponse; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add agents_hub/api/schemas/roles.py
git commit -m "feat(api): add roles schemas"
```

---

## Task 2: 创建 services/role_service.py - 服务层

**Files:**
- Create: `agents_hub/api/services/role_service.py`

- [ ] **Step 1: 创建服务文件**

```python
"""Roles 应用服务层"""

from agents_hub.api.schemas.roles import RoleCreateRequest, RoleUpdateRequest
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.exceptions import SkillNotFoundError, ValidationError
from agents_hub.roles.models import RoleInfo, SkillInfo
from agents_hub.roles.role_manager import RoleManager


class RoleService:
    """Roles 应用服务层

    协调 RoleManager，提供业务逻辑封装。
    """

    def __init__(self, role_manager: RoleManager | None = None):
        self.role_manager = role_manager or RoleManager()

    def list_roles(self) -> list[RoleInfo]:
        """获取所有角色"""
        return self.role_manager.list_roles()

    def get_role(self, name: str) -> RoleInfo:
        """获取单个角色"""
        role = self.role_manager.get_role(name)
        return role.get_info()

    def create_role(self, request: RoleCreateRequest) -> RoleInfo:
        """创建角色"""
        role = self.role_manager.create_role(
            name=request.name,
            platform=AgentPlatform(request.platform),
            avatar=request.avatar,
            abilities=request.abilities,
            type=request.type,
            scope=request.scope,
            description=request.description,
        )
        return role.get_info()

    def delete_role(self, name: str) -> None:
        """删除角色"""
        self.role_manager.delete_role(name)

    def update_role(self, name: str, request: RoleUpdateRequest) -> RoleInfo:
        """更新角色信息"""
        role = self.role_manager.get_role(name)
        if request.avatar is not None:
            role.update_avatar(request.avatar)
        if request.abilities is not None:
            role.update_abilities(request.abilities)
        if request.description is not None:
            role.update_description(request.description)
        return role.get_info()

    def list_role_skills(self, name: str) -> list[SkillInfo]:
        """列出角色的 skills"""
        role = self.role_manager.get_role(name)
        return role.list_skills()

    def add_role_skill(self, name: str, skill_id: str) -> SkillInfo:
        """为角色添加 skill"""
        role = self.role_manager.get_role(name)
        role.add_skill(skill_id)
        # 添加后重新获取 skill 信息
        skills = role.list_skills()
        for skill in skills:
            if skill.id == skill_id:
                return skill
        # 如果添加成功但无法获取元数据，说明全局 skill 的 skill.json 可能损坏
        raise ValidationError(
            message=f"Skill '{skill_id}' 已添加但元数据无效",
            error_code="SKILL_METADATA_INVALID",
            details={"skill_id": skill_id, "role_name": name},
        )

    def remove_role_skill(self, name: str, skill_id: str) -> None:
        """移除角色的 skill"""
        role = self.role_manager.get_role(name)
        role.remove_skill(skill_id)

    def list_avatars(self) -> list[str]:
        """列出可用头像"""
        return self.role_manager.list_avatars()
```

- [ ] **Step 2: 验证文件创建成功**

Run: `python -c "from agents_hub.api.services.role_service import RoleService; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add agents_hub/api/services/role_service.py
git commit -m "feat(api): add role service"
```

---

## Task 3: 创建 routes/roles.py - API 路由

**Files:**
- Create: `agents_hub/api/routes/roles.py`

- [ ] **Step 1: 创建路由文件**

```python
"""角色 API 路由"""

from fastapi import APIRouter, Depends

from agents_hub.api.schemas.roles import (
    RoleCreateRequest,
    RoleResponse,
    RoleSkillRequest,
    RoleUpdateRequest,
    SkillResponse,
)
from agents_hub.api.services.role_service import RoleService

router = APIRouter()


def get_role_service() -> RoleService:
    """获取 RoleService 实例（依赖注入）"""
    return RoleService()


# ========== 角色 CRUD ==========


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(service: RoleService = Depends(get_role_service)):
    """获取所有角色"""
    roles = service.list_roles()
    return [RoleResponse.from_domain(r) for r in roles]


@router.get("/roles/{name}", response_model=RoleResponse)
def get_role(name: str, service: RoleService = Depends(get_role_service)):
    """获取单个角色"""
    role = service.get_role(name)
    return RoleResponse.from_domain(role)


@router.post("/roles", response_model=RoleResponse, status_code=201)
def create_role(
    request: RoleCreateRequest, service: RoleService = Depends(get_role_service)
):
    """创建角色"""
    role = service.create_role(request)
    return RoleResponse.from_domain(role)


@router.delete("/roles/{name}", response_model=dict[str, str])
def delete_role(name: str, service: RoleService = Depends(get_role_service)):
    """删除角色"""
    service.delete_role(name)
    return {"message": f"Role '{name}' 删除成功"}


# ========== 更新角色信息 ==========


@router.patch("/roles/{name}", response_model=RoleResponse)
def update_role(
    name: str,
    request: RoleUpdateRequest,
    service: RoleService = Depends(get_role_service),
):
    """更新角色信息"""
    role = service.update_role(name, request)
    return RoleResponse.from_domain(role)


# ========== 角色 Skill 管理 ==========


@router.get("/roles/{name}/skills", response_model=list[SkillResponse])
def list_role_skills(
    name: str, service: RoleService = Depends(get_role_service)
):
    """列出角色的 skills"""
    skills = service.list_role_skills(name)
    return [SkillResponse.from_domain(s) for s in skills]


@router.post("/roles/{name}/skills", response_model=SkillResponse, status_code=201)
def add_role_skill(
    name: str,
    request: RoleSkillRequest,
    service: RoleService = Depends(get_role_service),
):
    """为角色添加 skill"""
    skill = service.add_role_skill(name, request.skill_id)
    return SkillResponse.from_domain(skill)


@router.delete(
    "/roles/{name}/skills/{skill_id}", response_model=dict[str, str]
)
def remove_role_skill(
    name: str, skill_id: str, service: RoleService = Depends(get_role_service)
):
    """移除角色的 skill"""
    service.remove_role_skill(name, skill_id)
    return {"message": f"Skill '{skill_id}' 从角色 '{name}' 移除成功"}


# ========== 头像管理 ==========


@router.get("/avatars", response_model=list[str])
def list_avatars(service: RoleService = Depends(get_role_service)):
    """列出可用头像"""
    return service.list_avatars()
```

- [ ] **Step 2: 验证文件创建成功**

Run: `python -c "from agents_hub.api.routes.roles import router; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add agents_hub/api/routes/roles.py
git commit -m "feat(api): add roles routes"
```

---

## Task 4: 修改 routes/__init__.py 和 app.py - 注册 roles router

**Files:**
- Modify: `agents_hub/api/routes/__init__.py`
- Modify: `agents_hub/api/app.py`

- [ ] **Step 1: 修改 __init__.py**

```python
"""API routes package."""

from .roles import router as roles_router
from .skills import router as skills_router

__all__ = ["roles_router", "skills_router"]
```

- [ ] **Step 2: 修改 app.py**

将：
```python
from .routes import router
```

改为：
```python
from .routes import roles_router, skills_router
```

将：
```python
# 注册路由
app.include_router(router)
```

改为：
```python
# 注册路由
app.include_router(roles_router)
app.include_router(skills_router)
```

- [ ] **Step 3: 验证修改成功**

Run: `python -c "from agents_hub.api.routes import roles_router, skills_router; print('OK')"`
Expected: OK

- [ ] **Step 4: Commit**

```bash
git add agents_hub/api/routes/__init__.py agents_hub/api/app.py
git commit -m "feat(api): register roles router"
```

---

## Task 5: 创建单元测试 - test_role_service.py

**Files:**
- Create: `tests/unit/test_role_service.py`

- [ ] **Step 1: 创建单元测试文件**

```python
"""RoleService 单元测试 - 契约驱动"""

import pytest
from unittest.mock import MagicMock

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
    mock_role_manager.get_role.return_value = mock_role

    # 执行
    result = service.get_role("test-role")

    # 验证
    assert result.name == "test-role"
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
    mock_role_manager.get_role.return_value = mock_role

    request = RoleUpdateRequest(avatar="new-avatar.png", abilities=["coding"])

    # 执行
    result = service.update_role("test-role", request)

    # 验证
    assert result.avatar == "new-avatar.png"
    assert result.abilities == ["coding"]
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
```

- [ ] **Step 2: 运行单元测试**

Run: `pytest tests/unit/test_role_service.py -v`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_role_service.py
git commit -m "test(api): add role service unit tests"
```

---

## Task 6: 创建集成测试 - test_roles_api.py

**Files:**
- Create: `tests/api/test_roles_api.py`

- [ ] **Step 1: 创建集成测试文件**

```python
"""Roles API 集成测试"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from agents_hub.api.routes.roles import router
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.exceptions import (
    RoleAlreadyExistsError,
    RoleNotFoundError,
    SkillAlreadyExistsError,
    SkillNotFoundError,
)
from agents_hub.roles.models import RoleInfo, RoleType, SkillInfo


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@pytest.fixture
def mock_role_service():
    """Mock RoleService"""
    with patch("agents_hub.api.routes.roles.RoleService") as mock:
        yield mock.return_value


# ========== GET /roles ==========


def test_list_roles_success(client, mock_role_service):
    """测试：成功列出角色"""
    mock_role_service.list_roles.return_value = [
        RoleInfo(
            name="role-1",
            platform=AgentPlatform.CLAUDE,
            avatar=None,
            abilities=[],
            type=RoleType.TEAM_MEMBER,
        ),
        RoleInfo(
            name="role-2",
            platform=AgentPlatform.CODEX,
            avatar="avatar.png",
            abilities=["coding"],
            type=RoleType.LEADER,
        ),
    ]

    response = client.get("/api/roles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "role-1"
    assert data[1]["name"] == "role-2"


def test_list_roles_empty(client, mock_role_service):
    """测试：列出空角色列表"""
    mock_role_service.list_roles.return_value = []

    response = client.get("/api/roles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0


# ========== GET /roles/{name} ==========


def test_get_role_success(client, mock_role_service):
    """测试：成功获取角色"""
    mock_role_service.get_role.return_value = RoleInfo(
        name="test-role",
        platform=AgentPlatform.CLAUDE,
        avatar=None,
        abilities=[],
        type=RoleType.TEAM_MEMBER,
    )

    response = client.get("/api/roles/test-role")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-role"
    assert data["platform"] == "claude"


def test_get_role_not_found(client, mock_role_service):
    """测试：获取不存在的角色"""
    mock_role_service.get_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    response = client.get("/api/roles/nonexistent")
    assert response.status_code == 404


# ========== POST /roles ==========


def test_create_role_success(client, mock_role_service):
    """测试：成功创建角色"""
    mock_role_service.create_role.return_value = RoleInfo(
        name="new-role",
        platform=AgentPlatform.CLAUDE,
        avatar=None,
        abilities=[],
        type=RoleType.TEAM_MEMBER,
    )

    response = client.post(
        "/api/roles",
        json={"name": "new-role", "platform": "claude"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new-role"


def test_create_role_already_exists(client, mock_role_service):
    """测试：创建已存在的角色"""
    mock_role_service.create_role.side_effect = RoleAlreadyExistsError(
        role_name="existing-role"
    )

    response = client.post(
        "/api/roles",
        json={"name": "existing-role", "platform": "claude"},
    )
    assert response.status_code == 422


# ========== DELETE /roles/{name} ==========


def test_delete_role_success(client, mock_role_service):
    """测试：成功删除角色"""
    response = client.delete("/api/roles/test-role")
    assert response.status_code == 200
    data = response.json()
    assert "删除成功" in data["message"]


def test_delete_role_not_found(client, mock_role_service):
    """测试：删除不存在的角色"""
    mock_role_service.delete_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    response = client.delete("/api/roles/nonexistent")
    assert response.status_code == 404


# ========== PATCH /roles/{name} ==========


def test_update_role_success(client, mock_role_service):
    """测试：成功更新角色"""
    mock_role_service.update_role.return_value = RoleInfo(
        name="test-role",
        platform=AgentPlatform.CLAUDE,
        avatar="new-avatar.png",
        abilities=["coding"],
        type=RoleType.TEAM_MEMBER,
    )

    response = client.patch(
        "/api/roles/test-role",
        json={"avatar": "new-avatar.png", "abilities": ["coding"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["avatar"] == "new-avatar.png"
    assert data["abilities"] == ["coding"]


def test_update_role_not_found(client, mock_role_service):
    """测试：更新不存在的角色"""
    mock_role_service.update_role.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    response = client.patch(
        "/api/roles/nonexistent",
        json={"avatar": "new-avatar.png"},
    )
    assert response.status_code == 404


# ========== GET /roles/{name}/skills ==========


def test_list_role_skills_success(client, mock_role_service):
    """测试：成功列出角色 skills"""
    mock_role_service.list_role_skills.return_value = [
        SkillInfo(id="skill-1", name="Skill 1", description="Description 1"),
        SkillInfo(id="skill-2", name="Skill 2", description="Description 2"),
    ]

    response = client.get("/api/roles/test-role/skills")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == "skill-1"


def test_list_role_skills_role_not_found(client, mock_role_service):
    """测试：列出不存在角色的 skills"""
    mock_role_service.list_role_skills.side_effect = RoleNotFoundError(
        role_name="nonexistent"
    )

    response = client.get("/api/roles/nonexistent/skills")
    assert response.status_code == 404


# ========== POST /roles/{name}/skills ==========


def test_add_role_skill_success(client, mock_role_service):
    """测试：成功为角色添加 skill"""
    mock_role_service.add_role_skill.return_value = SkillInfo(
        id="skill-1", name="Skill 1", description="Description 1"
    )

    response = client.post(
        "/api/roles/test-role/skills",
        json={"skill_id": "skill-1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "skill-1"


def test_add_role_skill_not_found(client, mock_role_service):
    """测试：添加不存在的 skill"""
    mock_role_service.add_role_skill.side_effect = SkillNotFoundError(
        skill_id="nonexistent"
    )

    response = client.post(
        "/api/roles/test-role/skills",
        json={"skill_id": "nonexistent"},
    )
    assert response.status_code == 404


def test_add_role_skill_already_exists(client, mock_role_service):
    """测试：添加已存在的 skill"""
    mock_role_service.add_role_skill.side_effect = SkillAlreadyExistsError(
        skill_id="skill-1", role_name="test-role"
    )

    response = client.post(
        "/api/roles/test-role/skills",
        json={"skill_id": "skill-1"},
    )
    assert response.status_code == 422


# ========== DELETE /roles/{name}/skills/{skill_id} ==========


def test_remove_role_skill_success(client, mock_role_service):
    """测试：成功移除角色 skill"""
    response = client.delete("/api/roles/test-role/skills/skill-1")
    assert response.status_code == 200
    data = response.json()
    assert "移除成功" in data["message"]


def test_remove_role_skill_not_found(client, mock_role_service):
    """测试：移除不存在的 skill"""
    mock_role_service.remove_role_skill.side_effect = SkillNotFoundError(
        skill_id="nonexistent"
    )

    response = client.delete("/api/roles/test-role/skills/nonexistent")
    assert response.status_code == 404


# ========== GET /avatars ==========


def test_list_avatars_success(client, mock_role_service):
    """测试：成功列出头像"""
    mock_role_service.list_avatars.return_value = [
        "avatar1.png",
        "avatar2.png",
    ]

    response = client.get("/api/avatars")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0] == "avatar1.png"


def test_list_avatars_empty(client, mock_role_service):
    """测试：列出空头像列表"""
    mock_role_service.list_avatars.return_value = []

    response = client.get("/api/avatars")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 0
```

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/api/test_roles_api.py -v`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add tests/api/test_roles_api.py
git commit -m "test(api): add roles API integration tests"
```

---

## Task 7: 修复 Role.get_info() 默认值问题

**Files:**
- Modify: `agents_hub/roles/role.py:82-83`

- [ ] **Step 1: 修改 Role.get_info() 方法**

将：
```python
role_type = RoleType(type_str) if type_str else None
```

改为：
```python
role_type = RoleType(type_str) if type_str else RoleType.TEAM_MEMBER
```

- [ ] **Step 2: 运行现有测试验证**

Run: `pytest tests/utils/roles/ -v`
Expected: 所有测试通过

- [ ] **Step 3: Commit**

```bash
git add agents_hub/roles/role.py
git commit -m "fix(roles): use default TEAM_MEMBER when type not in role.json"
```

---

## Task 8: 运行所有测试并验证

- [ ] **Step 1: 运行所有相关测试**

Run: `pytest tests/unit/test_role_service.py tests/api/test_roles_api.py tests/utils/roles/ -v`
Expected: 所有测试通过

- [ ] **Step 2: 运行代码检查**

Run: `ruff check agents_hub/api/`
Expected: 无错误

- [ ] **Step 3: 运行类型检查**

Run: `mypy agents_hub/api/`
Expected: 无错误

- [ ] **Step 4: Final Commit**

```bash
git add -A
git commit -m "feat(api): complete role service and API implementation"
```
