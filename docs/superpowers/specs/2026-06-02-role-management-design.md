# Role Management 设计

## 背景

当前 `roles` 模块已经承担角色创建、查询、删除、Skill 管理和平台配置初始化职责。新设计对角色控制面做收窄：`role.json` 只保存角色元信息，平台运行态能力由平台可见的 `work_root` 文件结构和 CLI 初始化结果决定。

本设计替代早期“`role.json.skills` + 复制 Skill + 抽象权限配置 + 原生配置编辑”的方向。目标是减少双重状态，保持 SSOT，并避免在权限和平台配置尚未稳定前过早固化接口。

## 已确认决策

### 1. role.json 只保存角色元信息

`role.json` 保留以下字段：

```json
{
  "name": "worker",
  "platform": "codex",
  "description": "负责实现代码",
  "avatar": "avatar.png",
  "abilities": ["frontend", "test"],
  "type": "team_member",
  "scope": null
}
```

字段边界：

| 字段 | 是否可修改 | 说明 |
| ---- | ---------- | ---- |
| `name` | 是 | 修改时同步重命名角色目录，并继续执行目录合法性和前缀冲突校验 |
| `platform` | 否 | 创建后不可修改，避免迁移平台配置 root |
| `type` | 否 | 创建后不可修改，避免运行中改变调度身份 |
| `description` | 是 | 角色职责描述 |
| `avatar` | 是 | 头像文件引用 |
| `abilities` | 是 | 能力标签，当前只作为元数据 |
| `scope` | 是 | 保留字段，只作为元数据，不提供群聊绑定语义 |

`role.json` 不再包含 `skills` 字段，也不做旧字段兼容。当前系统尚未投入使用该字段，因此直接移除，避免长期维护影子状态。

### 2. 角色创建生命周期

创建角色时执行以下流程：

1. 校验角色名称合法性。
2. 校验新名称与已有角色名称不存在互为前缀冲突。
3. 创建角色目录、`work_root` 和 `work_root/skills`。
4. 初始化平台配置 root：
   - Claude：复制必要配置，创建 `CLAUDE.md`。
   - Codex：复制必要配置，创建 `AGENTS.md`。
5. 自动为该角色添加固定的 `agents-hub` MCP。
6. 写入不含 `skills` 字段的 `role.json`。
7. 任一步失败，删除已创建的角色目录并回滚。

角色创建成功必须意味着角色已经具备连接 agents-hub MCP 的基础能力。若平台 CLI 不存在、配置 root 不正确或 MCP 添加失败，不生成半初始化角色。

### 3. Skill 启用状态以 work_root/skills 为准

Skill 的 SSOT 是全局 Skill 目录：

```text
local_data/skills/<skill_id>
```

角色是否启用某个 Skill，由角色目录下是否存在对应入口决定：

```text
local_data/agents/<role_name>/work_root/skills/<skill_id>
```

添加 Skill：

1. 校验全局 Skill 存在。
2. 校验角色下不存在同名 Skill。
3. 优先创建目录 symlink，让 `work_root/skills/<skill_id>` 指向 `local_data/skills/<skill_id>`。
4. 如果 symlink 创建失败，降级复制整个 Skill 目录。
5. 不写入 `role.json`。

删除 Skill：

1. 删除 `work_root/skills/<skill_id>`。
2. 如果它是 symlink，只删除链接。
3. 如果它是复制 fallback 的目录，删除该角色副本。
4. 不影响全局 Skill。
5. 不写入 `role.json`。

列出 Skill：

1. 扫描 `work_root/skills/`。
2. 读取每个 Skill 入口下的 `skill.json`。
3. 不读取 `role.json.skills`。

该策略让大多数角色通过 symlink 共享全局 Skill 更新，同时保留复制 fallback 作为环境兼容兜底。

### 4. MCP 只做创建时自动初始化

系统不提供通用 MCP 添加、删除、列表接口。当前只在创建角色时自动添加固定的 agents-hub MCP：

```text
name: agents-hub
url: http://localhost:8001/mcp
```

Claude 初始化时必须先设置配置 root：

```bash
CLAUDE_CONFIG_DIR=<role>/work_root
claude mcp add --transport http agents-hub -- http://localhost:8001/mcp
```

Codex 初始化时必须先设置配置 root：

```bash
CODEX_HOME=<role>/work_root
codex mcp add agents-hub --url http://localhost:8001/mcp
```

约束：

- MCP 添加命令必须写入当前角色的配置 root，不能写入用户全局配置。
- MCP 添加失败时角色创建失败并回滚。
- 不直接把任意 MCP 管理能力暴露给用户。
- 不把 MCP 管理状态写入 `role.json`。

### 5. 权限配置暂不落地

权限模式当前只保留未来设计空间，不定义字段、不存储、不传递给 executor。

暂不做：

- 不在 `role.json` 中增加权限字段。
- 不修改 Claude `settings.json` 或 Codex `config.toml`。
- 不为 Claude/Codex 建立权限模式映射。
- 不让 executor 拼接权限相关 CLI 参数。

原因：权限方案需要结合 Docker 或外部沙箱设计后再确定。当前过早固化字段会增加迁移成本。

### 6. 不提供原生配置编辑接口

当前不提供以下能力：

- 直接编辑 Claude `settings.json`。
- 直接编辑 Codex `config.toml`。
- 任意平台配置文件的原始文本读写。

原因：原生配置编辑容易与结构化接口形成双重状态，后续排错成本高。MVP 阶段只提供明确受控的角色元信息和 Skill 操作。

## 模块边界

### roles 模块负责

- 角色元信息 CRUD。
- 平台配置 root 初始化。
- 创建角色时自动添加固定 agents-hub MCP。
- Skill 添加、删除、列表。
- 构造给 agent_bridge 使用的角色运行配置。

### roles 模块不负责

- 用户自定义 MCP 管理。
- 权限策略落地。
- 原生平台配置编辑。
- `scope` 的群聊绑定逻辑。
- `abilities` 的调度匹配逻辑。
- `type` 的运行时调度语义。

## 验收标准

1. 新建角色的 `role.json` 不包含 `skills` 字段。
2. `platform` 和 `type` 创建后不可修改。
3. 修改 `name` 时继续校验目录合法性和前缀冲突。
4. 创建角色时自动为该角色配置 root 添加固定 `agents-hub` MCP。
5. MCP 添加失败时角色创建回滚，不留下半初始化目录。
6. 添加 Skill 时优先创建目录 symlink。
7. symlink 创建失败时 fallback 到复制目录。
8. 删除 Skill 不影响全局 Skill。
9. 列出 Skill 只扫描 `work_root/skills/`。
10. 当前不暴露权限配置、MCP 管理和原生配置编辑接口。

## 未解决问题

1. Docker 或外部沙箱如何参与权限模型，后续单独设计。
2. 如果用户未来需要自定义 MCP server，应单独设计 MCP 管理模块或接口。
3. symlink fallback 到复制后，全局 Skill 更新不会自动同步到该角色副本；这是可接受降级行为，后续如需要可增加同步检测。
