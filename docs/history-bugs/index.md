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

## GroupChat.load() 触发 agent.execute() 导致 GET 请求失败
 - updated_at : 2026-06-05
 - path: docs/history-bugs/2026-06-05-load-group-chat-triggers-agent-execute.md
 - 触发规则：从磁盘加载群聊时，如果 agent 的 main_session 为空，load() 会调用 agent.execute() 导致失败
 - 内容摘要：GroupChat.load() 声明"只读"但调用了 _initialize_new_members()，对无 main_session 的 agent 触发 LLM 调用。GET 请求因此报 500。待讨论修复方向

## Agent 初始化时 agent_member_info 时序问题
 - updated_at : 2026-06-05
 - path: docs/history-bugs/2026-06-05-agent-member-info-init-timing.md
 - 触发规则：新建群聊时，Agent.__init__() 在 _generate_and_register_tokens() 之前执行，agent_cwd 缓存为空
 - 内容摘要：agent_token/agent_cwd 在 __init__ 中缓存为空值，后续 token 生成不会更新已创建的 Agent 对象。修复：改为动态 property + get_or_create 默认 cwd=project_path

## Windows asyncio subprocess NotImplementedError
 - updated_at : 2026-06-05
 - path: docs/history-bugs/2026-06-05-windows-asyncio-subprocess-notimplementederror.md
 - 触发规则：Windows 平台创建群聊返回 409 Conflict，实际是 asyncio.create_subprocess_exec() 抛出 NotImplementedError
 - 内容摘要：Windows 的 SelectorEventLoop 不支持 subprocess，必须使用 ProactorEventLoop。uvicorn reload 模式会导致子进程重置事件循环策略。修复：模块顶部设置 WindowsProactorEventLoopPolicy + 禁用 reload 模式
