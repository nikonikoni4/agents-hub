---
updated_at: 2026-06-04
trigger: 修改 core/orchestration、core/context、MCP tool、API service 中的群聊状态读取或消息流转代码时
---

# Core Runtime Boundary Rules

## 编码规则

### GroupChatManager 不能绕过 GroupChat.runtime

**禁止**：
- ❌ 已经拿到 `GroupChat` 实例时再扫描磁盘读取群聊状态
- ❌ 为了 API 返回值直接读 `group_metadata.json` 或 `agent_member.json`
- ❌ 从 `GroupChatContext.repository` 读取业务状态

**示例**：
```python
# ✅ 正确
group_chat = await group_chat_manager.load_group_chat(group_chat_id)
return group_chat.runtime.get_member_dicts()

# ❌ 错误
agent_member_file = group_chat_paths.agent_member_file_path(...)
with open(agent_member_file, encoding="utf-8") as f:
    return json.load(f)
```

### Runtime 查询和命令分开

**禁止**：
- ❌ 在查询方法里写文件
- ❌ 在外层模块同时修改 `runtime.state` 和 repository

**示例**：
```python
# ✅ 正确
await group_chat.runtime.set_agent_use_docker(role_name, True)

# ❌ 错误
group_chat.runtime.state.agent_member_infos[role_name].use_docker = True
await group_chat.runtime.repository.save_agent_member(...)
```

### user 不是 Agent

**禁止**：
- ❌ 用字符串等号判断 user 身份
- ❌ 对 `config.default_user_name` 或带 `(user)` 的名称调用 `call_agent`
- ❌ 把发给 user 的完成回执投递到 `MessageRouter` 的 user 队列

**示例**：
```python
# ✅ 正确
if config.is_user_name(call.send_from):
    await group_chat.group_chat_context.add_message(...)

# ❌ 错误
if call.send_from == config.default_user_name:
    group_chat.message_router.send_message(notification)
```

### 显式公开和任务闭环分开

**禁止**：
- ❌ 用 `speak_in_group_chat` 关闭 AgentCall
- ❌ 用 `complete_task` 代替普通公开发言
- ❌ 把 Agent-to-Agent 的完成通知写入群聊历史

**示例**：
```python
# ✅ 正确：公开发言
await group_chat.group_chat_context.add_message(chat_result)

# ✅ 正确：Agent-to-Agent 完成通知
group_chat.message_router.send_message(notification_message)

# ❌ 错误：任务完成时直接写群聊给 Agent 调用方
await group_chat.group_chat_context.add_message(result_for_manager)
```

## 决策规则

| 场景 | 使用 |
|------|------|
| 内存中已有 GroupChat | `group_chat.runtime` |
| 需要从磁盘恢复 GroupChat | `GroupChatManager.load_group_chat_from_disk()` |
| 查询前端展示的成员/消息 | `GroupChatRuntime.get_member_dicts()` / `get_message_dicts()` |
| 修改 agent token/cwd/use_docker/context_state | `GroupChatRuntime.set_*` / `update_*` |
| 判断 user 名称 | `config.is_user_name(name)` |
| 显示 user 名称 | `config.default_user_name` |
| user TASK 完成 | 写群聊消息 + realtime refresh |
| Agent TASK 完成 | AgentCall 完成通知 + realtime refresh |
