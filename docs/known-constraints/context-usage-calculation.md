---
version: 1.0
created_at: 2026-06-20
updated_at: 2026-06-20
last_updated: 记录 Codex resume token 累计口径与 context_usage 计算限制
abstract: 说明 AgentBridge context_usage 计算的已知限制，包括 Codex resume 输出累计 usage 时的差分方案、Claude cache_read_input_tokens 口径，以及 OpenCode 暂不处理边界。
---

# Context Usage 计算限制

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档，记录 Codex/Claude context usage 计算限制 |

---

## 概述

`context_usage` 用于展示 Agent 当前上下文窗口输入占用，单位为 K tokens。它不是模型总计费 token，也不是整个会话累计 token。

当前实现只能基于 CLI 暴露的 usage 字段估算窗口占用，不直接访问模型内部请求体。因此各平台必须按各自 CLI 输出口径单独处理。

---

## Codex 计算限制

`codex exec --json` 在 resume 已有 session 时，stdout 的最后一条 `turn.completed.usage` 是 session 累计 usage，不是本轮 LLM 调用 usage。

实测关系：

```text
turn.completed.usage.input_tokens == session token_count.info.total_token_usage.input_tokens
```

而真正表示最后一次调用输入量的是 session JSONL 中的：

```text
token_count.info.last_token_usage.input_tokens
```

但 `last_token_usage` 不会出现在 `codex exec --json` stdout 中。因此当前方案是：

1. resume 前读取 session JSONL 最后一条 `token_count.info.total_token_usage` 作为 baseline。
2. 收到 stdout 的 `turn.completed.usage` 后，与 baseline 做差分。
3. 将差分后的 `input_tokens` 作为 `AgentResult.usage.input_tokens` 输出给上层。

这样上层继续使用 `result.usage.input_tokens // 1000` 时，得到的是本轮 LLM 调用的上下文输入占用，而不是会话累计输入量。

---

## Claude 计算方式

Claude CLI 的 usage 字段区分：

```text
usage.input_tokens
usage.cache_read_input_tokens
```

Claude 的历史上下文可能大量命中 `cache_read_input_tokens`。如果目标是估算窗口输入占用，应同时考虑普通输入与缓存读取输入：

```text
context_input_tokens = input_tokens + cache_read_input_tokens
```

历史 bug 记录中也确认过：只看 `input_tokens` 会漏算 Claude resume 后的大量缓存读取上下文。

---

## OpenCode 暂不处理

OpenCode 当前被禁用，不作为 context usage 计算修复范围。后续恢复 OpenCode 时，需要重新实测其 CLI token 输出口径，再决定是否需要类似 Codex 的累计差分或 Claude 的 cache read 合并。

---

## 已知限制

1. Codex 差分依赖执行前能找到对应 session JSONL；找不到时只能退回使用 stdout 原始 `turn.completed.usage`。
2. Codex session 文件写入时序不作为本轮计算依据；当前实现使用执行前 baseline 和 stdout 当前累计值，避免依赖执行后的文件 flush。
3. `context_usage` 只用于 UI 展示和粗略状态判断，不应作为精确计费或模型硬限制判断依据。
