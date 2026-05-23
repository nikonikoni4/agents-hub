# Codex CLI 与 Codex Python SDK 能力对比研究

**研究日期**: 2026-05-23  
**目标路径**: `D:\desktop\软件开发\agents-hub\docs\temp\研究报告\codex-sdk-vs-agentshub-cli-bridge.md`  
**当前落盘位置**: `D:\tmp\codex-sdk-vs-agentshub-cli-bridge.md`  
**说明**: 当前执行环境拒绝直接写入 `D:\desktop\软件开发\agents-hub`，因此先将完整报告写入可写目录 `D:\tmp`。

---

## 一、研究目标

本报告对比两类 Codex 集成方式：

1. **Codex CLI**：直接调用本地 `codex` 命令，包括交互式 TUI、非交互 `exec`、`review`、`login`、`mcp`、`plugin`、`app-server`、`doctor`、`sandbox` 等命令。
2. **Codex Python SDK**：使用 `openai_codex` 包，通过 `codex app-server --listen stdio://` 与本地 Codex app-server 进行 JSON-RPC v2 通信。

研究问题不是单纯判断“CLI 和 SDK 谁更好”，而是明确：

- Codex CLI 本身能做什么。
- Codex Python SDK 能做什么。
- 两者分别适合哪些集成场景。
- 对 agents-hub 这类多 agent 平台而言，当前 CLI bridge 与未来 SDK backend 的边界在哪里。

---

## 二、证据来源

### 2.1 本机 CLI help 输出

本次直接执行了以下命令，提取本机安装的 Codex CLI 能力面：

```powershell
codex --help
codex exec --help
codex exec resume --help
codex app-server --help
codex login --help
codex resume --help
codex review --help
codex exec review --help
codex mcp --help
codex plugin --help
codex doctor --help
codex sandbox --help
```

### 2.2 Codex Python SDK 本地源码和文档

参考上游 Codex 仓库中的：

```text
sdk/python/README.md
sdk/python/docs/api-reference.md
sdk/python/src/openai_codex/__init__.py
sdk/python/src/openai_codex/api.py
sdk/python/src/openai_codex/client.py
```

### 2.3 agents-hub 当前上下文

参考 agents-hub 现有实现和文档：

```text
agents_hub/agent_bridge/executors/codex.py
agents_hub/agent_bridge/parsers/codex.py
agents_hub/agent_bridge/bridge.py
agents_hub/agent_bridge/config.py
docs/specs/2026-05-23-agent-bridge.md
docs/design-decisions/2026-05-23-codex-system-prompt-strategy.md
docs/design-decisions/2026-05-23-agent-bridge-output-and-session-strategy.md
docs/temp/研究报告/codex-cli-resume-usage.md
```

---

## 三、Codex CLI 能力总览

本机 `codex --help` 显示，Codex CLI 不只是一个对话入口，而是一组本地开发工具命令集合。

### 3.1 顶层命令

| 命令 | 能力 | 适合场景 |
| ---- | ---- | ---- |
| `codex [PROMPT]` | 启动交互式 CLI / TUI，会把选项转发给 interactive CLI | 人类直接使用 |
| `codex exec` | 非交互执行 Codex agent | 脚本、CI、外部系统集成 |
| `codex review` | 非交互代码审查 | 本地审查、CI 审查入口 |
| `codex login` | 登录管理 | 用户认证配置 |
| `codex logout` | 删除本地认证凭据 | 退出账号 |
| `codex mcp` | 管理外部 MCP server | 工具生态配置 |
| `codex plugin` | 管理 Codex 插件 | 插件安装、市场配置 |
| `codex mcp-server` | 以 stdio 方式启动 Codex MCP server | 被其他 MCP client 调用 |
| `codex app-server` | 启动 app-server 或相关 tooling | SDK、IDE、远程控制、协议生成 |
| `codex remote-control` | 管理启用 remote control 的 app-server daemon | 长驻远程/后台控制 |
| `codex app` | 启动 Codex desktop app | 桌面端入口 |
| `codex completion` | 生成 shell completion | 终端体验 |
| `codex update` | 更新 Codex | 本地版本管理 |
| `codex doctor` | 诊断安装、配置、认证、运行时健康 | 支持排障和自动诊断 |
| `codex sandbox` | 在 Codex 提供的 sandbox 内运行命令 | 调试 sandbox 能力 |
| `codex debug` | 调试工具集合 | Codex 内部/高级调试 |
| `codex apply` | 应用 Codex agent 最近生成的 diff | 人类工作流里的补丁应用 |
| `codex resume` | 恢复交互式会话 | 人类继续 TUI 会话 |
| `codex fork` | fork 交互式会话 | 人类基于历史会话分叉 |
| `codex cloud` | 浏览 Codex Cloud 任务并本地应用 | 云任务衔接 |
| `codex exec-server` | 运行 standalone exec-server service | 实验性执行服务 |
| `codex features` | 查看 feature flags | 功能开关排查 |

### 3.2 顶层通用配置能力

顶层和多个子命令都支持：

| 参数 | 能力 |
| ---- | ---- |
| `-c, --config key=value` | 覆盖 `$CODEX_HOME/config.toml` 中的配置，支持 dotted path，值按 TOML 解析 |
| `--enable <FEATURE>` | 等价于 `-c features.<name>=true` |
| `--disable <FEATURE>` | 等价于 `-c features.<name>=false` |
| `--strict-config` | config.toml 中存在当前版本不认识的字段时直接报错 |
| `-m, --model <MODEL>` | 指定模型 |
| `--oss` | 使用开源 provider |
| `--local-provider <lmstudio|ollama>` | 指定本地 provider |
| `-p, --profile <CONFIG_PROFILE>` | 使用 config.toml 内定义的 profile |
| `--profile-v2 <CONFIG_PROFILE_V2>` | 叠加 `$CODEX_HOME/<name>.config.toml` |
| `-s, --sandbox <MODE>` | 指定 sandbox：`read-only`、`workspace-write`、`danger-full-access` |
| `--dangerously-bypass-approvals-and-sandbox` | 跳过审批和 sandbox，极高风险 |
| `--dangerously-bypass-hook-trust` | 跳过 hook trust，极高风险 |
| `-C, --cd <DIR>` | 指定 agent 工作根目录 |
| `--add-dir <DIR>` | 添加额外可写目录 |
| `-a, --ask-for-approval <POLICY>` | 指定审批策略：`untrusted`、`on-failure`、`on-request`、`never` |
| `--search` | 启用 live web search |
| `-i, --image <FILE>` | 附加图片 |

这些能力对集成方很重要，因为 CLI 本身已经暴露了大量 runtime 控制，不一定需要 SDK 才能做到配置覆盖、模型选择、工作目录、sandbox 或 web search。

---

## 四、Codex CLI 的非交互执行能力

### 4.1 `codex exec`

`codex exec` 是脚本和外部系统最关键的 CLI 入口。

用法：

```powershell
codex exec [OPTIONS] [PROMPT]
```

能力：

| 能力 | 参数或行为 |
| ---- | ---- |
| 非交互执行 | 不进入 TUI，适合脚本调用 |
| 从参数传 prompt | `codex exec "do something"` |
| 从 stdin 传 prompt | prompt 为空或 `-` 时从 stdin 读 |
| prompt + stdin 合并 | stdin 被 append 为 `<stdin>` block |
| 输出 JSONL 事件 | `--json` |
| 输出最后消息到文件 | `-o, --output-last-message <FILE>` |
| 附加图片 | `-i, --image <FILE>` |
| 指定模型 | `-m, --model <MODEL>` |
| 指定 cwd | `-C, --cd <DIR>` |
| 额外可写目录 | `--add-dir <DIR>` |
| 跳过 Git repo 检查 | `--skip-git-repo-check` |
| 临时会话不落盘 | `--ephemeral` |
| 不读用户 config | `--ignore-user-config`，但 auth 仍使用 `CODEX_HOME` |
| 不读 rules | `--ignore-rules` |
| 结构化输出约束 | `--output-schema <FILE>` |
| 控制颜色 | `--color always|never|auto` |

对 agents-hub 来说，当前最核心的命令是：

```powershell
codex exec --json <PROMPT>
```

### 4.2 `codex exec resume`

`codex exec resume` 是非交互继续会话入口。

用法：

```powershell
codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]
```

关键能力：

| 能力 | 参数或行为 |
| ---- | ---- |
| 恢复指定会话 | `codex exec resume <SESSION_ID> <PROMPT>` |
| 恢复最近会话 | `--last` |
| 显示全部会话候选 | `--all`，禁用 cwd filtering |
| 从 stdin 读继续 prompt | prompt 为 `-` |
| 输出 JSONL 事件 | `--json` |
| 附加图片 | `-i, --image <FILE>` |
| 临时执行 | `--ephemeral` |
| 忽略用户 config/rules | `--ignore-user-config` / `--ignore-rules` |
| 结构化输出 | `--output-schema <FILE>` |

这条命令适合外部系统恢复会话，不应该和顶层 `codex resume` 混淆。

### 4.3 `codex resume`

`codex resume` 是交互式会话恢复入口。

用法：

```powershell
codex resume [OPTIONS] [SESSION_ID] [PROMPT]
```

它的定位是人类继续 TUI 会话：

| 能力 | 参数或行为 |
| ---- | ---- |
| 默认打开 picker | 不传 session 时展示交互选择器 |
| 恢复最近交互会话 | `--last` |
| 包含非交互会话 | `--include-non-interactive` |
| 远程 app-server | `--remote <ADDR>` |
| 工作目录 | `-C, --cd <DIR>` |
| 交互审批 | `-a, --ask-for-approval` |

对 agents-hub 这类外部进程集成，应该优先使用 `codex exec resume`，避免进入 TUI 阻塞。

---

## 五、Codex CLI 的代码审查能力

### 5.1 `codex review`

`codex review` 是顶层非交互代码审查入口。

用法：

```powershell
codex review [OPTIONS] [PROMPT]
```

能力：

| 参数 | 能力 |
| ---- | ---- |
| `--uncommitted` | 审查 staged、unstaged、untracked changes |
| `--base <BRANCH>` | 审查相对 base branch 的变更 |
| `--commit <SHA>` | 审查某个 commit 引入的变更 |
| `--title <TITLE>` | 自定义审查摘要标题 |
| `[PROMPT]` 或 `-` | 自定义审查指令，`-` 从 stdin 读 |

### 5.2 `codex exec review`

`codex exec review` 是 `exec` 子命令下的代码审查入口，能力更贴近非交互 agent 执行。

额外支持：

| 参数 | 能力 |
| ---- | ---- |
| `--json` | 输出 JSONL 事件 |
| `-m, --model` | 指定模型 |
| `--ephemeral` | 不持久化 session |
| `--ignore-user-config` | 不加载用户 config |
| `--ignore-rules` | 不加载 rules |
| `--output-schema <FILE>` | 约束最终输出 JSON schema |
| `-o, --output-last-message <FILE>` | 输出最后消息到文件 |

如果 agents-hub 未来要做“代码审查 agent”，不必让普通 prompt 自己解释 diff；CLI 已经提供了专门的 review 入口。

---

## 六、Codex CLI 的配置、认证、MCP、插件和诊断能力

### 6.1 登录能力

`codex login` 支持：

| 命令或参数 | 能力 |
| ---- | ---- |
| `codex login status` | 查看登录状态 |
| `--with-api-key` | 从 stdin 读取 API key |
| `--with-access-token` | 从 stdin 读取 access token |
| `--device-auth` | 使用设备认证 |
| `codex logout` | 删除本地认证凭据 |

这说明 CLI 自身可以完成认证管理；SDK 则把登录能力放进 Python API。

### 6.2 MCP 管理能力

`codex mcp` 支持：

| 子命令 | 能力 |
| ---- | ---- |
| `list` | 列出 MCP server |
| `get` | 查看单个 MCP server |
| `add` | 添加 MCP server |
| `remove` | 删除 MCP server |
| `login` | MCP server 登录 |
| `logout` | MCP server 登出 |

这属于 Codex 本地配置管理面。当前 Python SDK 高层 API 没有显式暴露同等 MCP 管理接口。

### 6.3 Plugin 管理能力

`codex plugin` 支持：

| 子命令 | 能力 |
| ---- | ---- |
| `add` | 从 marketplace snapshot 安装插件 |
| `list` | 列出 marketplace 中可用插件 |
| `marketplace` | 添加、列出、升级、删除 plugin marketplace |
| `remove` | 从本地 config/cache 删除已安装插件 |

这属于 CLI 管理面能力。SDK 目前主要面向 app-server 线程/turn，不是插件 marketplace 管理工具。

### 6.4 Doctor 诊断能力

`codex doctor` 用于诊断本地安装、配置、认证和运行时健康。

关键参数：

| 参数 | 能力 |
| ---- | ---- |
| `--json` | 输出脱敏后的机器可读报告 |
| `--summary` | 只显示分组检查和最终摘要 |
| `--all` | 展开详细列表 |
| `--no-color` | 禁用 ANSI color |
| `--ascii` | 使用 ASCII 状态标签和分隔符 |

对 agents-hub 来说，`doctor --json` 很适合做“Codex 环境检查”功能，而不是自己重新探测所有配置。

### 6.5 Sandbox 调试能力

`codex sandbox` 支持按平台运行命令：

| 子命令 | 能力 |
| ---- | ---- |
| `macos` / `seatbelt` | macOS Seatbelt sandbox |
| `linux` / `landlock` | Linux sandbox / bubblewrap |
| `windows` | Windows restricted token sandbox |

这是 sandbox 调试工具，不等同于 agent turn 的审批和 sandbox 策略，但有助于排查平台 sandbox 行为。

---

## 七、Codex app-server 与远程控制能力

### 7.1 `codex app-server`

`codex app-server` 是 SDK 和 IDE 类集成的基础。

用法：

```powershell
codex app-server [OPTIONS] [COMMAND]
```

支持子命令：

| 子命令 | 能力 |
| ---- | ---- |
| `daemon` | 管理本地 app-server daemon |
| `proxy` | 将 stdio bytes 代理到运行中的 app-server control socket |
| `generate-ts` | 生成 TypeScript protocol bindings |
| `generate-json-schema` | 生成 app-server protocol JSON Schema |

关键参数：

| 参数 | 能力 |
| ---- | ---- |
| `--listen <URL>` | 指定 transport：`stdio://`、`unix://`、`unix://PATH`、`ws://IP:PORT`、`off` |
| `--analytics-default-enabled` | 控制 app-server analytics 默认行为 |
| `--ws-auth <MODE>` | websocket auth：`capability-token` 或 `signed-bearer-token` |
| `--ws-token-file <PATH>` | capability-token 文件 |
| `--ws-token-sha256 <HEX>` | capability token hash |
| `--ws-shared-secret-file <PATH>` | signed JWT bearer token shared secret |
| `--ws-issuer` / `--ws-audience` | JWT issuer / audience |

Python SDK 默认使用：

```text
codex app-server --listen stdio://
```

### 7.2 CLI 与 SDK 的关系

Python SDK 并不是绕过 CLI runtime。它仍然依赖 Codex runtime，只是把交互方式从 CLI JSONL 输出变成 app-server JSON-RPC：

```text
CLI exec path:
  Python/Node/外部系统 -> codex exec --json -> JSONL stdout

SDK path:
  Python SDK -> codex app-server --listen stdio:// -> JSON-RPC v2 -> typed objects
```

---

## 八、Codex Python SDK 能力总览

Codex Python SDK 是实验性 SDK，包名 `openai-codex`，导入名 `openai_codex`。

它的 README 明确说明：

- 面向 `codex app-server` JSON-RPC v2。
- 通过 stdio 与 app-server 通信。
- 发布包会 pin 同版本的 `openai-codex-cli-bin` runtime。
- Python 要求 `>=3.10`。

### 8.1 启动与配置

SDK 的 `AppServerConfig` 支持：

| 字段 | 能力 |
| ---- | ---- |
| `codex_bin` | 指定 Codex binary 路径 |
| `launch_args_override` | 完全覆盖启动参数 |
| `config_overrides` | 传递 `--config key=value` 覆盖项 |
| `cwd` | 设置 app-server 进程工作目录 |
| `env` | 设置 app-server 子进程环境变量 |
| `client_name` / `client_title` / `client_version` | 初始化握手中的 client info |
| `experimental_api` | 初始化时声明 experimental API capability |

SDK 会继承当前 Python 进程环境，并叠加 `AppServerConfig.env`。

因此，如果 agents-hub 使用 SDK，仍可通过：

```python
AppServerConfig(env={"CODEX_HOME": role.codex_home})
```

延续独立 `CODEX_HOME profile` 方案。

### 8.2 高层客户端

SDK 导出：

| 类 | 能力 |
| ---- | ---- |
| `Codex` | 同步高层 client，构造时启动并 initialize |
| `AsyncCodex` | 异步高层 client，推荐 `async with` 使用 |

高层方法包括：

| 方法 | 能力 |
| ---- | ---- |
| `metadata` | 读取 initialize response |
| `close()` | 关闭 app-server |
| `login_api_key()` | API key 登录 |
| `login_chatgpt()` | 浏览器 ChatGPT 登录 |
| `login_chatgpt_device_code()` | 设备码登录 |
| `account()` | 读取账号状态 |
| `logout()` | 清除账号 session |
| `models()` | 获取模型列表 |

### 8.3 Thread 生命周期

SDK 的主要会话抽象是 `Thread`。

| 方法 | 能力 |
| ---- | ---- |
| `thread_start(...)` | 创建新 thread |
| `thread_list(...)` | 列出 thread |
| `thread_resume(thread_id, ...)` | 恢复 thread |
| `thread_fork(thread_id, ...)` | fork thread |
| `thread_archive(thread_id)` | 归档 thread |
| `thread_unarchive(thread_id)` | 取消归档 |

`Thread` 对象提供：

| 方法 | 能力 |
| ---- | ---- |
| `run(input, ...)` | 启动 turn 并等待完成，返回 `TurnResult` |
| `turn(input, ...)` | 启动 turn，返回 `TurnHandle` |
| `read(include_turns=False)` | 读取 thread |
| `set_name(name)` | 设置 thread 名称 |
| `compact()` | 启动 thread compact |

### 8.4 Turn 执行与控制

`TurnHandle` 提供：

| 方法 | 能力 |
| ---- | ---- |
| `stream()` | 只消费当前 turn id 的 notification |
| `run()` | 对已有 turn handle 收集到完成 |
| `steer(input)` | 向运行中的 turn 追加 steering 输入 |
| `interrupt()` | 中断运行中的 turn |

`TurnResult` 包含：

| 字段 | 说明 |
| ---- | ---- |
| `id` | turn id |
| `status` | turn 状态 |
| `error` | turn error |
| `started_at` | Unix seconds |
| `completed_at` | Unix seconds |
| `duration_ms` | 持续时间 |
| `final_response` | 最终回复文本 |
| `items` | 完整 thread items |
| `usage` | token usage |

### 8.5 输入类型

SDK 支持：

| 类型 | 能力 |
| ---- | ---- |
| `TextInput` | 文本输入 |
| `ImageInput` | 远程图片 URL |
| `LocalImageInput` | 本地图片路径 |
| `SkillInput` | skill 引用 |
| `MentionInput` | mention 引用 |
| `str` | 作为 `TextInput` 简写 |

### 8.6 底层 JSON-RPC client

SDK 还提供更底层的 `AppServerClient` / `AsyncAppServerClient`。

底层能力包括：

| 方法 | 能力 |
| ---- | ---- |
| `request(method, params, response_model=...)` | 发送 typed JSON-RPC request |
| `notify(method, params)` | 发送 notification |
| `next_notification()` | 读取全局 notification |
| `account_login_start/cancel/read/logout` | 账号相关 RPC |
| `thread_start/resume/list/read/fork/archive/unarchive/set_name/compact` | thread RPC |
| `turn_start/interrupt/steer` | turn RPC |
| `model_list` | 模型列表 |
| `request_with_retry_on_overload` | overload retry |
| `wait_for_turn_completed` | 等待 turn 完成 |
| `stream_text` | 文本 delta 简化 stream |

### 8.7 错误与重试

SDK 导出：

| 错误类型 | 说明 |
| ---- | ---- |
| `AppServerError` | SDK 基础错误 |
| `TransportClosedError` | app-server transport 关闭 |
| `JsonRpcError` | JSON-RPC 错误 |
| `ParseError` | JSON-RPC parse error |
| `InvalidRequestError` | invalid request |
| `MethodNotFoundError` | method not found |
| `InvalidParamsError` | invalid params |
| `InternalRpcError` | internal error |
| `ServerBusyError` | overload，可重试 |
| `RetryLimitExceededError` | retry limit exceeded |

并提供：

```python
retry_on_overload(...)
is_retryable_error(exc)
```

---

## 九、CLI 能力与 SDK 能力对比

### 9.1 总体定位

| 维度 | Codex CLI | Codex Python SDK |
| ---- | ---- | ---- |
| 主要定位 | 人类终端工具 + 自动化命令集合 | Python 程序内 app-server typed client |
| 协议形态 | 命令行参数 + stdout/stderr + JSONL | JSON-RPC v2 over stdio |
| 运行时入口 | `codex` 子命令 | `codex app-server --listen stdio://` |
| 是否实验性 | 多数 CLI 主命令是正式入口，部分命令标 experimental | README 标注 Experimental |
| 对 humans 友好 | 高 | 低 |
| 对 Python 程序类型友好 | 中 | 高 |

### 9.2 执行能力

| 能力 | CLI | SDK |
| ---- | ---- | ---- |
| 新建任务/turn | `codex exec <PROMPT>` | `thread_start()` + `thread.run()` |
| 恢复会话 | `codex exec resume <SESSION_ID>` | `thread_resume(thread_id)` |
| 交互式恢复 | `codex resume` | 不面向 TUI |
| 流式输出 | `--json` 输出 JSONL | `TurnHandle.stream()` typed notifications |
| 非流式结果 | `--output-last-message` 或解析 JSONL | `TurnResult.final_response` |
| stdin prompt | 支持 | 由调用方传字符串或输入对象 |
| 图片输入 | `--image` | `ImageInput` / `LocalImageInput` |
| 结构化输出 | `--output-schema <FILE>` | `output_schema` 参数 |
| 临时不落盘 | `--ephemeral` | `thread_start(ephemeral=...)`，turn 层能力依协议参数 |

### 9.3 会话和线程能力

| 能力 | CLI | SDK |
| ---- | ---- | ---- |
| 列出会话 | TUI resume picker / app-server API 间接 | `thread_list()` |
| 读取 thread 内容 | CLI 不直接作为高层稳定 API 暴露 | `thread.read(include_turns=True)` |
| fork 会话 | `codex fork`，偏交互 | `thread_fork()` |
| 归档 / 取消归档 | CLI 顶层未在 help 中暴露同等命令 | `thread_archive()` / `thread_unarchive()` |
| 设置 thread 名称 | CLI 中不明显 | `thread.set_name()` |
| compact thread | CLI 中不明显 | `thread.compact()` |

### 9.4 控制面能力

| 能力 | CLI | SDK |
| ---- | ---- | ---- |
| 中断 turn | 外部可 kill 进程，但不是语义化 turn interrupt | `TurnHandle.interrupt()` |
| steer turn | CLI exec 模型不适合对运行中 turn 追加输入 | `TurnHandle.steer()` |
| 多 active turn 路由 | 多进程自行管理 | SDK 按 turn id 路由 notifications |
| 账号状态 | `codex login status` | `account()` |
| 登录 | `codex login` 参数 | `login_api_key()` / `login_chatgpt()` / device code |
| 模型列表 | CLI help 中未见直接 `models` 命令 | `models()` |
| retry overload | 调用方自行解析 stderr/exit code | `retry_on_overload()` 和 typed errors |

### 9.5 配置与环境

| 能力 | CLI | SDK |
| ---- | ---- | ---- |
| 读取 `CODEX_HOME/config.toml` | 默认读取 | app-server 默认读取 |
| 指定 `CODEX_HOME` | 子进程 env 注入 | `AppServerConfig.env` 注入 |
| 覆盖 config | `--config key=value` | `AppServerConfig.config_overrides` 或 start/turn params |
| 忽略用户 config | `--ignore-user-config` | 高层 SDK 未直接暴露；可用 launch args override 或低层方式研究 |
| 忽略 rules | `--ignore-rules` | 高层 SDK 未直接暴露 |
| profile | `--profile` / `--profile-v2` | 可通过 `config_overrides` 或 launch args override 间接处理 |
| cwd | `-C, --cd` | `AppServerConfig.cwd` 和 thread/turn `cwd` |
| sandbox | `--sandbox` | `thread_start(sandbox=...)` / `turn(..., sandbox_policy=...)` |
| approval policy | `--ask-for-approval` | `ApprovalMode` 简化为 `auto_review` / `deny_all`，低层可用生成类型 |

### 9.6 管理工具能力

| 能力 | CLI | SDK |
| ---- | ---- | ---- |
| MCP server 管理 | `codex mcp list/get/add/remove/login/logout` | 高层 SDK 未暴露 |
| Plugin 管理 | `codex plugin add/list/marketplace/remove` | 高层 SDK 未暴露 |
| Doctor 诊断 | `codex doctor --json` | 高层 SDK 未暴露 |
| Sandbox 单独调试 | `codex sandbox ...` | 高层 SDK 未暴露 |
| Completion/update/apply/cloud/features | CLI 提供 | 高层 SDK 未暴露 |
| app-server protocol schema 生成 | `codex app-server generate-*` | SDK 消费 schema，不负责 CLI 工具生成 |

---

## 十、对 agents-hub 的意义

### 10.1 当前 CLI Bridge 已经覆盖的能力

agents-hub 当前使用的是 Codex CLI 的最小非交互执行子集：

```text
codex exec --json <PROMPT>
codex exec resume --json <SESSION_ID> <PROMPT>
```

当前已经能做到：

| 能力 | 当前状态 |
| ---- | ---- |
| 新会话执行 | 已实现 |
| 恢复会话 | 已实现 |
| JSONL 流式解析 | 已实现基础版本 |
| 文本结果拼接 | 已实现 |
| tool_use 基础解析 | 已解析 `command_execution` |
| usage 提取 | 已解析 `turn.completed` |
| `CODEX_HOME` profile 隔离 | 已实现 env 注入 |
| Claude / Codex 统一 Executor + Parser 架构 | 已实现 |

这说明当前并不是“CLI 能力不足”，而是 agents-hub 目前只使用了 CLI 的一小部分能力。

### 10.2 CLI Bridge 可以继续扩展的能力

在不迁移 SDK 的前提下，agents-hub 仍可扩展：

| 方向 | CLI 能力 |
| ---- | ---- |
| cwd 支持 | 加 `-C, --cd <DIR>` |
| 模型选择 | 加 `-m, --model <MODEL>` |
| sandbox 选择 | 加 `--sandbox <MODE>` |
| approval 策略 | 加 `--ask-for-approval <POLICY>` |
| web search | 加 `--search` |
| 临时会话 | 加 `--ephemeral` |
| 忽略用户配置 | 加 `--ignore-user-config` |
| 忽略 rules | 加 `--ignore-rules` |
| 结构化输出 | 加 `--output-schema <FILE>` |
| 审查 agent | 使用 `codex exec review --json` |
| 环境诊断 | 使用 `codex doctor --json` |
| MCP 管理 | 包装 `codex mcp` |
| Plugin 管理 | 包装 `codex plugin` |

因此，短期如果只是增强 agents-hub 的角色执行能力，CLI 路线仍然有很大空间。

### 10.3 SDK 能带来的新增能力

SDK 对 agents-hub 的新增价值主要不是“能不能执行 prompt”，而是：

1. **更结构化的线程/turn 生命周期**：`thread_list`、`thread_read`、`thread_archive`、`thread_fork`、`compact`。
2. **运行中控制**：`interrupt()`、`steer()`。
3. **更完整事件模型**：typed `Notification` / `ThreadItem`，不必自己维护 CLI JSONL parser。
4. **账号与模型控制面**：`account()`、`models()`、登录 handle。
5. **错误类型化**：JSON-RPC typed errors 和 overload retry。
6. **app-server 长连接模型**：适合 IDE / 后台服务 / 多 turn 控制台。

这些能力适合 agents-hub 未来从“调用 CLI 的执行层”走向“管理 agent 运行态”的阶段。

---

## 十一、路线选择分析

### 11.1 路线 A：继续扩展 CLI Bridge

内容：继续以 `codex exec --json` 为默认 Codex 后端，逐步包装更多 CLI 参数和管理命令。

优势：

- 和当前架构完全一致。
- 和 Claude CLI 接入方式一致。
- 依赖少，部署简单。
- 能覆盖大部分 MVP 需求。
- 能直接复用 Codex CLI 的 review、doctor、mcp、plugin 等管理命令。

劣势：

- 需要维护 CLI JSONL parser。
- 运行中 turn 控制弱。
- 错误语义主要靠 exit code / stderr / JSONL 事件推断。
- 每次调用倾向于新进程，长期服务效率不如 app-server client。

适合：

- MVP 阶段。
- A2A 子任务调用。
- 简单多轮会话。
- 环境隔离优先、依赖控制优先的场景。

### 11.2 路线 B：迁移到 Codex SDK 作为默认后端

内容：用 `openai_codex.AsyncCodex` 替换当前 `CodexExecutor`，通过 app-server JSON-RPC 管理 thread/turn。

优势：

- 线程/turn 模型完整。
- 运行中控制能力强。
- Python 类型更清晰。
- 错误分类更好。
- 更适合长期运行的控制台或 IDE 后端。

劣势：

- 引入 `openai-codex`、`pydantic`、`openai-codex-cli-bin` 等依赖。
- SDK 标注 experimental。
- 需要重写 AgentEvent 映射层。
- 需要管理 app-server 生命周期。
- 与 Claude CLI subprocess 模型不一致。
- MCP/plugin/doctor 等 CLI 管理能力仍可能需要继续调用 CLI。

适合：

- 需要 `interrupt` / `steer`。
- 需要 thread list/read/archive/fork/compact。
- 需要内置模型列表、账号状态。
- 需要长期驻留 agent runtime。

### 11.3 路线 C：CLI Bridge 为默认，SDK 作为可选后端

内容：保留当前 CLI backend，新增 `codex_backend = "cli" | "sdk"`，让 SDK 后端先做实验和 parity。

优势：

- 不破坏当前已跑通能力。
- 可以逐步验证 SDK 的 thread_id、事件映射、CODEX_HOME 隔离和并发行为。
- CLI 管理命令仍然可用。
- SDK 能力可以按需引入，而不是一次性迁移。

劣势：

- 双后端会增加测试矩阵。
- 需要定义两套事件映射的一致性边界。
- 需要明确哪些功能只支持 SDK，哪些只支持 CLI。

适合：

- agents-hub 当前阶段。
- 既要保留 MVP 稳定性，又要为未来控制面预留空间。

---

## 十二、现状偏置检查

当前方案是 CLI Bridge。候选替代方案是 SDK backend。

内部上下文证据显示：

- agents-hub 已有 `Executor + Parser` 架构。
- 当前 Codex CLI bridge 已实现 `exec --json` 和 `exec resume --json`。
- 项目已有设计决策把 agent_bridge 定位为纯执行层。
- 项目已有 Codex `CODEX_HOME profile` 隔离策略。

比较性证据显示：

- CLI help 暴露了丰富的非交互、review、doctor、mcp、plugin、sandbox 管理能力。
- SDK API reference 暴露了更强的 thread/turn typed API、interrupt、steer、models、account、typed errors。

反方观点：

- 如果 agents-hub 的目标是做长期运行的多 agent IM 平台，未来需要实时中断、steer、thread 状态读取、账号/模型管理，那么继续只依赖 CLI JSONL 会逐渐吃力。
- CLI JSONL parser 是自维护适配层，Codex 输出格式变化时 agents-hub 需要跟进。

当前不建议立刻迁移 SDK，并不是因为 CLI 在技术上更高级，而是因为：

1. 当前需求主要是纯执行层，CLI 已匹配。
2. CLI 还有大量未利用能力，可以低成本补强。
3. SDK 的优势集中在运行态控制和 typed API，需要产品进入更复杂阶段才充分体现。
4. SDK 迁移会改变运行时模型和依赖结构，不适合作为当前最小路径。

因此，推荐 CLI 作为当前默认路径，是基于迁移经济性和本地约束，而不是断言 CLI 内在优于 SDK。

---

## 十三、建议

### 13.1 短期建议

继续使用 CLI Bridge 作为默认 Codex 接入方式。

优先补齐：

1. `RoleConfig` 增加 cwd/model/sandbox/approval/search/ephemeral 等字段。
2. `CodexExecutor` 映射这些字段到 CLI 参数。
3. 使用 `codex exec review --json` 支持专门的代码审查 agent。
4. 使用 `codex doctor --json` 增加环境诊断能力。
5. 增加单 `CODEX_HOME profile` 单实例锁。
6. 扩展 Codex JSONL parser，覆盖 error、file change、diff、plan、reasoning、token usage 等事件。

### 13.2 中期建议

新增实验性 SDK backend，而不是替换 CLI backend。

建议结构：

```text
agents_hub/agent_bridge/
  executors/
    codex.py          # CLI backend
    codex_sdk.py      # SDK backend
  parsers/
    codex.py          # CLI JSONL -> AgentEvent
    codex_sdk.py      # SDK Notification -> AgentEvent
```

配置：

```python
codex_backend: Literal["cli", "sdk"] = "cli"
```

### 13.3 SDK backend 的验证清单

在把 SDK 设为默认前，至少验证：

1. `CODEX_HOME` profile 隔离是否与 CLI 一致。
2. SDK 的 `thread_id` 是否能恢复 CLI 创建的 session，反向是否成立。
3. SDK notification 是否能完整映射到当前 `AgentEventType`。
4. SDK app-server 生命周期是否会在异常时可靠关闭。
5. 多角色并发时，一个 profile 一个 SDK client 是否安全。
6. SDK 默认 `ApprovalMode.auto_review` 是否符合 agents-hub 权限设计。
7. SDK 与 CLI 共同访问同一 profile 时是否存在状态争用。

---

## 十四、结论

Codex CLI 和 Codex Python SDK 不是简单的替代关系。

CLI 是完整的本地操作入口，覆盖：

- 交互式 TUI。
- 非交互 agent 执行。
- 非交互会话恢复。
- 代码审查。
- 登录/登出。
- MCP 管理。
- Plugin 管理。
- Doctor 诊断。
- Sandbox 调试。
- App-server 启动与 daemon/remote-control/protocol tooling。

SDK 是面向 Python 应用的 app-server typed client，强在：

- Thread / Turn 抽象。
- Typed notifications。
- `TurnResult`。
- `steer()` / `interrupt()`。
- `models()` / `account()`。
- JSON-RPC typed errors。
- 长连接式 app-server 生命周期。

对 agents-hub 当前阶段，最合理的判断是：

```text
默认继续使用 CLI Bridge。
充分利用 CLI 已有参数和管理命令。
把 SDK 作为未来可选 backend，而不是现在全量迁移目标。
```

当 agents-hub 的需求从“调用 agent 执行任务”升级为“管理 agent 运行态和控制面”时，SDK 的价值会明显上升。

