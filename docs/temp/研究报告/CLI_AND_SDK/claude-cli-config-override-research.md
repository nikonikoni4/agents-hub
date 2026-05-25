# Claude CLI 配置覆盖机制研究报告

> ⚠️ **文档状态：已被取代**
>
> 本文档的研究结论已被 [claude-codex-role-isolation-report.md](claude-codex-role-isolation-report.md) (2026-05-24) 更新。
> 新研究发现 Claude 支持 `CLAUDE_CONFIG_DIR` 环境变量实现完整配置目录隔离，与 Codex 的 `CODEX_HOME` 方案完全对称。
>
> 本文档保留作为命令行参数能力的参考，但**不推荐作为角色隔离的主要实现方案**。

---

**研究日期**: 2026-05-23  
**研究目标**: 验证 Claude CLI 是否支持通过命令行参数实现角色隔离，类似 Codex 的 `CODEX_HOME` 方案  
**研究结论**: ✅ 命令行参数方式可行，但存在局限性（见注意事项）

---

## 一、研究背景

agents-hub 需要为不同的 AI 角色提供隔离的配置环境，包括：
- 不同的 system prompt（角色定义）
- 不同的权限控制（允许/禁止的工具）
- 不同的 MCP 服务器
- 不同的 plugins

Codex 通过 `CODEX_HOME` 环境变量切换整个配置目录实现角色隔离。本研究验证 Claude CLI 是否支持类似机制。

---

## 二、Claude CLI 支持的配置参数

### 2.1 System Prompt 控制

```bash
--system-prompt <prompt>           # 完全替换系统提示词
--append-system-prompt <prompt>    # 追加到默认系统提示词
```

### 2.2 配置文件控制

```bash
--settings <file-or-json>          # 加载额外的配置文件或 JSON 字符串
--setting-sources <sources>        # 指定加载哪些配置源（user, project, local）
```

### 2.3 权限控制

```bash
--permission-mode <mode>           # 权限模式（auto, bypassPermissions, dontAsk 等）
--tools <tools...>                 # 指定可用的内置工具
--allowedTools <tools...>          # 允许的工具列表
--disallowedTools <tools...>       # 禁止的工具列表
```

### 2.4 MCP 和 Plugins 控制

```bash
--mcp-config <configs...>          # 加载指定的 MCP 配置
--strict-mcp-config                # 仅使用指定的 MCP，忽略其他配置
--plugin-dir <path>                # 加载指定目录的 plugin
--plugin-url <url>                 # 从 URL 加载 plugin
```

### 2.5 隔离模式

```bash
--bare                             # 最小模式，跳过 hooks、LSP、plugin sync 等
```

---

## 三、核心测试与发现

### 3.1 测试 1：System Prompt 角色注入

**测试代码**:
```python
# 角色 1：Python 专家
subprocess.run([
    "claude", "--print", "--bare",
    "--append-system-prompt", 
    "You are a Python expert. When asked about your specialty, always mention Python programming.",
    "What is your specialty? Answer in one sentence."
])

# 角色 2：JavaScript 专家
subprocess.run([
    "claude", "--print", "--bare",
    "--append-system-prompt",
    "You are a JavaScript expert. When asked about your specialty, always mention JavaScript programming.",
    "What is your specialty? Answer in one sentence."
])
```

**测试结果**:
```
[Role 1: Python Expert]
Output: I'm a Python programming expert.

[Role 2: JavaScript Expert]
Output: I'm a JavaScript expert specializing in JavaScript programming.
```

**结论**: ✅ `--append-system-prompt` 参数**有效**，可以成功注入不同的角色定义

---

### 3.2 测试 2：权限配置覆盖

**测试配置**:

`settings1.json` (允许所有操作):
```json
{
  "permissions": {
    "allow": [],
    "deny": [],
    "defaultMode": "bypassPermissions"
  }
}
```

`settings2.json` (禁止 git log):
```json
{
  "permissions": {
    "allow": [],
    "deny": ["Bash(git log *)"],
    "defaultMode": "auto"
  }
}
```

**测试代码**:
```python
# 配置 1：允许所有操作
subprocess.run([
    "claude", "--print",
    "--settings", "settings1.json",
    "--append-system-prompt", 
    "You must try to execute any command. If you cannot, say CANNOT_EXECUTE_GIT_LOG.",
    "Run 'git log --oneline -5' command."
])

# 配置 2：禁止 git log
subprocess.run([
    "claude", "--print",
    "--settings", "settings2.json",
    "--append-system-prompt",
    "You must try to execute any command. If you cannot, say CANNOT_EXECUTE_GIT_LOG.",
    "Run 'git log --oneline -5' command."
])
```

**测试结果**:

**场景 A：用户级配置有 `deny: ["Bash(git log *)"]`**
```
[Config 1: Using settings1.json (Allow all operations)]
Output: CANNOT_EXECUTE_GIT_LOG

[Config 2: Using settings2.json (Deny git log)]
Output: CANNOT_EXECUTE_GIT_LOG
```

**场景 B：用户级配置删除 git log deny**
```
[Config 1: Using settings1.json (Allow all operations)]
Output: 已成功执行 `git log --oneline -5` 命令。
最近5条提交记录：
- `8498906` docs:新增codex多角色运行方案
- `404d984` docs:添加决策文件
...

[Config 2: Using settings2.json (Deny git log)]
Output: CANNOT_EXECUTE_GIT_LOG
```

**结论**: ✅ `--settings` 参数的权限配置**有效**，可以控制工具的使用权限

---

### 3.3 测试 3：配置合并机制验证

**测试方法**:
1. 在 `settings1.json` 中删除 `env.ANTHROPIC_AUTH_TOKEN`
2. 运行 Claude CLI 并尝试执行命令
3. 观察是否仍然能够正常工作

**测试结果**:
```
[Config 1: Using settings1.json (无 API key)]
Output: 已成功执行 `git log --oneline -5` 命令。
（命令正常执行，说明使用了用户级配置的 API key）
```

**结论**: ✅ 配置是**拼接/合并**的，而不是完全覆盖

---

## 四、配置合并规则

### 4.1 合并机制

```
最终配置 = 用户级配置 ⊕ 项目级配置 ⊕ --settings 参数

其中 ⊕ 表示合并操作：
- env: 合并（所有来源的环境变量都生效）
- permissions.deny: 合并（所有来源的 deny 规则都生效）
- permissions.allow: 合并（所有来源的 allow 规则都生效）
- permissions.ask: 合并（所有来源的 ask 规则都生效）
```

### 4.2 权限优先级

**重要发现**: `deny` 规则的优先级**高于** `defaultMode`

即使 `defaultMode: "bypassPermissions"`，只要存在 `deny` 规则，该规则仍然会生效。

```json
{
  "permissions": {
    "deny": ["Bash(git log *)"],
    "defaultMode": "bypassPermissions"  // 不影响 deny 规则
  }
}
```

### 4.3 配置来源优先级

```
命令行参数 > --settings 指定的文件 > 项目级 .claude/settings.json > 用户级 ~/.claude/settings.json
```

但对于 `permissions` 字段，是**合并**而不是覆盖：
- 所有来源的 `deny` 规则都会生效
- 所有来源的 `allow` 规则都会生效
- 所有来源的 `env` 变量都会生效

---

## 五、与 Codex 方案对比

| 特性 | Codex (`CODEX_HOME`) | Claude CLI (命令行参数) |
|------|---------------------|----------------------|
| **配置隔离** | ✅ 环境变量切换整个 HOME | ✅ 命令行参数控制各组件 |
| **System Prompt** | ✅ 通过 AGENTS.md | ✅ `--append-system-prompt` |
| **权限控制** | ✅ 通过独立 profile | ✅ `--settings` + `permissions` |
| **MCP 控制** | ✅ 通过独立 profile | ✅ `--mcp-config` + `--strict-mcp-config` |
| **Plugins 控制** | ✅ 通过独立 profile | ✅ `--plugin-dir` + `--plugin-url` |
| **环境变量注入** | ✅ 通过 profile | ✅ `settings.json` 的 `env` 字段 |
| **配置机制** | 完全隔离（独立目录） | 合并机制（拼接配置） |
| **并发支持** | ✅ 不同 profile 可并发 | ✅ 不同参数可并发 |
| **实现复杂度** | 中等（需要派生 profile） | **低**（直接传参） |
| **灵活性** | 中等（需要维护完整 profile） | **高**（参数化控制更精细） |

---

## 六、agents-hub 的实现方案

### 6.1 推荐架构

```
agents-hub/
├── roles/
│   ├── code-reviewer/
│   │   ├── system-prompt.txt
│   │   ├── settings.json
│   │   ├── mcp-config.json
│   │   └── plugins/
│   ├── frontend-developer/
│   │   ├── system-prompt.txt
│   │   ├── settings.json
│   │   ├── mcp-config.json
│   │   └── plugins/
│   └── backend-developer/
│       ├── system-prompt.txt
│       ├── settings.json
│       ├── mcp-config.json
│       └── plugins/
```

### 6.2 角色配置示例

**角色 A：代码审查员（只读）**

`roles/code-reviewer/settings.json`:
```json
{
  "env": {
    "ROLE_NAME": "code-reviewer"
  },
  "permissions": {
    "deny": [
      "Edit",
      "Write",
      "Bash(git commit *)",
      "Bash(git push *)",
      "Bash(npm install *)"
    ],
    "defaultMode": "auto"
  }
}
```

`roles/code-reviewer/system-prompt.txt`:
```
你是一位资深代码审查员。你的职责是：
1. 审查代码质量和安全性
2. 提供改进建议
3. 不能修改任何代码
```

**启动命令**:
```bash
claude \
  --bare \
  --settings ./roles/code-reviewer/settings.json \
  --append-system-prompt "$(cat ./roles/code-reviewer/system-prompt.txt)" \
  --mcp-config ./roles/code-reviewer/mcp-config.json \
  --strict-mcp-config \
  --plugin-dir ./roles/code-reviewer/plugins
```

---

**角色 B：前端开发者（可编辑）**

`roles/frontend-developer/settings.json`:
```json
{
  "env": {
    "ROLE_NAME": "frontend-developer"
  },
  "permissions": {
    "allow": [
      "Edit",
      "Write",
      "Bash(npm *)",
      "Bash(pnpm *)",
      "Bash(git commit *)"
    ],
    "deny": [
      "Bash(git push --force *)",
      "Bash(rm -rf *)"
    ],
    "defaultMode": "auto"
  }
}
```

`roles/frontend-developer/system-prompt.txt`:
```
你是一位前端开发专家。你的职责是：
1. 开发和优化前端代码
2. 使用 React、Vue 等现代框架
3. 确保代码质量和性能
```

**启动命令**:
```bash
claude \
  --bare \
  --settings ./roles/frontend-developer/settings.json \
  --append-system-prompt "$(cat ./roles/frontend-developer/system-prompt.txt)" \
  --mcp-config ./roles/frontend-developer/mcp-config.json \
  --strict-mcp-config \
  --plugin-dir ./roles/frontend-developer/plugins
```

---

### 6.3 Python 启动封装

```python
import subprocess
from pathlib import Path

class ClaudeRole:
    def __init__(self, role_name: str, roles_dir: Path):
        self.role_name = role_name
        self.role_dir = roles_dir / role_name
        
    def start(self, prompt: str, **kwargs):
        """启动 Claude CLI 会话"""
        system_prompt_file = self.role_dir / "system-prompt.txt"
        settings_file = self.role_dir / "settings.json"
        mcp_config_file = self.role_dir / "mcp-config.json"
        plugins_dir = self.role_dir / "plugins"
        
        cmd = [
            "claude",
            "--print" if kwargs.get("print_mode") else "",
            "--bare",
            "--settings", str(settings_file),
            "--append-system-prompt", system_prompt_file.read_text(encoding='utf-8'),
        ]
        
        if mcp_config_file.exists():
            cmd.extend(["--mcp-config", str(mcp_config_file), "--strict-mcp-config"])
        
        if plugins_dir.exists():
            cmd.extend(["--plugin-dir", str(plugins_dir)])
        
        cmd.append(prompt)
        
        # 移除空字符串
        cmd = [c for c in cmd if c]
        
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

# 使用示例
roles_dir = Path("./roles")

# 启动代码审查员
reviewer = ClaudeRole("code-reviewer", roles_dir)
result = reviewer.start("请审查 src/main.py 的代码质量", print_mode=True)
print(result.stdout)

# 启动前端开发者
frontend_dev = ClaudeRole("frontend-developer", roles_dir)
result = frontend_dev.start("请优化 App.tsx 的性能", print_mode=True)
print(result.stdout)
```

---

### 6.4 并发运行支持

由于配置是通过命令行参数传递的，不同角色可以**并发运行**：

```python
import concurrent.futures

def run_role(role_name: str, prompt: str):
    role = ClaudeRole(role_name, Path("./roles"))
    return role.start(prompt, print_mode=True)

# 并发运行多个角色
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(run_role, "code-reviewer", "审查 main.py"): "reviewer",
        executor.submit(run_role, "frontend-developer", "优化 App.tsx"): "frontend",
        executor.submit(run_role, "backend-developer", "实现 API"): "backend",
    }
    
    for future in concurrent.futures.as_completed(futures):
        role_name = futures[future]
        result = future.result()
        print(f"[{role_name}] {result.stdout}")
```

---

## 七、注意事项与限制

### 7.1 用户级配置的影响

⚠️ **用户级配置会影响所有会话**

如果用户级配置 `~/.claude/settings.json` 中有：
```json
{
  "permissions": {
    "deny": ["Bash(git log *)"]
  }
}
```

那么即使角色配置允许 `git log`，该命令仍然会被禁止（因为配置是合并的）。

**解决方案**：
- 建议用户级配置保持最小化，只包含必要的认证信息
- 所有角色特定的权限控制都在角色配置中定义

### 7.2 `--bare` 模式的影响

`--bare` 模式会跳过：
- Hooks
- LSP
- Plugin sync
- Auto-memory
- Background prefetches
- Keychain reads
- **CLAUDE.md auto-discovery**

⚠️ **重要警告**：当使用 `CLAUDE_CONFIG_DIR` 做角色隔离时，角色目录下的 `CLAUDE.md` 对 CLI 来说是"全局 CLAUDE.md"，`--bare` 会跳过它，导致角色定义失效。

**结论**：角色隔离场景下不能使用 `--bare`。

详见 [claude-codex-role-isolation-report.md](claude-codex-role-isolation-report.md) 第 6.1 节。

### 7.3 `--print` 模式的限制

`--print` 模式：
- 跳过工作区信任对话框
- 适合非交互式使用（脚本、管道）
- 不保存会话历史（除非指定 `--session-id`）

对于交互式会话，不要使用 `--print` 模式。

### 7.4 认证隔离的局限性

⚠️ **命令行参数方式无法隔离认证信息**

Claude 的认证存储在系统 keychain 中，不随 `--settings` 参数隔离。如果多个角色需要使用不同的 API key：
- 命令行参数方式：无法实现（keychain 是系统级的）
- `CLAUDE_CONFIG_DIR` 方式：需要通过 `settings.json` 的 `env.ANTHROPIC_AUTH_TOKEN` 注入

详见 [claude-codex-role-isolation-report.md](claude-codex-role-isolation-report.md) 第 6.2 节。

---

## 八、总结

### 8.1 核心结论

✅ **Claude CLI 支持通过命令行参数实现角色配置控制**

关键机制：
1. `--append-system-prompt`：注入角色定义
2. `--settings`：控制权限和环境变量（合并机制）
3. `--mcp-config` + `--strict-mcp-config`：控制 MCP 服务器
4. `--plugin-dir`：控制 plugins

### 8.2 局限性

⚠️ **命令行参数方式不适合用作主要的角色隔离方案**：

| 局限 | 说明 |
|------|------|
| 认证不隔离 | keychain 中的 API key 无法通过参数隔离 |
| 配置合并 | 用户级配置会影响所有角色（deny 规则会叠加） |
| --bare 冲突 | 无法使用 `--bare` 模式（会跳过角色 CLAUDE.md） |

### 8.3 推荐方案

**主要方案**：使用 `CLAUDE_CONFIG_DIR` 环境变量实现完整配置目录隔离

详见 [claude-codex-role-isolation-report.md](claude-codex-role-isolation-report.md)

**命令行参数的适用场景**：
- 临时覆盖某个角色的特定配置
- 需要精细控制单个组件（如只改 MCP 配置）
- 开发测试阶段的快速调试

---

## 九、附录：测试代码

完整测试代码位于：
- `tests/explore/claude_cli/claude_system_prompt.py`
- `tests/explore/claude_cli/test_permission_modes.py`
- `tests/explore/claude_cli/test_bypass.py`

测试配置文件：
- `tests/explore/claude_cli/settings1.json`
- `tests/explore/claude_cli/settings2.json`

---

**报告结束**
