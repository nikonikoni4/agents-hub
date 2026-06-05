# GroupChat.load() 触发 agent.execute() 导致 GET 请求失败

- 发现时间：2026-06-05
- 影响范围：所有从磁盘加载群聊的 GET 请求（get_group_chat_members、get_group_chat_info 等）
- 状态：待修复

## 问题描述

`GET /api/v1/group-chats/{id}/members` 请求报 500 错误，异常堆栈指向 `group_chat.py:219` 的 `asyncio.gather(*[start_conversation(member) for member in new_members])`。

日志输出：
```
warning : manager在当前群聊中无历史记录
warning : 测试在当前群聊中无历史记录
warning : E2E测试角色在当前群聊中无历史记录
```

## 根因

`GroupChat.load()` 的 docstring 声明"只读，不启动 agent"，但实际调用了 `_initialize_new_members()`。该方法对所有缺少 `main_session` 的 agent 调用 `agent.execute()`（LLM 平台调用）。

调用链：
```
GET /api/v1/group-chats/{id}/members
  → get_group_chat_members()
    → group_chat_manager.load_group_chat()
      → load_group_chat_from_disk()     # 不在内存，从磁盘加载
        → group_chat.load()
          → _initialize_new_members()   # 对无 main_session 的 agent 调用 execute()
            → asyncio.gather(*[agent.execute() ...])  # → 失败
```

`agent_member.json` 中所有 agent 的 `main_session` 为空，导致全部被当作新成员初始化。

## 设计矛盾

`load()` 和 `start()` 都调用 `_initialize_new_members()`：

| 方法 | 用途 | 是否应调用 agent.execute() |
|------|------|---------------------------|
| `start()` | 首次创建群聊 | 是（初始化新成员） |
| `load()` | 从磁盘加载已有群聊 | 不应该（只读语义） |

`load()` 中调用 `_initialize_new_members()` 会导致：
1. GET 请求触发 LLM 调用（不应有的副作用）
2. agent 平台不可用时加载失败
3. 与"只读"语义矛盾

## 待讨论的修复方向

1. **移除 `load()` 中的 `_initialize_new_members()` 调用**：`load()` 保持纯只读，新增成员初始化在 `start()` 或专门的激活流程中处理
2. **保留但容错**：`load()` 中的 `_initialize_new_members()` 失败时 catch 异常，不影响加载流程
3. **分离加载和初始化**：新增一个 `load_and_initialize()` 方法，`load()` 保持只读
