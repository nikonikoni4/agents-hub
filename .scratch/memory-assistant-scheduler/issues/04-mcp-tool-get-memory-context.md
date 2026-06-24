# Issue 04: MCP 工具 - get_memory_context

Status: ready-for-agent

## What to build

在 `agents_hub/mcp/server.py` 新增 `get_memory_context` MCP 工具，为记忆助手提供群聊上下文数据。

工具功能：
1. 验证 Agent Token 身份
2. 验证调用者是否为记忆助手角色
3. 读取历史总结文件（history.jsonl）
4. 调用 `get_group_chat_messages` 获取新消息
5. 拼接返回完整上下文

## Acceptance criteria

- [ ] 在 `agents_hub/mcp/server.py` 中实现 `get_memory_context` 函数
- [ ] 使用 `_register_tool_with_docstring` 注册工具
- [ ] 实现 Token 验证（通过 `group_chat_manager.resolve_token`）
- [ ] 验证调用者是否为记忆助手角色（通过 `config.default_memory_assistant_name`）
- [ ] 读取 `{memory_path}/agents_hub_history/history.jsonl`（处理文件不存在的情况）
- [ ] 调用 `get_group_chat_messages(group_chat_id, after_time)` 获取新消息
- [ ] 拼接返回 `{"history_summary": "...", "new_messages": "...", "context": "..."}`

## Blocked by

None - can start immediately

## Architecture reference

架构约束文件：`.scratch/memory-assistant-scheduler/architecture.md`

## Implementation notes

参考现有 MCP 工具的实现模式（如 `check_agent_call`）。

关键函数：
- `group_chat_manager.resolve_token(agent_token)`：验证 Token
- `get_group_chat_messages(group_chat_id, after_time)`：获取群聊消息
- `config.memory_path`：记忆文件路径
- `config.default_memory_assistant_name`：记忆助手角色名

错误响应使用 `make_error_response()`。
