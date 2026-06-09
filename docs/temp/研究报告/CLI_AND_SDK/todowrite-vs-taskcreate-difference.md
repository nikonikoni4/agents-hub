# TodoWrite vs TaskCreate 工具差异研究

**创建时间**: 2026-06-09
**研究目的**: 搞清楚 CLI 和 TUI 中任务管理工具的差异

## 核心发现

**CLI 和 TUI 使用不同的任务管理工具，来源不同。**

## 工具对比

| 工具 | CLI 有 | TUI 有 | 来源 | 用途 |
|------|--------|--------|------|------|
| `TodoWrite` | ✅ | ❌ | Claude Code 原生内置 | 会话内任务清单（临时） |
| `TodoRead` | ✅ | ❌ | Claude Code 原生内置 | 读取任务清单 |
| `TaskCreate` | ❌ | ✅ | Superpowers 插件 | 创建结构化任务 |
| `TaskUpdate` | ❌ | ✅ | Superpowers 插件 | 更新任务状态 |
| `TaskList` | ❌ | ✅ | Superpowers 插件 | 列出所有任务 |
| `TaskGet` | ❌ | ✅ | Superpowers 插件 | 获取任务详情 |
| `TaskOutput` | ✅ | ✅ | Claude Code 原生 | 获取后台任务输出 |
| `TaskStop` | ✅ | ✅ | Claude Code 原生 | 停止后台任务 |

## 详细说明

### TodoWrite（CLI 原生）

- **生命周期**: 会话内临时，CLI 重启后丢失
- **状态**: pending / in_progress / completed
- **参数**: `{content, status, activeForm}`
- **问题**: 不持久化，容易导致重复调用循环

### TaskCreate（Superpowers 插件）

- **生命周期**: 持久化存储
- **状态**: pending / in_progress / completed / deleted
- **参数**: `{subject, description, activeForm, metadata}`
- **优势**: 支持依赖关系（blocks/blockedBy），支持 owner 分配

### TaskOutput / TaskStop（后台任务）

- **用途**: 管理后台运行的 shell、agent、remote session
- **与 Todo/Task 无关**: 这是进程管理，不是任务清单

## 禁用 TodoWrite 的方法

### 方法 1: CLI 参数

```bash
claude --disallowedTools "TodoWrite,TodoRead" "你的任务"
```

### 方法 2: settings.json

```json
{
  "permissions": {
    "deny": ["TodoWrite", "TodoRead"]
  }
}
```

### 方法 3: CLAUDE.md 软控制

```markdown
## 工具使用规则

- **禁止使用 TodoWrite 和 TodoRead 工具**。所有任务追踪必须通过 MCP 的任务管理工具或 progress-tracker skill 完成。
```

## 实测验证

### 测试命令

```bash
CLAUDE_CONFIG_DIR="path/to/settings" claude -p --disallowedTools "TodoWrite,TodoRead" --output-format json "你有哪些可用的工具？"
```

### 测试结果

Claude 回复：
> **我没有 TodoWrite 和 TodoRead 工具。** 这两个工具在当前环境中不可用。

## 建议

1. **禁用 TodoWrite**: 使用 `--disallowedTools` 或 `settings.json deny`
2. **使用替代方案**:
   - MCP 工具: `assign_tasks_to_team`（持久化）
   - 插件工具: `TaskCreate`（如果在 TUI 中）
   - Skill: `/progress-tracker`（输出到文件）

## 相关文档

- `docs/temp/研究报告/CLI_AND_SDK/claude_tool_settings.md` - CLI 工具权限设置
- `docs/history-bugs/2026-06-09-manager-tool-call-infinite-loop.md` - TodoWrite 循环 bug
