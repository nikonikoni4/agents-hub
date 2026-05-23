# Orchestrator 设计指南

> 本文档为多Agent IM平台的Orchestrator设计提供全面的技术分析框架，不包含特定推荐方案。

## 一、Orchestrator 的职责定义

### 1.1 核心功能

Orchestrator（主Agent协调器）在群聊模式下承担以下职责：

| 职责 | 说明 |
|------|------|
| 意图理解 | 解析用户自然语言输入，识别任务类型和复杂度 |
| 任务拆解 | 将复杂任务分解为可执行的子任务 |
| Agent选择 | 根据任务需求和Agent能力进行匹配 |
| 调度执行 | 管理子任务的执行顺序（串行/并行/依赖） |
| 结果聚合 | 收集各子Agent产出，整合为连贯的最终结果 |
| 异常处理 | 处理失败、超时、冲突等异常情况 |

### 1.2 与现有系统的关系

当前AgentBridge的特征：
- 纯执行层：只负责CLI调用 + 输出解析
- 双接口：`execute_stream()` 流式、`execute()` 非流式
- 无状态：session_id由CLI工具自身管理

Orchestrator作为上层模块，需要：
- 调用AgentBridge执行具体任务
- 管理AgentBridge不涉及的业务状态
- 提供AgentBridge不提供的协调能力

---

## 二、架构模式分析

### 2.1 五种主流编排模式

#### 模式A：中心化 Supervisor（主管模式）

**原理**：一个中心LLM作为Supervisor，接收用户消息后决定路由到哪个子Agent。子Agent完成后将结果返回Supervisor，由其聚合或继续分派。

**工作流**：`用户 → Supervisor(LLM) → 选择子Agent → 子Agent执行 → 结果返回Supervisor → 聚合/继续`

**代表框架**：LangGraph Supervisor、CrewAI Hierarchical Process

**特征**：
- 控制流清晰，易于调试和追踪
- Supervisor能看到全局状态
- 子Agent之间无法直接通信，必须经过Supervisor中转

**局限**：
- Supervisor是单点瓶颈
- 每次路由都需要一次LLM推理，成本较高
- 子Agent数量增加时，Supervisor决策复杂度上升

---

#### 模式B：分层编排（Hierarchical Delegation）

**原理**：多级Supervisor树。顶层Orchestrator拆解为子任务，分配给下级Manager，Manager再分配给具体Worker Agent。

**工作流**：`用户 → 顶层Orchestrator → 子任务分派给Manager → Manager调用Worker → 结果逐层回传聚合`

**代表框架**：CrewAI Hierarchical（多级Crew）、LangGraph Multi-Level Supervisor

**特征**：
- 天然支持复杂任务的递归拆解
- 每层只需关注自己的子域，职责隔离好
- 可以并行执行不同子树的任务

**局限**：
- 延迟累积（每层都是一次LLM调用）
- 架构复杂度高，调试困难
- 层级间的上下文传递容易丢失信息

---

#### 模式C：Selector Group Chat（选择器群聊）

**原理**：多个Agent处于同一个对话中，由一个Selector决定下一个发言的Agent。Agent之间可以看到彼此的消息。

**工作流**：`用户消息进入群聊 → Selector决定下一个发言者 → Agent发言 → 消息进入共享上下文 → Selector继续选择 → 直到任务完成`

**代表框架**：AutoGen SelectorGroupChat、AutoGen GroupChatManager

**特征**：
- 最接近IM群聊的交互模型
- Agent之间可以基于彼此的输出进行补充和修正
- 支持"涌现式协作"

**局限**：
- 控制流不确定，可能出现"乒乓"对话或死循环
- 共享上下文窗口随对话增长而膨胀
- Selector的质量直接决定系统效果

---

#### 模式D：Swarm / Handoff（蜂群/交接模式）

**原理**：Agent之间直接交接控制权，无需中心协调。每个Agent知道自己能做什么以及何时应该交给其他Agent。

**工作流**：`用户 → Agent A → 判断需要Agent B → 直接handoff给Agent B → Agent B处理 → 可能再handoff给Agent C`

**代表框架**：OpenAI Swarm（实验性）、LangGraph Swarm

**特征**：
- 无中心瓶颈，延迟最低
- 每个Agent自治，可独立演化

**局限**：
- 缺乏全局视角，可能导致任务遗漏
- handoff条件定义困难
- 调试极难，需要完整的trace系统

---

#### 模式E：Pipeline / DAG（流水线/有向无环图）

**原理**：将任务流程定义为一个DAG，每个节点是一个Agent或处理步骤。根据依赖关系自动调度执行顺序。

**工作流**：`用户输入 → DAG解析 → 按拓扑序执行节点 → 并行分支自动并发 → 汇合点等待 → 最终输出`

**代表框架**：LangGraph（核心机制）、CrewAI Flows、Temporal + Agent

**特征**：
- 执行顺序确定性强，可预测
- 天然支持并行和依赖管理

**局限**：
- 需要预先定义DAG结构，灵活性差
- 不适合开放式对话和动态调整

---

### 2.2 模式对比矩阵

| 维度 | Supervisor | 分层 | Selector群聊 | Swarm | DAG |
|------|------------|------|--------------|-------|-----|
| 控制流确定性 | 高 | 高 | 低 | 低 | 高 |
| 灵活性 | 中 | 中 | 高 | 高 | 低 |
| 调试难度 | 低 | 中 | 中 | 高 | 低 |
| 并行支持 | 有限 | 好 | 有限 | 有限 | 好 |
| IM适配度 | 中 | 低 | 高 | 中 | 低 |
| 实现复杂度 | 低 | 高 | 中 | 中 | 中 |

---

## 三、核心组件设计

### 3.1 任务拆解（Task Decomposition）

#### 方案对比

| 方案 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| 规则引擎 | 预定义模板匹配 | 延迟低、可控性强 | 覆盖面窄、维护成本高 |
| LLM推理 | 大模型理解意图并生成子任务 | 灵活、覆盖广 | 延迟高、不确定性、成本 |
| 混合模式 | 规则优先，LLM兜底 | 平衡速度与灵活性 | 架构复杂度增加 |

#### 子任务数据结构要素

设计子任务结构时需要考虑的字段：

| 字段 | 说明 | 是否必需 |
|------|------|---------|
| id | 唯一标识 | 是 |
| description | 任务描述 | 是 |
| required_skills | 所需能力标签 | 否 |
| required_tools | 所需工具 | 否 |
| depends_on | 依赖的前置任务ID | 否 |
| timeout_seconds | 超时阈值 | 否 |
| retry_policy | 重试策略 | 否 |
| fallback_agent | 降级备选Agent | 否 |

---

### 3.2 Agent选择（Agent Selection）

#### 选择因素

| 因素 | 说明 | 权重考虑 |
|------|------|---------|
| 技能匹配度 | Agent能力标签与任务需求的匹配程度 | 通常最高 |
| 工具匹配度 | Agent可用工具与任务所需工具的匹配 | 高 |
| 当前负载 | Agent当前正在处理的任务数 | 中 |
| 历史成功率 | Agent过去完成任务的成功率 | 中 |
| 响应延迟 | Agent的平均响应时间 | 低 |
| 成本 | Agent的调用成本（token消耗等） | 低 |

#### 选择策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| best_fit | 综合评分选择最佳匹配 | 通用场景 |
| round_robin | 轮询分配 | 负载均衡 |
| cost_optimized | 优先选择低成本Agent | 成本敏感场景 |

---

### 3.3 调度策略（Scheduling）

#### 三种调度模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| 串行 | 前一个完成才执行下一个 | 有强依赖关系的任务 |
| 并行 | 所有任务同时执行 | 无依赖关系的任务 |
| DAG | 基于依赖关系的拓扑序调度 | 混合依赖关系的复杂任务 |

#### 状态机设计

任务状态通常包括：

```
PENDING → QUEUED → RUNNING → COMPLETED
                    ↓   ↓
                 FAILED  TIMEOUT
                    ↓       ↓
                 RETRYING ←─┘
                    ↓
                 FAILED_FINAL
```

需要定义：
- 状态转换规则（哪些状态可以转换到哪些状态）
- 转换触发条件（什么事件触发状态转换）
- 转换副作用（状态转换时需要执行的操作）

---

### 3.4 结果聚合（Result Aggregation）

#### 聚合策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| 拼接（concat） | 简单拼接所有子任务结果 | 结果独立、无需整合 |
| 合并（merge） | 用LLM智能合并为连贯文本 | 需要生成人类可读摘要 |
| 投票（vote） | 多个Agent执行同一任务时取多数结果 | 需要提高可靠性 |

#### 聚合输入

聚合器需要的信息：
- 原始用户任务（用于理解上下文）
- 各子任务的执行结果
- 执行状态（成功/失败/超时）
- 执行元数据（耗时、token消耗等）

---

## 四、状态管理

### 4.1 需要管理的状态类型

| 状态类型 | 说明 | 关键字段示例 |
|---------|------|-------------|
| 会话状态 | 用户与Agent的对话会话 | session_id, status, turn_count |
| 任务状态 | Orchestrator拆解的任务 | task_id, status, retry_count, depends_on |
| Agent状态 | Agent运行时状态 | agent_id, status, current_task_id |

### 4.2 状态关系模型

```
Conversation ──── has many ──── Session
    │                              │
    │                        assigned to Agent
    │                              │
    └── has many ── Task ─────────┘
                        │
                   depends on
                        │
                       Task
```

### 4.3 持久化方案选项

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| 纯内存 | 最简单、零依赖 | 重启丢失、无法恢复 | 开发/原型阶段 |
| SQLite | 零部署、ACID事务、Python内置 | 单机限制 | 桌面端应用 |
| PostgreSQL | 功能完整、支持并发 | 需要外部服务 | 服务端部署 |
| 事件溯源 | 完整历史、可审计 | 复杂度高 | 需要审计追踪 |

### 4.4 事件日志设计

即使选择快照存储，也建议保留事件日志用于：
- 调试和问题排查
- 性能分析
- 审计追踪

事件日志字段建议：
| 字段 | 说明 |
|------|------|
| event_id | 自增主键 |
| timestamp | 事件时间 |
| entity_type | 实体类型（session/task/agent） |
| entity_id | 实体ID |
| event_type | 事件类型（created/status_change/error） |
| from_state | 变更前状态 |
| to_state | 变更后状态 |
| payload_json | 事件负载 |
| correlation_id | 关联ID（追踪一次操作的所有事件） |

---

## 五、容错机制

### 5.1 故障分类

| 故障类型 | 示例 | 影响范围 | 检测方式 |
|---------|------|---------|---------|
| Agent进程崩溃 | CLI子进程意外退出 | 单个Agent | 进程退出码 |
| Agent超时 | CLI执行时间过长 | 单个Agent | 超时计时器 |
| 网络中断 | API调用失败 | 单个Agent | 连接错误捕获 |
| 系统崩溃 | Orchestrator进程被杀 | 全局 | 启动时状态检查 |
| 死锁 | 任务间互相等待 | 多个Agent | 等待图检测 |

### 5.2 重试策略

需要考虑的参数：
| 参数 | 说明 | 典型值 |
|------|------|--------|
| max_retries | 最大重试次数 | 2-3次 |
| base_delay | 基础延迟 | 1秒 |
| max_delay | 最大延迟 | 60秒 |
| backoff_factor | 退避因子 | 2（指数退避） |
| jitter | 抖动范围 | 10%（避免惊群效应） |

### 5.3 Agent健康监控

监控指标：
| 指标 | 说明 | 阈值考虑 |
|------|------|---------|
| 心跳间隔 | Agent报告存活的频率 | 30秒 |
| 心跳超时 | 多久未收到心跳视为异常 | 3倍心跳间隔 |
| 连续错误次数 | 连续失败的次数 | 5次触发降级 |
| 进程存活 | CLI子进程是否仍在运行 | PID检查 |

### 5.4 崩溃恢复

Orchestrator启动时需要处理的遗留状态：
1. 中断的任务（RUNNING/QUEUED状态）→ 标记为FAILED，触发重试
2. 活跃的Agent状态 → 重置为IDLE
3. 活跃的会话状态 → 标记为可恢复

---

## 六、冲突处理

### 6.1 冲突场景

| 场景 | 说明 | 严重程度 |
|------|------|---------|
| 文件写入冲突 | 多个Agent同时修改同一文件 | 高 |
| 资源竞争 | 多个Codex Agent使用同一CODEX_HOME | 高 |
| 状态竞争 | 多个任务同时更新同一Agent状态 | 中 |
| 会话冲突 | 同一对话中多个Agent同时回复 | 低 |

### 6.2 冲突解决策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| 工作区隔离 | 每个任务独立工作区，完成后合并 | 并行子任务 |
| 文件级锁 | 操作同一文件时强制顺序执行 | 有文件依赖的任务 |
| Git分支隔离 | 每个Agent独立分支，Orchestrator合并 | 代码修改场景 |
| 乐观锁 | 更新时检查版本，冲突则重试 | 状态更新 |

### 6.3 冲突解决优先级

当冲突不可避免时的处理顺序：
1. 用户手动干预（最高优先级）
2. 先到先得（先开始执行的任务优先）
3. 重试次数少的优先（新任务让路给已重试多次的任务）
4. Orchestrator裁决（根据任务意图决定）

---

## 七、与AgentBridge的集成

### 7.1 接口选择

| AgentBridge接口 | 用途 | 使用场景 |
|----------------|------|---------|
| execute_stream() | 流式输出 | 面向用户的群聊发言 |
| execute() | 非流式输出 | Orchestrator内部A2A调用 |

### 7.2 集成模式

```
Orchestrator
    │
    ├── 需要流式展示给用户 ──→ execute_stream() ──→ WebSocket转发
    │
    └── 内部子任务调用 ──→ execute() ──→ 获取完整结果后处理
```

### 7.3 Session管理

- 首次调用agent_bridge后从返回事件中获取session_id
- session_id存储在会话状态中
- 后续恢复会话时从状态存储读取并传入agent_bridge

---

## 八、设计决策清单

设计Orchestrator时需要做出的决策：

| 决策点 | 选项 | 需要考虑的因素 |
|--------|------|---------------|
| D1: 架构模式 | Supervisor / 分层 / Selector群聊 / Swarm / DAG | 交互模型、复杂度、灵活性 |
| D2: 任务拆解方式 | 规则 / LLM / 混合 | 延迟、成本、覆盖面 |
| D3: Agent选择算法 | best_fit / round_robin / cost_optimized | 匹配度、负载均衡、成本 |
| D4: 调度策略 | 串行 / 并行 / DAG | 依赖关系、资源约束 |
| D5: 结果聚合方式 | 拼接 / LLM合并 / 投票 | 结果质量、延迟、成本 |
| D6: 持久化方案 | 内存 / SQLite / PostgreSQL / 事件溯源 | 数据量、可靠性要求、部署环境 |
| D7: Agent间通信 | 共享上下文 / Orchestrator中转 / 混合 | 信息传递效率、上下文膨胀 |
| D8: 失败处理策略 | 失败即停 / 重试 / 换Agent重试 | 可靠性要求、成本 |
| D9: 冲突处理策略 | 隔离 / 锁 / Git分支 | 冲突类型、复杂度 |

---

## 九、主流框架参考

### 9.1 LangGraph

- 核心抽象：Graph（状态机）
- 编排模式：Supervisor/Swarm/DAG均支持
- 状态管理：内置Checkpoint
- 流式支持：原生token级流式

### 9.2 CrewAI

- 核心抽象：Crew + Task + Agent
- 编排模式：Sequential/Hierarchical
- 特点：角色模型清晰，Agent有明确的role/goal/backstory

### 9.3 AutoGen

- 核心抽象：Agent + GroupChat
- 编排模式：SelectorGroupChat/Swarm
- 特点：群聊模型天然匹配IM场景

---

## 十、实施路径参考

### 阶段划分

| 阶段 | 目标 | 核心功能 | 预估工作量 |
|------|------|---------|-----------|
| Phase 1 | 最小可用 | AgentRegistry + 简单Router + 单步路由 | 2-3周 |
| Phase 2 | 任务拆解 | LLM意图分析 + DAG执行 + 结果聚合 | 3-4周 |
| Phase 3 | 高级特性 | 失败降级 + 用户确认 + Agent协作 | 按需 |

### 渐进式演进

1. 从最简单的单步路由开始（只做Agent选择，不做任务拆解）
2. 逐步引入LLM驱动的意图分析
3. 最后实现复杂的DAG调度和容错机制

---

## 附录：术语表

| 术语 | 说明 |
|------|------|
| Orchestrator | 主Agent协调器，负责任务拆解和分派 |
| Agent | 执行具体任务的AI实体（如Claude Code、Codex） |
| AgentBridge | Agent适配器层，负责CLI调用和输出解析 |
| Supervisor | 中心化的路由/协调组件 |
| Selector | 在群聊中选择下一个发言Agent的组件 |
| DAG | Directed Acyclic Graph，有向无环图 |
| Handoff | Agent间直接交接控制权 |
| Session | 用户与Agent的一次对话会话 |
| Task | Orchestrator拆解的可执行子任务 |

---

*文档创建时间：2026-05-23*
*文档类型：技术研究指南*
