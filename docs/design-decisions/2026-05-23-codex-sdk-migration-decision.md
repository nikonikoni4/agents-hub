---
version: 1.1
created_at: 2026-05-23
updated_at: 2026-05-23
last_updated: 2026-05-23
abstract: 确定 agent_bridge 对 Claude 和 Codex 两个平台继续使用 CLI 子进程方案，不迁移到各自的官方 Python SDK。初始设计时因调研不足未发现 Codex SDK，统一采用 CLI 方案；后续调研发现两个平台均有 SDK（Codex SDK 为实验版，Claude SDK 本质仍是 CLI 封装），重新评估后维持 CLI 方案
status: decided
---

# Agent Bridge 接入方式决策：CLI vs SDK

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿，仅覆盖 Codex 侧 |
| 1.1 | 扩展为 Claude + Codex 双平台决策，补充 Claude Agent SDK 调研结论 |

---

## 问题界定

### 问题简述

agents-hub 最初设计 agent_bridge 时，调研阶段未发现 Codex 存在官方 Python SDK，因此决定 Claude 和 Codex 统一采用 CLI 子进程方案——要么都用 SDK，要么都用 CLI，由于 Codex 没有 SDK，所以都走 CLI。

后续深入调研中发现了：
- **Codex Python SDK**（`openai-codex`，实验版）：通过 `codex app-server --listen stdio://` 的 JSON-RPC v2 通信
- **Claude Agent SDK**（`claude-agent-sdk`）：本质是对 `claude -p` 子进程的 Python 封装

现在需要重新评估：两个平台是否应该从 CLI 迁移到 SDK，还是继续使用 CLI。

### 讨论范围

- Claude CLI 与 Claude Agent SDK 的能力对比
- Codex CLI 与 Codex Python SDK 的能力对比
- 两个平台是否应保持一致的接入方式
- 当前 agent_bridge 定位下的最优接入策略

### 非讨论范围

- agent_bridge 职责边界的重新定义（已在其他决策中确定）
- SDK 的实验性质何时变为稳定版

### 模糊信息的明确定义

- **"统一接入方式"**：指 Claude 和 Codex 两个平台使用同一种技术路径（都是 CLI subprocess，或都是 SDK），而不是各自独立选择。这是初始设计时的核心约束。

### 问题深度

浅层方案选择。不涉及架构原则变更。agent_bridge 的定位（纯执行层）已确定，本次决策只回答"用什么方式调用 Claude 和 Codex"。

---

## 现状

### 初始决策的上下文

初始设计时的推理链：
1. agent_bridge 需要同时支持 Claude 和 Codex 两个平台
2. 两个平台最好使用一致的接入方式（降低维护成本和认知负担）
3. 调研发现 Claude 有 CLI（`claude -p`），Codex 有 CLI（`codex exec --json`）
4. 未发现 Codex 有官方 SDK
5. 因此统一采用 CLI subprocess 方案

这个推理链在当时是合理的，但前提 4 是错误的——Codex 确实有 SDK，只是当时调研遗漏了。

### 当前已确定的约束

1. **agent_bridge 是纯执行层**：负责启动进程、解析原始输出、提供统一调用接口。不承载业务逻辑、会话持久化、错误重试。
2. **Executor-Parser 分离架构已确定**：每个平台各有一个 Executor 和一个 Parser。
3. **CODEX_HOME profile 隔离已成立**：通过子进程环境变量注入实现角色隔离。
4. **当前只用了 CLI 的一小部分能力**：Claude 侧仅用 `claude -p --output-format stream-json`，Codex 侧仅用 `codex exec --json` 和 `codex exec resume --json`。

### 两个 SDK 的事实

| 维度 | Codex Python SDK | Claude Agent SDK |
|------|-----------------|-----------------|
| 包名 | `openai-codex` | `claude-agent-sdk` |
| 成熟度 | **实验性**（README 标注 Experimental） | 正式发布 |
| 底层机制 | 启动 `codex app-server --listen stdio://`，JSON-RPC v2 | 启动 `claude -p` 子进程，JSON 协议 |
| 本质 | 新的运行时模型（长驻 app-server） | CLI 的 Python 语法糖（仍走子进程） |
| 引入依赖 | `openai-codex`、`pydantic`、`openai-codex-cli-bin` | `claude-agent-sdk`（CLI 已内置） |
| 核心增量能力 | `interrupt()`、`steer()`、`thread_list()`、`models()`、`account()`、typed errors | `@tool` 自定义工具、`AgentDefinition` 子代理、会话持久化适配器、`HookMatcher` |
| 对 CLI 的替代性 | 本质性变化（长驻连接 vs 每次启动进程） | 形式性变化（仍是子进程，只是解析层换了） |

### 关键差异

**Claude SDK 不改变运行时模型**：它内部仍然启动 `claude -p` 子进程，只是把 JSON 流解析换成了类型化消息。迁移 Claude 侧到 SDK，本质上只是换了 parser，没有获得新的运行时能力。

**Codex SDK 改变运行时模型**：它启动长驻 app-server，支持 thread/turn 生命周期、中断/转向、长连接复用。这是一个本质性的能力提升，但代价是引入实验性依赖和新的生命周期管理。

---

## 可选方案

### 方案 A：两个平台都继续使用 CLI Bridge

保持当前方案：Claude 用 `claude -p --output-format stream-json`，Codex 用 `codex exec --json`。

**优势**

- 与当前架构完全一致，零迁移成本
- 两个平台接入方式一致，维护成本低
- 无新运行时依赖
- CLI 还有大量未利用能力可低成本补强
- 符合 agent_bridge 纯执行层定位

**劣势**

- 需要维护两个 CLI 的输出 parser
- 运行中 turn 控制能力弱
- 错误类型化程度低
- 每次调用启动新进程

### 方案 B：两个平台都迁移到 SDK

Claude 用 `claude-agent-sdk`，Codex 用 `openai-codex`。

**优势**

- 两个平台都用类型化 Python API
- Codex 侧获得 interrupt/steer/thread 生命周期能力
- Claude 侧获得自定义工具、子代理、Hook 能力

**劣势**

- 引入两个新依赖（其中 Codex SDK 为实验性）
- Codex SDK 需要管理 app-server 生命周期
- Claude SDK 本质仍是子进程，收益有限
- 两个 SDK 的 API 模型完全不同，反而不如 CLI 方案统一
- 迁移成本高

### 方案 C：CLI 为默认，按需为单个平台引入 SDK 后端

保留 CLI 作为默认后端，当某个平台确实需要 SDK 能力时，只为该平台新增 SDK 后端。

**优势**

- 不破坏当前能力
- 可以不对称地演进（Codex 侧可能先需要 SDK）
- 保持灵活性

**劣势**

- 双后端增加测试矩阵
- 两个平台的接入方式可能变得不一致

---

## 最终决策

选择 **方案 A：两个平台都继续使用 CLI Bridge**。

---

## 决策原因

1. **agent_bridge 是纯执行层**：当前需求是"发 prompt、收文本、记录 session_id、恢复会话"，CLI exec 路径完全覆盖。不需要 SDK 提供的运行态管理能力。

2. **Claude SDK 没有本质收益**：`claude-agent-sdk` 本质是对 `claude -p` 的 Python 封装，内部仍走子进程。迁移只是换了 parser，没有获得新能力，反而引入额外依赖。

3. **Codex SDK 是实验性的**：`openai-codex` 标注 Experimental，引入后可能面临 API 变更和稳定性问题。其核心增量能力（interrupt/steer/thread 生命周期）不在当前需求范围内。

4. **CLI 能力远未用尽**：两个平台的 CLI 都有大量未使用的参数和子命令（cwd、model、sandbox、review、doctor 等），可以通过透传参数低成本补强。

5. **两个 SDK 的 API 模型完全不同**：如果迁移，Claude SDK 和 Codex SDK 的接口形态差异很大，反而不如 CLI 方案在结构上统一（都是 subprocess + stdout 解析）。

6. **"统一接入方式"的初始约束仍然成立**：两个平台都用 CLI，架构一致，维护成本低。如果只为一个平台迁移到 SDK，会打破这种一致性，增加认知负担。

---

## 后续影响

### 短期行动

- `RoleConfig` 扩展字段：cwd、model、sandbox、approval、search、ephemeral
- `CodexExecutor` / `ClaudeCodeExecutor` 透传这些 CLI 参数
- 使用 `codex exec review --json` 支持代码审查 agent
- 使用 `codex doctor --json` 增加环境诊断能力
- 扩展两个平台的 parser 覆盖更多事件
- 单 `CODEX_HOME` profile 单实例锁

### 需要使用 SDK 的触发场景

当出现以下任一条件时，应重新评估并为**对应平台**启动 SDK 后端开发：

| 触发条件 | 涉及平台 | 原因 |
|---------|---------|------|
| 需要运行中 turn 的 `interrupt()` / `steer()` | Codex | CLI exec 模型无法对运行中进程做语义化中断/转向 |
| 需要 `thread_list()` / `thread_archive()` / `compact()` | Codex | CLI 不直接暴露这些能力 |
| 需要 `models()` / `account()` 控制面 | Codex | 多模型调度、账号状态管理 |
| 需要长驻进程减少启动开销 | Codex | 高频调用场景 |
| 需要 in-process 自定义工具 (`@tool`) | Claude | 将 agents-hub 能力注册为 Claude 可调用工具 |
| 需要程序化子代理 (`AgentDefinition`) | Claude | 代码级定义专业化子代理 |
| CLI 输出格式频繁变动导致 parser 维护成本过高 | 任一 | SDK 的 typed API 更稳定 |

### 不需要迁移的确认条件

如果长期只使用以下模式，则 CLI Bridge 始终足够：

- 一次 prompt → 一次执行 → 收集结果
- 简单多轮会话（resume session_id）
- A2A 子任务调用（非流式拼接结果）
