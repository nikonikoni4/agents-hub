---
version: 1.0
created_at: 2026-06-02
updated_at: 2026-06-02
last_updated: 创建 Docker 沙箱模式使用指南初稿
abstract: Docker 沙箱模式使用指南，说明如何为 Agent 启用 Docker 文件系统隔离，包括配置方法、前提条件和常见问题。
---

# Docker 沙箱模式使用指南

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 概述

Docker 沙箱模式为 Agent 提供内核级文件系统隔离，防止 Agent 访问未授权文件。当 Agent 的工作目录（cwd）与群聊项目路径不同时，Docker 容器会将 Agent 限制在自己的工作目录内，无法通过任何方式（包括相对路径）跳出。

## 启用条件

Docker 模式需要**同时满足两个条件**才会生效：

1. `agent_session_state.json` 中配置 `use_docker: true`
2. Agent 的 `cwd` 与群聊 `project_path` **不同**

如果 Agent 的 cwd 与群聊路径相同，Docker 隔离没有意义，系统会抛出 `DockerConfigError`。

## 配置方法

编辑 `local_data/teams/{project_path}/{group_chat_id}/agent_session_state.json`：

```json
{
  "小李": {
    "cwd": "explore/worktree-feature-a",
    "use_docker": true
  },
  "Leader": {
    "cwd": "local_data",
    "use_docker": false
  }
}
```

**说明**：
- `cwd`：Agent 的工作目录，相对于项目根目录
- `use_docker`：是否启用 Docker 沙箱

## 前提条件

1. 安装 Docker Desktop 并确保 Docker Engine 正在运行
2. 构建 `ai-tools:latest` 镜像：

```bash
cd explore/docker-experiment
docker build -f Dockerfile.ai-tools -t ai-tools:latest .
```

## 执行流程

```
用户消息 → GroupChat → Agent.run()
  ↓
Agent._validate_docker_config()  ← 校验配置合理性
  ↓
AgentBridge.execute(use_docker=True)
  ↓
DockerClaudeExecutor → DockerManager.get_or_create_container()
  ↓
docker exec -w /workspace \
  --dangerously-skip-permissions \
  container-{agent}-{group} \
  claude "prompt"
```

## 隔离效果

| 场景 | 结果 |
|------|------|
| 读取挂载的 worktree 文件 | 成功 |
| 读取未挂载的主仓库文件 | 失败（文件不存在） |
| 通过相对路径跳出挂载范围 | 失败（路径被截断） |

## 容器生命周期

- **懒启动**：第一次调用时才创建容器，不预占用资源
- **延迟销毁**：容器空闲 10 分钟后自动销毁
- **复用**：同一 Agent 在同一群聊中复用同一容器

## 网络策略

容器使用 `--network host` 模式：
- 可以访问 `localhost` 上的本地 MCP 服务（如 `localhost:8080`）
- 可以访问互联网（WebSearch 等功能正常）
- 文件系统仍然完全隔离

## 常见问题

**Q: Docker Engine 未运行怎么办？**

A: 启动 Docker Desktop，或在 `agent_session_state.json` 中设置 `use_docker: false`。系统不会自动降级到本地执行（安全优先），会抛出 `DockerNotAvailableError` 并给出明确的解决提示。

**Q: 容器多久会被清理？**

A: Agent 空闲 10 分钟后自动销毁。容器本身开销极小（1-2 MB），主要开销来自容器内的 Claude Code 进程（200-500 MB）。

**Q: 容器内可以访问本地 MCP 服务吗？**

A: 可以。容器使用 `--network host` 模式，可以透明访问 `localhost` 上的所有服务。

**Q: 配置了 use_docker=true 但报错 DockerConfigError？**

A: 检查 Agent 的 cwd 是否与群聊 project_path 相同。只有当两者不同时才需要 Docker 隔离。如果相同，将 `use_docker` 改为 `false`。

**Q: 如何查看正在运行的容器？**

A: 运行 `docker ps` 查看所有容器，容器名称格式为 `container-{agent_name}-{group_chat_id}`。

## 资源开销

| 资源类型 | 空闲容器 | 运行 Claude Code 时 |
|---------|---------|-------------------|
| 内存 | 1-2 MB | 200-500 MB（主要是 Claude Code 进程） |
| CPU | 0% | 根据任务 |
| 磁盘 | 0 MB（使用挂载卷） | 临时文件 < 100 MB |
| 启动时间 | 200-500 ms | - |

容器本身开销可忽略，主要开销来自 Claude Code 进程，与本地执行相同。
