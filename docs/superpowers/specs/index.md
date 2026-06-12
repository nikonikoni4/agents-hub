# Superpowers Specs 索引

本目录存放通过 superpowers 技能生成的设计规格文档。

## 前端设计

### frontend-mvp-design
- **更新时间**：2026-06-01
- **路径**：`docs/superpowers/specs/2026-06-01-frontend-mvp-design.md`
- **触发规则**：当设计、修改或扩展前端 MVP 界面时阅读
- **内容摘要**：Agents Hub 前端 MVP 界面设计规格，定义核心组件（TopBar、SessionList、ChatWindow、ChatInfoPanel）、两栏布局结构、交互流程和数据流

## 角色管理

### role-management-design
- **更新时间**：2026-06-02
- **路径**：`docs/superpowers/specs/2026-06-02-role-management-design.md`
- **触发规则**：当设计、修改或扩展 roles 角色管理、Skill 启用、角色 MCP 初始化或角色元信息边界时阅读
- **内容摘要**：Role Management 设计规格，定义 role.json 仅保存角色元信息、Skill 以 work_root/skills 为启用状态、创建角色时自动添加固定 agents-hub MCP，并明确权限和原生配置编辑暂不落地

## WebSocket 后端

### websocket-backend-design
- **更新时间**：2026-06-03
- **路径**：`docs/superpowers/specs/2026-06-03-websocket-backend-design.md`
- **触发规则**：当设计、修改或扩展 WebSocket 后端功能、消息推送机制或实时通信时阅读
- **内容摘要**：WebSocket 后端设计规格，定义多房间模式、刷新信号推送、FastAPI 原生 WebSocket 实现、错误处理机制和测试方案

## Core Runtime

### core-runtime-ssot-design
- **更新时间**：2026-06-04
- **路径**：`docs/superpowers/specs/2026-06-04-core-runtime-ssot-design.md`
- **触发规则**：当设计或规划 core runtime 内存 SSOT、GroupChat 职责收窄、Repository 所有权迁移或 core 对外查询边界时阅读
- **内容摘要**：Core Runtime 内存 SSOT 重构 brainstorm 设计稿，定义内存作为运行期 SSOT、文件作为 durable copy、Runtime/State/Repository/Context 职责划分和依赖注入方向

## Agent 上下文压缩

### agent-context-compression-design
- **更新时间**：2026-06-12
- **路径**：`docs/superpowers/specs/2026-06-12-agent-context-compression-design.md`
- **触发规则**：当设计、修改或扩展 Agent CLI session 上下文压缩、session 重建或压缩留痕机制时阅读
- **内容摘要**：Agent 上下文主动压缩设计规格，定义自动/手动触发机制、Agent 自我总结流程、立即新建 session 策略、留痕文件格式和前端同步方案

## Realtime 边界

### realtime-boundary-design
- **更新时间**：2026-06-04
- **路径**：`docs/superpowers/specs/2026-06-04-realtime-boundary-design.md`
- **触发规则**：当设计或修改 WebSocket 与 MCP、API 的依赖边界，或规划群聊实时刷新/消息推送能力时阅读
- **内容摘要**：Realtime 边界设计稿，定义 WebSocket 连接管理从 API 内部抽离为独立 realtime 能力，API 与 MCP 共同依赖 realtime；当前只发送 refresh signal，未来预留 message payload 推送
