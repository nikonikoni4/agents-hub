# Claude Code CLI 工具权限设置

## 概述

Claude Code CLI 提供三种工具限制机制，用于控制 Claude 可以使用哪些工具。

## 三个工具限制标志

| 标志 | 模式 | 说明 |
|------|------|------|
| `--tools` | 白名单 | 只允许列出的工具，其余全部阻止 |
| `--disallowedTools` | 黑名单 | 阻止列出的工具，其余全部允许 |
| `--allowedTools` | 细粒度 | 支持通配符模式，如 `Bash(git *)` |

### `--tools` — 严格白名单

最严格的限制方式。只允许列出的工具，其他全部不可用。

```bash
# 只允许 Read 和 Grep，无法执行任何写入操作
claude -p --tools "Read,Grep" "分析代码结构"
```

**实测发现（2026-06-06）：** `--tools` 标志在实际测试中无法正确注册 `Bash` 工具。即使指定 `--tools "Bash,Read"` 或 `--tools Bash --tools Read`，Claude 子进程仍报告没有 Bash 工具。**推荐使用 `--allowedTools` 替代。**

适用场景：只读分析、CI 检查、代码审查（推荐用 `--allowedTools`）。

### `--disallowedTools` — 黑名单

移除指定工具，其他保留。

```bash
# 禁止 Bash 和 Write，其余工具正常可用
claude -p --disallowedTools "Bash,Write" "重构这段代码"
```

适用场景：禁止危险操作但保留编辑能力。

### `--allowedTools` — 细粒度控制

支持通配符，可以精确控制 Bash 命令的范围。

```bash
# 只允许 git 相关的 bash 命令 + 文件读取
claude -p --allowedTools "Bash(git *) Read Glob Grep" "查看最近变更"

# 只允许 ls 命令
claude -p --allowedTools "Bash(ls:*) Read" "列出目录内容"
```

适用场景：需要 Bash 但要限制命令范围。

## 格式说明

- 逗号分隔：`"Tool1,Tool2,Tool3"`
- 空格分隔：`"Tool1 Tool2 Tool3"`
- 工具名区分大小写

## 可用工具列表

| 工具名 | 类型 | 说明 |
|--------|------|------|
| `Bash` | 执行 | 运行 shell 命令 |
| `Read` | 只读 | 读取文件内容 |
| `Glob` | 只读 | 按模式查找文件 |
| `Grep` | 只读 | 搜索文件内容 |
| `Edit` | 写入 | 精确替换文件内容 |
| `Write` | 写入 | 创建/覆盖文件 |
| `NotebookEdit` | 写入 | 编辑 Jupyter Notebook |
| `Agent` | 执行 | 启动子 Agent |
| `WebSearch` | 只读 | 网页搜索 |
| `WebFetch` | 只读 | 获取网页内容 |
| `TaskCreate` | 写入 | 创建任务 |
| `TaskUpdate` | 写入 | 更新任务状态 |

MCP 工具命名格式：`mcp__<server>__<tool>`，如 `mcp__mimo-image__understand_image`。

## 权限模式标志

| 标志 | 说明 |
|------|------|
| `--permission-mode default` | 默认模式，交互式确认 |
| `--permission-mode plan` | 只读模式（plan 文件除外） |
| `--permission-mode auto` | 自动批准编辑 |
| `--permission-mode bypassPermissions` | 跳过权限提示（仍遵守 deny 规则） |
| `--dangerously-skip-permissions` | 完全跳过所有权限检查（包括 deny） |

## 配置合并规则

```
CLI 参数 > --settings 文件 > 项目 .claude/settings.json > 用户 ~/.claude/settings.json
```

`deny` 规则优先级最高，`bypassPermissions` 模式也无法覆盖。

## 只读 CI 检查的推荐组合

```bash
# 方案 1：allowedTools 细粒度控制 + 系统提示双重保险（推荐）
claude -p \
  --allowedTools "Bash(git *) Bash(ls:*) Read Glob Grep WebSearch WebFetch" \
  --append-system-prompt "You are a read-only CI checker. Never modify any files." \
  "审查最近的代码变更"

# 方案 2：更严格的 Bash 限制
claude -p \
  --allowedTools "Bash(git log:*) Bash(git diff:*) Bash(git show:*) Read Glob Grep" \
  --append-system-prompt "You are a read-only CI checker." \
  "查看最近变更"

# 方案 3：配合 settings 文件
claude -p \
  --settings ./ci-settings.json \
  --append-system-prompt "You are a read-only CI checker." \
  "执行 CI 检查"
```

**注意：** `--tools` 标志实测无法正确注册 Bash 工具，推荐始终使用 `--allowedTools`。

## 关键实测发现（2026-06-09）

### `--allowedTools` 无法阻止子 Agent 调用

**测试命令：**
```bash
claude -p --allowedTools "Bash" "请启动一个子agent来分析项目架构"
```

**结果：** 子 Agent 成功调用，使用了 Read、Glob 等 36 次工具调用，`permission_denials: []`。

**结论：`--allowedTools` 是增量白名单，无法可靠阻止未列出的工具（尤其是 Agent）。**

### `--disallowedTools` 是唯一可靠的禁用方式

**测试 1：禁用 Agent**
```bash
claude -p --disallowedTools "Agent" "你有名为Agent的工具吗？"
```
**结果：** Agent 工具直接不在可用工具列表中，Claude 明确回答"没有名为 Agent 的工具"。

**测试 2：禁用 Read**
```bash
claude -p --disallowedTools "Read" "使用Read工具读取文件"
```
**结果：** Claude 尝试调用 Read 时收到错误：
```
Error: No such tool available: Read. Read exists but is not enabled in this context.
```

**测试 3：禁用 MCP 工具**
```bash
claude -p --disallowedTools='mcp__agents-hub__health_check' '使用mcp__agents-hub__health_check工具检查服务状态'
```
**结果：** Claude 明确回答工具不可用，列出了剩余可用的 MCP 工具。`--disallowedTools` 对 MCP 工具同样有效，命名格式为 `mcp__<server>__<tool>`。

### `--disallowedTools` 的工作机制

| 层面 | 是否被过滤 | 说明 |
|------|-----------|------|
| API `tools` 参数 | ✅ 被移除 | 工具定义不会发送给模型 |
| System Prompt 文本 | ❌ 未过滤 | 系统提示词中仍然描述了该工具 |

- 工具定义在 API 请求构建时被移除（模型看不到工具 schema）
- 但系统提示词仍会提及该工具，Claude 从训练数据中"知道"它的存在
- 调用时会收到 `"exists but is not enabled in this context"` 错误
- `bypassPermissions` 模式也无法覆盖 `disallowedTools`

## 注意事项

1. `--tools` 和 `--allowedTools` 语义不同：`--tools` 是严格白名单，`--allowedTools` 是细粒度控制
2. **实测发现**：`--tools` 无法正确注册 Bash 工具，`--allowedTools` 可以正常工作
3. `--allowedTools` 的通配符只对 `Bash` 有效，对其他工具无意义
4. `--dangerously-skip-permissions` 会跳过所有安全检查，CI 环境慎用
5. 多个标志可以组合使用，效果叠加
6. **禁用工具必须用 `--disallowedTools`，`--allowedTools` 无法阻止 Agent 等元工具**
7. `--disallowedTools` 从 API 层面移除工具定义，但系统提示词不会同步清理
