---
version: 1.0
created_at: 2026-06-06
updated_at: 2026-06-06
last_updated: 创建生产部署 spec
abstract: 生产部署规格，定义 Docker 容器化方案、网络架构、数据持久化、部署流程和运维监控
id: production-deployment
title: 生产部署
status: draft
module: deployment
sourc_spec:
related_plan:
code_scope: docker/, agents_hub/config.py, scripts/
contract_refs: docker/Dockerfile, docker/docker-compose.prod.yml
---

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## Overview

生产部署模块提供 Docker 容器化方案，将 agents-hub 后端、前端和依赖服务打包为可独立运行的生产级部署单元。

## Scope

**职责边界**：

- Docker 镜像构建：多阶段构建，分离构建环境和运行环境
- 容器编排：Docker Compose 定义服务依赖和网络拓扑
- 数据持久化：会话数据、配置文件、日志的卷挂载策略
- 环境配置：生产环境变量、密钥管理、配置注入
- 部署脚本：一键部署、升级、回滚流程

**不负责**：

- Kubernetes 集群编排（当前仅支持单机 Docker Compose）
- CI/CD 流水线配置（由外部 CI 服务负责）
- 云服务商特定基础设施（如 AWS ECS、阿里云 ACK）

## Core Behavior

### 镜像构建策略

采用多阶段构建优化镜像体积：

1. **构建阶段**：安装编译依赖，构建前端静态资源，安装 Python 包
2. **运行阶段**：仅复制运行时必需文件，使用最小基础镜像

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

### 环境配置

生产环境通过 `.env` 文件注入配置，敏感信息（API Key、Token）通过 Docker Secrets 管理：

- `AGENTS_HUB_ENV=production`：启用生产模式
- `AGENTS_HUB_DATA_PATH=/app/data`：数据存储路径
- `AGENTS_HUB_LOG_LEVEL=INFO`：日志级别
- `OPENAI_API_KEY`：OpenAI API 密钥（Secret）
- `ANTHROPIC_API_KEY`：Anthropic API 密钥（Secret）

### 部署流程

**首次部署**：
1. 克隆仓库到目标服务器
2. 复制 `.env.example` 为 `.env` 并填写配置
3. 运行 `docker compose -f docker/docker-compose.prod.yml up -d`
4. 验证服务健康检查通过

**升级流程**：
1. 拉取最新代码
2. 重新构建镜像 `docker compose build`
3. 滚动更新 `docker compose up -d --no-deps agents-hub`
4. 验证新版本正常运行

**回滚流程**：
1. 指定旧版本镜像标签
2. 重新部署 `docker compose up -d --no-deps agents-hub`

### 健康检查

后端服务提供 `/health` 端点，Docker 健康检查配置：

- 检查间隔：30 秒
- 超时时间：10 秒
- 重试次数：3
- 启动等待：40 秒

### 日志管理

- 容器日志输出到 stdout/stderr
- Docker 日志驱动配置 `json-file`，限制单文件 10MB，保留 3 个文件
- 应用日志同时写入 `/app/logs` 卷，便于持久化和分析

## Technical Contract

### Dockerfile 规范

- 基础镜像：`python:3.11-slim`（后端）、`node:20-alpine`（前端构建）
- 非 root 用户运行
- 健康检查内置
- 时区配置：`Asia/Shanghai`

### docker-compose.prod.yml 规范

- 服务依赖：`agents-hub` depends_on `redis`（可选）
- 网络：自定义桥接网络 `agents-hub-net`
- 卷：命名卷用于持久化数据
- 重启策略：`unless-stopped`

### 配置注入规范

- 优先级：环境变量 > `.env` 文件 > 默认值
- 敏感信息通过 Docker Secrets 或环境变量注入，不写入镜像
- 配置文件支持热重载（通过 watchfiles）

## Out of Spec

- 开发环境部署（见 `docker-compose.yml` 和 `docs/RUN.md`）
- CI/CD 流水线配置（由外部服务负责）
- Kubernetes 部署方案（未来扩展）
- 云服务商特定配置（如 AWS CloudFormation、阿里云 ROS）
- 前端构建细节（见 `frontend-core` spec）
