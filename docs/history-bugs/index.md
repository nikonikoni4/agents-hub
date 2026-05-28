## Codex CLI 环境变量路径找不到
 - updated_at : 2026-05-23
 - path: docs/history-bugs/2026-05-23-codex-cli-path-not-found.md
 - 触发规则：Windows 上 asyncio.create_subprocess_exec 启动 codex 报 FileNotFoundError
 - 内容摘要：codex 通过 npm 安装，.cmd 路径不在 PATH 中，需用 Path.home() 拼接完整路径

## Claude CLI --bare 模式跳过全局 CLAUDE.md
 - updated_at : 2026-05-24
 - path: docs/history-bugs/2026-05-24-claude-bare-mode-skips-global-claude-md.md
 - 触发规则：使用 CLAUDE_CONFIG_DIR 做角色隔离时，如果加了 --bare 标志，角色 CLAUDE.md 不会被加载
 - 内容摘要：--bare 模式跳过全局 CLAUDE.md 和 skills 的加载，但不跳过项目级 CLAUDE.md。角色隔离场景下不能使用 --bare

## Codex CLI Prompt 换行符导致解析错误
 - updated_at : 2026-05-28
 - path: docs/history-bugs/2026-05-28-cli-system-prompt-blocks-simple-requests.md
 - 触发规则：使用 Codex CLI 且 prompt 包含换行符时，CLI 无法正确解析
 - 内容摘要：Codex CLI 对换行符的处理存在问题，导致 prompt 被截断或错误分割。解决方案：在 CodexExecutor 中自动移除换行符
