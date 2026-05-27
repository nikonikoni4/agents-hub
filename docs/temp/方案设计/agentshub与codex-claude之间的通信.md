# agents-hub 与 Claude Code / Codex 之间的通信方案

## 问题背景

agents-hub 作为多 Agent 编排平台，需要解决以下核心问题：

1. **跨平台工具调用**：如何让 Claude Code CLI 调用 agents-hub 的编排逻辑？
2. **主动控制流程**：agents-hub 需要主动启动和管理多个 Agent sessions
3. **任务分解与调度**：如何将复杂任务拆解为多个子任务，并按序执行？
4. **结果聚合**：如何收集各个 Agent 的产物并汇总？

## 架构设计原则

### 核心理念

- **agents-hub 是主控进程**：主动启动和管理 Claude Code CLI / Codex API
- **MCP 作为垂直工具层**：Claude Code CLI 通过 MCP 调用 agents-hub 的编排工具
- **Agent 间通信由 agents-hub 内部实现**：不依赖 MCP 进行 Agent 间消息传递

### 角色定位

| 组件 | 角色 | 职责 |
|------|------|------|
| **agents-hub** | 主控 Orchestrator | 任务分析、Agent 调度、结果聚合 |
| **Claude Code CLI** | 工具执行者 | 执行具体任务（代码编写、文件操作等） |
| **Codex API** | 工具执行者 | 执行具体任务（代码生成、分析等） |
| **MCP Server** | 工具提供者 | 暴露编排工具给 Claude Code CLI |

## 方案设计

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│ agents-hub (主控进程)                                        │
│                                                             │
│  ┌────────────────────────────────────────────┐            │
│  │ Orchestrator (编排器)                      │            │
│  │  - 任务分析与拆解                          │            │
│  │  - Agent 序列生成                          │            │
│  │  - Session 生命周期管理                    │            │
│  │  - 产物收集与聚合                          │            │
│  └────────────────────────────────────────────┘            │
│                      │                                      │
│         ┌────────────┼────────────┐                        │
│         ▼            ▼            ▼                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│  │ MCP      │ │ CLI      │ │ Codex    │                  │
│  │ Server   │ │ Manager  │ │ Adapter  │                  │
│  └──────────┘ └──────────┘ └──────────┘                  │
│       │             │             │                        │
└───────┼─────────────┼─────────────┼────────────────────────┘
        │             │             │
        ▼             ▼             ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │ Claude   │ │ Claude   │ │ OpenAI   │
  │ Code CLI │ │ Code CLI │ │ Codex    │
  │ (主会话) │ │ (子会话) │ │ API      │
  └──────────┘ └──────────┘ └──────────┘
```

### 工作流程

#### 阶段 1：任务分析与计划生成

1. **用户发起请求**
   - 用户在 agents-hub IM 界面输入任务描述
   - 示例："实现一个用户认证系统，包括登录、注册、权限管理"

2. **启动主 CLI Session**
   - agents-hub 启动 Claude Code CLI 进程
   - CLI 自动加载 agents-hub MCP Server（通过配置文件）

3. **Claude 调用编排工具**
   - Claude 分析任务复杂度
   - 调用 MCP 工具 `orchestrate_task`
   - 传入参数：任务描述、复杂度评估

4. **MCP Server 返回执行计划**
   - 分析任务依赖关系
   - 生成 Agent 角色序列
   - 返回结构化计划：
     ```
     {
       "agents": ["需求分析师", "架构师", "后端工程师", "前端工程师", "测试工程师"],
       "dependencies": {
         "架构师": ["需求分析师"],
         "后端工程师": ["架构师"],
         "前端工程师": ["架构师"],
         "测试工程师": ["后端工程师", "前端工程师"]
       },
       "estimated_time": "2-3 hours"
     }
     ```

#### 阶段 2：子任务执行

1. **agents-hub 解析执行计划**
   - 提取 Agent 序列
   - 构建依赖图
   - 确定执行顺序（拓扑排序）

2. **按序启动子 Agent Sessions**
   - 为每个角色启动独立的 CLI session 或 Codex API 调用
   - 传入角色特定的 System Prompt
   - 传入上游 Agent 的产物作为上下文

3. **子任务执行示例**
   - **需求分析师 Session**：
     - Prompt: "你是需求分析师，分析用户认证系统的功能需求"
     - 产物: 需求文档（Markdown）
   
   - **架构师 Session**：
     - Prompt: "你是架构师，基于以下需求设计系统架构：\n[需求文档内容]"
     - 产物: 架构设计文档、数据库 Schema、API 设计
   
   - **后端工程师 Session**：
     - Prompt: "你是后端工程师，实现以下架构：\n[架构文档内容]"
     - 产物: 后端代码文件、数据库迁移脚本
   
   - **前端工程师 Session**：
     - Prompt: "你是前端工程师，实现以下 API 的前端界面：\n[API 文档内容]"
     - 产物: 前端组件代码
   
   - **测试工程师 Session**：
     - Prompt: "你是测试工程师，为以下代码编写测试：\n[代码内容]"
     - 产物: 测试代码、测试报告

4. **进度汇报**
   - 每个子任务完成后，agents-hub 调用主 Session
   - 通过 MCP 工具 `report_progress` 汇报进度
   - 主 Session 的 Claude 可以实时了解整体进度

#### 阶段 3：结果聚合与汇报

1. **产物收集**
   - 从各个 CLI session 的输出中提取：
     - 文件变更（新增、修改、删除）
     - 代码 Diff
     - 命令执行结果
     - 错误日志

2. **恢复主 Session**
   - 将所有子任务结果传回主 Session
   - Claude 生成最终报告：
     - 任务完成情况
     - 产物清单
     - 潜在问题与建议

3. **展示给用户**
   - 在 IM 界面展示最终报告
   - 提供产物预览（代码、文档、部署链接）
   - 支持用户进一步交互（修改、部署等）

### MCP Server 设计

#### 工具定义

##### 1. orchestrate_task（任务编排）

**功能**：分析任务并返回执行计划

**输入参数**：
- `task_description` (string, required): 用户任务描述
- `complexity` (enum, optional): 任务复杂度 [simple, medium, complex]
- `constraints` (object, optional): 约束条件（时间、资源等）

**输出**：
- `agents` (array): Agent 角色序列
- `dependencies` (object): 依赖关系图
- `estimated_time` (string): 预估时间
- `parallel_groups` (array): 可并行执行的 Agent 组

**决策逻辑**：
- 简单任务（single）：单个 Agent 完成
- 中等任务（medium）：2-3 个 Agent 串行
- 复杂任务（complex）：4+ 个 Agent，支持并行

##### 2. report_progress（进度汇报）

**功能**：子任务向主 Session 汇报执行状态

**输入参数**：
- `agent_role` (string, required): Agent 角色名称
- `status` (enum, required): 状态 [in_progress, completed, failed]
- `output` (string, optional): 产物摘要
- `artifacts` (array, optional): 产物列表（文件路径、类型）
- `error` (string, optional): 错误信息（如果失败）

**输出**：
- `acknowledged` (boolean): 是否已记录
- `next_action` (string): 建议的下一步操作

##### 3. query_context（上下文查询）

**功能**：子 Agent 查询其他 Agent 的产物

**输入参数**：
- `agent_role` (string, required): 目标 Agent 角色
- `query_type` (enum, required): 查询类型 [output, artifacts, status]

**输出**：
- 对应的上下文信息

#### 通信协议

- **传输层**：stdio（标准输入输出）
- **协议**：JSON-RPC 2.0
- **消息格式**：
  ```json
  {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "orchestrate_task",
      "arguments": {
        "task_description": "...",
        "complexity": "complex"
      }
    },
    "id": 1
  }
  ```

### CLI Session 管理

#### Session 生命周期

1. **创建 Session**
   - 生成唯一 Session ID
   - 启动 CLI 子进程
   - 配置环境变量（角色、MCP 配置路径）
   - 设置工作目录

2. **执行任务**
   - 通过 stdin 发送 Prompt
   - 监听 stdout/stderr 收集输出
   - 解析工具调用（MCP 工具）
   - 提取产物（文件变更、代码等）

3. **暂停与恢复**
   - 支持暂停 Session（保存状态）
   - 支持恢复 Session（传入新的 Prompt）
   - 维护对话历史

4. **销毁 Session**
   - 收集最终产物
   - 清理临时文件
   - 终止子进程

#### 角色配置

每个 Agent 角色有独立的 System Prompt：

- **需求分析师**：
  - 专注于需求挖掘、用户故事、验收标准
  - 输出格式：结构化需求文档

- **架构师**：
  - 专注于系统设计、技术选型、模块划分
  - 输出格式：架构图、API 设计、数据模型

- **工程师**（后端/前端）：
  - 专注于代码实现、最佳实践、性能优化
  - 输出格式：可运行的代码文件

- **测试工程师**：
  - 专注于测试用例、边界条件、回归测试
  - 输出格式：测试代码、测试报告

### Codex 集成方案

#### 问题

Codex（OpenAI API）目前不原生支持 MCP 协议

#### 解决方案

**方案 A：API 层模拟 MCP**

- Codex 通过 Function Calling 调用工具
- agents-hub 拦截 Function Call，转发到 MCP Server 逻辑
- 将 MCP 响应转换为 Function Call 结果

**方案 B：统一适配器层**

- 定义统一的 Agent 接口
- Claude Code Adapter：通过 MCP 通信
- Codex Adapter：通过 API Function Calling 通信
- Orchestrator 无需关心底层差异

**推荐方案**：方案 B（统一适配器层）

#### 适配器接口设计

```
IAgentAdapter
├─ initialize(config)
├─ execute(request) → AsyncIterator<AgentMessage>
├─ resume(sessionId, request) → AsyncIterator<AgentMessage>
├─ callTool(toolName, args) → ToolResult
└─ dispose()
```

#### Codex Adapter 实现要点

- 将 MCP 工具 schema 转换为 OpenAI Function schema
- 拦截 Function Call，调用 agents-hub 的 MCP Server 逻辑
- 将 MCP 响应转换为 Function Call 结果，继续对话
- 模拟 Session 管理（通过对话历史）

## 技术细节

### 产物收集机制

#### 文件变更追踪

- 监听 CLI 的 `Edit`/`Write` 工具调用
- 通过 MCP hooks 拦截文件操作
- 记录变更：
  ```
  {
    "type": "file_change",
    "action": "create" | "modify" | "delete",
    "path": "src/auth/login.ts",
    "content": "...",
    "diff": "..."
  }
  ```

#### 命令执行结果

- 监听 `Bash` 工具调用
- 记录命令和输出：
  ```
  {
    "type": "command_execution",
    "command": "npm test",
    "stdout": "...",
    "stderr": "...",
    "exit_code": 0
  }
  ```

#### 结构化产物

- 解析 Markdown 输出（需求文档、架构设计）
- 提取代码块
- 识别特定格式（如 Mermaid 图表）

### 上下文管理

#### 对话历史传递

- 每个子 Agent 需要了解上游产物
- 构建上下文 Prompt：
  ```
  你是[角色]。以下是上游 Agent 的产物：
  
  ## 需求分析师的输出
  [需求文档内容]
  
  ## 架构师的输出
  [架构设计内容]
  
  请基于以上内容完成你的任务：[具体任务描述]
  ```

#### 上下文压缩

- 对于长文档，提取关键信息
- 使用摘要工具（如 Claude 的 summarize）
- 保留关键决策点和约束条件

#### Pinned Messages

- 用户可以 Pin 关键消息作为长期上下文
- 所有子 Agent 都能访问 Pinned 内容
- 示例：技术栈约束、编码规范、项目背景

### 错误处理与重试

#### 子任务失败处理

1. **记录错误**：
   - 错误类型（工具调用失败、代码错误、超时等）
   - 错误上下文（当前 Agent、执行阶段）

2. **通知主 Session**：
   - 通过 `report_progress` 汇报失败状态
   - 主 Session 的 Claude 决定下一步：
     - 重试（调整 Prompt）
     - 跳过（标记为可选任务）
     - 终止（致命错误）

3. **降级策略**：
   - 复杂任务降级为简单任务
   - 减少 Agent 数量
   - 人工介入

#### 超时控制

- 每个子任务设置超时时间
- 超时后自动终止 Session
- 记录部分产物（如果有）

### 性能优化

#### 并行执行

- 识别无依赖关系的 Agent
- 同时启动多个 CLI sessions
- 示例：前端工程师和后端工程师可并行

#### 成本优化

- **Prompt Caching**：
  - 复用 System Prompt 和项目上下文
  - 减少 90% 的 token 成本
  
- **增量更新**：
  - 只传递变更部分，而非完整上下文
  
- **智能路由**：
  - 简单任务使用 Haiku（便宜）
  - 复杂任务使用 Opus（强大）

## 配置示例

### MCP Server 配置

```json
{
  "name": "agents-hub-orchestrator",
  "version": "1.0.0",
  "transport": "stdio",
  "tools": [
    {
      "name": "orchestrate_task",
      "description": "分析任务并返回执行计划",
      "inputSchema": { ... }
    },
    {
      "name": "report_progress",
      "description": "汇报子任务执行进度",
      "inputSchema": { ... }
    },
    {
      "name": "query_context",
      "description": "查询其他 Agent 的产物",
      "inputSchema": { ... }
    }
  ]
}
```

### Claude Code CLI 配置

```json
{
  "mcpServers": {
    "agents-hub": {
      "command": "node",
      "args": ["/path/to/agents-hub/mcp-server.js"],
      "env": {
        "AGENTS_HUB_API": "http://localhost:3000",
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

### Agent 角色配置

```json
{
  "roles": {
    "需求分析师": {
      "systemPrompt": "你是需求分析师...",
      "tools": ["Read", "Write"],
      "outputFormat": "markdown"
    },
    "架构师": {
      "systemPrompt": "你是架构师...",
      "tools": ["Read", "Write", "Bash"],
      "outputFormat": "markdown+mermaid"
    },
    "工程师": {
      "systemPrompt": "你是工程师...",
      "tools": ["Read", "Write", "Edit", "Bash"],
      "outputFormat": "code"
    },
    "测试工程师": {
      "systemPrompt": "你是测试工程师...",
      "tools": ["Read", "Write", "Bash"],
      "outputFormat": "code+report"
    }
  }
}
```

## 实施路线图

### MVP 阶段（2-3 周）

**目标**：验证核心流程

1. **Week 1**：
   - 实现 MCP Server 基础框架
   - 实现 `orchestrate_task` 工具（简单规则）
   - 实现 CLI Session 管理器

2. **Week 2**：
   - 实现 Orchestrator 核心逻辑
   - 支持 2-3 个预设角色
   - 实现产物收集机制

3. **Week 3**：
   - 集成 Codex Adapter
   - 端到端测试
   - 优化错误处理

**验收标准**：
- 能够将"实现登录功能"拆解为 3 个子任务
- 各子任务能正确执行并产出代码
- 主 Session 能汇总结果

### 扩展阶段（1-2 个月）

**目标**：增强能力与稳定性

1. **任务分析智能化**：
   - 使用 LLM 分析任务复杂度
   - 动态生成 Agent 序列
   - 支持自定义角色

2. **并行执行**：
   - 实现依赖图分析
   - 支持多 Session 并行
   - 资源调度优化

3. **产物管理**：
   - 版本控制集成（Git）
   - 产物预览（代码、文档、部署）
   - 回滚机制

4. **成本优化**：
   - Prompt Caching 集成
   - 智能模型路由
   - Token 使用监控

### 企业阶段（3+ 个月）

**目标**：生产级可靠性

1. **高级编排**：
   - 支持循环与条件分支
   - 支持人工审批节点
   - 支持外部系统集成

2. **监控与可观测性**：
   - 任务执行追踪
   - 性能指标监控
   - 成本分析报表

3. **多租户支持**：
   - 用户隔离
   - 资源配额管理
   - 权限控制

## 总结

### 核心优势

1. **架构清晰**：
   - agents-hub 作为主控，职责明确
   - MCP 作为工具层，符合协议设计理念
   - Agent 间通信由 agents-hub 内部实现

2. **扩展性强**：
   - 统一适配器层，易于接入新 Agent 平台
   - MCP 工具可灵活扩展
   - 支持自定义角色和工作流

3. **成本可控**：
   - Prompt Caching 大幅降低成本
   - 智能路由优化模型选择
   - 并行执行提升效率

### 关键风险

1. **MCP 生态成熟度**：
   - MCP 协议较新，工具链可能不完善
   - 需要持续关注协议更新

2. **CLI Session 稳定性**：
   - 长时间运行可能出现内存泄漏
   - 需要完善的错误恢复机制

3. **上下文管理复杂度**：
   - 多 Agent 间的上下文传递需要精心设计
   - 避免上下文爆炸

### 下一步行动

1. **技术验证**：
   - 验证 Claude Code CLI 的 MCP 配置
   - 测试 stdio 通信稳定性
   - 验证 Codex Function Calling 能力

2. **原型开发**：
   - 实现最小可用的 MCP Server
   - 实现简单的 Orchestrator
   - 端到端测试一个简单任务

3. **方案细化**：
   - 设计详细的 API 接口
   - 定义数据模型
   - 编写技术规格文档
