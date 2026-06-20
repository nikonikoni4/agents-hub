---
version: 1.0
created_at: 2026-06-20
updated_at: 2026-06-20
last_updated: 创建文档：CLI stderr 输出 ANSI 转义码乱码
abstract: 记录 CLI 执行失败时 stderr 中的 ANSI 终端颜色转义码直接输出导致乱码的问题
---

# CLI stderr 输出 ANSI 转义码乱码

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题描述

当 CLI 执行失败时，stderr 输出中包含 ANSI 终端颜色转义码（如 `\x1b[31;1m`），这些原始字节被直接拼接到错误信息中，导致日志和前端显示为乱码。

## 问题场景

1. **Codex CLI 执行失败**：Codex 内部工具执行报错时，stderr 带有颜色高亮
2. **Claude CLI 执行失败**：Claude CLI 错误输出带有终端颜色
3. **Docker 容器执行失败**：容器内进程的彩色错误输出

## 问题表现

- 错误信息中出现类似 `\x1b[31;1mParserError:\x1b[0m` 的乱码
- 日志可读性差，难以定位真实错误
- 前端展示的错误信息对用户不友好

## 根因

CLI 工具的 stderr 输出默认带有 ANSI 转义码用于终端高亮显示。Agent Hub 直接 `stderr.decode("utf-8")` 后传入错误信息，没有剥离这些非文本字符。

## 修复方案

在所有 executor 的 stderr 解码处增加 ANSI 转义码清理：

```python
import re

# 修复前
stderr_text = stderr.decode("utf-8")

# 修复后
stderr_text = re.sub(r"\x1b\[[0-9;]*m", "", stderr.decode("utf-8"))
```

影响文件：
- `agents_hub/agent_bridge/executors/codex.py`
- `agents_hub/agent_bridge/executors/claude.py`
- `agents_hub/agent_bridge/executors/docker_base.py`
- `agents_hub/agent_bridge/executors/opencode.py`

## 副作用：Codex CLI 在 Windows 执行 bash heredoc 失败

在排查此问题时发现 Codex CLI 的另一个问题：Codex 内部执行代码时使用了 bash heredoc 语法 `python - <<'PY'`，但 Windows PowerShell 不支持此语法，导致 `ParserError: Missing file specification after redirection operator`。

**这是 Codex CLI 自身的 bug**，非 Agent Hub 问题，需向 Codex CLI repo 报告。

## 优先级

**中** - 不影响功能，但影响错误排查效率和用户体验

## 记录信息

- 记录时间：2026-06-20
- 问题来源：用户反馈
- 状态：已修复（ANSI 乱码）/ 待报告（Codex Windows heredoc）
