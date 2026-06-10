---
version: 1.0
created_at: 2026-06-03
updated_at: 2026-06-03
last_updated: 创建 skills API spec 初稿
abstract: skills 模块的正式规格，定义全局 skill 库管理、API 契约、数据结构和安全约束
id: spec-skills-api
title: Skills API 模块规格
status: unstable
module: skills
sourc_spec: N/A（从现有代码提炼）
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

## Overview

skills 模块是 agents-hub 系统的**全局 skill 库管理层**，负责 skill 的全生命周期管理，包括查询、删除和预留的网络添加功能。

模块定位：
- **负责**：全局 skill 库的 CRUD 操作、SKILL.md 解析、skill 元信息管理、路径安全校验
- **不负责**：角色级 skill 激活管理（由 roles 模块负责）、skill 内容执行、skill 版本管理

核心设计原则：
- **SSOT**：`local_data/skills/` 是 skill 内容的唯一来源
- **引用优先**：角色通过 symlink 或复制引用全局 skill
- **安全优先**：所有路径操作必须防止路径穿越攻击

## Scope

### 范围内

- 全局 skill 库的查询、删除操作
- SKILL.md 文件解析和元信息提取
- 路径安全校验（防止路径穿越）
- API 请求/响应 schema 定义
- 异常处理和错误响应

### 范围外

- 角色级 skill 激活/停用管理
- skill 内容的执行和调用
- skill 版本控制和更新
- skill 依赖关系管理
- skill 市场和社区功能

## Core Behavior

### Skill 存储结构

```
local_data/skills/
├── <skill_id>/
│   ├── SKILL.md          # skill 元信息（frontmatter）
│   └── ...               # skill 内容文件
```

### SKILL.md 格式

```markdown
---
name: skill-name
description: Skill 的功能描述
---

# Skill 内容
```

**必需字段**：
- `name`：skill 名称（字符串）
- `description`：skill 描述（字符串）

**解析规则**：
- 必须以 `---` 开头的 frontmatter
- frontmatter 必须包含 `name` 和 `description` 字段
- 字段值必须是字符串类型

### API 端点行为

#### 列出所有 skills

- 扫描 `local_data/skills/` 目录下的所有子目录
- 解析每个子目录的 SKILL.md 文件
- 跳过无效的 skill 目录（SKILL.md 不存在或格式错误）
- 返回有效的 skill 列表

#### 获取单个 skill

- 根据 skill_name 定位 `local_data/skills/<skill_name>` 目录
- 验证目录存在且 SKILL.md 有效
- 返回 skill 元信息

#### 删除 skill

- 根据 skill_name 定位目录
- 验证目录存在
- 递归删除整个 skill 目录
- 删除后不可恢复

### 安全约束

**路径穿越防护**：
- 所有路径操作必须验证 skill_name 不包含路径分隔符（如 `..`）
- 确保解析后的路径仍在 skills_root 目录内
- 防止通过 skill_name 访问 skills_root 之外的文件系统资源

## Technical Contract

### 数据结构

#### SkillInfo（领域模型）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | skill 名称 |
| description | str | skill 描述 |
| path | str | skill 目录绝对路径（内部使用，不暴露给 API） |

#### SkillResponse（API 响应）

| 字段 | 类型 | 说明 |
|------|------|------|
| name | str | skill 名称 |
| description | str | skill 描述 |

#### SkillCreateRequest（API 请求）

| 字段 | 类型 | 说明 |
|------|------|------|
| url | str | skill 的网络地址（预留字段） |

### API 契约

#### 列出所有 skills

```
GET /api/v1/skills

Response 200:
[
  {
    "name": "skill-name",
    "description": "Skill description"
  }
]
```

#### 获取单个 skill

```
GET /api/v1/skills/{skill_name}

Response 200:
{
  "name": "skill-name",
  "description": "Skill description"
}

Response 404:
{
  "error_code": "SKILL_NOT_FOUND",
  "message": "Skill 'xxx' not found"
}
```

#### 删除 skill

```
DELETE /api/v1/skills/{skill_name}

Response 200:
{
  "message": "Skill 'xxx' 删除成功"
}

Response 404:
{
  "error_code": "SKILL_NOT_FOUND",
  "message": "Skill 'xxx' not found"
}
```

#### 添加 skill（预留）

```
POST /api/v1/skills

Request Body:
{
  "url": "https://example.com/skill.zip"
}

Response 500:
{
  "error_code": "INTERNAL_ERROR",
  "message": "网络获取功能暂未实现"
}
```

### 异常类型

| 异常 | 触发场景 | HTTP 状态码 |
|------|----------|-------------|
| SkillNotFoundError | skill 不存在 | 404 |
| InvalidSkillError | SKILL.md 格式错误或路径无效 | 400 |

## Acceptance Notes

1. 能成功列出全局 skill 库中的所有有效 skills
2. 能根据 skill_name 获取单个 skill 的元信息
3. 能删除指定的 skill 目录
4. 无效的 skill 目录（SKILL.md 缺失或格式错误）被自动跳过
5. 路径穿越攻击被有效阻止
6. API 响应格式符合契约定义
7. 错误响应包含正确的错误码和消息

## Out of Spec

- 角色级 skill 激活/停用管理（属于 roles 模块）
- skill 内容的执行和调用机制
- skill 版本控制和更新策略
- skill 依赖关系和冲突解决
- skill 市场、社区和分享功能
- skill 安全扫描和权限控制
- 从网络添加 skill 的具体实现（当前为预留接口）
