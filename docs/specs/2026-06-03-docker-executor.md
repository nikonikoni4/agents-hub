---
version: 1.0
created_at: 2026-06-03
updated_at: 2026-06-03
last_updated: 初始版本
abstract: Docker 沙箱执行器的规格定义，描述容器生命周期管理、CLI 路径配置、卷挂载策略和 git worktree 路径修复机制
id: spec-docker-executor
title: Docker 沙箱执行器规格
status: draft
module: agent_bridge/docker, agent_bridge/executors
sourc_spec: null
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

---

## Overview

Docker 沙箱执行器是 agent_bridge 模块的隔离执行层，通过 Docker 容器为 AI CLI 工具提供隔离的执行环境。

模块定位：
- **负责**：容器生命周期管理、CLI 命令在容器内执行、git worktree 路径修复、资源清理
- **不负责**：CLI 工具本身的逻辑、业务层会话管理、容器镜像构建

## Scope

### 范围内

- 容器创建、复用、销毁的生命周期管理
- 宿主机与容器的 CLI 命令路径映射
- 卷挂载策略（work_root、工作目录、git 仓库）
- git worktree 路径修复与回退机制
- AgentBridge 对 Docker 模式的集成

### 范围外

- Docker 镜像的构建与维护
- 容器内 CLI 工具的版本管理
- 容器资源限制（CPU、内存）
- 容器网络隔离策略

## Core Behavior

### 架构模式

Docker 执行器采用容器池管理架构：

1. AgentBridge 初始化时创建 DockerManager 和对应平台的 DockerExecutor
2. 调用时通过 `use_docker=True` 参数启用 Docker 模式
3. DockerManager 负责容器的创建、缓存和销毁
4. DockerExecutor 负责构建容器内 CLI 命令并执行

### 容器生命周期

1. **创建**：首次调用时创建容器，挂载必要目录
2. **复用**：同一 (agent_name, group_chat_id) 组合复用已创建的容器
3. **释放**：执行完成后启动延迟销毁计时器
4. **销毁**：超过配置的空闲超时时间后自动停止并删除容器

### 容器命名规则

容器名称格式：`container-{agent_name}-{group_chat_id}`

### 卷挂载策略

| 宿主机路径 | 容器路径 | 说明 |
|-----------|----------|------|
| 角色 work_root | /home/ai-user/.claude | 角色配置目录（CLAUDE_CONFIG_DIR） |
| 工作目录（通常是 worktree） | /workspace | 执行上下文目录 |
| 主仓库 .git 目录 | /repo-git | git 元数据（可选，无仓库时不挂载） |

## Technical Contract

### CLI 路径配置

Docker 容器内使用 npm 全局安装的 CLI 工具。配置常量定义在 config/types.py 中：

| CLI 工具 | 宿主机路径常量 | 容器内路径常量 |
|---------|---------------|---------------|
| Claude | CLAUDE_COMMAND | DOCKER_CLAUDE_COMMAND |
| Codex | CODEX_COMMAND | DOCKER_CODEX_COMMAND |

### DockerExecutor 命令参数

#### Claude CLI 容器内执行参数

- 基础参数：`--dangerously-skip-permissions`, `--print`, `--verbose`, `--output-format stream-json`, `--include-partial-messages`
- 可选参数：`--bare`（极简模式）, `--resume <session_id>`（会话恢复）

#### Codex CLI 容器内执行参数

- 基础参数：`--dangerously-bypass-approvals-and-sandbox`, `--print`, `--output-format stream-json`
- 可选参数：`--resume <session_id>`（会话恢复）

### git worktree 路径修复

**问题**：worktree 的 `.git` 文件包含指向宿主机的绝对路径，容器内无法访问。

**解决方案**：创建容器前临时修改 `.git` 和 `gitdir` 文件，容器销毁后回退。

#### 修复流程

1. 读取原始内容并保存到内部状态
2. 修改 `.git` 文件为容器内路径：`gitdir: /repo-git/worktrees/{worktree_name}`
3. 修改 `gitdir` 文件为容器内路径：`/workspace/.git`
4. 容器销毁时回退到原始内容

#### 关键路径

- `{cwd}/.git` → 指向 worktree 的 gitdir
- `{git_dir}/worktrees/{worktree_name}/gitdir` → 指向 worktree 的 .git

### 异常类型

| 异常 | 触发场景 |
|------|----------|
| DockerNotAvailableError | Docker Engine 未运行 |
| DockerStartError | 容器创建失败（镜像不存在、端口冲突等） |
| StateError | worktree 模式下 git_dir 为 None |

### AgentBridge 集成

AgentBridge 在初始化时创建 DockerManager 和 DockerExecutor 实例。调用时通过 `use_docker=True` 参数启用 Docker 模式，需要同时提供 `group_chat_id` 参数。

## Acceptance Notes

1. 容器能正确创建并挂载指定目录
2. CLI 命令能在容器内执行并返回结果
3. 同一 (agent_name, group_chat_id) 组合复用同一容器
4. 超过空闲超时后容器自动销毁
5. git worktree 路径修复后容器内 git 命令正常工作
6. 容器销毁后 git 路径正确回退到宿主机状态
7. Docker 未运行时抛出明确错误信息
8. 容器创建失败时抛出包含 stderr 的错误信息

## Out of Spec

1. **Docker 镜像构建**：镜像由 template/Dockerfile 定义，不在本 spec 维护
2. **容器资源限制**：当前未设置 CPU/内存限制
3. **并发安全**：同一容器的并发 exec 调用未做同步
4. **容器健康检查**：未实现容器健康状态检测

---

## ⚠️ 不确定性事件清单

以下配置或路径一旦改变，Docker 执行器可能无法正常工作：

### 1. CLI 路径依赖

| 配置项 | 当前值 | 风险 | 影响 |
|--------|--------|------|------|
| DOCKER_CLAUDE_COMMAND | /usr/bin/claude | npm 全局安装路径可能因 Node.js 版本或系统不同而变化 | 容器内找不到 claude 命令 |
| DOCKER_CODEX_COMMAND | /usr/bin/codex | 同上 | 容器内找不到 codex 命令 |
| CLAUDE_COMMAND | {HOME}/.local/bin/claude | 安装方式改变可能导致路径不同 | 本地模式执行失败 |
| CODEX_COMMAND | {HOME}/AppData/Roaming/npm/codex.cmd | Windows 特定路径，跨平台不兼容 | 本地模式执行失败 |

### 2. Docker 镜像依赖

| 配置项 | 当前值 | 风险 | 影响 |
|--------|--------|------|------|
| config.docker_image | ai-tools:latest | 镜像名称改变或镜像不存在 | 容器创建失败 |
| Dockerfile 基础镜像 | debian:bookworm-slim | 基础镜像更新可能导致包名变化 | 镜像构建失败 |
| npm 包名 | @anthropic-ai/claude-code, @openai/codex | 包名或安装方式变化 | CLI 未安装到容器 |

### 3. 路径挂载依赖

| 配置项 | 当前值 | 风险 | 影响 |
|--------|--------|------|------|
| 容器内工作目录 | /workspace | 硬编码在 DockerExecutor 中 | cwd 参数失效 |
| 容器内配置目录 | /home/ai-user/.claude | 硬编码在 DockerManager 中 | work_root 挂载失败 |
| 容器内 git 目录 | /repo-git | 硬编码在 DockerManager 中 | git 命令无法访问仓库 |
| 容器用户名 | ai-user | Dockerfile 中创建的用户 | 文件权限问题 |

### 4. git worktree 路径依赖

| 配置项 | 当前值 | 风险 | 影响 |
|--------|--------|------|------|
| worktree 目录结构 | {git_dir}/worktrees/{name}/ | git worktree 格式变化 | 路径修复失败 |
| .git 文件格式 | gitdir: {absolute_path} | git 版本更新可能改变格式 | 路径解析失败 |
| commondir 文件 | 存在于 worktree 的 gitdir 中 | git 版本不支持 commondir | 无法找到主仓库 .git 目录 |

### 5. 环境变量依赖

| 配置项 | 当前值 | 风险 | 影响 |
|--------|--------|------|------|
| CLAUDE_CONFIG_DIR | /home/ai-user/.claude | Claude CLI 配置目录环境变量名变化 | CLI 无法加载配置 |
| CODEX_HOME | 未在 Docker 模式设置 | Codex CLI 配置目录环境变量名变化 | CLI 无法加载配置 |
| --network host | 使用宿主机网络 | Docker 网络策略限制 | 容器无法访问外部服务 |

### 6. 时序与并发风险

| 场景 | 风险 | 影响 |
|------|------|------|
| docker rm -f 异步执行 | 删除未完成时创建同名容器 | 容器名冲突 |
| 并发调用 get_or_create_container | 多个协程同时创建容器 | 竞态条件 |
| git 路径修复期间进程崩溃 | 回退逻辑未执行 | 宿主机 git 状态损坏 |
| 空闲超时期间新请求 | 容器正在被销毁 | 执行失败 |

### 7. 平台兼容性

| 平台 | 风险 | 影响 |
|------|------|------|
| Windows | --network host 在 Windows Docker Desktop 行为不同 | 网络不通 |
| Windows | 路径分隔符 \ vs / | 卷挂载失败 |
| macOS | Docker Desktop 性能较差 | 执行超时 |
| Linux | 需要 sudo 或 docker 组权限 | 权限不足 |
