---
version: 2.0
created_at: 2026-06-03
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：移除执行细节，添加 key_function 标签和 Design Rationale
abstract: skills 模块的正式规格，定义全局 skill 库管理的业务意图、API 契约和设计决策
id: spec-skills-api
title: Skills API 模块规格
status: unstable
module: skills
source_spec: N/A（从现有代码提炼）
related_plan: N/A
code_scope:
  - agents_hub/skills/
  - agents_hub/api/routes/skills.py
  - agents_hub/api/services/skill_service.py
  - agents_hub/api/schemas/skills.py
contract_refs:
  - agents_hub/skills/models.py
  - agents_hub/skills/exceptions.py
  - agents_hub/api/schemas/skills.py
---

# Skills API 模块规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 skills API spec 初稿 |
| 1.1 | 审查修正：说明 SkillInfo 命名冲突、补充 InvalidSkillError 400 响应、明确 skill_name 与 frontmatter name 关系、修正 frontmatter 字段名 |
| 2.0 | 按新 spec 规则重构：移除执行细节，添加 key_function 标签和 Design Rationale |

## Overview

**业务问题**：系统需要一个全局 skill 库管理层，统一管理 skill 的存储、查询和删除，为角色模块提供 skill 引用基础。

**核心职责**：
- 全局 skill 库的查询和删除操作
- SKILL.md 文件解析和元信息提取
- 路径安全校验（防止路径穿越攻击）

**不负责**：角色级 skill 激活管理（由 roles 模块负责）、skill 内容执行、skill 版本管理。

## Scope

### 范围内

- 全局 skill 库的查询、删除操作
- SKILL.md 文件解析和元信息提取
- 路径安全校验（防止路径穿越）
- API 请求/响应 schema 定义
- 异常处理和错误响应

### 范围外

- 角色级 skill 激活/停用管理（见 roles 模块 spec）
- skill 内容的执行和调用
- skill 版本控制和更新
- skill 依赖关系管理
- skill 市场和社区功能

## Technical Contract

### API 端点

<key_function last_update="2026-06-21T17:23:54+08:00">
- agents_hub/api/routes/skills.py
  - skills.list_skills:16
  - skills.get_skill:23
  - skills.delete_skill:30
  - skills.add_skill:37
</key_function>

| 方法 | 路径 | 说明 | 路由处理函数 |
|------|------|------|------------|
| GET | `/api/v1/skills` | 列出所有 skills | `list_skills` |
| GET | `/api/v1/skills/{skill_name}` | 获取单个 skill | `get_skill` |
| DELETE | `/api/v1/skills/{skill_name}` | 删除 skill | `delete_skill` |
| POST | `/api/v1/skills` | 添加 skill（预留） | `add_skill` |

### Response Schema

**GET /api/v1/skills** 响应（200）：

| 字段 | 类型 | 说明 |
|------|------|------|
| (array) | list[SkillResponse] | skill 列表 |

**GET /api/v1/skills/{skill_name}** 响应：

| 状态码 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| 200 | name | str | skill 名称 |
| 200 | description | str | skill 描述 |
| 404 | error_code | str | `SKILL_NOT_FOUND` |
| 404 | message | str | 错误描述 |
| 400 | error_code | str | `INVALID_SKILL` |
| 400 | message | str | 错误描述 |

**DELETE /api/v1/skills/{skill_name}** 响应：

| 状态码 | 字段 | 类型 | 说明 |
|--------|------|------|------|
| 200 | message | str | 删除成功描述 |
| 404 | error_code | str | `SKILL_NOT_FOUND` |
| 404 | message | str | 错误描述 |
| 400 | error_code | str | `INVALID_SKILL` |
| 400 | message | str | 错误描述 |

**POST /api/v1/skills** 请求与响应：

| 方向 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 请求 | url | str | skill 的网络地址 |
| 响应(500) | error_code | str | `INTERNAL_ERROR` |
| 响应(500) | message | str | 错误描述 |

### 数据模型

#### SkillInfo（领域模型）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | skill 名称（等于目录名，唯一标识） |
| description | str | skill 描述 |
| path | str | skill 目录绝对路径（内部使用，不暴露给 API） |

> **命名冲突说明**：roles 模块也定义了同名 `SkillInfo`，但字段为 `id`、`name`、`description`（摘要视图）。本模块的 `SkillInfo` 是 skill 详情视图，包含 `path` 字段。两处 `SkillInfo` 各自独立，不共享定义。

#### SkillResponse（API 响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | skill 名称 |
| description | str | skill 描述 |

#### SkillCreateRequest（API 请求）

| 字段 | 类型 | 说明 |
|------|------|------|
| url | str | skill 的网络地址（预留字段） |

### 异常类型

| 异常 | 触发场景 | HTTP 状态码 |
|------|----------|-------------|
| SkillNotFoundError | skill 不存在 | 404 |
| InvalidSkillError | SKILL.md 格式错误或路径无效 | 400 |

### 约束规则

- **skill 唯一标识**：`skill_name`（目录名）是 skill 的唯一标识，frontmatter 中的 `name` 字段仅用于显示
- **路径安全**：所有路径操作必须防止路径穿越攻击，确保解析后的路径在 skills_root 目录内
- **无效 skill 处理**：列出 skills 时自动跳过无效目录（SKILL.md 缺失或格式错误）

## Design Rationale

**为什么 skill_name 用目录名而非 frontmatter name？**
- 目录名是文件系统的物理标识，稳定且唯一
- frontmatter name 可能包含特殊字符或变化，不适合作为 API 路径参数
- 避免了重命名 skill 时需要同步修改目录和 frontmatter 的复杂性

**为什么需要 InvalidSkillError？**
- SKILL.md 可能因手动编辑导致格式错误
- 区分"skill 不存在"（404）和"skill 存在但无效"（400）两种错误场景
- 让调用方能针对性处理：404 可忽略，400 需要提示用户修复

**为什么添加 skill 接口设计为预留？**
- 网络添加涉及下载、解压、安全扫描等复杂流程
- 当前优先实现本地 skill 管理，网络功能作为未来扩展
- 接口契约先行定义，确保未来实现时 API 风格一致

**相关 ADR**：暂无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **roles 模块**：角色级 skill 激活/停用管理
- **skill 执行引擎**：skill 内容的执行和调用机制
- **skill 版本控制**：版本管理和更新策略
