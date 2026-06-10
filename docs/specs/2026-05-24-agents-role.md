---
version: 1.6
created_at: 2026-05-24
updated_at: 2026-06-06
last_updated: 修正 PATCH /{name} 端点说明，明确 name 为路径参数不在 request body 中，RoleUpdateRequest 仅含 avatar/abilities/description
abstract: roles 角色配置模块的正式规格，定义角色生命周期管理、配置数据结构、头像引用机制、Skill 管理和 HTTP API 契约
id: spec-roles
title: Roles 角色配置模块规格
status: unstable
module: roles
sourc_spec: docs/superpowers/specs/2026-05-24-role-config-design.md
related_plan: docs/superpowers/plans/2026-05-24-role-config-implementation.md
code_scope:
  - agents_hub/roles/
  - agents_hub/api/routes/roles.py
  - agents_hub/api/schemas/roles.py
  - agents_hub/api/services/role_service.py
contract_refs:
  - agents_hub/roles/models.py
  - agents_hub/roles/exceptions.py
  - agents_hub/config/types.py
  - agents_hub/api/schemas/roles.py
---

# Roles 角色配置模块规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 从当前代码提炼生成正式 spec 初稿 |
| 1.1 | 模块路径从 agents 重命名为 roles |
| 1.2 | RoleConfig 字段重构（统一 work_root，新增 description/role_type/bare）；RoleInfo 默认 role_type；contract_refs 更新 |
| 1.3 | 新增角色名称互为前缀冲突校验规则，避免 @mention 歧义 |
| 1.4 | role.json 不再保存 skills；Skill 以 work_root/skills 为启用状态；创建角色自动初始化固定 agents-hub MCP；权限和原生配置编辑暂不落地 |
| 1.5 | 新增 Roles API 层规格：路由端点、Request/Response Schemas、Service 层契约 |
| 1.6 | 修正 PATCH /{name} 端点说明：name 为路径参数不在 body 中，仅支持更新 avatar/abilities/description |

---

## Overview

roles 模块是 agents-hub 系统的**角色管理层**，负责 AI Agent 角色的全生命周期管理，包括创建、配置、查询和删除。

模块分层：
- **领域层**（`agents_hub/roles/`）：RoleManager、Role、数据模型、异常定义
- **API 层**（`agents_hub/api/`）：路由、Request/Response Schemas、Service 协调层

模块定位：
- **负责**：角色 CRUD、配置持久化、Skill 管理、头像引用管理、创建角色时初始化固定 agents-hub MCP、构造给 agent_bridge 的 RoleConfig、通过 HTTP API 暴露上述能力
- **不负责**：用户自定义 MCP 管理、权限策略落地、原生平台配置编辑、消息传递、prompt 构造、多 agent 协调、群聊管理、任务调度

核心设计原则：
- **SSOT**：`role.json` 是角色数据的唯一来源
- **配置分层**：`role.json`（业务配置，面向用户）→ `RoleConfig`（系统配置，面向 agent_bridge）
- **角色发现**：扫描 `local_data/agents/*/role.json`，不维护额外索引

## Scope

### 范围内

- 角色的创建、删除、查询、列表
- 角色元信息管理（名称、头像、能力标签、类型、群聊范围）
- 头像文件引用管理（头像文件统一存放在 `assets/` 目录）
- Skill 的添加、移除、列表
- 平台配置初始化（Claude / Codex）
- 构造给 agent_bridge 的 RoleConfig

### 范围外

- 头像文件的实际上传与存储（MVP 阶段仅支持从 `assets/` 选择预设头像）
- type 字段的调度逻辑（leader/team_member）
- scope 字段的群聊绑定逻辑
- abilities 的匹配调度
- 消息传递与会话管理
- 权限配置语义化操作暂不落地，等待 Docker / 外部沙箱方案明确
- 不提供 settings.json / config.toml 原生编辑接口

## Core Behavior

### 角色与平台绑定

一个角色绑定一个 platform（`claude` 或 `codex`），一对一关系。需要多平台支持时，创建多个角色。

### 配置分层

| 层 | 用途 | 存储位置 | 消费方 |
|---|------|----------|--------|
| role.json | 业务配置 | `local_data/agents/<name>/role.json` | 前端、用户 |
| RoleConfig | 系统内部配置 | 运行时由 role.json + 目录结构派生 | agent_bridge |

`RoleConfig` 不包含 `system_prompt` 和 `skills`——这些由 CLI 从角色目录自动加载。

### system_prompt 存储

不存入 `role.json`，直接写入角色的平台配置文件：
- Claude：`work_root/CLAUDE.md`
- Codex：`work_root/AGENTS.md`

### 头像管理机制

头像采用**引用模式**：所有头像文件统一存放在 `local_data/agents/assets/` 目录，角色只在 `role.json` 中存储文件名引用。

路径规则：
- 头像文件：`local_data/agents/assets/`（预设 + 上传）
- 角色目录：`local_data/agents/<role_name>/`，含 `role.json` 和 `work_root/`
- 全局 Skill 库：`local_data/skills/`

行为规则：
- `avatar` 字段为 `Optional[str]`，存储文件名（如 `"avatar_01.png"`），可为 `None`
- 更新头像只修改 `role.json` 中的文件名引用，不涉及文件复制或移动
- 可用头像列表通过扫描 `assets/` 目录获取

### Skill 管理机制

Skill 采用**引用优先模式**：全局 `local_data/skills/` 是 Skill 内容的 SSOT，角色的 `work_root/skills/<skill_id>` 是平台可见的启用入口。

行为规则：
- 添加 skill 时，优先在角色 `work_root/skills/` 下创建指向全局 skill 目录的 symlink
- 如果 symlink 创建失败，降级复制整个 skill 目录
- `role.json` 不保存 skills 字段
- 列出 skill 时扫描 `work_root/skills/`
- 移除 skill 时只删除角色下的入口，不影响全局 skill

### 角色创建初始化

创建角色时的目录初始化顺序：
1. 验证角色名称合法性（见下方命名规则）
2. 检查名称与已有角色是否存在互为前缀冲突
3. 创建 `role_dir`、`work_root`、`work_root/skills` 目录
4. 根据 platform 复制平台配置（从 `~/.claude` 或 `~/.codex`）
5. 写入 `role.json`
6. 若初始化失败，自动清理已创建的目录（回滚）

### 角色命名规则

角色名称需同时满足以下两层校验：

**基础校验**：
- 非空
- 不以 `.` 开头
- 不以空格结尾
- 不包含空格
- 不包含 Windows 禁止字符 `\/:*?"<>|`
- 不是 Windows 保留名（CON、PRN、AUX、NUL、COM1-9、LPT1-9）

**前缀冲突校验**：

新名称 A 与任意已有名称 B 不能互为前缀，即不能满足 `A.startswith(B)` 或 `B.startswith(A)`。

目的：避免群聊中 `@mention` 解析歧义。例如 `nico` 与 `nico_1` 互为前缀，`@nico` 会误匹配 `@nico_1`，因此禁止。

| 新名称 | 已有名称 | 结果 | 原因 |
|--------|----------|------|------|
| `nico_1` | `nico` | 冲突 | `nico` 是 `nico_1` 的前缀 |
| `nico` | `nico_1` | 冲突 | 同上 |
| `1_nico` | `nico` | 不冲突 | 互不为前缀 |
| `alice` | `nico` | 不冲突 | 互不为前缀 |

### 角色名称更新

更新角色名称时，同步修改 `role.json` 中的 `name` 字段和角色目录名，保持二者一致。新名称同样需要通过基础校验和前缀冲突校验。

## Technical Contract

### 数据结构

#### RoleInfo（角色摘要）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称，与目录名一致 |
| platform | AgentPlatform | 是 | 目标平台（claude / codex） |
| avatar | Optional[str] | 否 | 头像文件名（位于 assets/ 目录） |
| abilities | List[str] | 否 | 能力标签列表 |
| type | Optional[RoleType] | 否 | 角色类型（leader / team_member / system），默认 team_member |
| description | Optional[str] | 否 | 角色职责描述 |
| scope | Optional[List[str]] | 否 | 所属群聊列表 |

#### SkillInfo（Skill 摘要）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | str | 是 | skill 唯一标识 |
| name | str | 是 | skill 名称 |
| description | str | 是 | skill 描述 |

#### RoleType 枚举

| 值 | 说明 |
|---|------|
| LEADER | 领导者角色 |
| TEAM_MEMBER | 团队成员角色 |
| SYSTEM | 系统角色，由系统预置的特殊角色 |

### role.json 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称，与目录名一致 |
| platform | "claude" \| "codex" | 是 | 目标平台 |
| description | str \| null | 否 | 角色职责描述 |
| avatar | str \| null | 否 | 头像文件名 |
| abilities | list[str] | 否 | 能力标签列表 |
| type | "leader" \| "team_member" \| "system" \| null | 否 | 角色类型，默认 team_member |
| scope | list[str] \| null | 否 | 所属群聊列表 |

### 异常类型

| 异常 | 触发场景 |
|------|----------|
| RoleNotFoundError | get_role 时角色不存在 |
| RoleAlreadyExistsError | create_role 时名称已存在 |
| ValueError | 名称不合法（基础校验失败）或与已有角色互为前缀冲突 |
| PlatformConfigNotFoundError | 平台源配置目录不存在（~/.claude 或 ~/.codex） |
| SkillNotFoundError | add/remove skill 时 skill 不存在 |
| SkillAlreadyExistsError | add_skill 时 skill 已存在于角色中 |

### 领域组件职责划分

| 组件 | 职责 |
|------|------|
| RoleManager | 角色生命周期管理（创建、删除、查询、列表）、名称验证、可用头像发现 |
| Role | 单个角色的配置读写、Skill 管理、构造给 agent_bridge 的 RoleConfig |

### 调用流程

用户选择角色 → 通过 RoleManager 加载角色实例 → 构造 RoleConfig → 传入 agent_bridge 执行

### API 层

#### 架构分层

```
route → service → manager
```

- **route**：HTTP 入口，只做参数接收和响应转换，不写业务逻辑和 try/except
- **service**：业务协调，编排 manager 调用，处理 schema ↔ 领域模型转换
- **manager**：领域逻辑（RoleManager / Role）

路由通过 FastAPI `Depends` 注入 Service 实例，禁止在路由中直接实例化。

#### API 端点

所有端点挂在 `/roles` 前缀下。

**角色 CRUD**

| 方法 | 路径 | 说明 | 成功状态码 |
|------|------|------|-----------|
| GET | `/roles` | 列出所有角色 | 200 |
| GET | `/roles/{name}` | 获取单个角色 | 200 |
| POST | `/roles` | 创建角色 | 201 |
| PATCH | `/roles/{name}` | 更新角色信息（`name` 为路径参数，不在 request body 中；仅支持更新 avatar、abilities、description） | 200 |
| DELETE | `/roles/{name}` | 删除角色 | 200 |

**头像查询**

| 方法 | 路径 | 说明 | 成功状态码 |
|------|------|------|-----------|
| GET | `/roles/avatars` | 列出可用头像文件名 | 200 |
| GET | `/roles/avatars/{filename}` | 获取头像文件（静态文件服务），前端通过 `buildAvatarUrl(filename)` 构建此 URL | 200 |

**角色 Skill 管理**

| 方法 | 路径 | 说明 | 成功状态码 |
|------|------|------|-----------|
| GET | `/roles/{name}/skills` | 列出角色已启用的 skills | 200 |
| POST | `/roles/{name}/skills` | 为角色添加 skill | 201 |
| DELETE | `/roles/{name}/skills/{skill_id}` | 移除角色的 skill | 200 |

#### 路由约束

- 静态路径（`/avatars`）必须在动态路径（`/{name}`）之前定义，避免被抢先匹配
- 每个端点必须声明 `response_model`
- 所有异常由全局异常处理器统一处理，路由层禁止 try/except
- 领域模型必须通过 schema 的 `from_domain` 转换后返回，禁止直接返回领域对象

#### Request Schemas

**RoleCreateRequest**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称 |
| platform | "claude" \| "codex" | 是 | 目标平台 |
| avatar | str \| None | 否 | 头像文件名 |
| abilities | list[str] | 否 | 能力标签，默认 `[]` |
| type | "leader" \| "team_member" \| "system" \| None | 否 | 角色类型 |
| scope | list[str] \| None | 否 | 所属群聊列表 |
| description | str \| None | 否 | 角色职责描述 |

**RoleUpdateRequest**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| avatar | str \| None | 否 | 头像文件名，传入则更新 |
| abilities | list[str] \| None | 否 | 能力标签，传入则覆盖 |
| description | str \| None | 否 | 角色描述，传入则更新 |

所有字段可选，仅更新传入的字段（PATCH 语义）。

**RoleSkillRequest**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| skill_id | str | 是 | 要添加的 skill 标识 |

#### Response Schemas

**RoleResponse**

与 `RoleInfo` 领域模型字段一一对应，通过 `from_domain` 类方法转换。

**RoleSkillResponse**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | skill 唯一标识 |
| name | str | skill 名称 |
| description | str | skill 描述 |

通过 `from_domain` 从 `SkillInfo` 领域模型转换。

**删除/移除响应**

统一返回 `{"message": "..."}` 格式的成功提示。

#### API 异常映射

领域异常由全局异常处理器统一转换为 HTTP 错误响应，路由层不感知异常：

| 领域异常 | HTTP 状态码 | 触发场景 |
|----------|------------|----------|
| RoleNotFoundError | 404 | 角色不存在 |
| RoleAlreadyExistsError | 409 | 角色名已存在 |
| ValueError | 422 | 名称不合法或前缀冲突 |
| PlatformConfigNotFoundError | 404 | 平台配置目录不存在 |
| SkillNotFoundError | 404 | Skill 不存在 |
| SkillAlreadyExistsError | 409 | Skill 已存在于角色中 |
| ValidationError | 422 | 通用校验失败（如 Skill 元数据无效） |

## Acceptance Notes

1. 能创建角色，目录结构和 role.json 正确生成
2. 能列出所有角色，损坏的 role.json 被跳过
3. 能按名称加载角色并构造 RoleConfig
4. 能添加/移除 skill，以 symlink 优先模式管理 work_root/skills/ 目录
5. 能更新角色基本信息（名称、头像引用、能力标签）
6. 能列出 `assets/` 目录下所有可用头像
7. 创建角色失败时自动回滚已创建的目录
8. API 端点返回的 RoleResponse 字段与 RoleInfo 领域模型一致
9. POST/PATCH 请求体校验失败时返回 422
10. 领域异常正确映射为对应的 HTTP 状态码
11. `/roles/avatars` 静态路径不被 `/{name}` 动态路径抢先匹配

## Out of Spec

- 头像文件的实际上传、存储和图片处理
- type 字段（leader/team_member）的调度逻辑
- scope 字段的群聊绑定逻辑
- abilities 的匹配调度
- 多 agent 协调与消息传递
- 权限配置语义化操作暂不落地，等待 Docker / 外部沙箱方案明确
- 不提供 settings.json / config.toml 原生编辑接口
