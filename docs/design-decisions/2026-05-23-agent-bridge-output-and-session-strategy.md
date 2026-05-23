---
version: 1.0
created_at: 2026-05-23
updated_at: 2026-05-23
last_updated: 2026-05-23
abstract: 确定 agent_bridge 底层统一流式输出策略，以及 session_id 采用调用后返回的处理方式
status: decided
---

# Agent Bridge 输出模式与 session_id 策略决策

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿，确定底层流式输出策略和 session_id 返回策略 |

---

## 一、问题界定

### 问题简述

agent_bridge 模块需要确定两个设计问题：
1. **输出模式**：底层应该统一使用流式输出，还是同时支持流式和非流式？
2. **session_id 处理**：session_id 应该由调用方传入（创建时指定），还是由模块返回（调用后获取）？

### 讨论范围

**范围内**：
- Executor 层的输出模式选择（流式 vs 非流式）
- Bridge 层的接口设计（流式/非流式双接口）
- session_id 的生命周期管理（谁生成、谁传递、何时可用）
- 外部模块（任务管理等）对 session_id 的依赖

**范围外**：
- 具体的 CLI 命令参数细节（已在 spec 中定义）
- 会话持久化存储策略
- 错误重试机制（留白）

### 问题深度

这是一个**接口设计层面的决策**，涉及：
- 底层实现与上层接口的分层策略
- 外部模块的耦合度与控制权权衡
- 跨平台（Claude/Codex）兼容性约束

---

## 二、决策一：底层统一流式输出

### 现状

agent_bridge 需要同时支持 Claude 和 Codex 两个平台的 CLI 调用。两个平台都支持流式输出，但非流式输出的格式和解析方式差异较大。

### 可选方案

#### 方案 A：底层同时支持流式和非流式

Executor 提供两种执行方法：
- `execute_stream()` → 返回流式输出
- `execute()` → 返回非流式输出

**优势**：
- 非流式场景理论上更简单（直接拿结果）

**劣势**：
- Codex 的非流式输出格式不好解析，需要额外适配
- 两套解析逻辑，维护成本翻倍
- 违反 DRY 原则

#### 方案 B：底层统一流式，上层包装（推荐）

Executor 只提供流式输出，Bridge 层包装两种接口：
- `execute_stream()` → 流式，直接透传
- `execute()` → 非流式，内部拼接流式结果后返回

**优势**：
- 解析逻辑只实现一次（DRY）
- Codex 流式输出格式好解析，可靠
- 上层接口灵活，按需选择
- `execute()` 是 `execute_stream()` 的薄包装，无重复实现

**劣势**：
- 非流式场景多一层包装（可忽略不计）

### 最终决策

**选择方案 B：底层统一流式输出，上层提供双接口**

### 决策原因

1. **Codex 约束**：Codex 的非流式输出格式不好解析，底层统一流式更可靠
2. **DRY 原则**：解析逻辑只实现一次，维护成本低
3. **接口灵活**：上层 `execute_stream()` 给人看，`execute()` 给 A2A 用，各取所需
4. **薄包装**：`execute()` 内部复用 `execute_stream()`，不重复实现

---

## 三、决策二：session_id 采用调用后返回策略

### 现状

session_id 是会话的唯一标识，外部模块（如任务管理）需要记录 session_id 以便后续恢复会话。当前有两种管理策略：

### 可选方案

#### 方案 A：调用方传入 session_id（创建时指定）

调用方在第一次调用时生成 session_id 并传入：
```python
session_id = generate_uuid()
async for event in bridge.execute_stream(prompt, config, session_id=session_id):
    ...
# 外部模块直接记录 session_id，无需等待返回
```

**优势**：
- 外部模块在调用前就能拿到 session_id
- 逻辑上更直观：先有 ID，再有会话

**劣势**：
- 需要增加新会话/旧会话标志位（`is_new_session`），接口复杂度增加
- 如果调用失败，session_id 不应被记录，需要额外的错误处理和验证逻辑
- Codex 是否支持指定 session_id 尚未确认，存在平台兼容性风险
- 增加了外部模块的控制负担

#### 方案 B：调用后从返回事件中获取 session_id（推荐）

session_id 由 CLI 工具生成，通过事件返回给调用方：
```python
async for event in bridge.execute_stream(prompt, config):
    session_id = event["session_id"]  # 从事件中获取
    # 外部模块在首次调用后记录 session_id
```

**优势**：
- 接口简洁，不需要额外的标志位
- 不需要额外的验证逻辑（session_id 由 CLI 保证有效）
- 天然适配 Codex（无需确认是否支持指定 ID）
- 调用方只需关注"拿到 ID 后记录"这一条路径

**劣势**：
- 外部模块必须在第一次调用完成后才能获取 session_id
- 任务创建等模块需要在首次会话后才能关联 session_id

### 最终决策

**选择方案 B：session_id 从返回事件中获取**

### 决策原因

1. **简洁性**：接口不需要额外的标志位和验证逻辑，调用方只关心"拿到就记录"
2. **可靠性**：session_id 由 CLI 工具保证有效，不存在"传入了但调用失败"的脏数据问题
3. **Codex 适配**：无需确认 Codex 是否支持指定 session_id，天然兼容
4. **可演进**：如果后续外部模块确实不方便，可以在方案 B 基础上增加方案 A 的支持（向前兼容），但当前不做过度设计

### 对外部模块的影响

任务管理等模块需要调整逻辑：
- **首次调用**：不传 session_id，调用完成后从事件中获取并记录
- **后续调用**：传入已记录的 session_id 恢复会话
- **容错**：如果首次调用失败，不记录 session_id，下次重新创建

---

## 四、相关文档

- [Agent Bridge 设计文档](../superpowers/specs/2026-05-23-agent-bridge-design.md)
- [Agent Bridge 架构决策](./2026-05-23-agent-bridge-architecture-choice.md)
