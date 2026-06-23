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

## context_window 持久化丢失 + CLI 解析器遗漏 + 缓存 token 未计入
 - updated_at : 2026-06-10
 - path: docs/history-bugs/2026-06-10-context-window-persistence-and-parsing.md
 - 触发规则：Agent 处理消息后前端 context_window 显示为 0 或不显示
 - 内容摘要：三个独立 bug 叠加：(1) save_agent_member 漏掉 status/context_window 字段，重启后丢失；(2) ClaudeParser 不处理 result 事件，usage 数据被忽略；(3) context_window 只算 input_tokens 漏掉 cache_read_input_tokens，第二次调用 72//1000=0。关键发现：Claude CLI 会话历史走缓存（cache_read），不走 input_tokens

## Manager 工具调用无限循环
 - updated_at : 2026-06-09
 - path: docs/history-bugs/2026-06-09-manager-tool-call-infinite-loop.md
 - 触发规则：Manager agent 处理多步骤任务且需要等待其他 Agent 调用结果时
 - 内容摘要：Manager agent 陷入无限循环，反复执行 TodoWrite 和 Read 工具调用（50+ 次），导致上下文空间被大量重复内容占用（约 150K-180K tokens）。根因是模型的"安全行为"模式和缺乏"已完成"状态感知。TodoWrite 未持久化到 TaskList 也是原因之一。建议：限制工具调用频率、添加 heartbeat 机制、TodoWrite 应持久化

## MCP 多进程访问导致连接冲突和消息卡住
 - updated_at : 2026-06-10
 - path: docs/history-bugs/2026-06-10-mcp-multi-process-connection-conflict.md
 - 触发规则：多个进程同时访问同一个 MCP 服务器，其中一个进程突然中断连接时
 - 内容摘要：多进程同时访问 MCP 服务器时，一个进程突然关闭会导致连接竞争，消息排队但不处理，延迟数分钟。日志中出现 ConnectionResetError 和 OSError [WinError 64]。解决方案：避免多进程同时访问，或实现连接重连机制

## MCP 工具命名导致 Agent 无法正确调用
 - updated_at : 2026-06-10
 - path: docs/history-bugs/2026-06-10-mcp-tool-naming-confusion.md
 - 触发规则：Agent 处理任务时无法正确调用 report_progress 和 finish_agent_call 工具
 - 内容摘要：MCP 工具使用从平台角度编写的名称，Agent 不理解其含义导致调用失败。改名为 report_progress 和 complete_task 后效果改善。后续改进方向：从显式工具调用闭环 → 输出标签识别的降级方案

## 隐藏右侧栏网页预览的地球图标
 - updated_at : 2026-06-10
 - path: docs/history-bugs/2026-06-10-hide-globe-icon-in-web-preview.md
 - 触发规则：右侧栏"网页" tab 中显示地球图标，用户要求隐藏
 - 内容摘要：RightSidebar.tsx 中 webPreviewHeader 包含 GlobeIcon 组件，注释掉该组件即可隐藏图标。GlobeIcon 组件定义保留，WebPreviewCard 中的独立定义不受影响。低风险修改，易于回滚

## GroupChat.activate() 幂等性缺陷导致消息投递失败
 - updated_at : 2026-06-13
 - path: docs/history-bugs/2026-06-13-group-chat-activate-missing-agent-registration.md
 - 触发规则：GroupChat 对象重建后首次发送消息时，MessageRouter 中找不到接收者 agent
 - 内容摘要：activate() 只检查 _activated 实例变量，对象重建后新实例的 MessageRouter 为空但不重新注册 agents。消息投递时抛出 AgentNotFoundError（DEBUG 级别不可见）。修复方案：在 activate() 中强制调用 _register_agents_to_router() 确保注册完成

## Core 模块问题报告（排查记录）
 - updated_at : 2026-06-14
 - path: docs/history-bugs/2026-06-14-core-module-issues.md
 - 触发规则：排查 core 模块在群聊生命周期中的问题
 - 内容摘要：记录 core 模块在群聊生命周期中的问题，包括架构性问题（Runtime/Context 耦合）、群聊创建/列表/详情加载问题、Agent 状态变化流程与问题、Agent 压缩/停止/启动/重置流程问题

## Manager Agent sleep 轮询循环 Bug + 任务回执异步性问题
 - updated_at : 2026-06-14
 - path: docs/history-bugs/2026-06-14-agent-sleep-polling-loop-and-async-receipt.md
 - 触发规则：Manager 调用 report_progress/complete_task 后使用 sleep 轮询等待消息
 - 内容摘要：两个问题：(1) 任务回执异步性 - Manager 处理 CLI 任务时无法同时接收 Worker 回执，存在延迟（非 Bug，架构改进点）；(2) sleep 轮询循环 Bug（严重） - Manager 陷入无限 sleep 10 循环等待消息，实际上消息通过 runtime incoming_message 推送，不需要轮询。修复：调用 complete_task 后直接结束，等待系统推送

## Manager run() 任务静默死亡导致消息队列堆积
 - updated_at : 2026-06-15
 - path: docs/history-bugs/2026-06-14-manager-run-task-silent-death.md
 - 触发规则：stop_member 后 start_member 重启 manager，发送消息给 manager；依次停止所有 Worker 后再停止 Manager
 - 内容摘要：两个相关问题：(1) activate() 幂等性缺陷 Bug 的延续，manager 的 run() 任务静默死亡导致消息堆积，已添加诊断日志；(2) 停止 Worker 后停止 Manager 时，cleanup 流程直接调用 message_router.send_message() 绕过 GroupChat 包装层，导致异常无完整堆栈。违反编码规则（Agent 间通信必须通过控制面），已修复为使用 send_message_to_agent() 包装层并添加异常容错

## broadcast_group_chat_refresh 全链路问题审查
 - updated_at : 2026-06-15
 - path: docs/history-bugs/2026-06-15-broadcast-refresh-full-chain-issues.md
 - 触发规则：后端发送 refresh 信号但前端有时不刷新；前端短时间内大批量重复请求
 - 内容摘要：9 个问题，覆盖后端广播时序、前端请求风暴、WebSocket 可靠性、竞态条件。后端时序正确（先持久化后广播），问题集中在前端和通信层。最高置信度问题：双重广播 base_agent.py:600（85分，DRY 违反）、N+1 广播 group_chat_service.py:1260（85分）。前端单个 refresh 触发 10 个并发请求（6 个冗余），无任何防抖/去重/取消机制。WebSocket 无心跳、断连期间 refresh 丢失、重连后不补拉数据

## Parser 并发竞态导致 session_id 串台（完整报告）
 - updated_at : 2026-06-16
 - path: docs/history-bugs/2026-06-15-parser-concurrency-race-condition.md
 - 触发规则：多个 Codex agent 并发执行（如 asyncio.gather 初始化新成员），agent_member.json 中多个 agent 的 main_session 相同，resume 时报 thread/resume failed: no rollout found
 - 内容摘要：AgentBridge 中 Parser 共享单例在 asyncio 并发环境下导致 session_id 串台。包含：根因分析（4 个原因）、Codex vs Claude Parser 对比、asyncio.gather 顺序验证、修复方案（每次创建独立 parser）、19 个测试验证。修复：移除 `_parsers` 单例字典，添加 `_create_parser()` 方法每次创建新实例

## 群聊删除时文件被占用导致 502 错误
 - updated_at : 2026-06-19
 - path: docs/history-bugs/2026-06-19-group-chat-delete-file-lock.md
 - 触发规则：Windows 环境下删除群聊时 API 返回 502 Bad Gateway，日志显示 [WinError 32] 文件被占用
 - 内容摘要：AgentCallManager 和 TaskManager 的 RotatingFileHandler 未在 cleanup 时关闭，导致 Windows 上 shutil.rmtree 失败。修复：在 AgentCallManager 和 TaskManager 中添加 close() 方法，在 GroupChat.cleanup() 中调用

## 单聊历史记录加载失败 - session_id 未保存
 - updated_at : 2026-06-19
 - path: docs/history-bugs/2026-06-19-single-chat-session-id-not-saved.md
 - 触发规则：用户在单聊 AI 回复未完成时切换聊天，切回来后历史记录为空
 - 内容摘要：两个问题叠加：(1) Codex 解析器的 thread.started 事件不生成 StreamEvent，session_id 获取延迟；(2) session_id 保存延迟到流结束，流中断导致保存操作永远不执行。修复：Codex 生成 INIT 事件 + 获取 session_id 后立即保存到磁盘

## NOTIFICATION 消息在接收方不保存到群聊历史
 - updated_at : 2026-06-19
 - path: docs/history-bugs/2026-06-19-notification-message-not-saved.md
 - 触发规则：所有 Agent 间通过 NOTIFICATION 通信的场景
 - 内容摘要：设计漏洞。_fallback_close_task 只处理 TASK 类型消息，NOTIFICATION 被直接跳过。完整流程：Manager → TASK → Worker → complete_task/兜底保存 + NOTIFICATION → Manager → _fallback_close_task 检查 msg.type != TASK → return，消息不保存。不管 complete_task 是否存在，都没有正式的对于 NOTIFICATION 的回应机制

## Codex stdout 超长单行 JSON 导致 LimitOverrunError
 - updated_at : 2026-06-20
 - path: docs/history-bugs/2026-06-20-codex-stdout-long-json-line-limit.md
 - 触发规则：Codex Agent 执行时报 `Separator is not found, and chunk exceed the limit` 或 `LimitOverrunError`
 - 内容摘要：Codex `--json` 的单行 JSON 可能因 `command_execution.aggregated_output` 超过 asyncio StreamReader limit；`readline`/`readuntil` 都会失败。修复：改用固定 chunk `read()`，自行维护 buffer 按换行切分，并添加超长单行复现测试

## Codex/Claude 进程 wait() 阻塞导致任务无法闭环
 - updated_at : 2026-06-20
 - path: docs/history-bugs/2026-06-20-codex-process-wait-blocking.md
 - 触发规则：Agent 任务一直处于 running 状态，消息无法显示在群聊中，日志最后停留在"等待进程退出"
 - 内容摘要：偶发性 bug（出现频率较高）。CLI 进程 stdout 关闭后，`await process.wait()` 永久阻塞导致任务无法完成。可能原因：进程僵尸、子进程未关闭、Windows asyncio 进程管理问题。修复：添加 30 秒超时，超时后强制 kill 进程。已在 CodexExecutor 和 ClaudeExecutor 中修复

## GroupChat stop_member 成员状态缺失导致 KeyError
 - updated_at : 2026-06-20
 - path: docs/history-bugs/2026-06-20-group-chat-stop-member-missing-member-info.md
 - 触发规则：快速重复停止/启动群聊成员时，停止接口报 `KeyError: '<agent_name>'` 或 API 返回 500
 - 内容摘要：运行态 Agent 对象存在，但 `runtime.agent_member_infos` 中对应成员状态短暂缺失，`stop_member()` 读取状态时抛 KeyError。修复：在 stop 流程中把缺失状态视为可恢复不一致，使用 `get_or_create_agent_member_info()` 恢复状态记录后继续停止和清理

## CLI stdout 流式解码跨块多字节字符截断导致 UnicodeDecodeError
 - updated_at : 2026-06-22
 - path: docs/history-bugs/2026-06-22-stream-decoder-unicode-split-multibyte.md
 - 触发规则：Claude/OpenCode Agent 执行任务，stdout 输出包含多字节 UTF-8 字符（如中文）且字符恰好跨 chunk 边界时
 - 内容摘要：`process.stdout.read(256KB)` 按固定字节数读取后直接 `chunk.decode("utf-8")`，多字节字符被截断在块边界导致 UnicodeDecodeError。位置 131070-131071 是 3 字节中文字符的截断点。修复：用 `codecs.getincrementaldecoder("utf-8")()` 增量解码器替代，自动处理跨块多字节序列。ClaudeExecutor 和 OpenCodeExecutor 已修复

## Loop 详情弹窗滚动失败 - max-height 与 flex 布局冲突
 - updated_at : 2026-06-23
 - path: docs/history-bugs/2026-06-23-loop-modal-scroll-issue.md
 - 触发规则：使用 max-height 限制 flex 容器高度，且容器内有多层嵌套的滚动区域时
 - 内容摘要：LoopDetailModal 左右两侧滚动容器无法触发滚动条，内容溢出。根因：(1) modal 使用 max-height 而非 height，flex 子元素无法获得确定高度；(2) .mainArea 缺少 flex: 1，无法占据剩余空间；(3) .nodeList 设置 flex-shrink: 0，拒绝压缩导致内容撑破容器。修复：使用固定 height、完整的 flex 链条（每层都有 flex: 1 + min-height: 0）、移除 flex-shrink: 0
