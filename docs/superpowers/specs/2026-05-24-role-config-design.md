# Role Config 模块设计

## 背景

agents-hub 需要一个角色配置模块来管理不同 AI Agent 角色。用户通过 IM 界面与 agents 交互，每个 agent 有独立的配置（平台、技能、能力标签等）。

核心问题：多 agent 架构尚未确定，但角色配置模块可以先独立实现，因为底层调用方式（agent_bridge）不受上层交互模式影响。

## 已确认的设计决策

### 1. 配置分层

| 层 | 用途 | 存储位置 |
|---|------|----------|
| role.json | 业务配置（面向用户/前端） | `local_data/agents/<name>/role.json` |
| RoleConfig | 系统内部配置（面向 agent_bridge） | 运行时由 role.json 派生 |

### 2. 角色与项目的关系

- **角色不绑定项目**：角色是全局实体，可在多个项目中使用
- **群聊绑定项目**：MVP 阶段，一个群聊 = 一个项目文件夹
- 调用 agent 时，由群聊提供项目路径

### 3. 一对一平台绑定

一个角色绑定一个 platform（claude 或 codex）。想要多平台就创建多个角色。

### 4. system_prompt 存储

不存 role.json，直接写进 CLAUDE.md（Claude 平台）或 AGENTS.md（Codex 平台），CLI 启动时自动加载。

### 5. 角色发现机制

扫描 `local_data/agents/*/role.json`，不维护额外索引文件。

### 6. Orchestrator 实现方式

复用 agent_bridge，Orchestrator 也是一个 agent，通过 `agent_bridge.execute()` 调用 CLI，由 CLI 自身的 subagent 功能处理子任务分派。

---

## 数据结构定义

### AgentPlatform

```python
AgentPlatform = Literal["claude", "codex"]
```

### RoleInfo（角色摘要）

```python
@dataclass
class RoleInfo:
    name: str
    platform: AgentPlatform
    avatar: Optional[str]
    abilities: list[str]
```

### SkillInfo（Skill 摘要）

```python
@dataclass
class SkillInfo:
    id: str           # skill 标识
    name: str         # skill 名称
    description: str  # skill 描述
```

### PermissionsConfig（权限配置）

```python
@dataclass
class PermissionsConfig:
    mode: Literal["default", "plan", "auto"]
    allow: list[str]    # 允许的工具模式列表
    deny: list[str]     # 拒绝的工具模式列表
    ask: list[str]      # 需要询问的工具模式列表
```

### RoleConfig（给 agent_bridge）

```python
@dataclass
class RoleConfig:
    platform: AgentPlatform
    codex_home: Optional[str]        # Codex 配置目录路径
    claude_config_dir: Optional[str] # Claude 配置目录路径
```

---

## role.json 字段定义

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | str | 是 | 角色名称，与目录名一致 |
| platform | "claude" \| "codex" | 是 | 目标平台 |
| type | "leader" \| "team_member" | 否 | 角色类型（MVP 不实现逻辑） |
| scope | list[str] | 否 | 所属群聊列表（MVP 不实现逻辑） |
| avatar | str | 否 | 头像相对路径 |
| abilities | list[str] | 否 | 能力标签，先用于展示，将来用于调度 |
| skills | list[str] | 否 | 已选择的 skill 标识列表 |

---

## 目录结构

```
local_data/
├── agents/
│   ├── <role_name>/
│   │   ├── role.json              # 角色元信息
│   │   ├── avatar/
│   │   │   ├── current.png        # 当前头像
│   │   │   └── history_##.png     # 历史头像
│   │   └── work_root/             # 作为 CODEX_HOME 或 CLAUDE_CONFIG_DIR
│   │       ├── skills/            # 角色的 skills
│   │       ├── CLAUDE.md 或 AGENTS.md         # Claude 平台 system_prompt 或 Codex 平台 system_prompt
│   └── assets/
│       └── (预设头像)
└── skills/
    └── (全局 skill 库)
```

---

## 核心组件

### RoleManager

职责：角色 CRUD、扫描发现、按名称加载。

#### 方法定义

```python
class RoleManager:
    def list_roles() -> list[RoleInfo]
    """扫描 local_data/agents/*/role.json，返回所有角色摘要列表"""

    def get_role(name: str) -> Role
    """按名称加载单个角色，返回 Role 实例。不存在则抛出 RoleNotFoundError"""

    def create_role(
        name: str,
        platform: Literal["claude", "codex"],
        type: Optional[Literal["leader", "team_member"]] = None,
        avatar: Optional[str] = None,
        abilities: Optional[list[str]] = None,
    ) -> Role
    """创建新角色，初始化目录结构和 role.json"""

    def delete_role(name: str) -> None
    """删除角色及其目录"""
```

#### create_role 初始化逻辑

1. 验证角色名称合法性（目录名安全字符）
2. 创建目录结构：`local_data/agents/<name>/`、`avatar/`、`work_root/`、`work_root/skills/`
3. 根据 platform 复制配置：
   - **Claude**：从 `~/.claude` 复制 `settings.json`，创建空白 `CLAUDE.md`
   - **Codex**：从 `~/.codex` 复制 `auth.json`、`config.toml`、`rules/`.创建AGENTS.md
4. 写入 `role.json`
5. 返回 Role 实例

#### 错误处理

- `RoleNotFoundError`：get_role 时角色不存在
- `RoleAlreadyExistsError`：create_role 时名称冲突
- `PlatformConfigNotFoundError`：源配置目录不存在（如 `~/.claude` 不存在）

---

### Role

职责：单个角色的配置管理、构造 RoleConfig。

#### 方法定义

```python
class Role:
    # === 基本信息管理 ===

    def get_info() -> RoleInfo
    """返回角色摘要信息（name, platform, avatar, abilities）"""

    def update_name(new_name: str) -> None
    """更新角色名称，同步修改目录名和 role.json"""

    def update_avatar(avatar_path: str) -> None
    """更新头像，将旧头像移入 history"""

    def update_abilities(abilities: list[str]) -> None
    """更新能力标签列表"""

    # === Skill 管理 ===

    def list_skills() -> list[SkillInfo]
    """列出角色已启用的 skills"""

    def add_skill(skill_id: str) -> None
    """添加 skill，从全局 skill 库复制到 work_root/skills/"""

    def remove_skill(skill_id: str) -> None
    """移除 skill，从 work_root/skills/ 删除"""

    # === 权限配置（抽象接口）===

    def get_permissions_config() -> dict
    """读取平台特定的权限配置，返回原始字典"""

    def update_permissions_config(config: dict) -> None
    """更新平台特定的权限配置"""

    # === 构造 RoleConfig ===

    def get_role_config() -> RoleConfig
    """构造给 agent_bridge 使用的 RoleConfig"""
```

#### 权限配置说明

权限配置是平台特定的，Claude 和 Codex 的实现不同。MVP 阶段：
- 提供抽象接口读取/更新原始配置（dict）
- 不实现语义化的权限操作（如 add_allow、set_mode）
- 具体实现留待后续设计

---

## 调用流程

```
用户选择角色
  → RoleManager.get_role("name")
  → Role 实例
  → role.get_role_config()
  → RoleConfig
  → agent_bridge.execute(config, prompt)
```

---

## 职责边界

| 在 Role 模块内 | 不在 Role 模块内 |
|---------------|-----------------|
| 角色 CRUD | 消息传递 |
| 配置管理 | prompt 构造 |
| Skill 管理 | 多 agent 协调 |
| 头像管理 | 群聊管理 |
| 权限配置（抽象接口） | 任务调度 |
| 构造 RoleConfig | |

---

## MVP 范围

### 实现

- **RoleManager**：create_role、get_role、list_roles、delete_role
- **Role**：基本信息管理、Skill 管理、权限配置（抽象接口）、构造 RoleConfig
- **初始化**：配置复制、创建目录结构

### 不实现（留待后续）

- type: leader/team_member 的调度逻辑
- scope 群聊绑定逻辑
- abilities 匹配调度
- 头像上传（只支持从 `local_data/agents/assets/` 选择预设头像）

---

## 验收标准

1. 能创建角色，目录结构和 role.json 正确生成
2. 能列出所有角色
3. 能按名称加载角色并构造 RoleConfig
4. 能添加/移除 skill，同步到目录
5. 能读取和更新权限配置（抽象接口）
6. 能更新角色基本信息（名称、头像、能力标签）
