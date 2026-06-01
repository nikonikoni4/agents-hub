# MCP 工具系统 E2E 演示

## 概述

这个脚本演示了 MCP 工具系统的完整流程，包括：

1. 创建群聊（Manager + 3 个 Worker）
2. 启动 MCP Server
3. 测试 MCP 工具调用

## 团队成员

| 角色 | 名称 | 职责 |
|------|------|------|
| Manager | Leader | 团队领导，负责任务分配和进度跟踪 |
| 架构师 | 小李 | 负责系统架构设计和技术方案 |
| PRD | 小赵 | 负责产品需求文档和需求分析 |
| 执行和测试 | 小钱 | 负责开发执行和质量保证 |

## 运行方式

```bash
# 进入 explore/多agent架构 目录
cd explore/多agent架构

# 运行演示脚本
python e2e_mcp_demo.py
```

## 演示内容

### 场景 1：验证 token 生成
- 创建群聊后自动生成 token
- 验证 token 可以正确解析

### 场景 2：Manager 派活给 Worker
- Manager 使用 `call_agent` 工具派活给各个 Worker
- 支持需要响应和不需要响应两种模式

### 场景 3：Manager 分配任务
- 使用 `assign_tasks_to_team` 工具分配任务列表
- 支持创建、更新、保持不变三种操作
- 验证 Worker 无权分配任务

### 场景 4：归档任务
- 使用 `archive_task_list` 工具归档当前任务列表
- 验证 Worker 无权归档任务

## MCP Server

脚本启动后，MCP Server 会在 `http://localhost:8001/mcp` 运行。

### 可用工具

1. **call_agent** - 派活给团队成员
2. **assign_tasks_to_team** - 覆盖式更新任务列表（Leader-only）
3. **archive_task_list** - 归档当前 ACTIVE 列表（Leader-only）
4. **check_agent_call** - 查询 AgentCall 状态

## 注意事项

1. 首次运行会自动创建小钱这个角色（如果不存在）
2. 脚本会使用 `explore/多agent架构/local_data` 目录存储数据
3. 按 Ctrl+C 可以停止 MCP Server
