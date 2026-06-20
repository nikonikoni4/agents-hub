---
version: 2.0
created_at: 2026-06-03
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：聚焦业务意图 + 技术契约 + 设计决策，移除执行细节
abstract: Docker 沙箱执行器的规格定义，通过 Docker 容器为 AI CLI 工具提供隔离执行环境
id: spec-docker-executor
title: Docker 沙箱执行器规格
status: draft
module: agent_bridge/docker, agent_bridge/executors
source_spec: null
related_plan: null
code_scope:
  - agents_hub/agent_bridge/docker/
  - agents_hub/agent_bridge/executors/docker_claude.py
  - agents_hub/agent_bridge/executors/docker_codex.py
contract_refs:
  - agents_hub/agent_bridge/docker/manager.py
  - agents_hub/agent_bridge/docker/container.py
  - agents_hub/agent_bridge/executors/docker_base.py
  - agents_hub/config/types.py
  - template/Dockerfile
---

# Docker 沙箱执行器规格

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 初始版本，定义容器生命周期、CLI 路径、卷挂载和 worktree 修复机制 |
| 1.1 | 补充 stop_session、ensure_image_ready、CLI fork/system_prompt/disabled_tools 参数、容器内环境变量和工作目录、RuntimeError 异常、并发安全精确化 |
| 2.0 | 按新 spec 规则重构：聚焦业务意图 + 技术契约 + 设计决策，移除执行细节 |

---

## Overview

**业务问题**：AI CLI 工具（Claude、Codex）直接在宿主机执行存在安全风险和环境污染问题，需要提供隔离的执行环境来保护宿主机文件系统和进程空间。

**核心职责**：
- **负责**：容器生命周期管理（创建、复用、销毁）、CLI 命令在容器内执行、git worktree 路径修复、资源清理
- **不负责**：CLI 工具本身的逻辑、业务层会话管理、容器镜像构建

## Scope

### 范围内

- 容器创建、复用、销毁的生命周期管理
- 容器内 CLI 命令构建与执行
- 卷挂载策略（work_root、工作目录、git 仓库）
- git worktree 路径修复与回退
- AgentBridge 对 Docker 模式的集成接口

### 范围外

- Docker 镜像的构建与维护（见 `template/Dockerfile`）
- 容器内 CLI 工具的版本管理
- 容器资源限制（CPU、内存）
- 容器网络隔离策略

## Technical Contract

### 对外接口总览

<key_function last_update="2026-06-20T14:08:10+08:00">
- agents_hub/agent_bridge/docker/manager.py
  - manager.DockerManager.get_or_create_container:262
  - manager.DockerManager.release_container:297
  - manager.DockerManager.ensure_image_ready:54
- agents_hub/agent_bridge/executors/docker_base.py
  - docker_base.DockerExecutor.execute:36
  - docker_base.DockerExecutor.stop_session:103
</key_function>

| 接口 | 所属类 | 说明 | 约束 |
|------|--------|------|------|
| `get_or_create_container(agent_name, group_chat_id, work_root, cwd)` | DockerManager | 获取缓存容器或创建新容器 | 同一 (agent_name, group_chat_id) 复用同一容器；worktree 模式下自动修复 git 路径 |
| `release_container(agent_name, group_chat_id)` | DockerManager | 释放容器并启动延迟销毁 | 超过空闲超时后自动 stop + rm |
| `ensure_image_ready()` | DockerManager | 确保 Docker 可用且镜像已就绪 | 镜像不存在且 Dockerfile 存在时自动构建 |
| `execute(prompt, config, session_id, cwd, group_chat_id, fork_from, system_prompt)` | DockerExecutor | 在容器内执行 CLI 命令并流式返回输出 | 必须提供 cwd、group_chat_id、work_root；内部维护 session_id 到进程的映射 |
| `stop_session(session_id)` | DockerExecutor | 立即终止指定 session 的容器内进程 | 发送强制终止信号，等待退出后清理映射；进程已退出则静默忽略 |

### 容器生命周期状态机

```
[不存在] --get_or_create_container()--> [运行中]
[运行中] --release_container()--> [等待销毁（延迟）]
[等待销毁] --超时--> [已销毁]
[等待销毁] --新请求--> [运行中]（取消销毁任务）
```

**容器命名规则**：`container-{agent_name}-{group_chat_id}`

### 卷挂载契约

| 宿主机路径 | 容器路径 | 用途 |
|-----------|----------|------|
| 角色 work_root | /home/ai-user/.claude | 角色配置目录（通过 CLAUDE_CONFIG_DIR 环境变量指定） |
| 工作目录（通常是 worktree） | /workspace | CLI 执行上下文目录 |
| 主仓库 .git 目录 | /repo-git | git 元数据（无仓库时不挂载） |

### CLI 路径配置

CLI 路径常量（`CLAUDE_COMMAND`、`CODEX_COMMAND`、`DOCKER_CLAUDE_COMMAND`、`DOCKER_CODEX_COMMAND`）统一定义在 [config spec](2026-06-06-config.md) 的 CLI 路径映射章节，遵循 SSOT 原则，本 spec 不重复定义。

### 容器内执行环境

- **环境变量**：每次 `docker exec` 注入 `CLAUDE_CONFIG_DIR=/home/ai-user/.claude`
- **工作目录**：`docker exec` 工作目录固定为 `/workspace`

### CLI 命令参数

**Claude CLI**：
- 基础参数：`--dangerously-skip-permissions`, `--print`, `--verbose`, `--output-format stream-json`, `--include-partial-messages`
- 可选参数：`--bare`（极简模式）, `--resume <session_id>`（会话恢复）
- Fork 模式：`--fork-session --resume <fork_from>`
- 系统提示注入：`--append-system-prompt <system_prompt>`
- 工具禁用：`--disallowedTools=<comma_separated_tools>`

**Codex CLI**：
- 基础参数：`--dangerously-bypass-approvals-and-sandbox`, `--print`, `--output-format stream-json`
- 可选参数：`--resume <session_id>`（会话恢复）
- Fork 模式：`codex fork <fork_from> <prompt>`（跳过基础参数）
- 系统提示注入：`-c instructions=<system_prompt>`

### git worktree 路径修复

**问题**：worktree 的 `.git` 文件包含指向宿主机的绝对路径，容器内无法访问。

**契约**：创建容器前临时修改 worktree 的 `.git` 和 `gitdir` 文件为容器内路径，容器销毁后回退到原始内容。

**关键路径**：
- `{cwd}/.git` → `gitdir: /repo-git/worktrees/{worktree_name}`
- `{git_dir}/worktrees/{worktree_name}/gitdir` → `/workspace/.git`

### 异常类型

| 异常 | 触发场景 |
|------|----------|
| DockerNotAvailableError | Docker Engine 未运行 |
| DockerStartError | 容器创建失败（镜像不存在、端口冲突等） |
| StateError | worktree 模式下 git_dir 为 None |
| RuntimeError | 容器内命令执行失败（进程返回非零退出码），包含 stderr 信息 |

### AgentBridge 集成

AgentBridge 在初始化时创建 DockerManager 和 DockerExecutor 实例。调用时通过 `use_docker=True` 参数启用 Docker 模式，需要同时提供 `group_chat_id` 参数。

## Design Rationale

**为什么使用容器池管理？**
- 避免每次执行都创建/销毁容器的开销（Docker 启动耗时 1-3 秒）
- 同一 (agent_name, group_chat_id) 组合复用容器，保持会话上下文连续性
- 延迟销毁机制平衡资源释放与响应速度

**为什么需要 git worktree 路径修复？**
- worktree 的 `.git` 文件使用绝对路径指向宿主机 gitdir，容器内 volume 映射后路径不匹配
- 临时修改 + 回退方案避免了对 git 格式的深度依赖，降低实现复杂度

**有哪些约束？**
- 容器内 CLI 工具通过 npm 全局安装，路径依赖 Node.js 安装位置
- 卷挂载使用 `--network host`，Windows Docker Desktop 下行为可能不同
- worktree 路径修复涉及文件写入，进程崩溃可能导致宿主机 git 状态损坏

**有哪些已知限制？**
- DockerManager 的 `get_or_create_container` 在高并发下存在竞态条件（多个协程可能同时创建同一容器）
- 未实现容器健康状态检测
- 未设置容器 CPU/内存资源限制

**相关 ADR**：
- 无

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **Docker 镜像构建**：`template/Dockerfile` - 镜像定义与构建流程
- **AgentBridge 执行层**：`docs/specs/2026-05-23-agent-bridge.md` - 统一事件契约、三接口设计、会话管理策略

---

## Uncertainty Event List

以下配置或路径一旦改变，Docker 执行器可能无法正常工作：

### CLI 路径依赖

| 配置项 | 当前值 | 风险 |
|--------|--------|------|
| DOCKER_CLAUDE_COMMAND | /usr/bin/claude | npm 全局安装路径可能因 Node.js 版本或系统不同而变化 |
| DOCKER_CODEX_COMMAND | /usr/bin/codex | 同上 |
| CLAUDE_COMMAND | {HOME}/.local/bin/claude | 安装方式改变可能导致路径不同 |
| CODEX_COMMAND | {HOME}/AppData/Roaming/npm/codex.cmd | Windows 特定路径，跨平台不兼容 |

### Docker 镜像依赖

| 配置项 | 当前值 | 风险 |
|--------|--------|------|
| config.docker_image | ai-tools:latest | 镜像名称改变或镜像不存在 |
| Dockerfile 基础镜像 | debian:bookworm-slim | 基础镜像更新可能导致包名变化 |

### 路径挂载依赖

| 配置项 | 当前值 | 风险 |
|--------|--------|------|
| 容器内工作目录 | /workspace | 硬编码在 DockerExecutor 中 |
| 容器内配置目录 | /home/ai-user/.claude | 硬编码在 DockerManager 中 |
| 容器内 git 目录 | /repo-git | 硬编码在 DockerManager 中 |

### 平台兼容性

| 平台 | 风险 |
|------|------|
| Windows | --network host 在 Docker Desktop 行为不同；路径分隔符 \ vs / |
| macOS | Docker Desktop 性能较差，可能导致执行超时 |
| Linux | 需要 sudo 或 docker 组权限 |
