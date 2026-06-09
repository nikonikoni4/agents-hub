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

## set_agent_token_and_default_cwd 中 AI 自作主张的目录拼接规则
 - updated_at : 2026-06-05
 - path: docs/history-bugs/2026-06-05-agent-cwd-unspeced-logic.md
 - 触发规则：新建群聊后 Agent 的 cwd 路径末尾多出 `/m`、`/测` 等无意义子目录
 - 内容摘要：spec/plan 未定义 cwd 规则，AI 自行发明「首字母+末尾数字」拼接逻辑导致路径错误。教训：spec 没说的不要自己编。修复：直接使用 project_path 作为 cwd

## AgentCall 状态重复更新导致日志泛滥和 MCP 连接重建
 - updated_at : 2026-06-05
 - path: docs/history-bugs/2026-06-05-agent-call-status-duplicate-logging.md
 - 触发规则：日志中出现大量 "running -> running" 状态变更记录，每次更新触发 MCP transport 重建
 - 内容摘要：AgentCallManager.update_status() 缺少状态检查，即使新旧状态相同也会执行日志记录、持久化和触发下游逻辑。修复：在 update_status 开头检查状态是否变化，相同则跳过更新

## API 路由创建独立 GroupChatManager 实例导致双 Manager 状态分裂
 - updated_at : 2026-06-06
 - path: docs/history-bugs/2026-06-06-api-route-created-separate-group-chat-manager.md
 - 触发规则：API 路由中直接 `GroupChatManager()` 创建新实例而非使用全局单例，导致重启后两套 Agent 并行运行、消息路由分裂
 - 内容摘要：API 路由单独创建 Manager 实例，与 Core 全局单例各自从磁盘加载出独立的 GroupChat，消息投递到错误队列、Token 索引不一致、Agent 重复启动。调试耗时约 6 小时。教训：全局单例需防呆机制，AI 倾向就近实例化

## GroupChatRuntimeState 状态改变与并发问题
 - updated_at : 2026-06-05
 - path: docs/history-bugs/2026-06-05-group-chat-runtime-state-concurrency.md
 - 触发规则：多协程并发访问 GroupChatRuntime 的 command 方法（如 add_message、append_compact_record），或 AgentCallManager 后台清理与主流程竞态
 - 内容摘要：Runtime 层 read-modify-write 序列缺乏锁保护，Repository 层文件锁无法覆盖内存状态竞态。涉及 6 处代码位置，核心方案是在 Runtime 层添加 asyncio.Lock

## 前端侧栏抽屉按钮失效 - 内联样式优先级覆盖 CSS 类
 - updated_at : 2026-06-07
 - path: docs/history-bugs/2026-06-07-sidebar-collapse-inline-style-priority.md
 - 触发规则：点击左侧栏或右侧栏的抽屉按钮，CSS 类正确变化但侧栏宽度不变
 - 内容摘要：LeftSidebar 和 RightSidebar 组件中，内联样式 `width: 220px` 优先级高于 CSS 类的 `width: 0`，导致 collapsed 状态失效。修复：当 collapsed 为 true 时，内联宽度设置为 0

## 角色添加 Skill 后报元数据无效
 - updated_at : 2026-06-07
 - path: docs/history-bugs/2026-06-07-role-skill-metadata-invalid.md
 - 触发规则：前端角色编辑面板添加 Skill 后报 SKILL_METADATA_INVALID，角色卡片不显示已添加的 Skill
 - 内容摘要：list_skills() 查找 skill.json 但实际 Skill 用 SKILL.md 格式；RoleResponse 已包含 skills 字段，前端直接用 getRoleInfo() 读取

## 前端 Mutation 后组件刷新链路断裂
 - updated_at : 2026-06-08
 - path: docs/history-bugs/2026-06-07-frontend-refresh-dependency-gaps.md
 - 触发规则：修改角色头像/描述后，Session 列表群聊头像、消息气泡发言人头像、成员列表头像不刷新；增删群成员后 CompositeAvatar 不刷新
 - 内容摘要：6 个刷新链路断裂问题，根因是缺少跨 feature 刷新协调机制。修复：扩展现有 WebSocketManager.emit() 作为本地事件总线，mutation 成功后触发关联刷新。已修复 5/6 个问题

## Message PIN 后右侧栏不自动刷新
 - updated_at : 2026-06-08
 - path: docs/history-bugs/pin-message-refresh-bug.md
 - 触发规则：群聊中置顶/取消置顶消息后，右侧栏 Pinned 列表不自动更新，必须手动刷新
 - 内容摘要：后端 pin_message 返回 None，前端需要额外 GET 请求。修复：改为 POST 后返回 PinnedMessageInfo，前端直接使用返回数据更新 state

## MCP 创建群聊后发送消息报"接收者未注册"
 - updated_at : 2026-06-08
 - path: docs/history-bugs/2026-06-08-mcp-created-group-chat-message-router-agent-not-registered.md
 - 触发规则：通过 MCP create_group_chat 创建群聊后，在群聊中发送消息偶发报"接收者未注册"。成员已打招呼证明初始化成功，但后续消息路由找不到 agent
 - 内容摘要：偶发 bug，未找到根因。已排除双实例问题（历史 bug 已修复）、显式 cleanup、GC 回收。最可能假设：MCP server 运行在独立进程导致 GroupChatManager 单例分裂，或 activate() 幂等性缺陷。已添加诊断日志（GroupChatManager 实例 ID、MessageRouter 注册状态），待下次复现时定位

## load_group_chat_from_disk 自动激活群聊导致前端加载时启动 agent 任务
 - updated_at : 2026-06-08
 - path: docs/history-bugs/2026-06-08-load-group-chat-auto-activate.md
 - 触发规则：前端加载 session 列表时，调用 getMembers API 触发 load_group_chat_from_disk，自动调用 activate() 启动所有 agent 任务
 - 内容摘要：load_group_chat_from_disk 在加载时自动调用 activate()，违反"只读操作不应有副作用"原则。用户已明确说明"加载不是激活"，但 AI 执行时仍错误地在加载时调用激活。修复：移除 activate() 调用，激活延迟到发送消息时执行

## 单聊双位置显示：API 调用未完全区分单聊/群聊
 - updated_at : 2026-06-09
 - path: docs/history-bugs/2026-06-09-single-chat-dual-location-api-leak.md
 - 触发规则：点击单聊时控制台报 "GroupChat 'xxx' 不存在"，单聊消息显示在主界面而非右侧栏
 - 内容摘要：ChatArea 组件内多个 hook（usePinnedMessages, useMembers, useTasks 等）未根据 activeSessionType 区分，单聊 ID 被传给群聊 API。已缓解部分问题（usePinnedMessages 条件调用），但残留其他 hook 未隔离和 displayLocation 状态竞争问题。待后续彻底修复
