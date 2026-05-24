## 需要面临的问题

### 1. 安全机制和命令审核：
1. claude code / codex 有着不同的权限模式（安全机制），这个是否需要体现在agents hub中？是否需要与平台进行深绑定？即围绕着这些平台做配置集成，可以一键选择和切换？类似于cc-switch，不过还需要加上权限
2. claude code 和codex好像在CLI工具上，如果权限出现问题（比如超出沙箱范围）是不能直接选择确认的，如果错误的话并且由于权限问题无法完成任务时，应该会直接弹出错误报告内容，也就是无论是agenthub的主agent还是subagent都会受限于CLI权限问题，如果要解决这个问题的话只能修改claude的权限设置，至少要减少deny的命令，与切换更高权限模式。
3. 如果用户已经有了自己的claude 权限设置，是否能够修改？比如修改deny的内容？还是说先读取项目和.claude的权限内容，让用户自己修改。或者可以像CC-switch一样切换

### 2. 主agent是否还是使用codex claude等接入？

还是使用平台接入，不自己实现底层的内容

### 3. system prompt如何修改？
#### claude
claude 通过cli可以直接加载system prompt ，可以替换或附加
#### codex
codex 不是很好修改，当前确定有两种思路：

1. 方案一：修改项目内的 AGENTS.md

这个方案不适合作为 agents-hub 的正式产品方案，原因如下：

- AGENTS.md 属于项目资产，不属于 agents-hub 的平台配置。为了实现跨项目角色能力而去修改项目文件，本质上是在污染用户仓库。
- 这个修改会在用户退出 agents-hub 后继续保留，用户如果不再使用该产品，还需要手工清理或恢复文档，对用户不友好。
- 该方案会把“平台级角色配置”和“项目级约束”混在一起，破坏职责边界。项目 AGENTS.md 应该表达项目自身规则，而不应该承载某个 IM 平台的外部角色定义。
- 如果用户本身已经在项目里维护了 AGENTS.md，这种做法还可能和用户原有规则冲突，甚至影响其在其他工具中的使用。

结论：方案一可以作为极特殊情况下的手工兼容手段，但不能作为默认方案，也不能自动修改。

2. 方案二：使用临时环境变量拉起独立的 Codex 数据目录，通过设置 CODEX_HOME 实现

这个方案当前测试通过，可作为 Codex 的正式方向。实现方式如下：

- 在 agents-hub 外部维护一套独立的 Codex profile 目录，而不是直接复用用户默认的 CODEX_HOME。
- 新建 profile 时，以用户当前默认 CODEX_HOME 为基线复制一份最小可用配置，保证行为尽量与用户现有 Codex 一致。
- 建议复制的内容：config.toml、auth.json、rules/、skills/、superpowers/。可选复制 memories/、cap_sid 等需要共享的内容。
- 不建议复制的内容：log/、sessions/、tmp/、.tmp/、.sandbox/、.sandbox-bin/、.sandbox-secrets/、history.jsonl、session_index.jsonl，以及 goals/logs/state 等 sqlite 运行时文件。
- 在派生出来的新 profile 中，写入或覆盖 profile 级 AGENTS.md，用于定义该 agent 的角色 system prompt。
- agents-hub 启动 Codex CLI 子进程时，临时设置 CODEX_HOME 指向该独立 profile。该环境变量只对当前进程及其子进程生效，不会污染用户全局环境。
- 运行时仍然可以把工作目录设置为当前项目目录，这样 Codex 会同时读取当前项目的 AGENTS.md 和 profile 级 AGENTS.md，从而测试两层指令链的叠加效果。

当前测试结论：

- 通过独立 CODEX_HOME 可以实现跨项目的外部角色注入。
- 不需要修改用户项目内的 AGENTS.md。
- 该方式更符合平台配置属于平台自身、项目配置属于项目自身的边界。
#### opencode
opencode 可以通过多种方式添加系统提示词：

**方案一：使用 `instructions` 字段（推荐）**

在 `opencode.json` 中通过 `instructions` 字段指定额外的指令文件，这些文件的内容会被追加到系统提示词中：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "instructions": ["AGENTS.md", "docs/custom-instructions.md"]
}
```

配置路径：
- 项目级：`./opencode.json`、`./opencode.jsonc` 或 `.opencode/opencode.json`
- 全局级：`~/.config/opencode/opencode.json`

**方案二：自定义 Agent 的 `prompt` 字段**

创建 agent 文件 `.opencode/agent/my-agent.md`，在 frontmatter 中定义配置，文件内容作为 agent 的 prompt：

```markdown
---
description: 自定义 agent
mode: primary
---

你是一个专注于...的助手。遵循以下规则：
- 规则 1
- 规则 2
```

或在 `opencode.json` 中内联定义：

```json
{
  "agent": {
    "my-agent": {
      "prompt": "自定义系统提示词内容...",
      "mode": "primary"
    }
  }
}
```

**方案三：使用插件钩子（高级）**

通过插件的 `experimental.chat.system.transform` 钩子动态修改系统提示词：

```typescript
export default (async ({ client, project, directory, $ }) => {
  return {
    "experimental.chat.system.transform": async (input, output) => {
      // 动态修改系统提示词
      output.system = output.system + "\n\n额外的自定义指令...";
    },
  }
}) satisfies Plugin
```

**方案对比：**

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| `instructions` 字段 | 简单、支持多文件、声明式 | 只能追加，不能替换 | 通用场景 |
| 自定义 Agent | 可完全自定义 prompt、支持多角色 | 需要创建文件或配置 | 多角色场景 |
| 插件钩子 | 完全控制、可动态修改 | 复杂、需要编写代码 | 高级定制 |

**对 agents-hub 的建议：**

- 优先使用 `instructions` 字段追加自定义指令，不修改用户原有配置
- 如需多角色支持，可为每个角色创建独立的 agent 文件
- 配置文件路径明确，不会污染用户项目资产
- 修改配置后需要重启 opencode 才能生效


### 5. 不同角色的权限设置

有待讨论

