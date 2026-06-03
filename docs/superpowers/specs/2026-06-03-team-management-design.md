---
version: 1.0
created_at: 2026-06-03
updated_at: 2026-06-03
last_updated: 初始版本
abstract: teams 团队管理模块的设计规格，定义团队的 CRUD 操作、成员验证机制、持久化策略和 HTTP API 契约
id: spec-teams
title: Teams 团队管理模块设计
status: draft
module: teams
sourc_spec: null
related_plan: null
code_scope:
  - agents_hub/teams/
  - agents_hub/api/routes/teams.py
  - agents_hub/api/schemas/teams.py
  - agents_hub/api/services/team_service.py
contract_refs:
  - agents_hub/teams/models.py
  - agents_hub/teams/exceptions.py
  - agents_hub/api/schemas/teams.py
---

# Teams 团队管理模块设计

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0  | 初始版本，定义团队管理的完整功能 |

---

## Overview

teams 模块是 agents-hub 系统的**团队配置管理层**，负责团队的全生命周期管理，包括创建、查询、更新和删除。

模块分层：
- **领域层**（`agents_hub/teams/`）：TeamManager、数据模型、异常定义
- **API 层**（`agents_hub/api/`）：路由、Request/Response Schemas、Service 协调层

模块定位：
- **负责**：团队 CRUD、成员列表管理、成员验证（调用 RoleManager）、持久化到 JSON 文件、通过 HTTP API 暴露功能
- **不负责**：团队的运行时调度逻辑、消息传递、群聊管理、角色配置管理

核心设计原则：
- **SSOT**：`teams.json` 是团队数据的唯一来源
- **简单性**：团队只是角色的集合，用于创建群聊时作为预设
- **验证优先**：添加成员时必须验证角色是否存在

## Scope

### 范围内

- 团队的创建、删除、查询、列表、更新
- 团队成员列表管理（role 名称列表）
- 成员验证（调用 RoleManager 验证 role 是否存在）
- 持久化到 `config.data_path/teams/teams.json`
- 并发安全的文件读写
- HTTP API 接口

### 范围外

- 团队的运行时调度逻辑
- 团队与群聊的绑定关系（由 GroupChat 负责）
- 角色配置的 CRUD（由 roles 模块负责）
- 消息传递和会话管理
- 团队权限管理

## Core Behavior

### 团队的本质

团队是**角色名称的集合**，在创建群聊时作为预设，将 `members` 列表传入 `GroupChat` 的初始化参数。

### 数据模型

**TeamInfo**（领域模型）：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 团队名称（唯一标识） |
| members | list[str] | 是 | 成员角色名称列表，至少包含一个成员 |

### 持久化格式

保存到 `config.data_path/teams/teams.json`，采用**数组格式**：

```json
[
  {
    "name": "frontend-team",
    "members": ["alice", "bob"]
  },
  {
    "name": "backend-team",
    "members": ["charlie", "david"]
  }
]
```

### 成员验证机制

**验证时机**：
- 创建团队时验证所有成员
- 更新团队成员列表时验证新成员列表

**验证流程**：
1. 调用 `RoleManager.list_role_names()` 获取所有可用角色
2. 检查 `members` 中的每个角色名称是否存在
3. 如果存在不存在的角色，抛出 `InvalidTeamMembersError`（422）
4. 如果成员列表为空，抛出 `EmptyTeamMembersError`（422）

### 并发控制

使用 `threading.Lock` 保护 `teams.json` 文件的读写操作：

```python
with self._lock:
    teams = self._load_teams()
    # 修改操作
    self._save_teams(teams)
```

确保读-修改-写的原子性。

### 名称唯一性

团队名称作为唯一标识，不允许重复：
- 创建时检查名称是否已存在，存在则抛出 `TeamAlreadyExistsError`（409）
- 更新名称时检查新名称是否与其他团队冲突，冲突则抛出 `TeamAlreadyExistsError`（409）

### 文件初始化

- 如果 `teams/` 目录不存在，自动创建
- 如果 `teams.json` 不存在，自动创建并写入空数组 `[]`

## Technical Contract

### 数据结构

#### TeamInfo（领域模型）

```python
from pydantic import BaseModel

class TeamInfo(BaseModel):
    """团队信息"""
    name: str
    members: list[str]
```

#### Request Schemas

**TeamCreateRequest**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 团队名称 |
| members | list[str] | 是 | 成员角色名称列表 |

**TeamUpdateRequest**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str \| None | 否 | 新的团队名称，为 None 时保持原名称 |
| members | list[str] \| None | 否 | 新的成员列表，为 None 时保持原成员列表 |

所有字段可选，仅更新传入的字段（PATCH 语义）。

#### Response Schema

**TeamResponse**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 团队名称 |
| members | list[str] | 成员角色名称列表 |

通过 `from_domain` 类方法从 `TeamInfo` 领域模型转换。

### 异常类型

| 异常 | 基类 | 触发场景 |
|------|------|----------|
| TeamNotFoundError | ResourceNotFoundError | 获取/更新/删除不存在的团队 |
| TeamAlreadyExistsError | ValidationError | 创建时名称已存在，或更新时新名称冲突 |
| InvalidTeamMembersError | ValidationError | 成员列表包含不存在的角色 |
| EmptyTeamMembersError | ValidationError | 成员列表为空 |

所有异常继承自 `agents_hub.exceptions` 的顶层基类。

### 领域组件职责划分

| 组件 | 职责 |
|------|------|
| TeamManager | 团队生命周期管理（创建、删除、查询、列表、更新）、持久化读写、并发控制、成员验证 |
| TeamInfo | 团队数据模型 |

### API 层

#### 架构分层

```
route → service → manager
```

- **route**：HTTP 入口，只做参数接收和响应转换，不写业务逻辑和 try/except
- **service**：业务协调，编排 manager 调用，处理 schema ↔ 领域模型转换
- **manager**：领域逻辑（TeamManager）

路由通过 FastAPI `Depends` 注入 Service 实例，禁止在路由中直接实例化。

#### API 端点

所有端点挂在 `/teams` 前缀下。

| 方法 | 路径 | 说明 | 成功状态码 |
|------|------|------|-----------|
| GET | `/teams` | 列出所有团队 | 200 |
| GET | `/teams/{name}` | 获取单个团队 | 200 |
| POST | `/teams` | 创建团队 | 201 |
| PATCH | `/teams/{name}` | 更新团队信息 | 200 |
| DELETE | `/teams/{name}` | 删除团队 | 200 |

#### 路由约束

- 每个端点必须声明 `response_model`
- 所有异常由全局异常处理器统一处理，路由层禁止 try/except
- 领域模型必须通过 schema 的 `from_domain` 转换后返回，禁止直接返回领域对象
- 使用 `Depends` 注入 Service，禁止直接实例化

#### API 异常映射

领域异常由全局异常处理器统一转换为 HTTP 错误响应，路由层不感知异常：

| 领域异常 | HTTP 状态码 | 触发场景 |
|----------|------------|----------|
| TeamNotFoundError | 404 | 团队不存在 |
| TeamAlreadyExistsError | 409 | 团队名已存在或新名称冲突 |
| InvalidTeamMembersError | 422 | 成员列表包含不存在的角色 |
| EmptyTeamMembersError | 422 | 成员列表为空 |
| ValidationError | 422 | 通用校验失败 |

## Data Flow

### 创建团队流程

```
前端发送 POST /teams
  ↓
Route 接收 TeamCreateRequest
  ↓
Service.create_team(request)
  ↓
TeamManager._validate_members(request.members)
  ↓ 如果成员列表为空
  抛出 EmptyTeamMembersError (422)
  ↓ 如果有无效成员
  抛出 InvalidTeamMembersError (422)
  ↓ 验证通过
TeamManager._load_teams()  ← 加锁读取 JSON
  ↓
检查名称是否已存在
  ↓ 如果存在
  抛出 TeamAlreadyExistsError (409)
  ↓ 不存在
添加新 team 到列表
  ↓
TeamManager._save_teams()  ← 写回 JSON
  ↓
返回 TeamInfo
  ↓
Route 转换为 TeamResponse
  ↓
返回 201 Created
```

### 更新团队流程

```
前端发送 PATCH /teams/{name}
  ↓
Route 接收 TeamUpdateRequest
  ↓
Service.update_team(name, request)
  ↓
TeamManager._load_teams()  ← 加锁读取
  ↓
查找 team
  ↓ 如果不存在
  抛出 TeamNotFoundError (404)
  ↓ 找到 team
如果 request.name 不为 None:
  检查新名称是否与其他 team 冲突
    ↓ 如果冲突
    抛出 TeamAlreadyExistsError (409)
  ↓
如果 request.members 不为 None:
  验证新成员列表
    ↓ 如果为空
    抛出 EmptyTeamMembersError (422)
    ↓ 如果有无效成员
    抛出 InvalidTeamMembersError (422)
  ↓
更新 team 数据
  ↓
TeamManager._save_teams()  ← 写回 JSON
  ↓
返回更新后的 TeamInfo
  ↓
Route 转换为 TeamResponse
  ↓
返回 200 OK
```

## Module Structure

```
agents_hub/
├── teams/                           # 新增模块
│   ├── __init__.py
│   ├── models.py                    # TeamInfo
│   ├── team_manager.py              # TeamManager（CRUD + 持久化）
│   └── exceptions.py                # Team 异常
├── api/
│   ├── routes/teams.py              # 5 个端点
│   ├── schemas/teams.py             # Request/Response schemas
│   └── services/team_service.py     # Service 协调层
└── config/
    └── data_path/
        └── teams/
            └── teams.json           # 持久化数据（数组格式）
```

## Acceptance Notes

1. ✅ 能创建团队，自动创建 `teams/` 目录和 `teams.json` 文件
2. ✅ 能列出所有团队，返回正确的 TeamResponse 列表
3. ✅ 能按名称获取单个团队
4. ✅ 能更新团队名称和成员列表
5. ✅ 能删除指定团队
6. ✅ 创建/更新时验证成员是否存在，不存在则返回 422
7. ✅ 成员列表为空时返回 422
8. ✅ 创建/更新时检查名称冲突，冲突时返回 409
9. ✅ 获取/更新/删除不存在的团队时返回 404
10. ✅ `teams.json` 格式正确（数组形式）
11. ✅ 创建/更新/删除操作正确反映到文件中
12. ✅ 并发读写时数据不丢失（加锁保护）
13. ✅ API 端点返回正确的 HTTP 状态码
14. ✅ Response Schema 与 TeamInfo 领域模型一致
15. ✅ 异常正确映射为 HTTP 错误响应
16. ✅ Route 层不包含业务逻辑和 try/except
17. ✅ Service 层正确协调 Manager 调用
18. ✅ TeamManager 正确调用 RoleManager 验证成员
19. ✅ 异常继承自 `agents_hub.exceptions` 顶层基类

## Out of Spec

- 团队的运行时调度逻辑（由 core/orchestration 负责）
- 团队与群聊的绑定关系管理
- 角色配置的 CRUD 操作（由 roles 模块负责）
- 团队权限管理
- 团队模板功能
- 团队成员的角色分配（manager/worker 等）
