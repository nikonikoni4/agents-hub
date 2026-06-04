---
version: 1.0
created_at: 2026-06-04
updated_at: 2026-06-04
last_updated: 2026-06-04
abstract: 确定 core runtime 运行态的单一数据源（SSOT）策略——选择以内存为准，文件作为持久化副本，由 Runtime 提供统一接口
status: decided
---

# Core Runtime 运行态 SSOT 选择

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题界定

### 问题简述

Core 模块的运行态状态来源不清晰，导致同一状态既可能来自内存对象，也可能重新从文件读取，造成潜在的数据不一致风险。需要明确确定运行态的单一数据源（SSOT）究竟是以文件为准还是以内存为准。

### 讨论范围

- Core runtime 的运行态状态管理策略（group chat session、agent session、context load state 等长生命周期运行态）
- 内存与文件的同步机制
- `GroupChat`、`GroupChatContext`、`Repository` 的职责边界
- API/service 层如何获取运行态信息

### 非讨论范围

- Roles 和 Skills 等配置/资源模块（它们更适合文件优先策略）
- 未加载群聊的历史查询（这些仍然需要读取文件）
- Event Sourcing / WAL 等复杂持久化方案（不在当前阶段引入）
- `AgentCallManager` 和 `TaskManager` 的状态迁移（后续再评估）

### 问题深度

这是涉及架构原则和长期维护方式的深层问题。SSOT 选择不仅影响当前代码组织，还会影响：

- 未来状态一致性保证
- 并发访问策略
- 持久化失败处理
- 模块职责划分
- 测试和调试复杂度

## 现状

当前 core 的主要问题不是单个函数错误，而是运行态状态来源混乱：

1. `GroupChatContext` 创建并持有 `GroupChatRepository`
2. `GroupChat`、`Agent`、`AgentContext` 等对象会穿透 `group_chat_context.repository` 访问文件持久化能力或 `project_path`
3. 同一类状态有时来自内存对象，有时重新从文件读取
4. API / service 层未来如果继续通过文件读取运行态信息，会扩大不一致风险

**核心风险**：文件和内存都像"权威数据源"，但二者并不能天然保持同步。一旦某个路径只改内存、另一个路径读文件，或者某个路径保存失败但内存继续前进，就会产生难以定位的状态偏差。

**已观察到的穿透访问**：

- `GroupChat` 直接读写 repository 保存 metadata、agent session state
- `Agent` 通过 `group_chat_context.repository.project_path` 获取项目路径
- `AgentContext` 直接保存 agent session state
- `GroupChatContext` 内部大量直接调用 repository load/save

## 可选方案

### 方案 A：以文件为 SSOT

文件作为唯一权威数据源，所有读取都从文件获取最新状态。

**优势**

- 无需担心内存与文件不一致
- 进程重启或崩溃后天然恢复到最新状态
- 多进程访问同一群聊时更容易保持一致（通过文件锁）
- 实现简单，不需要复杂的内存状态管理

**劣势**

- 每次查询都需要 IO，性能差
- 文件锁会成为性能瓶颈和并发限制
- 频繁读写文件会增加磁盘压力和故障风险
- 无法利用内存提供快速查询
- Agent 执行过程中的频繁状态更新会导致大量文件操作
- 不符合运行期系统的常见设计模式

### 方案 B：以内存为 SSOT，同步持久化

内存作为运行期单一数据源，文件作为持久化副本和恢复源。所有运行态查询读内存，所有状态修改先改内存再同步保存到文件。

**优势**

- 运行期查询性能高，无需 IO
- 符合常见的运行期系统设计模式
- 清晰的职责划分：内存负责运行态，文件负责持久化和恢复
- 可以更灵活地优化内存结构和查询接口
- 减少文件 IO 频率，降低磁盘压力
- 便于后续引入缓存、批量写入等优化策略

**劣势**

- 需要明确的同步持久化机制
- 保存失败时需要处理状态不一致（需要显式暴露错误）
- 内存状态管理增加代码复杂度
- 需要新增 `GroupChatRuntimeState` 和 `GroupChatRuntime` 抽象层

### 方案 C：混合策略（不同状态类型使用不同策略）

根据状态特点选择不同策略：长生命周期运行态用内存 SSOT，配置/资源态用文件优先。

**优势**

- 灵活性高，可以针对不同场景优化
- 配置类数据仍然可以保持简单的文件读取
- 运行态数据获得性能优势

**劣势**

- 策略混合会增加理解成本
- 需要明确划分哪些状态属于哪种类型
- 可能导致代码路径更复杂

## 最终决策

选择 **方案 B：以内存为 SSOT，同步持久化**，并在此基础上应用方案 C 的部分思想——对配置/资源类模块保持文件优先。

具体策略：

```text
启动 / 加载：
  file -> repository.load -> runtime state

运行期间：
  read/write runtime state

关键写操作：
  update runtime state -> sync persist file

重启恢复：
  file -> runtime state
```

更准确的定义：

```text
内存是运行期 SSOT。
文件是 durable copy / recovery source。
```

**实现方式**：引入 `GroupChatRuntime` 和 `GroupChatRuntimeState`

- `GroupChatRuntimeState`：保存运行期内存 SSOT
- `GroupChatRuntime`：持有 State 和 Repository，提供统一的 query/command 接口
- `GroupChat`：收窄为生命周期协调器，不再作为状态大仓库
- `GroupChatContext`：依赖 Runtime，不再拥有 Repository

## 决策原因

### 原因 1：性能与用户体验

运行期系统的核心特点是频繁查询和更新状态。如果每次查询都读文件，性能会成为明显瓶颈：

- API 层获取群聊信息、成员列表、消息列表等操作会变慢
- Agent 执行过程中需要频繁读取 context load state、session state
- 前端实时刷新需要快速响应

**内存 SSOT 可以提供亚毫秒级查询响应，而文件 IO 通常需要几毫秒到几十毫秒。**

### 原因 2：符合运行期系统的常见设计模式

几乎所有成熟的运行期系统（数据库、消息队列、应用服务器）都采用内存优先、持久化副本的设计：

- 数据库：内存中的 buffer pool，WAL 日志持久化
- Redis：内存存储，RDB/AOF 持久化
- Web 应用：内存中的 session，数据库持久化

**以文件为 SSOT 的设计在运行期系统中非常罕见，通常只用于纯配置管理或低频访问场景。**

### 原因 3：清晰的职责边界

内存 SSOT 策略迫使我们明确划分职责：

- **内存状态**：运行期权威数据，快速查询和修改
- **文件持久化**：durable copy，用于恢复和跨会话保存
- **Runtime**：统一的状态管理入口，封装同步持久化逻辑
- **Repository**：纯粹的文件 IO 适配器，不参与业务判断

这种划分比"文件和内存都是权威源"的混乱状态要清晰得多。

### 原因 4：可扩展性

内存 SSOT 为未来优化留下空间：

- 可以引入批量写入减少 IO
- 可以引入异步快照（当前阶段不做，但架构支持）
- 可以引入内存缓存优化
- 可以更容易地支持事务性操作

文件 SSOT 则几乎没有优化空间，性能天花板很低。

### 原因 5：同步持久化的风险可控

内存 SSOT 的主要风险是持久化失败导致不一致。但这个风险是可控的：

1. **显式错误暴露**：保存失败时抛出错误，设置 `persistence_error` 标记
2. **阻止后续操作**：高风险操作检查 persistence_error，拒绝继续执行
3. **不追求完整回滚**：因为 Agent 执行、外部工具调用等副作用本身不可回滚

**关键是避免系统在"内存已前进、文件没跟上"的状态下静默运行。**

## 后续影响

### 代码结构影响

1. 新增 `GroupChatRuntimeState` 和 `GroupChatRuntime` 模块
2. `GroupChatContext` 不再拥有 Repository，改为依赖 Runtime
3. `GroupChat` 职责收窄为生命周期协调器
4. API/service 层通过 Runtime query 获取稳定 dict，不直接访问内部 dataclass

### 持久化机制

所有 runtime command 必须遵循：

```python
async def command():
    # 1. 修改内存状态
    self.state.xxx = new_value
    
    # 2. 同步持久化
    try:
        await self.repository.save_xxx()
        self.state.persistence_error = None
    except Exception as e:
        self.state.persistence_error = str(e)
        raise
```

### 配置/资源模块保持文件优先

Roles 和 Skills 不纳入 `GroupChatRuntimeState`，它们保持文件优先策略：

| 类型 | 示例 | 数据来源策略 |
| ---- | ---- | ------------ |
| 长生命周期运行态 | group chat session、agent session、context load state、runtime flags | 内存 SSOT，同步落盘 |
| 配置 / 资源态 | roles、skills | 文件优先，可缓存 |
| 只读列表 / 历史索引 | 未加载群聊列表、历史 metadata | 文件读取或 read model |

### 测试策略

1. Runtime 层单元测试覆盖 load/query/command/persist 路径
2. 集成测试验证 Context/Agent/API 通过 Runtime 正确读写状态
3. 持久化失败测试验证 error flag 和异常处理

### 迁移路径

实施计划已编写为 `docs/superpowers/plans/2026-06-04-core-runtime-ssot-implementation.md`，分 8 个任务逐步迁移：

1. 添加 Runtime State 和 Runtime 单元测试
2. 实现 Runtime load、query、command
3. 重构 Context 使用 Runtime
4. 将 Runtime 接入 GroupChat 生命周期
5. 替换 Agent 的 Repository 访问
6. 更新 GroupChatManager 目录和加载路径
7. 更新 GroupChatService 使用 Runtime query/command
8. 添加守卫检查和全面回归测试

### 验收标准

重构完成后应满足：

1. `GroupChatContext` 不再创建并拥有 Repository
2. 运行中的群聊状态查询不通过 repository 重新读取当前状态
3. API / service 不能直接访问 `context.repository`
4. Agent / AgentContext 不直接保存 repository 文件
5. GroupChat 只组装依赖和管理生命周期，不成为状态大仓库
6. 所有运行态写操作都有明确 command 路径
7. Command 修改内存后同步持久化，保存失败有显式错误或 degraded 标记
8. Roles / skills 保持配置/资源模块定位，不被强行纳入 runtime state
