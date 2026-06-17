---
version: 1.0
created_at: 2026-06-16
updated_at: 2026-06-16
last_updated: 2026-06-16
abstract: 补记：解释为什么删除 GroupChatContext 中间层——从"Context 持有 Repository"到"引入 Runtime 由 Context 持有"再到"删除 Context 直接用 Runtime"的演进过程
status: decided
---

# GroupChatContext 中间层移除决策

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 补记演进历史和决策原因 |

## 问题界定

### 问题简述

Core 模块的 GroupChatContext 层经历了三次架构调整：最初 Context 直接持有 Repository 管理状态，后来引入 Runtime 作为 SSOT 但由 Context 持有，最终发现 Context 沦为透传包装层被彻底删除。需要记录这个演进过程，解释为什么最终选择删除 Context。

### 讨论范围

- GroupChatContext 的职责演变
- Runtime 引入后 Context 的定位问题
- 删除 Context 的决策依据和影响

### 非讨论范围

- Runtime/State 的 SSOT 策略（已在 [0009-core-runtime-ssot-choice.md](./0009-core-runtime-ssot-choice.md) 中记录）
- 并发安全修复（属于 P0 bug 修复，非架构决策）

### 问题深度

涉及架构原则：中间层存在的价值判断、渐进式重构的时机选择、"快速修改"与"架构整洁"的权衡。

## 现状

当前架构已删除 GroupChatContext，Agent 直接持有 GroupChatRuntime：

```
GroupChat → GroupChatRuntime → GroupChatRuntimeState / Repository
     ↓
  Agent (直接持有 runtime)
```

源代码和测试代码中 0 个 GroupChatContext 残留引用。

## 演进历史

| 版本 | 方案 | 解决的问题 | 引入的新问题 |
| ---- | ---- | ---------- | ------------ |
| v1 | GroupChatContext 直接持有 Repository | 统一群聊状态管理入口 | 文件和内存状态来源混乱，同一状态有时来自内存有时重新读文件，产生状态偏差 |
| v2 | 引入 GroupChatRuntime 作为 SSOT，由 GroupChatContext 持有 | 运行态以内存为 SSOT，文件作为持久化副本，解决状态来源混乱 | Context 沦为透传层，9/10 方法是 Runtime 的简单包装，增加调用链长度和维护成本 |
| v3 | 删除 GroupChatContext，Agent 直接持有 Runtime | 消除无价值的中间层，简化调用链 | — |

### v1 → v2：引入 Runtime

**触发问题**：内部状态混乱。GroupChatContext 创建并持有 Repository，但 GroupChat、Agent、AgentContext 等对象穿透 `group_chat_context.repository` 直接访问文件持久化。同一份状态有时从内存读、有时从文件重新读取，文件和内存都像"权威数据源"但不能天然同步。

**决策**：引入 GroupChatRuntime 和 GroupChatRuntimeState，以内存为运行期 SSOT，文件作为持久化副本。

**快速修改策略**：为了最小化改动，Runtime 由 GroupChatContext 持有，Context 作为中间层调用 Runtime 的方法。当时 Repository 保留在 Context 层，没有立即调整依赖方向。

### v2 → v3：删除 Context

**触发问题**：Context 层耦合严重。引入 Runtime 后，GroupChatContext 的 10 个方法中有 9 个是 Runtime 的简单透传：

```python
# group_chat_context.py - 典型透传方法
async def update_agent_member_info(self, agent_result):
    await self.runtime.update_agent_member_info_from_result(agent_result)

async def add_message(self, agent_result):
    await self.runtime.add_message(agent_result)
```

**具体问题**：

1. **调用链冗长**：`GroupChat → Context → Runtime → Repository`，Context 只增加了一层间接调用
2. **职责边界模糊**：Context 没有独立的业务逻辑，只是 Runtime 的包装
3. **维护成本高**：修改 Runtime 接口必须同步修改 Context 的对应方法
4. **数据访问路径混乱**：同一份数据（如 agent_member_infos）有 3 种访问方式

**评估**：分析 Context 层 10 个方法，9 个是透传或别名，只有 `load()` 方法有少量编排逻辑（调用 Runtime 的 load）。这 9 个透传方法不提供任何额外价值。

**决策**：删除 GroupChatContext，将剩余的编排逻辑（load）移入 GroupChat，Agent 直接持有 Runtime。

## 最终决策

删除 GroupChatContext 中间层，采用 `Agent → GroupChatRuntime → State/Repository` 的扁平架构。

## 决策原因

1. **中间层无业务价值**：9/10 方法是透传，不增加任何业务逻辑或数据转换，只是增加了调用链长度
2. **降低维护成本**：消除 Runtime 接口变更时必须同步修改 Context 的负担
3. **简化调用链**：从 4 层（GroupChat → Context → Runtime → Repository）减少到 3 层（GroupChat → Runtime → Repository）
4. **渐进式重构的自然收尾**：v2 引入 Runtime 时为了快速修改保留了 Context，这是合理的渐进策略；但当 Runtime 稳定后，Context 的存在就变成了技术债务
5. **34 处改动、5 文件修改、1 文件删除**——改动范围可控，风险可接受

## 后续影响

- GroupChat 直接持有 Runtime，承担原来的编排职责
- Agent 直接通过 runtime 访问状态和持久化能力
- 测试代码同步更新，消除所有 Context 引用
- 更新了 6 个 spec 文档适配新架构
