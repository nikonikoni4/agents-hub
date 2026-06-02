---
version: 1.0
created_at: 2026-06-02
updated_at: 2026-06-02
abstract: role_service 和 API 接口的设计文档，定义角色管理的 RESTful API
id: spec-role-service
title: Role Service 和 API 接口设计
status: unstable
module: roles/api
related_spec: docs/specs/2026-05-24-agents-role.md
code_scope:
  - agents_hub/api/routes/roles.py
  - agents_hub/api/schemas/roles.py
  - agents_hub/api/services/role_service.py
---

# Role Service 和 API 接口设计

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 初始设计，定义角色管理的 RESTful API |

---

## Overview

本设计为 `roles` 模块提供 RESTful API 接口，使前端可以通过 HTTP 调用角色管理功能。

设计定位：
- **负责**：角色 CRUD、角色 Skill 管理、角色信息更新、头像列表
- **不负责**：RoleConfig 构造（由 role 内部使用）、权限管理、原生配置编辑

设计原则：
- **一致性**：复用 `skills` API 的结构和风格
- **简洁性**：路由层只做参数接收和响应转换
- **契约驱动**：单元测试基于函数契约，而非覆盖率

## Scope

### 范围内

- 角色 CRUD（创建、读取、删除、列表）
- 角色信息更新（头像、能力标签、类型、范围、描述）
- 角色 Skill 管理（列表、添加、移除）
- 头像列表

### 范围外

- RoleConfig 构造
- 权限管理
- 原生配置编辑
- 头像上传和存储

## Core Behavior

### API 端点概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/roles` | 列出所有角色 |
| GET | `/roles/{name}` | 获取单个角色 |
| POST | `/roles` | 创建角色 |
| DELETE | `/roles/{name}` | 删除角色 |
| PATCH | `/roles/{name}` | 更新角色信息 |
| GET | `/roles/{name}/skills` | 列出角色的 skills |
| POST | `/roles/{name}/skills` | 为角色添加 skill |
| DELETE | `/roles/{name}/skills/{skill_id}` | 移除角色的 skill |
| GET | `/avatars` | 列出可用头像 |

### 依赖关系

```
routes/roles.py → services/role_service.py → roles/RoleManager → roles/Role
```

### 路由层规则

根据 `agents_hub/api/routes/CLAUDE.md`：

1. **禁止在路由中写 try/except** - 全局异常处理器已注册
2. **禁止在路由中导入异常类**
3. **禁止在路由中实例化 Service** - 使用 Depends 做依赖注入
4. **禁止在路由中写业务逻辑** - 只做参数接收和响应转换
5. **禁止直接返回领域模型** - 使用 Pydantic schema 的 from_domain 方法转换
6. **每个端点必须声明 response_model**

## Technical Contract

### 数据结构

#### 请求模型

```python
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
    type: Literal["leader", "team_member"] | None = None
    scope: list[str] | None = None
    description: str | None = None

class RoleSkillRequest(BaseModel):
    """添加角色 skill 请求"""
    skill_id: str
```

#### 响应模型

```python
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

class AvatarResponse(BaseModel):
    """头像列表响应"""
    avatars: list[str]
```

### 服务层设计

```python
class RoleService:
    """Roles 应用服务层

    协调 RoleManager，提供业务逻辑封装。
    """

    def __init__(self):
        self.role_manager = RoleManager()

    def list_roles(self) -> list[RoleInfo]:
        """获取所有角色"""
        return self.role_manager.list_roles()

    def get_role(self, name: str) -> RoleInfo:
        """获取单个角色"""
        role = self.role_manager.get_role(name)
        return role.to_role_info()

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
        return role.to_role_info()

    def delete_role(self, name: str) -> None:
        """删除角色"""
        self.role_manager.delete_role(name)

    def update_role(self, name: str, request: RoleUpdateRequest) -> RoleInfo:
        """更新角色信息"""
        role = self.role_manager.get_role(name)
        role.update_info(
            avatar=request.avatar,
            abilities=request.abilities,
            type=request.type,
            scope=request.scope,
            description=request.description,
        )
        return role.to_role_info()

    def list_role_skills(self, name: str) -> list[SkillInfo]:
        """列出角色的 skills"""
        role = self.role_manager.get_role(name)
        return role.list_skills()

    def add_role_skill(self, name: str, skill_id: str) -> SkillInfo:
        """为角色添加 skill"""
        role = self.role_manager.get_role(name)
        return role.add_skill(skill_id)

    def remove_role_skill(self, name: str, skill_id: str) -> None:
        """移除角色的 skill"""
        role = self.role_manager.get_role(name)
        role.remove_skill(skill_id)

    def list_avatars(self) -> list[str]:
        """列出可用头像"""
        return self.role_manager.list_avatars()
```

### 路由层设计

```python
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
def create_role(request: RoleCreateRequest, service: RoleService = Depends(get_role_service)):
    """创建角色"""
    role = service.create_role(request)
    return RoleResponse.from_domain(role)

@router.delete("/roles/{name}", status_code=204)
def delete_role(name: str, service: RoleService = Depends(get_role_service)):
    """删除角色"""
    service.delete_role(name)

# ========== 更新角色信息 ==========

@router.patch("/roles/{name}", response_model=RoleResponse)
def update_role(name: str, request: RoleUpdateRequest, service: RoleService = Depends(get_role_service)):
    """更新角色信息"""
    role = service.update_role(name, request)
    return RoleResponse.from_domain(role)

# ========== 角色 Skill 管理 ==========

@router.get("/roles/{name}/skills", response_model=list[SkillResponse])
def list_role_skills(name: str, service: RoleService = Depends(get_role_service)):
    """列出角色的 skills"""
    skills = service.list_role_skills(name)
    return [SkillResponse(id=s.id, name=s.name, description=s.description) for s in skills]

@router.post("/roles/{name}/skills", response_model=SkillResponse, status_code=201)
def add_role_skill(name: str, request: RoleSkillRequest, service: RoleService = Depends(get_role_service)):
    """为角色添加 skill"""
    skill = service.add_role_skill(name, request.skill_id)
    return SkillResponse(id=skill.id, name=skill.name, description=skill.description)

@router.delete("/roles/{name}/skills/{skill_id}", status_code=204)
def remove_role_skill(name: str, skill_id: str, service: RoleService = Depends(get_role_service)):
    """移除角色的 skill"""
    service.remove_role_skill(name, skill_id)

# ========== 头像管理 ==========

@router.get("/avatars", response_model=AvatarResponse)
def list_avatars(service: RoleService = Depends(get_role_service)):
    """列出可用头像"""
    avatars = service.list_avatars()
    return AvatarResponse(avatars=avatars)
```

### 异常处理

异常类已存在（`agents_hub/roles/exceptions.py`）：
- `RoleNotFoundError` → 继承 `ResourceNotFoundError`
- `RoleAlreadyExistsError` → 继承 `ValidationError`
- `PlatformConfigNotFoundError` → 继承 `ResourceNotFoundError`
- `SkillNotFoundError` → 继承 `ResourceNotFoundError`
- `SkillAlreadyExistsError` → 继承 `ValidationError`

异常处理流程：
```
service/manager 抛出异常
  → 全局异常处理器捕获
  → 调用异常的 to_dict() 方法
  → 返回 JSON 响应
```

### 测试策略

#### 单元测试（契约驱动）

文件：`tests/unit/test_role_service.py`

覆盖点：
1. **RoleService.create_role**
   - 契约：成功创建角色，返回 RoleInfo
   - 契约：名称重复时抛出 RoleAlreadyExistsError
   - 契约：名称不合法时抛出 ValueError

2. **RoleService.get_role**
   - 契约：成功获取角色，返回 RoleInfo
   - 契约：角色不存在时抛出 RoleNotFoundError

3. **RoleService.delete_role**
   - 契约：成功删除角色
   - 契约：角色不存在时抛出 RoleNotFoundError

4. **RoleService.update_role**
   - 契约：成功更新角色信息
   - 契约：角色不存在时抛出 RoleNotFoundError

5. **RoleService.list_role_skills**
   - 契约：成功列出角色的 skills

6. **RoleService.add_role_skill**
   - 契约：成功添加 skill
   - 契约：skill 不存在时抛出 SkillNotFoundError
   - 契约：skill 已存在时抛出 SkillAlreadyExistsError

7. **RoleService.remove_role_skill**
   - 契约：成功移除 skill
   - 契约：skill 不存在时抛出 SkillNotFoundError

#### 集成测试（API 端点）

文件：`tests/api/test_roles_api.py`

参考 `tests/api/test_skills_api.py` 的风格，使用 TestClient 测试端点。

## Acceptance Notes

1. 能通过 API 创建角色，返回正确的响应格式
2. 能通过 API 获取角色列表和单个角色
3. 能通过 API 删除角色
4. 能通过 API 更新角色信息
5. 能通过 API 管理角色的 skills
6. 能通过 API 获取可用头像列表
7. 所有端点都遵循路由层规则（无 try/except、无异常导入）
8. 单元测试基于契约驱动，覆盖所有关键路径

## Out of Spec

- RoleConfig 构造（由 role 内部使用）
- 权限管理
- 原生配置编辑
- 头像上传和存储
