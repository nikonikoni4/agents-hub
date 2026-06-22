---
version: 2.0
created_at: 2026-05-24
updated_at: 2026-06-18
last_updated: 按照新 spec 规则重构：移除执行细节，添加 key_function 标签和 Design Rationale
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
| 2.0 | 按照新 spec 规则重构：移除执行细节，添加 key_function 标签和 Design Rationale |

---

## Overview

**业务问题**：agents-hub 系统需要一个统一的角色管理层，用于管理 AI Agent 角色的配置和生命周期。

**核心职责**：
- 角色的创建、删除、查询、列表
- 角色配置的持久化（role.json）
- Skill 的引用管理
- 头像文件的引用管理
- 构造给 agent_bridge 的 RoleConfig
- 通过 HTTP API 暴露上述能力

**不负责**：
- 用户自定义 MCP 管理
- 权限策略落地
- 原生平台配置编辑
- 消息传递、prompt 构造
- 多 agent 协调、群聊管理、任务调度

## Scope

### 范围内

- 角色的创建、删除、查询、列表
- 角色元信息管理（名称、头像、能力标签、类型、群聊范围）
- 头像文件引用管理（头像文件统一存放在 `assets/` 目录）
- Skill 的添加、移除、列表
- 平台配置初始化（Claude / Codex / OpenCode）
- 构造给 agent_bridge 的 RoleConfig

### 范围外

- 头像文件的实际上传与存储（MVP 阶段仅支持从 `assets/` 选择预设头像）
- type 字段的调度逻辑（leader/team_member）
- scope 字段的群聊绑定逻辑
- abilities 的匹配调度
- 消息传递与会话管理
- 权限配置语义化操作暂不落地，等待 Docker / 外部沙箱方案明确
- 不提供 settings.json / config.toml 原生编辑接口

## Technical Contract

### 领域层

<key_function last_update="2026-06-23T05:41:09+08:00">
- agents_hub/roles/role_manager.py
  - role_manager.RoleManager.list_roles:146
  - role_manager.RoleManager.get_role:211
  - role_manager.RoleManager.create_role:266
  - role_manager.RoleManager.delete_role:369
  - role_manager.RoleManager.list_avatars:192
</key_function>

**对外接口**：

| 接口 | 说明 | 约束 |
|------|------|------|
| `RoleManager.list_roles()` | 列出所有角色 | 返回 `List[RoleInfo]`，损坏的 role.json 被跳过 |
| `RoleManager.get_role(name)` | 按名称获取角色实例 | 名称不合法抛 `ValueError`，不存在抛 `RoleNotFoundError` |
| `RoleManager.create_role(...)` | 创建新角色 | 名称已存在抛 `RoleAlreadyExistsError`，平台配置不存在抛 `PlatformConfigNotFoundError` |
| `RoleManager.delete_role(name)` | 删除角色及其目录 | 不存在抛 `RoleNotFoundError` |
| `RoleManager.list_avatars()` | 列出可用头像文件名 | 扫描 `assets/` 目录 |

### API 层

<key_function last_update="2026-06-18T10:00:00+08:00">
- agents_hub/api/routes/roles.py
  - roles.list_roles:30
  - roles.get_role:67
  - roles.create_role:74
  - roles.update_role:91
  - roles.delete_role:81
  - roles.list_avatars:37
  - roles.add_role_skill:105
  - roles.remove_role_skill:116
</key_function>

**API 端点**：

所有端点挂在 `/roles` 前缀下。

| 方法 | 路径 | 说明 | 成功状态码 |
|------|------|------|-----------|
| GET | `/roles` | 列出所有角色 | 200 |
| GET | `/roles/{name}` | 获取单个角色 | 200 |
| POST | `/roles` | 创建角色 | 201 |
| PATCH | `/roles/{name}` | 更新角色信息（`name` 为路径参数，不在 request body 中；仅支持更新 avatar、abilities、description） | 200 |
| DELETE | `/roles/{name}` | 删除角色 | 200 |
| GET | `/roles/avatars` | 列出可用头像文件名 | 200 |
| GET | `/roles/avatars/files/{filename}` | 获取头像文件（静态文件服务） | 200 |
| GET | `/roles/{name}/skills` | 列出角色已启用的 skills | 200 |
| POST | `/roles/{name}/skills` | 为角色添加 skill | 201 |
| DELETE | `/roles/{name}/skills/{skill_id}` | 移除角色的 skill | 200 |

**路由约束**：
- 静态路径（`/avatars`）必须在动态路径（`/{name}`）之前定义，避免被抢先匹配
- 每个端点必须声明 `response_model`
- 所有异常由全局异常处理器统一处理，路由层禁止 try/except
- 领域模型必须通过 schema 的 `from_domain` 转换后返回，禁止直接返回领域对象

### 数据结构

#### RoleInfo（角色摘要）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称，与目录名一致 |
| platform | AgentPlatform | 是 | 目标平台（claude / codex / opencode） |
| avatar | Optional[str] | 否 | 头像文件名（位于 assets/ 目录） |
| abilities | List[str] | 否 | 能力标签列表 |
| type | Optional[RoleType] | 否 | 角色类型（leader / team_member / system），默认 team_member |
| description | Optional[str] | 否 | 角色职责描述 |
| scope | Optional[List[str]] | 否 | 所属群聊列表 |
| disabled_tools | List[str] | 否 | 禁用的工具列表 |
| skills | List[SkillInfo] | 否 | 关联的 Skill 列表 |

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

#### RoleConfig（角色运行时配置）

构造给 agent_bridge 的运行时配置，由 `RoleManager.get_role()` 返回。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | str | 是 | 角色名称，用于标识和事件填充 |
| `platform` | AgentPlatform | 是 | 目标平台类型 |
| `description` | str? | 否 | 角色职责描述 |
| `work_root` | str? | 否 | 角色工作目录路径，注入 `CLAUDE_CONFIG_DIR` 或 `CODEX_HOME` 环境变量 |
| `role_type` | RoleType | 是 | 角色类型（leader / team_member），默认 team_member |
| `bare` | bool | 否 | Claude CLI 极简模式：跳过 hooks/LSP/plugin sync/auto-memory/CLAUDE.md 自动发现 |
| `disabled_tools` | list[str]? | 否 | 禁用的工具列表（通过 CLI --disallowedTools 传递） |

**注**：`system_prompt` 和 `skills` 不在 RoleConfig 中——由 CLI 从角色目录自动加载（Claude 从 `CLAUDE.md`，Codex 从 `AGENTS.md`；skills 从 `work_root/skills/`）。

#### role.json 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称，与目录名一致 |
| platform | "claude" \| "codex" \| "opencode" | 是 | 目标平台 |
| description | str \| null | 否 | 角色职责描述 |
| avatar | str \| null | 否 | 头像文件名 |
| abilities | list[str] | 否 | 能力标签列表 |
| type | "leader" \| "team_member" \| "system" \| null | 否 | 角色类型，默认 team_member |
| scope | list[str] \| null | 否 | 所属群聊列表 |
| disabled_tools | list[str] | 否 | 禁用的工具列表 |

### Request Schemas

**RoleCreateRequest**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称 |
| platform | "claude" \| "codex" \| "opencode" | 是 | 目标平台 |
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
| enabled_tools | list[str] \| None | 否 | 启用的工具列表，传入则覆盖 |

所有字段可选，仅更新传入的字段（PATCH 语义）。

**RoleSkillRequest**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| skill_id | str | 是 | 要添加的 skill 标识 |

### Response Schemas

**RoleResponse**

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | 角色名称 |
| platform | "claude" \| "codex" \| "opencode" | 目标平台 |
| avatar | str \| None | 头像文件名 |
| abilities | list[str] | 能力标签 |
| type | "leader" \| "team_member" \| "system" \| None | 角色类型 |
| scope | list[str] \| None | 所属群聊列表 |
| description | str \| None | 角色职责描述 |
| disabled_tools | list[str] | 禁用的工具列表 |
| skills | list[RoleSkillResponse] | 关联的 Skill 列表 |

通过 `from_domain` 从 `RoleInfo` 领域模型转换。

**RoleSkillResponse**

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str | skill 唯一标识 |
| name | str | skill 名称 |
| description | str | skill 描述 |

通过 `from_domain` 从 `SkillInfo` 领域模型转换。

**删除/移除响应**

统一返回 `{"message": "..."}` 格式的成功提示。

### 异常类型

| 异常 | 触发场景 |
|------|----------|
| RoleNotFoundError | get_role 时角色不存在 |
| RoleAlreadyExistsError | create_role 时名称已存在 |
| ValueError | 名称不合法（基础校验失败）或与已有角色互为前缀冲突 |
| PlatformConfigNotFoundError | 平台源配置目录不存在（~/.claude 或 ~/.codex） |
| SkillNotFoundError | add/remove skill 时 skill 不存在 |
| SkillAlreadyExistsError | add_skill 时 skill 已存在于角色中 |

### API 异常映射

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

## Design Rationale

### 为什么采用配置分层设计？

**设计**：`role.json`（业务配置）→ `RoleConfig`（系统配置）

**理由**：
- `role.json` 面向用户和前端，存储业务可见的配置
- `RoleConfig` 面向 agent_bridge，包含系统内部需要的配置
- `system_prompt` 和 `skills` 不存入 `role.json`，由 CLI 从角色目录自动加载
- 分离关注点，避免配置文件臃肿

**约束**：`RoleConfig` 不包含 `system_prompt` 和 `skills`

### 为什么头像采用引用模式？

**设计**：所有头像文件统一存放在 `assets/` 目录，角色只存储文件名引用

**理由**：
- 避免头像文件重复存储
- 便于头像文件的统一管理
- 角色配置文件保持轻量

**约束**：MVP 阶段仅支持从 `assets/` 选择预设头像，不支持上传

### 为什么 Skill 采用引用优先模式？

**设计**：全局 `local_data/skills/` 是 SSOT，角色的 `work_root/skills/<skill_id>` 是启用入口

**理由**：
- Skill 内容集中管理，避免重复
- 角色通过 symlink 或复制引用全局 Skill
- 移除角色 Skill 不影响全局 Skill 库

**约束**：优先使用 symlink，失败时降级复制

### 为什么需要名称前缀冲突校验？

**设计**：新名称 A 与已有名称 B 不能互为前缀

**理由**：
- 避免群聊中 `@mention` 解析歧义
- 例如 `nico` 与 `nico_1` 互为前缀，`@nico` 会误匹配 `@nico_1`

**约束**：创建和更新角色时都必须校验

### 为什么创建角色时自动初始化 agents-hub MCP？

**设计**：创建角色时自动配置 agents-hub MCP 服务

**理由**：
- 每个角色需要通过 MCP 与 agents-hub 交互
- 自动初始化减少手动配置步骤
- 确保所有角色都有统一的 MCP 配置

**约束**：MCP URL 由 `config.mcp_port` 决定

### 相关 ADR

- 暂无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **消息传递与会话管理**：见 `docs/specs/2026-05-31-core-communication.md`
- **群聊管理**：见 `docs/specs/2026-06-03-group-chat-api.md`
- **多 agent 协调与任务调度**：待定义

---

**以下内容已移至 Flow 文档**（如需要了解实现细节，请参考相应的 Flow 文档）：
- 角色创建的详细初始化步骤
- Skill 管理的具体实现（symlink/复制逻辑）
- 头像管理的详细路径规则
- system_prompt 的存储位置
- 角色命名规则的详细校验逻辑
