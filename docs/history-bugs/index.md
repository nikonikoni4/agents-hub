## Codex CLI 环境变量路径找不到
 - updated_at : 2026-05-23
 - path: docs/history-bugs/2026-05-23-codex-cli-path-not-found.md
 - 触发规则：Windows 上 asyncio.create_subprocess_exec 启动 codex 报 FileNotFoundError
 - 内容摘要：codex 通过 npm 安装，.cmd 路径不在 PATH 中，需用 Path.home() 拼接完整路径
