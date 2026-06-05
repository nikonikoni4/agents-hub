# 规则文档模板

## 基础模板

```markdown
---
updated_at: YYYY-MM-DD
trigger: 编写 <模块> 代码时
---

# <Layer> CLAUDE.md

> 上级规则：[../CLAUDE.md]（如果是子模块）

## 编码规则

### <模块> 规则

**禁止**：
- ❌ <具体禁止项>

**示例**：
```typescript
// ✅ 正确
<code>

// ❌ 错误
<code>
```

---

## 决策规则

| 场景 | 决策 |
|------|------|
| X | Y |
```

## 模板说明

### 元数据部分
- `updated_at`：最后更新日期
- `trigger`：触发场景，说明什么时候需要遵守这些规则

### 上级链接
- 子模块必须包含指向上级的链接
- 格式：`> 上级规则：[../CLAUDE.md]`
- 顶级 CLAUDE.md 不需要此链接

### 编码规则部分
- **只写禁止项**：不写"允许"或"强制"（这些是教学性内容）
- **必须有示例**：正确 vs 错误的代码对比
- **示例要具体**：不要用抽象的占位符

### 决策规则部分
- **快速决策表**：帮助 AI 快速判断"放哪里"、"何时创建"
- **场景具体**：不要用"某个功能"，要用"单聊功能"

## 反模式（不要这样写）

### ❌ 错误示例 1：包含教学性内容

```markdown
## 什么是单一职责原则

单一职责原则（SRP）是指一个模块只做一件事...
```

**问题**：AI 已经知道 SRP，不需要解释

---

### ❌ 错误示例 2：没有具体示例

```markdown
**禁止**：
- ❌ 不要在组件中写业务逻辑
```

**问题**：没有具体代码示例，AI 不知道什么是"业务逻辑"

---

### ❌ 错误示例 3：重复上级内容

```markdown
# features/CLAUDE.md

## 强制约束
1. 禁止 feature 之间直接依赖
2. 单向依赖：components → hooks → store → core
```

**问题**：这些约束在上级 `frontend/CLAUDE.md` 已定义

---

### ❌ 错误示例 4：抽象的决策表

```markdown
| 场景 | 决策 |
|------|------|
| 某个功能 | 放在某个地方 |
```

**问题**：太抽象，AI 无法判断

---

## ✅ 正确示例

```markdown
---
updated_at: 2026-06-02
trigger: 编写 features/ 下的代码时
---

# Features CLAUDE.md

> 上级规则：[../../CLAUDE.md]

## 编码规则

### Components 规则

**禁止**：
- ❌ 直接调用 `wsManager.send()` 或 `api.xxx()`

**示例**：
```typescript
// ✅ 正确
function ChatWindow() {
  const { messages, sendMessage } = useChat();
  return <div>{messages.map(...)}</div>;
}

// ❌ 错误
function ChatWindow() {
  wsManager.send(...);  // 必须通过 hooks
}
```

---

## 决策规则

| 场景 | 决策 |
|------|------|
| 单聊功能 | 复用 `features/chat/`（通过 props 区分） |
| 消息搜索 | 创建 `features/search/`（独立功能） |
```
