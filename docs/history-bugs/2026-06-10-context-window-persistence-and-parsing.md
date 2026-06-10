# context_window 持久化丢失 + CLI 解析器遗漏 + 缓存 token 未计入

## 触发条件

Agent 处理消息后，前端成员列表的 context_window 显示为 0 或不显示。涉及三个独立 bug 叠加。

## Bug 1: save_agent_member 漏掉 status 和 context_window 字段

**现象**: agent_member.json 中没有 status 和 context_window 字段，重启后丢失。

**根因**: `group_chat_repository.py` 的 `save_agent_member()` 序列化时只包含 main_session、btw_session、context_state、token、cwd、use_docker，漏掉了 status 和 context_window。`load_agent_member_infos()` 反序列化时也没有读取这两个字段。

**影响范围**: 所有通过 `update_agent_status()` 和 `update_agent_context_window()` 更新的状态，重启后全部丢失。

**修复**: 在 `save_agent_member()` 中添加 `"status"` 和 `"context_window"` 的序列化，在 `load_agent_member_infos()` 中添加反序列化。

## Bug 2: ClaudeParser 没有处理 result 事件类型

**现象**: `result.usage.input_tokens` 始终为 0，context_window 无法更新。

**根因**: Claude CLI `--output-format stream-json` 输出三种事件类型：
- `type: "system"` — 初始化事件
- `type: "assistant"` — 消息事件（usage 全为 0）
- `type: "result"` — 最终结果（包含真实 usage 数据）

但 ClaudeParser.parse_event() 只处理了 `stream_event` 和 `system` 两种类型，`result` 事件直接返回 None。真实的 input_tokens 数据在 `result` 事件中，被完全忽略。

**影响范围**: 所有通过 Claude CLI 执行的 Agent 调用，usage 数据丢失。

**修复**: 在 ClaudeParser 中添加 `_parse_result_event()` 方法，从 `result` 事件中提取 usage 并生成 `TURN_COMPLETE` 事件。

## Bug 3: context_window 计算漏掉 cache_read_input_tokens

**现象**: 同一会话中第二次调用的 context_window 远小于第一次（如 0K vs 27K）。

**根因**: Claude CLI 对会话历史的 token 计数方式：
- 第一次调用: `input_tokens=27974, cache_read=4096`（全部作为 input）
- 第二次调用: `input_tokens=72, cache_read=28544`（历史走缓存）

代码只用 `input_tokens // 1000` 计算 context_window，第二次调用 `72 // 1000 = 0`。实际上会话上下文是 `72 + 28544 = 28616` tokens。

**关键数据**（实测）:
```
第一次: input_tokens=24489, cache_read=4096, total=28585
第二次: input_tokens=72,    cache_read=28544, total=28616
```

第二次 total > 第一次，符合预期（上下文增长）。但只看 input_tokens 则相反。

**影响范围**: 所有多轮对话的 context_window 显示。第二次及之后的调用，context_window 会被严重低估。

**修复**:
- `Usage` 模型添加 `cache_read_input_tokens` 字段
- `AgentBridge` 从 usage 数据中提取 `cache_read_input_tokens`
- `BaseAgent` 使用 `input_tokens + cache_read_input_tokens` 计算 context_window

## 调试过程

1. 用户报告前端不显示 context_window
2. 检查 agent_member.json 发现字段缺失 → 修复 Bug 1
3. 添加日志后发现 `input_tokens=190, context_window=0K`
4. 直接测试 ClaudeExecutor 两次调用，发现第二次 input_tokens 只有 43
5. 直接用 CLI `--resume` 测试，发现 `cache_read_input_tokens=28544` → 修复 Bug 3
6. 检查解析器发现不处理 `result` 事件 → 修复 Bug 2

## 关联文件

- `agents_hub/core/context/group_chat_repository.py` — Bug 1
- `agents_hub/agent_bridge/parsers/claude.py` — Bug 2
- `agents_hub/agent_bridge/models.py` — Bug 3
- `agents_hub/agent_bridge/bridge.py` — Bug 3
- `agents_hub/core/agent/base_agent.py` — Bug 3
