# Codex CLI 环境变量路径找不到

- 发现时间：2026-05-23
- 影响范围：CodexExecutor 在 Windows 上无法启动 codex 进程
- 状态：已修复

## 问题描述

`CodexExecutor` 使用 `asyncio.create_subprocess_exec("codex", ...)` 启动 Codex CLI，但在 Windows 上报错：

```
FileNotFoundError: [WinError 2] 系统找不到指定的文件。
```

## 根因

Codex 通过 npm 安装，实际路径为 `C:\Users\<用户>\AppData\Roaming\npm\codex.cmd`。`asyncio.create_subprocess_exec` 在 Windows 上不会自动解析 `.cmd` 批处理文件，且该路径可能不在系统 PATH 中，导致找不到命令。

## 解决方案

在 `agents_hub/agent_bridge/config.py` 中定义 CLI 命令常量，使用 `Path.home()` 动态拼接完整路径：

```python
from pathlib import Path

CODEX_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
CLAUDE_COMMAND = str(Path.home() / ".local" / "bin" / "claude")
```

Executor 从常量读取命令路径，不硬编码用户名。

## 注意事项

- 不同用户的安装路径可能不同，需要确认实际路径
- 如果 codex 改为其他安装方式（如全局安装），路径可能变化
- Claude CLI 安装在 `~/.local/bin/claude`，同样需要完整路径
