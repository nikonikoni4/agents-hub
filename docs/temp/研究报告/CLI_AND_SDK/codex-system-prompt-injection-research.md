# Codex CLI 系统提示词注入机制研究

**研究日期**: 2026-06-08
**研究目标**: 验证 Codex CLI 的 `instructions` 参数如何注入系统提示词，以及多会话间是否相互干扰
**测试环境**: OpenAI Codex v0.137.0, mimo-v2.5-pro 模型, Windows PowerShell

---

## 一、测试方法

通过 `codex -c "instructions='...'"` 参数注入自定义系统提示词，验证以下两点：

1. 注入内容是否确实出现在系统提示词中
2. 多个独立会话的指令是否会相互干扰

---

## 二、测试结果

### 2.1 单独系统提示词注入

**测试命令**:
```powershell
codex -c "instructions='我是Ami，你将和user讨论codex的系统提示词加载方式'" exec "当前你能看到我单独注入的一段系统提示词吗"
```

**结果**: ✅ 注入成功

Codex 确认注入内容出现在 `<custom_system_prompt>` 标签中，并能完整复述注入的指令内容。

**结论**: `instructions` 参数的内容会被注入到系统提示词的 `<custom_system_prompt>` 标签内，模型可见且遵循。

---

### 2.2 角色名称注入

**测试命令**:
```powershell
codex -c "instructions='你的名称叫做Ami'" exec "你是谁"
```

**结果**: ✅ 角色定义生效

Codex 回复"我是 Ami，你的 AI 助手"，说明 `instructions` 能成功定义角色身份。

---

### 2.3 会话隔离性验证

**测试方法**: 两个独立会话分别注入不同的 token 值，观察是否互相干扰。

**会话 A**:
```powershell
codex -c "instructions='当询问你，你的token是什么时回答A'" exec "你现在需要回答你的token是什么，并且计时一分钟，在一分钟之后再回答..."
```

**会话 B**（会话 A 结束后立即启动）:
```powershell
codex -c "instructions='当询问你，你的token是什么时回答B'" exec "你现在需要回答你的token是什么，并且计时一分钟..."
```

**结果**:

| 会话 | 注入指令 | 第一次回答 | 一分钟后回答 | 结果 |
|------|---------|-----------|-------------|------|
| A | token=A | A | A | ✅ 一致 |
| B | token=B | B | B | ✅ 一致 |

**结论**:
- ✅ 会话间完全隔离，无指令泄漏
- ✅ 同一会话内指令持久稳定，不受时间/上下文影响

---

## 三、核心结论

### 3.1 `instructions` 参数机制

| 特性 | 行为 | 验证结果 |
|------|------|---------|
| 注入位置 | `<custom_system_prompt>` 标签内 | ✅ |
| 角色定义 | 可成功定义 agent 身份 | ✅ |
| 行为控制 | 可控制回答方式（如固定回复值） | ✅ |
| 持久性 | 整个会话内保持不变 | ✅ |
| 会话隔离 | 不同会话间互不干扰 | ✅ |

### 3.2 与 Claude CLI 对比

| 特性 | Codex `-c instructions` | Claude `--append-system-prompt` |
|------|------------------------|--------------------------------|
| 注入方式 | `-c "instructions='...'"` | `--append-system-prompt "..."` |
| 注入位置 | `<custom_system_prompt>` 标签 | 追加到默认系统提示词末尾 |
| 会话隔离 | ✅ 独立会话互不干扰 | ✅ 独立进程互不干扰 |
| 合并机制 | 独立标签，与 AGENTS.md 等共存 | 追加拼接 |

### 3.3 对 agents-hub 的意义

Codex 的 `instructions` 参数是实现角色注入的可靠方式：

1. **可直接用于角色定义** — 通过 `instructions` 注入角色 system prompt，无需依赖 `CODEX_HOME` + AGENTS.md
2. **天然会话隔离** — 每次 `codex exec` 是独立进程，不用担心指令污染
3. **与 `CODEX_HOME` 互补** — `instructions` 管角色 prompt，`CODEX_HOME` 管配置/MCP/权限，两者可组合使用

---

**测试代码来源**: 手动 CLI 测试
**相关文档**:
- [claude-cli-config-override-research.md](claude-cli-config-override-research.md) — Claude CLI 命令行参数研究
- [claude-codex-role-isolation-report.md](claude-codex-role-isolation-report.md) — 角色隔离方案
- [claude-md-runtime-injection-mechanism.md](claude-md-runtime-injection-mechanism.md) — CLAUDE.md 注入机制
