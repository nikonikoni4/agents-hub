# Claude Code 权限系统说明

## 概述

Claude Code 的权限系统分为两层：
1. **交互式权限模式** — 控制是否弹出权限确认提示
2. **持久化权限配置** — 通过 settings.json 中的 allow/deny/ask 规则列表进行细粒度控制

---

## 一、Settings.json 权限模式配置

### 1.1 权限模式关键词

在 settings.json 中使用 `defaultMode` 字段设置默认权限模式：

```json
{
  "defaultMode": "bypassPermissions"
}
```

**可选值：**

| 关键词 | 模式名称 | 说明 |
|--------|----------|------|
| `"default"` 或不设置 | Normal（正常模式） | 默认模式，按 allow/deny/ask 规则决定是否弹提示 |
| `"autoAcceptEdits"` | Auto-accept edits | 自动接受文件编辑，Bash 命令仍需确认 |
| `"bypassPermissions"` | Bypass permissions | 跳过所有确认，但 deny 列表仍然生效 |

### 1.2 权限规则配置关键词

在 settings.json 的 `permissions` 字段中配置细粒度规则：

```json
{
  "permissions": {
    "allow": ["Bash(git status)", "Read", "Write"],
    "deny": ["Bash(rm *)", "Bash(eval *)"],
    "ask": ["Bash(git push *)", "Bash(pip install *)"]
  }
}
```

**规则关键词说明：**

| 关键词 | 作用 | 优先级 |
|--------|------|--------|
| `allow` | 自动放行，不弹提示 | 高 |
| `deny` | 直接拒绝，不弹提示 | 最高 |
| `ask` | 每次都需要用户确认 | 中 |
| 不在任何列表 | 按 defaultMode 行为处理 | 低 |

**支持的工具类型：**
- `Bash(command)` — Bash 命令，支持通配符匹配
- `Read` — 文件读取
- `Write` — 文件写入
- `Edit` — 文件编辑
- `Glob` — 文件搜索
- `Grep` — 内容搜索
- `WebFetch` — 网页抓取
- `WebSearch` — 网页搜索

### 1.3 配置文件位置（按优先级从高到低）

| 文件路径 | 说明 | 是否提交到 Git |
|----------|------|----------------|
| `.claude/settings.local.json` | 本地项目配置 | 否 |
| `.claude/settings.json` | 项目级配置 | 是 |
| `~/.claude/settings.json` | 用户级全局配置 | — |

### 1.4 完整配置示例

```json
{
  "defaultMode": "bypassPermissions",
  "permissions": {
    "allow": [
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(eval *)",
      "Bash(exec *)",
      "Bash(curl * | bash)",
      "Bash(wget * | bash)"
    ],
    "ask": [
      "Bash(git push *)",
      "Bash(git commit *)",
      "Bash(pip install *)",
      "Bash(npm install *)",
      "Write",
      "Edit"
    ]
  }
}
```

---

## 二、CLI 命令权限跳过

### 2.1 完整 CLI 命令

```bash
claude --dangerously-skip-permissions
```

### 2.2 命令含义

这个选项会**完全无条件地跳过所有权限确认提示**，包括：
- 所有 Bash 命令（包括 `rm -rf`、修改系统文件、网络请求等）
- 所有文件操作（读取、写入、编辑）
- 所有网络操作（抓取、搜索）

**与 `bypassPermissions` 模式的区别：**

| 特性 | `bypassPermissions` 模式 | `--dangerously-skip-permissions` |
|------|---------------------------|----------------------------------|
| deny 列表是否生效 | ✅ 生效 | ❌ 不生效 |
| ask 列表是否生效 | ✅ 生效 | ❌ 不生效 |
| 安全性 | 有管控的绕过 | 完全无管控 |
| 适用场景 | 交互式开发 | CI/CD、自动化脚本 |

### 2.3 使用场景

`--dangerously-skip-permissions` 主要设计用于**非交互式场景**：

1. **CI/CD 流水线** — 自动运行 Claude Code 进行代码审查、测试等
2. **脚本自动化调用** — 通过脚本批量执行任务
3. **无人值守的 headless 模式** — 没有人坐在终端前点击 "Allow"

### 2.4 安全警告

⚠️ **这个命令名字中包含 "dangerously" 是刻意的**，因为：

1. **完全移除安全网** — Claude 可以执行任何命令，无需任何人确认
2. **可能造成不可逆损害** — 包括删除文件、修改系统配置、泄露敏感信息等
3. **不应在交互式开发中使用** — 日常开发应使用 `bypassPermissions` 模式 + 详细的规则列表

### 2.5 其他相关 CLI 选项

| 选项 | 说明 |
|------|------|
| `--dangerously-skip-permissions` | 跳过所有权限确认（最高权限） |
| `-p, --print` | 打印模式，不进入交互式界面 |
| `-c, --continue` | 继续上一次对话 |
| `-r, --resume` | 恢复指定对话 |
| `--model <model>` | 指定使用的模型 |
| `--permission-mode <mode>` | 指定权限模式（default/auto-accept-edits/bypass-permissions） |

---

## 三、最佳实践建议

### 3.1 日常开发推荐配置

```json
{
  "defaultMode": "bypassPermissions",
  "permissions": {
    "allow": [
      "Bash(git *)",
      "Read",
      "Glob",
      "Grep"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(eval *)",
      "Bash(exec *)",
      "Bash(curl * | bash)"
    ],
    "ask": [
      "Bash(git push *)",
      "Write",
      "Edit"
    ]
  }
}
```

### 3.2 CI/CD 环境推荐配置

```bash
# 在 CI/CD 脚本中使用
claude --dangerously-skip-permissions --print "执行任务描述"
```

### 3.3 权限模式切换

在 Claude Code 交互界面中，可以通过 `Shift+Tab` 快捷键切换权限模式：
- Normal → Auto-accept edits → Bypass permissions → Normal（循环）

---

## 四、常见问题

### Q1: `bypassPermissions` 模式下，deny 列表还会生效吗？

**A:** 是的，`bypassPermissions` 模式只是跳过了确认提示，但 deny 列表中的规则仍然会生效，直接拒绝执行。

### Q2: 如何查看当前的权限配置？

**A:** 在 Claude Code 中输入 `/permissions` 命令可以查看和管理当前的权限配置。

### Q3: `--dangerously-skip-permissions` 和 `--permission-mode bypass-permissions` 有什么区别？

**A:** `--dangerously-skip-permissions` 是完全无条件跳过一切，连 deny 列表都不生效；而 `--permission-mode bypass-permissions` 等同于在 settings.json 中设置 `defaultMode: "bypassPermissions"`，deny 列表仍然生效。

### Q4: 可以同时使用多个权限配置文件吗？

**A:** 可以，多个配置文件会按优先级合并（本地项目 > 项目级 > 用户级），同名字段以高优先级为准。
