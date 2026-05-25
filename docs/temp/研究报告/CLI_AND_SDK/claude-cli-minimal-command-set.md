# Claude Code CLI 最小命令集指南

**创建日期**: 2026-05-23
**目的**: 为 agents-hub 项目提供最小化的 Claude Code CLI 命令集合，覆盖会话管理、System Prompt 覆盖、配置覆盖、工具管理和 Skill 管理五大功能
**排除**: TUI 独有命令（如 `codex resume` 的交互式选择器）

---

## 一、会话管理

### 1.1 查看会话列表

Claude Code 没有内置的 `conversation list` CLI 命令。会话以 `.jsonl` 文件形式存储在项目目录下。

**会话存储路径**:
```
~/.claude/projects/<project-path-encoded>/
├── <session-id-1>.jsonl
├── <session-id-2>.jsonl
├── <session-id-3>.jsonl
└── memory/
```

**查看会话列表**:
```bash
# 列出当前项目的所有会话文件
ls ~/.claude/projects/<project-path-encoded>/*.jsonl

# 获取会话 ID 列表（去掉路径和扩展名）
ls ~/.claude/projects/<project-path-encoded>/*.jsonl | xargs -I{} basename {} .jsonl

# 按修改时间排序，查看最近的会话
ls -lt ~/.claude/projects/<project-path-encoded>/*.jsonl | head -10
```

**会话文件格式**: 每行一个 JSON 对象，首行包含 `sessionId` 和时间戳：
```json
{"type":"queue-operation","operation":"enqueue","timestamp":"2026-05-22T19:20:26.963Z","sessionId":"09c97f64-3306-42f9-a541-78e9d4bf7fe4","content":"..."}
```

### 1.2 开启新会话

```bash
# 交互式新会话
claude

# 非交互式新会话（--print 模式，输出后退出）
claude -p "你的提示词"

# 带名称的新会话
claude -n "会话名称"
claude --name "会话名称"

# 指定 session ID 开启新会话
claude --session-id "自定义-uuid"
```

**参数说明**:

| 参数 | 缩写 | 说明 |
|------|------|------|
| `--print` | `-p` | 非交互模式，输出结果后退出 |
| `--name <name>` | `-n` | 为会话设置显示名称 |
| `--session-id <uuid>` | | 指定会话 UUID（必须是有效 UUID 格式） |

**`--session-id` 行为**:
- UUID 不存在 → 创建新会话并使用该 ID
- UUID 已存在 → **报错** `Session ID is already in use`

> 如需继续已有会话，使用 `--resume <session-id>` 而非 `--session-id`。

### 1.3 继续最近会话

```bash
# 继续当前目录下最近的会话
claude --continue
claude -c

# 非交互式继续最近会话
claude -c -p "继续上次的话题"
```

**测试结果**: `--continue` 会自动加载当前目录下最近的会话上下文。

### 1.4 依据 session_id 继续会话

```bash
# 通过 session ID 恢复会话（交互式选择器）
claude --resume
claude -r

# 通过指定 session ID 恢复会话
claude --resume "09c97f64-3306-42f9-a541-78e9d4bf7fe4"
claude -r "09c97f64-3306-42f9-a541-78e9d4bf7fe4"

# 非交互式恢复指定会话
claude -r "session-id" -p "继续讨论"
```

**测试结果**: `--resume <session_id>` 成功恢复指定会话，保留完整上下文。

### 1.5 分叉会话

```bash
# 恢复会话但创建新的 session ID（不修改原会话）
claude --resume "session-id" --fork-session

# 继续最近会话但分叉
claude -c --fork-session
```

**测试结果**: `--fork-session` 基于原会话上下文创建新会话，原会话不受影响。

### 1.6 会话管理命令汇总

| 命令 | 说明 | 交互式 | 非交互式 |
|------|------|--------|----------|
| `claude` | 开启新会话 | ✅ | — |
| `claude -p "prompt"` | 非交互式新会话 | — | ✅ |
| `claude -n "name"` | 命名新会话 | ✅ | ✅ |
| `claude -c` | 继续最近会话 | ✅ | ✅ |
| `claude -r "session-id"` | 恢复/继续指定会话 | ✅ | ✅ |
| `claude --session-id "uuid"` | 创建新会话并指定 ID（已存在则报错） | ✅ | ✅ |
| `claude -r "id" --fork-session` | 分叉会话 | ✅ | ✅ |

---

## 二、System Prompt 覆盖

### 2.1 替换 System Prompt

```bash
# 使用字符串替换系统提示词
claude --system-prompt "你是一个代码审查专家，只做代码审查，不修改代码。" -p "审查当前项目"

# 使用文件内容替换系统提示词
claude --system-prompt "$(cat ./prompts/reviewer.txt)" -p "审查代码"
```

**测试结果**: `--system-prompt` 完全替换默认系统提示词，注入的角色定义完全生效。

### 2.2 附加 System Prompt

```bash
# 使用字符串追加系统提示词
claude --append-system-prompt "你是 Python 专家，回答时优先使用 Python 示例。" -p "什么是装饰器？"

# 使用文件内容追加系统提示词
claude --append-system-prompt "$(cat ./prompts/python-expert.txt)" -p "解释闭包"
```

**测试结果**: `--append-system-prompt` 在默认系统提示词基础上追加内容，保留原有功能。

### 2.3 参数对比

| 参数 | 作用 | 适用场景 |
|------|------|----------|
| `--system-prompt <prompt>` | 完全替换系统提示词 | 需要完全自定义角色行为 |
| `--append-system-prompt <prompt>` | 追加到默认系统提示词 | 在保留默认能力的基础上增加角色定义 |

**输入格式**: 两种参数都支持：
- 直接字符串: `--system-prompt "你的提示词"`
- 文件内容: `--system-prompt "$(cat path/to/file.txt)"`

---

## 三、settings.json 覆盖

> 详细测试结果见 [claude-cli-config-override-research.md](./claude-cli-config-override-research.md)

### 3.1 加载额外配置文件

```bash
# 加载 JSON 文件
claude --settings ./config/role-settings.json -p "执行任务"

# 加载 JSON 字符串
claude --settings '{"permissions":{"deny":["Bash(rm -rf *)"]}}' -p "执行任务"
```

### 3.2 控制配置来源

```bash
# 只加载用户级和项目级配置
claude --setting-sources "user,project" -p "执行任务"

# 只加载用户级配置
claude --setting-sources "user" -p "执行任务"
```

### 3.3 配置合并规则

```
最终配置 = 用户级配置 ⊕ 项目级配置 ⊕ --settings 参数
```

**合并机制**:
- `env`: 合并（所有来源的环境变量都生效）
- `permissions.deny`: 合并（所有来源的 deny 规则都生效）
- `permissions.allow`: 合并（所有来源的 allow 规则都生效）

**优先级**:
```
命令行参数 > --settings 指定的文件 > 项目级 .claude/settings.json > 用户级 ~/.claude/settings.json
```

**重要**: `deny` 规则优先级高于 `defaultMode`，即使 `defaultMode: "bypassPermissions"`，`deny` 规则仍然生效。

---

## 四、工具管理

### 4.1 指定可用工具（白名单）

```bash
# 只允许使用 Bash 和 Read 工具
claude --tools "Bash,Read" -p "列出当前目录文件"

# 只允许使用 Read 和 Grep 工具
claude --tools "Read,Grep" -p "搜索代码中的 TODO"
```

**测试结果**: `--tools` 限制为白名单模式，未列出的工具不可用。

### 4.2 禁用指定工具（黑名单）

```bash
# 禁用 Bash 和 Write 工具
claude --disallowedTools "Bash,Write" -p "分析代码"

# 禁用 Edit 工具
claude --disallowedTools "Edit" -p "查看文件"
```

**测试结果**: `--disallowedTools` 从可用工具中移除指定工具，其余工具正常使用。

### 4.3 允许特定工具模式

```bash
# 只允许 git 相关的 Bash 命令和 Read 工具
claude --allowedTools "Bash(git *) Read" -p "查看 git 状态"
```

**测试结果**: `--allowedTools` 支持通配符模式，精确控制工具使用范围。

### 4.4 工具管理参数对比

| 参数 | 模式 | 说明 |
|------|------|------|
| `--tools "Tool1,Tool2"` | 白名单 | 只能使用列出的工具 |
| `--disallowedTools "Tool1,Tool2"` | 黑名单 | 禁用列出的工具，其余可用 |
| `--allowedTools "Tool1,Tool2"` | 精确控制 | 支持通配符，如 `Bash(git *)` |

**格式**: 逗号分隔 `"Tool1,Tool2"` 或空格分隔 `"Tool1 Tool2"`

---

## 五、Skill 管理

### 5.1 禁用所有 Skill

```bash
# 禁用所有 slash commands（技能）
claude --disable-slash-commands -p "执行任务"
```

**测试结果**: `--disable-slash-commands` 禁用所有 Skill 的自动加载和调用能力。

### 5.2 禁用特定插件（Plugin）

Skill 来源于两类：**插件（Plugin）** 和 **用户自定义 Skill**。插件包含多个 Skill，可通过 `enabledPlugins` 控制。

```bash
# 禁用 superpowers 插件（包含 brainstorming、TDD、debugging 等 15+ 个 Skill）
claude --settings '{"enabledPlugins":{"superpowers@claude-plugins-official":false}}' -p "列出技能"

# 禁用多个插件
claude --settings '{"enabledPlugins":{"superpowers@claude-plugins-official":false,"code-review@claude-plugins-official":false}}' -p "执行任务"
```

**测试结果**: 设置 `enabledPlugins` 为 `false` 后，该插件下的所有 Skill 不再加载。

**插件命名格式**: `<plugin-name>@<marketplace>`，例如：
- `superpowers@claude-plugins-official`
- `code-review@claude-plugins-official`
- `frontend-design@claude-plugins-official`

### 5.3 跳过用户级 Skill

```bash
# 只加载项目级配置，跳过用户级 Skill（~/.claude/skills/ 下的技能不加载）
claude --setting-sources "project" -p "列出技能"
```

**测试结果**: 使用 `--setting-sources "project"` 后，只显示内置 Skill 和项目级 Skill，用户自定义 Skill 不加载。

### 5.4 Skill 管理方式汇总

| 需求 | 方案 | 命令 |
|------|------|------|
| 禁用所有 Skill | `--disable-slash-commands` | `claude --disable-slash-commands` |
| 禁用某个插件的所有 Skill | `enabledPlugins` 设为 `false` | `claude --settings '{"enabledPlugins":{"superpowers@claude-plugins-official":false}}'` |
| 跳过用户自定义 Skill | `--setting-sources` 排除 user | `claude --setting-sources "project"` |
| 只加载指定插件 | `--plugin-dir` 指定目录 | `claude --plugin-dir ./my-plugins` |

**注意**: 用户自定义 Skill（`~/.claude/skills/` 下的目录）目前没有单个禁用的配置项。如需禁用单个用户 Skill，需删除或移走对应的 Skill 目录。

---

## 六、常用组合示例

### 6.1 角色隔离启动

```bash
# 代码审查员（只读，自定义角色）
claude \
  --system-prompt "$(cat ./roles/code-reviewer/prompt.txt)" \
  --settings ./roles/code-reviewer/settings.json \
  --disallowedTools "Write,Edit" \
  -p "审查 src/main.py"
```

### 6.2 非交互式脚本调用

```bash
# 简单的非交互式调用
claude -p "生成一个 Hello World 的 Python 脚本"

# 带输出格式的调用（JSON）
claude -p --output-format json "分析当前项目结构"

# 指定模型
claude -p --model sonnet "快速回答：什么是闭包？"
```

### 6.3 恢复会话继续工作

```bash
# 查看最近会话
ls -lt ~/.claude/projects/<project-path>/*.jsonl | head -5

# 恢复指定会话
claude -r "session-id"

# 恢复并分叉（不影响原会话）
claude -r "session-id" --fork-session
```

---

## 七、参数速查表

### 会话管理

| 参数 | 缩写 | 说明 |
|------|------|------|
| `--continue` | `-c` | 继续最近会话 |
| `--resume [id]` | `-r` | 恢复指定会话 |
| `--session-id <uuid>` | | 创建新会话并指定 ID（已存在则报错） |
| `--fork-session` | | 分叉会话（配合 --resume 使用） |
| `--name <name>` | `-n` | 设置会话名称 |
| `--no-session-persistence` | | 不保存会话历史 |

### System Prompt

| 参数 | 说明 |
|------|------|
| `--system-prompt <prompt>` | 替换系统提示词 |
| `--append-system-prompt <prompt>` | 追加系统提示词 |

### 配置覆盖

| 参数 | 说明 |
|------|------|
| `--settings <file-or-json>` | 加载额外配置文件或 JSON 字符串 |
| `--setting-sources <sources>` | 指定配置来源（user, project, local） |
| `--mcp-config <configs...>` | 加载 MCP 配置 |
| `--strict-mcp-config` | 仅使用指定的 MCP 配置 |
| `--plugin-dir <path>` | 加载指定目录的插件 |

### 工具管理

| 参数 | 说明 |
|------|------|
| `--tools <tools...>` | 白名单：指定可用工具 |
| `--disallowedTools <tools...>` | 黑名单：禁用指定工具 |
| `--allowedTools <tools...>` | 精确控制：支持通配符 |

### Skill 管理

| 参数 | 说明 |
|------|------|
| `--disable-slash-commands` | 禁用所有 Skill |
| `--settings '{"enabledPlugins":{"<plugin>@<market>":false}}'` | 禁用特定插件的所有 Skill |
| `--setting-sources "project"` | 跳过用户级 Skill |

### 输出控制

| 参数 | 说明 |
|------|------|
| `--print` `-p` | 非交互模式，输出后退出 |
| `--output-format <format>` | 输出格式：text, json, stream-json |
| `--model <model>` | 指定模型 |

---

## 八、测试验证记录

| 功能 | 命令 | 测试状态 | 测试日期 |
|------|------|----------|----------|
| System Prompt 替换 | `--system-prompt "..."` | ✅ 通过 | 2026-05-23 |
| System Prompt 文件输入 | `--system-prompt "$(cat file)"` | ✅ 通过 | 2026-05-23 |
| System Prompt 追加 | `--append-system-prompt "..."` | ✅ 通过 | 2026-05-23 |
| System Prompt 追加文件输入 | `--append-system-prompt "$(cat file)"` | ✅ 通过 | 2026-05-23 |
| 配置文件覆盖 | `--settings file.json` | ✅ 通过 | 2026-05-23 |
| 配置来源控制 | `--setting-sources "user,project"` | ✅ 通过 | 2026-05-23 |
| 工具白名单 | `--tools "Bash,Read"` | ✅ 通过 | 2026-05-23 |
| 工具黑名单 | `--disallowedTools "Bash,Write"` | ✅ 通过 | 2026-05-23 |
| 工具精确控制 | `--allowedTools "Bash(git *)"` | ✅ 通过 | 2026-05-23 |
| 继续最近会话 | `--continue` / `-c` | ✅ 通过 | 2026-05-23 |
| 恢复指定会话 | `--resume "session-id"` | ✅ 通过 | 2026-05-23 |
| 指定 session ID | `--session-id "uuid"` | ✅ 通过 | 2026-05-23 |
| 分叉会话 | `--fork-session` | ✅ 通过 | 2026-05-23 |
| 命名会话 | `--name "name"` | ✅ 通过 | 2026-05-23 |
| 禁用所有 Skill | `--disable-slash-commands` | ✅ 通过 | 2026-05-23 |
| 禁用特定插件 | `enabledPlugins: false` | ✅ 通过 | 2026-05-23 |
| 跳过用户 Skill | `--setting-sources "project"` | ✅ 通过 | 2026-05-23 |
| JSON 输出 | `--output-format json` | ✅ 通过 | 2026-05-23 |

---

**文档结束**
