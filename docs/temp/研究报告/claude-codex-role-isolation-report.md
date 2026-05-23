# Claude 与 Codex 角色隔离机制研究报告

**研究日期**: 2026-05-24
**研究目标**: 明确 Claude 和 Codex 两个平台如何通过环境变量实现 profile 隔离，为 agents-hub 的多角色架构提供技术基础。
**研究结论**: 两个平台都支持通过环境变量覆盖配置目录，实现方式完全对称——Codex 用 `CODEX_HOME`，Claude 用 `CLAUDE_CONFIG_DIR`。

---

## 一、背景

agents-hub 需要支持多个角色（如 nico 负责后端、xiaoli 负责前端），每个角色有独立的：
- 系统提示词（CLAUDE.md / AGENTS.md）
- 权限配置（settings.json / config.toml）
- 会话历史
- 插件/工具配置

角色隔离的核心要求是：**同一台机器上，不同角色的配置和状态互不干扰**。

---

## 二、Codex 角色隔离：CODEX_HOME

### 2.1 机制

Codex CLI 通过 `CODEX_HOME` 环境变量指定配置目录，默认值为 `~/.codex/`。

```python
env = os.environ.copy()
env["CODEX_HOME"] = "/path/to/role-nico"
subprocess.run(["codex", "exec", "--json", prompt], env=env)
```

### 2.2 隔离内容

`CODEX_HOME` 目录包含：

| 文件/目录 | 说明 |
|----------|------|
| `config.toml` | 主配置（模型、审批策略、sandbox 等） |
| `auth.json` | 认证凭据 |
| `sessions/` | 会话历史 |
| `AGENTS.md` | 角色系统提示词（通过 profile-v2 机制派生） |

### 2.3 agents-hub 中的实现

```python
class CodexExecutor:
    async def execute_stream(self, prompt, config, session_id=None):
        env = os.environ.copy()
        if config.codex_home:
            env["CODEX_HOME"] = config.codex_home
        # 启动 codex exec --json ...
```

### 2.4 验证状态

已通过集成测试验证：不同 `CODEX_HOME` 目录下的角色表现出不同的系统提示词和配置行为。

---

## 三、Claude 角色隔离：CLAUDE_CONFIG_DIR

### 3.1 机制

Claude CLI 通过 `CLAUDE_CONFIG_DIR` 环境变量指定配置目录，默认值为 `~/.claude/`。

```python
env = os.environ.copy()
env["CLAUDE_CONFIG_DIR"] = "/path/to/role-nico"
subprocess.run(["claude", "-p", prompt], env=env)
```

### 3.2 隔离内容

`CLAUDE_CONFIG_DIR` 目录包含：

| 文件/目录 | 说明 |
|----------|------|
| `settings.json` | 主配置（模型、权限、插件、env 等） |
| `CLAUDE.md` | 角色系统提示词 |
| `sessions/` | 会话历史 |
| `projects/` | 项目级状态 |
| `plugins/` | 已安装插件 |
| `skills/` | 已安装 skills |
| `history.jsonl` | 命令历史 |
| `tasks/` | 任务追踪 |
| `memory/` | 自动记忆 |

### 3.3 agents-hub 中的实现

```python
class ClaudeCodeExecutor:
    async def execute_stream(self, prompt, config, session_id=None):
        env = os.environ.copy()
        if config.claude_config_dir:
            env["CLAUDE_CONFIG_DIR"] = config.claude_config_dir
        # 启动 claude -p --output-format stream-json ...
```

### 3.4 验证状态

已通过探索性测试验证：不同 `CLAUDE_CONFIG_DIR` 目录下的角色表现出不同的身份和权限行为。

---

## 四、对称性对比

| 维度 | Codex (`CODEX_HOME`) | Claude (`CLAUDE_CONFIG_DIR`) |
|------|---------------------|----------------------------|
| 环境变量 | `CODEX_HOME` | `CLAUDE_CONFIG_DIR` |
| 默认值 | `~/.codex/` | `~/.claude/` |
| 角色提示词 | `AGENTS.md`（通过 profile 派生） | `CLAUDE.md`（config dir 根目录） |
| 主配置文件 | `config.toml` | `settings.json` |
| 认证文件 | `auth.json` | keychain / `ANTHROPIC_AUTH_TOKEN` |
| 会话目录 | `sessions/` | `sessions/` |
| 注入方式 | 子进程 `env` 参数 | 子进程 `env` 参数 |
| 隔离粒度 | 完整隔离（配置+认证+会话） | 完整隔离（配置+认证+会话+插件） |

---

## 五、RoleConfig 扩展方案

基于以上分析，`RoleConfig` 可以统一扩展：

```python
@dataclass
class RoleConfig:
    platform: AgentPlatform
    system_prompt: str
    skills: list[str]

    # Codex 专用
    codex_home: str | None = None

    # Claude 专用
    claude_config_dir: str | None = None

    # 通用（CLI 参数透传）
    cwd: str | None = None
    model: str | None = None
```

Executor 层根据 `platform` 类型注入对应的环境变量：

```python
# CodexExecutor
if config.codex_home:
    env["CODEX_HOME"] = config.codex_home

# ClaudeCodeExecutor
if config.claude_config_dir:
    env["CLAUDE_CONFIG_DIR"] = config.claude_config_dir
```

---

## 六、注意事项

### 6.1 Claude 的 --bare 模式陷阱

`--bare` 模式会跳过全局 CLAUDE.md 的加载。当使用 `CLAUDE_CONFIG_DIR` 做角色隔离时，该目录下的 `CLAUDE.md` 对 CLI 来说是"全局 CLAUDE.md"，`--bare` 会跳过它，导致角色定义失效。

**结论**：角色隔离场景下不能使用 `--bare`。

详见 `docs/history-bugs/2026-05-24-claude-bare-mode-skips-global-claude-md.md`。

### 6.2 认证方式差异

| | Codex | Claude |
|---|---|---|
| 认证存储 | `auth.json`（在 CODEX_HOME 内） | keychain（系统级）或环境变量 |
| 隔离影响 | 认证随 CODEX_HOME 隔离 | keychain 不随 CLAUDE_CONFIG_DIR 隔离 |
| 解决方案 | 自然隔离 | 使用 `ANTHROPIC_AUTH_TOKEN` 环境变量代替 keychain |

如果 Claude 角色需要不同的 API key，必须通过 `settings.json` 的 `env.ANTHROPIC_AUTH_TOKEN` 或 `env.ANTHROPIC_API_KEY` 注入，不能依赖 keychain。

### 6.3 插件隔离

Claude 的插件安装在 `CLAUDE_CONFIG_DIR/plugins/` 下，天然随 config dir 隔离。但如果 `settings.json` 中引用了不存在的插件，启动时可能报错或忽略。

建议：每个角色目录只启用该角色需要的插件，或不启用插件。

### 6.4 并发安全

同一 `CODEX_HOME` 或 `CLAUDE_CONFIG_DIR` 目录不能被多个进程并发写入。如果 agents-hub 需要同一角色并发执行，需要：
- 要么为每次调用创建临时 config dir 副本
- 要么在角色级别加锁
- 要么使用不同的 session_id 隔离会话（但配置和历史仍共享）

---

## 七、结论

Claude 和 Codex 的角色隔离机制完全对称，都通过环境变量覆盖配置目录实现。agents-hub 的 `ClaudeCodeExecutor` 只需像 `CodexExecutor` 注入 `CODEX_HOME` 一样注入 `CLAUDE_CONFIG_DIR`，即可实现统一的多角色架构。
