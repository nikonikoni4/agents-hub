# CLAUDE.md 运行时注入机制研究报告

> 调研日期：2026-05-31
> 调研目的：验证 CLAUDE.md 的加载位置、是否重复发送、缓存行为，为 MCP tools 设计中的 Runtime Prompt 注入方案提供依据。

---

## 1. 核心问题

在设计 Agent 系统的 Runtime Prompt 注入时，需要确认：

1. CLAUDE.md 加载在 API 调用的哪个位置（system prompt vs user message）
2. 每轮对话是否重复发送 CLAUDE.md 内容
3. 是否通过缓存避免重复消耗 token

## 2. 实验设计

### 实验 1：基础验证（小文件）

- 会话 ID：`1eed7bbc-6a67-480d-91e1-e9d09c139093`
- CLAUDE.md 大小：原始大小（约 2KB）
- 对话轮次：2 轮，用户消息分别为 "测试" 和 "测试连接"

### 实验 2：大文件验证（40KB）

- 会话 ID：`1f6c6237-5e2c-4951-adcf-740e3b20b501`
- CLAUDE.md 大小：扩充到 40KB
- 对话轮次：2 轮，用户消息均为 "测试连接"

## 3. 实验结果

### 实验 1 数据

| 轮次 | 用户消息 | input_tokens | cache_read | total |
|------|---------|-------------|-----------|-------|
| 1 | "测试" | 31492 | 2048 | 33540 |
| 2 | "测试连接" | 357 | 33536 | 33893 |

**差值：353 tokens**（仅用户消息差异）

### 实验 2 数据

| 轮次 | 用户消息 | input_tokens | cache_read | total |
|------|---------|-------------|-----------|-------|
| 1 | "测试连接" | 47050 | 4096 | 51146 |
| 2 | "测试连接" | 54 | 51136 | 51190 |

**差值：44 tokens**

### 关键推算

- 实验 2 中 CLAUDE.md 约 40KB（约 12000 tokens）
- 如果每轮重复发送，第二轮 total 应比第一轮多 ~12000 tokens
- 实际差值仅 44 tokens，证明 **CLAUDE.md 未被重复发送**

## 4. 结论

### 4.1 CLAUDE.md 的加载行为

| 行为 | 结论 |
|------|------|
| 每轮都加载 | 是 — 每次 API 调用都包含 CLAUDE.md |
| 重复发送 | 否 — 通过 prompt cache 复用，不重复消耗 token |
| 持久化到对话历史 | 否 — JSONL 聊天记录中不包含 CLAUDE.md 内容 |

### 4.2 加载位置

- CLAUDE.md 内容在 JSONL 对话记录中不可见（用户消息只有纯文本）
- 但从 token 数量（第一轮 input_tokens 远大于用户消息长度）可证明它被包含在 API 请求中
- 具体是在 `system` 参数还是 `messages` 中，JSONL 层面无法确认
- Claude Code 的 `<system-reminder>` 标签机制暗示可能注入在 user message 中

### 4.3 缓存机制

```
第一轮: [system prompt + CLAUDE.md + 用户消息] → 写入缓存
第二轮: [system prompt + CLAUDE.md + 用户消息] → CLAUDE.md 部分从缓存读取
```

- 第一轮：大量 input_tokens（首次发送，写入缓存）
- 后续轮次：大量 cache_read_input_tokens（从缓存读取），极少 input_tokens（仅新增内容）

## 5. 对 MCP Tools 设计的启示

### 5.1 Runtime Prompt 注入方案

CLAUDE.md 的机制完全符合 Runtime Prompt 注入的需求：

- 每轮都注入最新状态（identity、team、workboard）
- 通过 prompt cache 避免重复 token 消耗
- 不污染对话历史

### 5.2 推荐方案

参照 CLAUDE.md 的机制，Runtime Prompt 注入应：

1. **放在 system prompt 层**（而非 user message），以获得最佳缓存效果
2. **静态部分**（identity、team）变化极少，缓存命中率高
3. **动态部分**（workboard）变化频繁，但体积小，缓存失效成本低

### 5.3 注意事项

- prompt cache 是前缀匹配，system prompt 中越靠前的内容缓存越稳定
- 频繁变化的内容应放在 system prompt 末尾，减少缓存失效范围
- 如果 Runtime 信息放在 user message 中（如 `<system-reminder>` 方式），会随对话历史累积，但 Claude Code 似乎接受了这个 trade-off

---

*最后更新：2026-05-31*
