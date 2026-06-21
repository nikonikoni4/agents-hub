# Loop Feature Issues - 垂直切片清单

本目录包含 Loop（循环）功能的 8 个垂直切片 issue，每个切片都是端到端可验证的独立任务。

## 切片概览

| # | 文件 | 标题 | 类型 | 阻塞 | 用户故事 |
|---|------|------|------|------|---------|
| 1 | [slice-1-data-model-persistence.md](./slice-1-data-model-persistence.md) | 基础数据模型和持久化 | AFK | 无 | 29-33 |
| 2 | [slice-2-agent-state-isolation.md](./slice-2-agent-state-isolation.md) | Agent 状态扩展和循环隔离 | AFK | #1 | 16-19 |
| 3 | [slice-3-loop-context-rendering.md](./slice-3-loop-context-rendering.md) | 循环上下文构造和消息渲染 | AFK | #2 | 10-11, 20-22 |
| 4 | [slice-4-output-validation-retry.md](./slice-4-output-validation-retry.md) | 输出校验和自动重试 | AFK | #3 | 12-15, 24-25 |
| 5 | [slice-5-event-driven-notification.md](./slice-5-event-driven-notification.md) | 事件驱动的节点完成通知 | AFK | #2 | 内部机制 |
| 6 | [slice-6-loop-executor-core.md](./slice-6-loop-executor-core.md) | LoopExecutor 核心循环执行 | AFK | #4, #5 | 10-15, 26-27 |
| 7 | [slice-7-mcp-tools.md](./slice-7-mcp-tools.md) | MCP 工具接口（全部 5 个工具） | AFK | #6 | 1-9 |
| 8 | [slice-8-update-context.md](./slice-8-update-context.md) | 更新 CONTEXT.md | HITL | #1 | 文档维护 |

## 依赖关系图

```
Slice 1: 基础数据模型和持久化
  ├─→ Slice 2: Agent 状态扩展和循环隔离
  │     ├─→ Slice 3: 循环上下文构造和消息渲染
  │     │     └─→ Slice 4: 输出校验和自动重试
  │     │           └─→ Slice 6: LoopExecutor 核心循环执行
  │     │                 └─→ Slice 7: MCP 工具接口
  │     └─→ Slice 5: 事件驱动的节点完成通知
  │           └─→ Slice 6: LoopExecutor 核心循环执行
  │                 └─→ Slice 7: MCP 工具接口
  └─→ Slice 8: 更新 CONTEXT.md (HITL)
```

## 实施顺序建议

**阶段 1：基础设施**
1. Slice 1: 基础数据模型和持久化
2. Slice 8: 更新 CONTEXT.md（并行，HITL）

**阶段 2：Agent 扩展**
3. Slice 2: Agent 状态扩展和循环隔离

**阶段 3：循环机制（可并行）**
4. Slice 3: 循环上下文构造和消息渲染
5. Slice 5: 事件驱动的节点完成通知（与 Slice 3 并行）

**阶段 4：校验和执行**
6. Slice 4: 输出校验和自动重试
7. Slice 6: LoopExecutor 核心循环执行

**阶段 5：集成**
8. Slice 7: MCP 工具接口（端到端验证）

## 关键里程碑

- **Slice 1 完成**：数据层就绪，可以开始 Agent 扩展和文档更新
- **Slice 2 完成**：Agent 支持循环隔离，可以并行开发上下文和通知机制
- **Slice 6 完成**：核心执行引擎就绪，功能基本可用（但无 MCP 接口）
- **Slice 7 完成**：功能完全可用，可以端到端测试

## 类型说明

- **AFK**（Away From Keyboard）：可以由 AI Agent 独立实现和合并，无需人工交互
- **HITL**（Human In The Loop）：需要人工审核、决策或验证

## 参考文档

- PRD: `docs/temp/loop-feature-prd.md`
- MVP 限制说明: `docs/known-contracts/loop-mvp-limitations.md`
- 术语表: `CONTEXT.md`（Slice 8 更新后）

## 注意事项

1. **测试优先**：每个切片都要求单元测试和/或集成测试覆盖
2. **依赖顺序**：严格按照阻塞关系实施，避免返工
3. **端到端验证**：Slice 7 完成后进行完整的端到端测试
4. **文档同步**：Slice 8 需要在实现完成后再次检查术语定义是否准确
5. **日志规范**：遵循编码规则的日志级别要求（INFO/WARNING/ERROR/DEBUG）
6. **异常处理**：遵循分层错误处理规则，使用项目现有的异常体系
