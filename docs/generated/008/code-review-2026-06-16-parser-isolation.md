# Code Review Report

**审查范围**: agents_hub/agent_bridge/bridge.py (HEAD~2..HEAD)
**审查时间**: 2026-06-16
**变更文件**: agents_hub/agent_bridge/bridge.py

## 架构上下文

### 相关 Spec
- `docs/specs/2026-05-23-agent-bridge.md` — agent_bridge 纯执行层规格，执行器-解析器分离的扁平化架构

### 相关设计决策
- `docs/design-decisions/0003-agent-bridge-architecture-choice.md` — SRP + 组合优于继承 (decided)
- `docs/design-decisions/0002-agent-bridge-output-and-session-strategy.md` — session_id 采用调用后返回策略

### 编码规则
- `docs/coding-rules/backend-style.md` — 错误处理分层 + 日志级别规范
- `docs/coding-rules/backend-singleton.md` — 禁止自行实例化单例

## 审查结果

No issues found (confidence >= 80). Checked for bugs, security, performance, and architecture compliance.

### 低于阈值的发现

| # | 类型 | 置信度 | 描述 |
|---|------|--------|------|
| 1 | Testing | 75 | `_create_parser()` 缺少对不支持 platform 的边界测试（else 分支未覆盖） |
| 2 | 代码注释 | 50 | `__init__` 中 `# 创建执行器实例（可复用）` 和 `execute_stream` 中 `# 每次创建新的 parser 实例` 属于冗余注释 |

### 各维度审查详情

| 维度 | 结果 |
|------|------|
| Security | No issues — 枚举类型输入无注入风险，parser 不持有凭据，每次创建消除了跨请求状态泄漏 |
| Performance | No issues — parser `__init__` 极轻量（~1μs），Docker 路径在循环外创建一次 |
| Architecture | No issues — 符合 0003 决策（SRP + 组合），Parser 不在 backend-singleton 单例表中 |
| Code Quality | No issues — 方法简洁，类型注解完备，SRP 合规 |
| Best Practices | No issues — 工厂方法模式正确，Python 3.10+ union type 惯用写法 |
| Testing | 1 finding (75) — 缺少 unsupported platform 边界测试 |
| Documentation | No issues — docstring 引用 bug 文档路径正确，无过时引用 |
| 代码注释 | 1 finding (50) — 2 处冗余注释 |

## 变更摘要

将 `AgentBridge` 中 parser 从共享单例改为每次调用创建独立实例，消除 asyncio 并发环境下的竞态问题（`CodexParser._thread_id` 串台）。具体变更：

- **移除** `__init__` 中的 `_parsers` 单例字典
- **新增** `_create_parser(platform)` 工厂方法，每次返回新实例
- **修改** `execute_stream` 和 Docker 执行路径使用 `_create_parser()`
- **修复** Docker 路径中 parser 创建位置（从循环内移到循环外，避免丢失工具调用跨行状态）

AgentBridge、Executor、DockerManager 保持单例不变。19 个测试全部通过。
