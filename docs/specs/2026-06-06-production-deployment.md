---
version: 2.0
created_at: 2026-06-06
updated_at: 2026-06-18
last_updated: 按新 spec 规则重构：移除执行细节，添加 Design Rationale
abstract: 生产部署规格，定义 Docker 容器化方案的技术契约、网络架构、数据持久化和配置管理
id: production-deployment
title: 生产部署
status: draft
module: deployment
source_spec:
related_plan:
code_scope: docker/, agents_hub/config.py, scripts/
contract_refs: docker/Dockerfile, docker/docker-compose.prod.yml
---

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 2.0 | 按新 spec 规则重构：移除执行细节，添加 Design Rationale |
| 1.0 | 创建文档初稿 |

## Overview

**业务问题**：agents-hub 需要一套标准化的生产部署方案，将后端、前端和依赖服务打包为可独立运行的生产级部署单元，使开发者能够在单机环境下快速完成部署和运维。

**核心职责**：
- 定义 Docker 镜像构建规范（多阶段构建、基础镜像、安全约束）
- 定义容器服务架构（服务组成、网络拓扑、数据持久化）
- 定义环境配置注入规范（配置优先级、密钥管理）
- 定义健康检查和日志管理契约

## Scope

### 范围内

- Docker 镜像构建规范（多阶段构建，分离构建环境和运行环境）
- 容器编排规范（Docker Compose 服务定义、依赖关系、网络拓扑）
- 数据持久化契约（卷挂载策略、数据路径）
- 环境配置注入规范（环境变量、Docker Secrets、配置优先级）
- 健康检查契约（端点定义、检查参数）
- 日志管理契约（日志驱动、轮转策略）

### 范围外

- Kubernetes 集群编排（当前仅支持单机 Docker Compose）
- CI/CD 流水线配置（由外部 CI 服务负责）
- 云服务商特定基础设施（如 AWS ECS、阿里云 ACK）
- 首次部署/升级/回滚的具体执行步骤（属于运维流程，见 Flow 文档）
- 开发环境部署（见 `docs/RUN.md`）
- 前端构建细节（见 `frontend-core` spec）

## Technical Contract

### 容器服务架构

| 服务 | 镜像 | 端口 | 职责 |
|------|------|------|------|
| `agents-hub` | 本地构建 | 8000 | FastAPI 后端 + WebSocket |
| `frontend` | 本地构建 | 3000 | React 前端静态资源 |
| `redis` | redis:7-alpine | 6379 | 会话缓存（可选） |

### 网络拓扑

- 所有服务运行在同一 Docker 网络 `agents-hub-net`
- `agents-hub` 服务通过内部网络访问 Redis
- `frontend` 服务通过 Nginx 反向代理 API 请求到后端
- 仅暴露 80/443 端口到宿主机

### 数据持久化

| 卷 | 容器路径 | 用途 |
|----|----------|------|
| `agents-data` | `/app/data` | 会话、群聊、角色配置 |
| `agents-logs` | `/app/logs` | 运行日志 |
| `agents-config` | `/app/config` | 自定义配置覆盖 |

### Dockerfile 规范

- 基础镜像：`python:3.11-slim`（后端）、`node:20-alpine`（前端构建）
- 采用多阶段构建：构建阶段安装编译依赖并构建前端静态资源，运行阶段仅复制运行时必需文件
- 非 root 用户运行
- 健康检查内置
- 时区配置：`Asia/Shanghai`

### docker-compose.prod.yml 规范

- 服务依赖：`agents-hub` depends_on `redis`（可选）
- 网络：自定义桥接网络 `agents-hub-net`
- 卷：命名卷用于持久化数据
- 重启策略：`unless-stopped`

### 环境配置规范

**配置注入优先级**：环境变量 > `.env` 文件 > 默认值

**环境变量**：

| 变量 | 说明 | 来源 |
|------|------|------|
| `AGENTS_HUB_ENV` | 运行模式，生产环境设为 `production` | `.env` |
| `AGENTS_HUB_DATA_PATH` | 数据存储路径，默认 `/app/data` | `.env` |
| `AGENTS_HUB_LOG_LEVEL` | 日志级别，默认 `INFO` | `.env` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | Docker Secret |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 | Docker Secret |

**密钥管理**：敏感信息（API Key、Token）通过 Docker Secrets 或环境变量注入，不写入镜像。

### 健康检查契约

后端服务提供 `/health` 端点，Docker 健康检查参数：

| 参数 | 值 |
|------|-----|
| 检查间隔 | 30 秒 |
| 超时时间 | 10 秒 |
| 重试次数 | 3 |
| 启动等待 | 40 秒 |

### 日志管理契约

- 容器日志输出到 stdout/stderr
- Docker 日志驱动：`json-file`，单文件上限 10MB，保留 3 个文件
- 应用日志同时写入 `/app/logs` 卷，便于持久化和分析

### 配置热重载

应用配置支持热重载（通过 watchfiles），无需重启容器即可生效。

## Design Rationale

**为什么选择 Docker Compose 而非 Kubernetes？**
- 当前阶段以单机部署为主，目标用户是中小规模团队或个人开发者
- Docker Compose 学习成本低，部署链路短，适合快速上手
- 未来如需扩展到集群部署，可通过独立 spec 补充 Kubernetes 方案

**为什么采用多阶段构建？**
- 分离构建依赖和运行依赖，显著减小最终镜像体积
- 构建阶段包含编译工具（node、gcc 等），运行阶段仅保留运行时必需文件
- 提升安全性：减少攻击面，运行镜像不包含编译工具

**为什么使用命名卷而非绑定挂载？**
- 命名卷由 Docker 管理，生命周期独立于容器，容器重建不丢数据
- 避免绑定挂载的权限问题（宿主机 UID/GID 映射）
- 便于备份和迁移（`docker volume` 命令）

**为什么敏感信息不写入镜像？**
- 镜像可能被推送到公共或共享 Registry，泄露密钥风险高
- Docker Secrets / 环境变量注入方式使同一镜像可复用于不同环境
- 符合 12-Factor App 原则（配置与代码分离）

**为什么没有 key_function 标签？**
- 部署配置模块主要定义 Docker Compose 和 Dockerfile 规范，不涉及 Python 函数接口
- 关键契约体现在容器服务架构、网络拓扑、卷挂载等声明式配置中，而非函数签名

**有哪些已知限制？**
- 仅支持单机部署，不支持水平扩展和负载均衡
- Redis 为可选组件，未配置时回退到内存缓存，重启丢失会话
- 无内置 SSL/TLS 终止，需外部反向代理（如 Nginx、Caddy）提供 HTTPS

## Out of Scope

本 spec 不覆盖以下内容，请参考相应文档：

- **开发环境部署**：`docs/RUN.md` - 本地开发环境的启动和配置
- **前端构建规范**：`frontend-core` spec - 前端构建流程和产物规范
- **架构总览**：`docs/ARCHITECTURE.md` - 系统整体架构和模块关系
