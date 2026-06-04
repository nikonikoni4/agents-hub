# Role 功能规格说明

## 概述

角色（Role）是 Agent 编排系统中的核心实体，代表一个具有特定能力和职责的 AI Agent。

## 数据结构

### RoleApiResponse

对应后端 `RoleResponse` / `RoleInfo` schema。

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `string` | 角色名称（唯一标识） |
| `platform` | `AgentPlatform` | 所属平台：`'claude'` \| `'codex'` |
| `avatar` | `string \| null` | 头像内容（见下方说明） |
| `abilities` | `string[]` | 能力列表 |
| `type` | `RoleType \| null` | 角色类型：`'leader'` \| `'team_member'` |
| `scope` | `string[] \| null` | 作用域 |
| `description` | `string \| null` | 角色描述 |

### 头像字段 (`avatar`) 存储规范

**存储内容**：SVG 内容字符串

```
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">...</svg>
```

**前端渲染方式**：
- SVG 内容（以 `<svg` 开头）：使用 `dangerouslySetInnerHTML` 渲染
- URL：使用 `<img src>` 渲染
- `null`：降级显示角色名首字母

**为什么存储 SVG 内容**：
- 无需额外的文件服务
- 支持 Agent 动态生成个性化头像
- 矢量图，任意尺寸自适应

**后端存储**：
- 数据库 TEXT 字段
- 或 JSON 文件中的字符串字段

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/roles` | GET | 列出所有角色 |
| `/roles/{name}` | GET | 获取单个角色 |
| `/roles` | POST | 创建角色 |
| `/roles/{name}` | PATCH | 更新角色 |
| `/roles/{name}` | DELETE | 删除角色 |
| `/roles/{name}/skills` | GET | 获取角色关联的 Skills |
| `/roles/{name}/skills` | POST | 为角色添加 Skill |
| `/roles/{name}/skills/{id}` | DELETE | 移除角色的 Skill |
| `/roles/avatars` | GET | 获取可用头像列表 |

## 前端交互

### 创建角色
- 表单：名称、平台、头像选择、描述
- 头像从 `/roles/avatars` 获取列表供选择
- 创建后自动刷新角色列表

### 编辑角色
- 可修改：描述、头像
- 不可修改：名称、平台、类型
- 编辑后自动刷新角色列表

### 删除角色
- 需要确认弹窗
- 删除后自动刷新角色列表

## 关联关系

- **Role ↔ Skill**：多对多关系，通过 `/roles/{name}/skills` 管理
- **Role ↔ Team**：Team 包含多个 Role 成员
- **Role ↔ GroupChat**：GroupChat 成员引用 Role 名称

## Mock 数据规范

- Mock 数据使用 `const` 声明，不可变
- 通过 `mockableRequest` 函数切换 mock/真实 API
- 环境变量 `VITE_USE_MOCK=true` 控制 mock 模式
