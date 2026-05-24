---
version: 1.1
created_at: 2026-05-24
updated_at: 2026-05-24
last_updated: 模块路径从 agents 重命名为 roles
abstract: roles 角色配置模块的正式规格，定义角色生命周期管理、配置数据结构、头像引用机制和 Skill 管理
id: spec-roles
title: Roles 角色配置模块规格
status: unstable
module: roles
sourc_spec: docs/superpowers/specs/2026-05-24-role-config-design.md
related_plan: docs/superpowers/plans/2026-05-24-role-config-implementation.md
code_scope:
  - agents_hub/roles/
contract_refs:
  - agents_hub/roles/models.py
  - agents_hub/roles/exceptions.py
  - agents_hub/agent_bridge/config.py
---

# Roles 角色配置模块规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 从当前代码提炼生成正式 spec 初稿 |
| 1.1 | 模块路径从 agents 重命名为 roles |

---

## Overview

roles 模块是 agents-hub 系统的**角色管理层**，负责 AI Agent 角色的全生命周期管理，包括创建、配置、查询和删除。

模块定位：
- **负责**：角色 CRUD、配置持久化、Skill 管理、头像引用管理、构造给 agent_bridge 的 RoleConfig
- **不负责**：消息传递、prompt 构造、多 agent 协调、群聊管理、任务调度

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
- 权限配置的读取与更新（抽象接口，原始字典）
- 构造给 agent_bridge 的 RoleConfig

### 范围外

- 头像文件的实际上传与存储（MVP 阶段仅支持从 `assets/` 选择预设头像）
- type 字段的调度逻辑（leader/team_member）
- scope 字段的群聊绑定逻辑
- abilities 的匹配调度
- 消息传递与会话管理

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

目录结构：
```
local_data/agents/
├── assets/                    # 所有头像文件（预设 + 上传）
│   ├── default.png
│   └── ...
├── <role_name>/
│   ├── role.json              # avatar 字段仅存文件名
│   └── work_root/
└── skills/                    # 全局 skill 库
```

行为规则：
- `avatar` 字段为 `Optional[str]`，存储文件名（如 `"avatar_01.png"`），可为 `None`
- 更新头像只修改 `role.json` 中的文件名引用，不涉及文件复制或移动
- 可用头像列表通过扫描 `assets/` 目录获取

### Skill 管理机制

Skill 采用**复制模式**：从全局 `local_data/skills/` 复制到角色的 `work_root/skills/` 目录。

行为规则：
- 添加 skill 时，从全局 skill 库复制整个 skill 目录到角色下
- 移除 skill 时，删除角色下的 skill 目录
- `role.json` 中的 `skills` 列表与 `work_root/skills/` 目录保持同步
- 同一 skill 不能重复添加到同一角色

### 角色创建初始化

创建角色时的目录初始化顺序：
1. 验证角色名称合法性（非空、不以 `-` 开头、仅允许字母数字下划线连字符）
2. 创建 `role_dir`、`work_root`、`work_root/skills` 目录
3. 根据 platform 复制平台配置（从 `~/.claude` 或 `~/.codex`）
4. 写入 `role.json`
5. 若初始化失败，自动清理已创建的目录（回滚）

### 角色名称更新

更新角色名称时，同步修改 `role.json` 中的 `name` 字段和角色目录名，保持二者一致。

## Technical Contract

### 数据结构

#### RoleInfo（角色摘要）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称，与目录名一致 |
| platform | AgentPlatform | 是 | 目标平台（claude / codex） |
| avatar | Optional[str] | 否 | 头像文件名（位于 assets/ 目录） |
| abilities | List[str] | 否 | 能力标签列表 |
| type | Optional[RoleType] | 否 | 角色类型（leader / team_member） |
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

### role.json 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称，与目录名一致 |
| platform | "claude" \| "codex" | 是 | 目标平台 |
| avatar | str \| null | 否 | 头像文件名 |
| abilities | list[str] | 否 | 能力标签列表 |
| type | "leader" \| "team_member" \| null | 否 | 角色类型 |
| scope | list[str] \| null | 否 | 所属群聊列表 |
| skills | list[str] | 否 | 已选择的 skill 标识列表 |

### 异常类型

| 异常 | 触发场景 |
|------|----------|
| RoleNotFoundError | get_role 时角色不存在 |
| RoleAlreadyExistsError | create_role 时名称冲突 |
| PlatformConfigNotFoundError | 平台源配置目录不存在（~/.claude 或 ~/.codex） |
| SkillNotFoundError | add/remove skill 时 skill 不存在 |
| SkillAlreadyExistsError | add_skill 时 skill 已存在于角色中 |

### RoleManager 与 Role 的职责划分

| 组件 | 职责 |
|------|------|
| RoleManager | 角色 CRUD、扫描发现、名称验证、列出可用头像 |
| Role | 单个角色的配置读写、Skill 管理、权限配置、构造 RoleConfig |

### 调用流程

```
用户选择角色
  → RoleManager.get_role("name")
  → Role 实例
  → role.get_role_config()
  → RoleConfig
  → agent_bridge.execute(config, prompt)
```

## Acceptance Notes

1. 能创建角色，目录结构和 role.json 正确生成
2. 能列出所有角色，损坏的 role.json 被跳过
3. 能按名称加载角色并构造 RoleConfig
4. 能添加/移除 skill，目录和 role.json 保持同步
5. 能读取和更新权限配置（抽象接口，返回原始 dict）
6. 能更新角色基本信息（名称、头像引用、能力标签）
7. 能列出 `assets/` 目录下所有可用头像
8. 创建角色失败时自动回滚已创建的目录

## Out of Spec

- 头像文件的实际上传、存储和图片处理
- type 字段（leader/team_member）的调度逻辑
- scope 字段的群聊绑定逻辑
- abilities 的匹配调度
- 多 agent 协调与消息传递
- 权限配置的语义化操作（如 add_allow、set_mode）
