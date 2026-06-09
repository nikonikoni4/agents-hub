# Claude CLI 工具分类研究报告

**创建时间**: 2026-06-09
**研究目的**: 搞清楚 CLI 工具的完整列表、分类和配置方式

## 核心发现

1. **CLI 共有 26 个内置工具**，不需要在 settings.json 中配置
2. **settings.json 只控制权限**（allow/deny/ask），不控制工具加载
3. **Plan 工具在 `-p` 模式下有限制**：可以进入但无法退出
4. **CLI 和 TUI 的任务管理工具不同**：CLI 用 TodoWrite，TUI 用 TaskCreate

---

## 工具完整列表（26 个）

| # | 工具名 | 用途 | 分类 |
|---|--------|------|------|
| 1 | Agent | 启动子代理处理复杂任务 | core |
| 2 | AskUserQuestion | 向用户提问澄清需求 | core |
| 3 | Skill | 调用已安装的 skill | core |
| 4 | Read | 读取文件内容 | read |
| 5 | Glob | 按模式查找文件 | read |
| 6 | Grep | 搜索文件内容 | read |
| 7 | WebSearch | 网络搜索 | read |
| 8 | WebFetch | 抓取网页内容 | read |
| 9 | ListMcpResourcesTool | 列出 MCP 资源 | read |
| 10 | ReadMcpResourceTool | 读取 MCP 资源 | read |
| 11 | Edit | 精确替换文件内容 | write |
| 12 | Write | 创建/覆盖文件 | write |
| 13 | NotebookEdit | 编辑 Jupyter Notebook | write |
| 14 | PowerShell | 执行 shell 命令 | execute |
| 15 | EnterWorktree | 创建/进入 worktree | execute |
| 16 | ExitWorktree | 退出 worktree | execute |
| 17 | CronCreate | 创建定时任务 | execute |
| 18 | CronDelete | 删除定时任务 | execute |
| 19 | CronList | 列出定时任务 | execute |
| 20 | EnterPlanMode | 进入规划模式 | plan |
| 21 | ExitPlanMode | 退出规划模式 | plan |
| 22 | TodoWrite | 管理任务清单（临时） | task |
| 23 | TaskOutput | 获取后台任务输出 | task |
| 24 | TaskStop | 停止后台任务 | task |
| 25 | ScheduleWakeup | 调度唤醒 | task |
| 26 | mcp__mimo-image__understand_image | 图片理解 | mcp |

---

## 工具分类方案

### 1. Core（核心工具）- 每次会话必备

| 工具 | 用途 |
|------|------|
| Agent | 启动子代理处理复杂任务 |
| AskUserQuestion | 向用户提问澄清需求 |
| Skill | 调用已安装的 skill |
| Read | 读取文件内容 |

### 2. Read（只读查询）- 不修改任何内容

| 工具 | 用途 |
|------|------|
| Glob | 按模式查找文件 |
| Grep | 搜索文件内容 |
| WebSearch | 网络搜索 |
| WebFetch | 抓取网页内容 |
| ListMcpResourcesTool | 列出 MCP 资源 |
| ReadMcpResourceTool | 读取 MCP 资源 |

### 3. Write（写入修改）- 修改文件或状态

| 工具 | 用途 |
|------|------|
| Edit | 精确替换文件内容 |
| Write | 创建/覆盖文件 |
| NotebookEdit | 编辑 Jupyter Notebook |

### 4. Execute（执行操作）- 运行命令或管理环境

| 工具 | 用途 |
|------|------|
| PowerShell | 执行 shell 命令 |
| EnterWorktree | 创建/进入 worktree |
| ExitWorktree | 退出 worktree |
| CronCreate | 创建定时任务 |
| CronDelete | 删除定时任务 |
| CronList | 列出定时任务 |

### 5. Plan（规划模式）- 设计方案

| 工具 | 用途 |
|------|------|
| EnterPlanMode | 进入规划模式 |
| ExitPlanMode | 退出规划模式 |

### 6. Task（任务管理）- 追踪进度

| 工具 | 用途 |
|------|------|
| TodoWrite | 管理任务清单（临时） |
| TaskOutput | 获取后台任务输出 |
| TaskStop | 停止后台任务 |
| ScheduleWakeup | 调度唤醒 |

### 7. MCP（外部工具）- 扩展能力

| 工具 | 用途 |
|------|------|
| mcp__mimo-image__understand_image | 图片理解 |
| mcp__agents-hub__* | Agents Hub 平台工具 |

---

## 工具加载机制

### 内置工具 vs 配置工具

| 类型 | 示例 | 是否需要配置 |
|------|------|--------------|
| **内置工具** | Read, Write, Edit, Agent, TodoWrite, Plan... | ❌ CLI 自动加载 |
| **MCP 工具** | mcp__agents-hub__*, mcp__mimo-image__* | ✅ 需要在 .mcp.json 配置 |

### settings.json 的作用

**只控制权限，不控制加载**：

```json
{
  "permissions": {
    "allow": ["Bash(git *)"],      // 允许 git 相关命令
    "deny": ["TodoWrite"],         // 禁止 TodoWrite
    "ask": ["Bash(git push *)"]    // git push 需要询问
  }
}
```

### 权限控制方式

| 方式 | 说明 | 优先级 |
|------|------|--------|
| `--disallowedTools` | CLI 参数，黑名单 | 最高 |
| `settings.json deny` | 配置文件，黑名单 | 高 |
| `settings.json allow` | 配置文件，白名单 | 中 |
| `settings.json ask` | 配置文件，询问 | 低 |

---

## Plan 工具测试

### 测试结果

| 模式 | EnterPlanMode | ExitPlanMode |
|------|---------------|--------------|
| **交互模式** | ✅ 可用 | ✅ 可用 |
| **`-p` 模式** | ✅ 可用 | ❌ 被拒绝 |

### 原因

`ExitPlanMode` 需要用户批准才能退出，但 `-p` 模式没有用户交互，所以会被拒绝。

### 建议

- 交互模式：完整支持 plan 工具
- `-p` 模式：让 Claude 直接输出计划，不走 plan 工具

---

## 任务管理工具对比

| 工具 | CLI 有 | TUI 有 | 来源 | 持久性 |
|------|--------|--------|------|--------|
| TodoWrite | ✅ | ❌ | CLI 内置 | 临时（会话结束丢失） |
| TaskCreate | ❌ | ✅ | Superpowers 插件 | 持久化 |
| TaskUpdate | ❌ | ✅ | Superpowers 插件 | 持久化 |
| TaskList | ❌ | ✅ | Superpowers 插件 | 持久化 |
| TaskGet | ❌ | ✅ | Superpowers 插件 | 持久化 |

### 禁用 TodoWrite 的方法

```bash
# 方法 1: CLI 参数
claude --disallowedTools "TodoWrite,TodoRead"

# 方法 2: settings.json
{
  "permissions": {
    "deny": ["TodoWrite", "TodoRead"]
  }
}
```

---

## 按任务分配建议

| 任务类型 | 推荐工具 |
|----------|----------|
| **代码探索** | Read + Glob + Grep |
| **代码修改** | Edit + Write |
| **复杂任务** | Agent + Plan |
| **测试验证** | PowerShell |
| **任务追踪** | TodoWrite（或 MCP 替代） |
| **网络调研** | WebSearch + WebFetch |

---

## 相关文档

- `docs/temp/研究报告/CLI_AND_SDK/claude_tool_settings.md` - CLI 工具权限设置
- `docs/temp/研究报告/CLI_AND_SDK/todowrite-vs-taskcreate-difference.md` - TodoWrite vs TaskCreate 差异
- `docs/history-bugs/2026-06-09-manager-tool-call-infinite-loop.md` - TodoWrite 循环 bug
