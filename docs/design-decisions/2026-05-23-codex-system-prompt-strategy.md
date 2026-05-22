---
version: 1.0
created_at: 2026-05-23
updated_at: 2026-05-23
last_updated: 确定 Codex system prompt 的正式接入策略
abstract: 明确 agents-hub 中 Codex 的 system prompt 不通过修改项目 AGENTS.md 实现，而通过独立 CODEX_HOME profile 派生方案实现跨项目角色注入。
status: decided
---

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

- 问题简述：agents-hub 需要为 Codex 提供一个可跨项目复用的 system prompt / 角色配置方案，同时不能污染用户项目本身。
- 讨论范围：Codex 的角色注入方式、项目 AGENTS.md 与平台 profile 的边界、最小可行实现路径。
- 非讨论范围：Claude / OpenCode 的实现细节、前端 UI、权限审批交互设计。
- 问题深度：这是平台接入层的正式架构决策，会影响后续 Codex agent 的创建、运行和维护方式。

## 现状（当前的问题）

1. Codex 没有公开一个简单的“外部直接传任意 system prompt”CLI 参数可作为正式集成接口。
2. Codex 会读取项目级 AGENTS.md，这使“直接修改项目文件”成为一个看似可用但高侵入的方案。
3. agents-hub 需要的是跨项目的外部角色能力，而不是把平台配置写进某一个项目仓库。
4. 如果平台默认修改项目 AGENTS.md，会导致用户仓库被污染，并在退出产品后留下额外清理成本。

## 可选方案

### 方案一：修改项目内的 AGENTS.md

#### 优势

- 技术接入简单，容易被 Codex 原生指令发现机制读取。
- 不需要额外维护 profile 派生目录。

#### 劣势

- 会修改用户项目资产，污染仓库内容。
- 用户退出 agents-hub 后仍然残留平台相关配置，需要手工恢复。
- 混淆了“项目级规则”和“平台级角色配置”的职责边界。
- 可能与用户已有 AGENTS.md 冲突，并影响其他 agent 工具的行为。

### 方案二：使用独立 CODEX_HOME profile 派生方案

#### 优势

- 平台配置保留在平台自身，不需要修改用户项目文件。
- 角色能力可跨项目复用，符合 agents-hub 的产品目标。
- 环境变量只作用于当前进程和子进程，不污染用户全局环境。
- 运行时仍可把工作目录设置为当前项目目录，从而保留项目级 AGENTS.md 的参与能力。

#### 劣势

- 需要额外维护 profile 派生目录。
- 需要区分哪些文件属于配置，哪些属于运行时状态。
- 比直接改 AGENTS.md 多一层派生和启动管理逻辑。

## 最终决策和决策原因

### 最终决策

Codex 的 system prompt 修改采用 **独立 CODEX_HOME profile 派生方案**，不采用默认修改项目 AGENTS.md 的方案。

### 决策原因

1. agents-hub 需要的是平台级、跨项目的角色能力，而不是把平台配置写入用户项目。
2. 修改项目 AGENTS.md 会带来明显的仓库污染和退出产品后的残留副作用，不符合产品边界。
3. 独立 CODEX_HOME 更符合“平台配置属于平台、项目配置属于项目”的职责分离原则。
4. 当前测试已经验证：通过独立 CODEX_HOME 可以实现多轮 Codex CLI 对话，并可同时保留当前项目目录下 AGENTS.md 的参与能力。

### 实施要点

1. 以用户当前默认 CODEX_HOME 为基线，复制最小可用配置到独立 profile。
2. 建议复制：`config.toml`、`auth.json`、`rules/`、`skills/`、`superpowers/`。
3. 可选复制：`memories/`、`cap_sid`，是否复制取决于是否需要共享长期记忆或相关状态。
4. 不复制：`log/`、`sessions/`、`tmp/`、`.tmp/`、`.sandbox/`、`.sandbox-bin/`、`.sandbox-secrets/`、`history.jsonl`、`session_index.jsonl` 以及各类 sqlite 运行时文件。
5. 在派生 profile 中写入或覆盖 profile 级 `AGENTS.md`，承载该 agent 的角色定义。
6. agents-hub 启动 Codex CLI 子进程时，临时设置 `CODEX_HOME` 指向该 profile，并把工作目录设置为当前项目目录。

### 运行限制

如果某个角色选择 Codex 作为执行引擎，同一任务或同一会话中只允许一个 Codex 角色实际工作，不支持多个 Codex 角色同时参与同一轮协作。

原因是 Codex 的角色能力依赖 `CODEX_HOME` profile、当前工作目录、项目级 `AGENTS.md` 和会话上下文共同形成指令链。多个 Codex 角色同时在同一任务中工作时，容易出现角色身份、profile 指令和项目指令的混淆，也会增加会话恢复、结果归因和冲突处理成本。

因此，agents-hub 在产品层需要把 Codex 视为“单活角色执行器”：一个任务中可以选择一个 Codex 角色干活；如果需要多个不同角色协作，应优先让不同平台的 agent 参与，或把多个 Codex 角色拆成不同任务顺序执行。
