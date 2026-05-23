# Codex CLI 继续会话用法研究

## 背景

本次验证目标是确认 Codex CLI 如何在命令行中继续已有会话，并避免进入交互式 TUI 界面。

用户遇到的问题是：直接使用 `codex resume` 会进入 TUI 界面，但需要的是由 CLI 非交互方式直接运行并继续会话。

## 结论

不要使用：

```powershell
codex resume
```

该命令属于交互式恢复入口，默认会打开会话选择器或进入 TUI。

应该使用：

```powershell
codex exec resume <SESSION_ID> <PROMPT>
```

或继续最近一次会话：

```powershell
codex exec resume --last <PROMPT>
```

`codex exec resume` 是非交互式恢复入口，适合脚本、测试和 agents-hub 这类外部进程集成场景。

## 命令对比

| 命令 | 行为 | 是否进入 TUI | 适用场景 |
| ---- | ---- | ------------ | -------- |
| `codex resume` | 恢复交互式会话，默认打开选择器 | 是 | 人工在终端继续对话 |
| `codex resume --last` | 恢复最近一次交互式会话 | 是 | 人工继续最近会话 |
| `codex exec <PROMPT>` | 新建一次非交互执行 | 否 | 脚本发起单次任务 |
| `codex exec resume <SESSION_ID> <PROMPT>` | 非交互恢复指定会话并发送 prompt | 否 | 外部系统继续指定会话 |
| `codex exec resume --last <PROMPT>` | 非交互恢复最近会话并发送 prompt | 否 | 外部系统快速继续最近会话 |

## 官方帮助输出要点

本地 `codex --help` 显示：

```text
Commands:
  exec    Run Codex non-interactively
  resume  Resume a previous interactive session (picker by default; use --last to continue the most recent)
```

这说明：

- `exec` 是非交互入口。
- 顶层 `resume` 是交互式恢复入口。

本地 `codex exec --help` 显示：

```text
Commands:
  resume  Resume a previous session by id or pick the most recent with --last
```

本地 `codex exec resume --help` 显示：

```text
Usage: codex exec resume [OPTIONS] [SESSION_ID] [PROMPT]

Arguments:
  [SESSION_ID]
          Conversation/session id (UUID) or thread name. UUIDs take precedence if it parses. If
          omitted, use --last to pick the most recent recorded session

  [PROMPT]
          Prompt to send after resuming the session. If `-` is used, read from stdin

Options:
      --last
          Resume the most recent recorded session (newest) without specifying an id

      --json
          Print events to stdout as JSONL
```

## 推荐用法

### 1. 继续指定 session

```powershell
codex exec resume "019e5122-2a0e-7c61-a26b-19c036bf9315" "继续刚才的任务，总结当前状态"
```

适合 agents-hub 持久化 `session_id` 后精确恢复。

### 2. 继续最近 session

```powershell
codex exec resume --last "继续刚才的任务，总结当前状态"
```

适合人工探索或测试，但不建议作为长期稳定集成方案，因为 `--last` 依赖本机最近会话状态，容易被其他 Codex 调用影响。

### 3. 使用 JSONL 输出

```powershell
codex exec resume --json --last "继续刚才的任务，并用一句话回答"
```

适合程序解析事件流。Codex JSONL 输出通常包含：

- `thread.started`
- `turn.started`
- `item.started`
- `item.completed`
- `turn.completed`

### 4. 从 stdin 传入 prompt

```powershell
"继续刚才的任务，并输出下一步计划" | codex exec resume --last -
```

当 prompt 较长或由程序动态生成时，可以使用 `-` 从 stdin 读取。

## 对 tests/explore/codex_cli 的测试建议

当前探索测试应验证命令构造，而不是直接调用真实模型。

建议覆盖：

1. `resume(session_id, prompt)` 应调用：

   ```text
   codex exec resume <SESSION_ID> <PROMPT>
   ```

2. `resume_last(prompt)` 应调用：

   ```text
   codex exec resume --last <PROMPT>
   ```

3. 测试应明确断言没有调用顶层：

   ```text
   codex resume
   ```

4. 继续保留 `CODEX_HOME` 环境变量注入，确保不同角色 profile 仍能隔离。

5. 若需要结构化输出，应测试 `--json` 被加入 `exec resume` 命令，而不是加入顶层 `resume`。

## 集成建议

对于 agents-hub，推荐设计为：

1. 新会话使用 `codex exec --json <PROMPT>`。
2. 从输出中记录 `thread_id` 或可恢复的 session 标识。
3. 后续消息使用 `codex exec resume --json <SESSION_ID> <PROMPT>`。
4. 仅在人工调试时允许使用 `codex exec resume --last <PROMPT>`。
5. 不在自动化链路中使用 `codex resume`，避免进入 TUI 阻塞进程。

## 风险与待验证点

1. `--last` 会受本机最近会话影响，不适合作为多 agent 并发场景的稳定选择。
2. 真实可恢复标识需要通过实际 Codex 输出和本地会话存储进一步确认，不能只依赖展示用的 `thread_id` 字段。
3. 端到端测试会调用真实 Codex 模型，依赖登录状态、网络和额度，建议默认只写 mock 单元测试。
4. 如果使用独立 `CODEX_HOME` profile，需要确认 resume 查询的是同一个 `CODEX_HOME` 下的会话记录。

## 当前判断

要实现“不进入 TUI 而是 CLI 直接运行的继续会话”，核心命令是：

```powershell
codex exec resume <SESSION_ID> <PROMPT>
```

临时探索时可以用：

```powershell
codex exec resume --last <PROMPT>
```

