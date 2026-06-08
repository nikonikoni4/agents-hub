# Bug: MCP 创建群聊后发送消息报"接收者未注册"

**日期**：2026-06-08
**状态**：未复现（已添加诊断日志）
**影响范围**：`message_router.py`, `group_chat_manager.py`, `group_chat.py`, MCP `create_group_chat` 工具
**调试耗时**：~2 小时（排查 + 诊断日志）

## 问题描述

通过 MCP 工具 `create_group_chat` 创建群聊后，群聊成员已在群内打招呼（证明 `_init_agents()` 和 `_initialize_new_members()` 成功执行），但随后在该群聊中发送消息时报错：

```
消息校验失败: call_id=edff6d2c, 原因=接收者 '群聊显示增强执行者' 未注册
```

错误来自 `message_router.py:_validate_message()`，说明目标 Agent 不在 `MessageRouter._agents_queue` 中。

## 复现步骤

1. 通过系统助手（MCP `create_group_chat` 工具）创建群聊
2. 群聊成员自动打招呼（正常）
3. 在该群聊中发送消息
4. 偶发：消息路由报"接收者未注册"

**注意**：该 bug 为偶发，后续两次测试均未能复现。

## 排查过程

### 已排除的原因

1. **双 GroupChatManager 实例（历史 bug 2026-06-06）**
   - 已确认所有代码路径使用同一个单例（通过 `__new__` + 锁保证）
   - API 路由：`from agents_hub.core.orchestration import group_chat_manager as _group_chat_manager` ✅
   - MCP server：`from agents_hub.core.orchestration import group_chat_manager` ✅
   - 两者导入路径相同，Python 模块系统保证同一对象

2. **显式 cleanup/clear 调用**
   - `cleanup()` 只在 `delete_group_chat` 时调用，用户未执行删除操作
   - `MessageRouter.clear()` 只在 `cleanup()` 中调用
   - 无其他代码路径会清空 `_agents_queue`

3. **`_init_agents()` 执行失败**
   - 成员打招呼成功，证明 `_init_agents()` 已完成（注册在打招呼之前）
   - `RoleManager.get_role()` 从磁盘读取，不修改任何状态

4. **GC 回收 GroupChat 实例**
   - `_group_chats` 字典持有强引用，不会被 GC 回收

### 未排除的假设

#### 假设 1：MCP server 运行在独立进程（最可能）

`app.py` 中 MCP server 通过 `mcp.run_async(transport="http")` 启动，内部使用 uvicorn。如果 FastMCP 或 uvicorn 以多 worker/子进程模式运行，MCP 进程中的 `group_chat_manager` 单例与 API 进程中的独立存在。

- MCP 进程：GroupChat 创建并注册到 MCP 进程的单例 → agents 注册成功 → 打招呼成功
- API 进程：`send_message` 查找 API 进程的单例 → 内存未命中 → 从磁盘加载 → 新 GroupChat 实例
- 如果磁盘加载的 `_init_agents()` 因时序问题失败 → agents 未注册 → 报错

#### 假设 2：`activate()` 幂等性缺陷

`GroupChat.activate()` 检查 `_activated` 标志后直接返回，不会重新注册 agents。如果 GroupChat 被 `load_group_chat_from_disk` 替换后，新实例的激活流程存在边界条件问题。

#### 假设 3：时序竞态

MCP `create_group_chat` 的 `start()` 内部启动了 agent 任务（`_start_agent_tasks()`），这些任务通过 `asyncio.create_task()` 并发运行。如果在 `register()` 调用之前有异步切换，且另一个协程同时操作同一 GroupChat，可能产生竞态。但由于 `register()` 是同步操作且在 `await group_chat.start()` 之后，正常情况下不会发生。

## 已添加的诊断日志

为后续复现定位，在以下位置添加了诊断日志：

1. **`message_router.py:_validate_message`**（line 114-120）
   - 校验失败时输出：已注册 agents 列表、MessageRouter 实例 ID

2. **`group_chat_manager.py:load_group_chat`**（line 101-108）
   - 内存命中时输出：GroupChatManager 实例 ID、已注册群聊数
   - 内存未命中时输出：GroupChatManager 实例 ID、已注册群聊列表

3. **`group_chat_manager.py:register`**（line 66-67）
   - 注册时输出：GroupChatManager 实例 ID、已注册群聊数

4. **`group_chat.py:_init_agents`**（line 209-213）
   - 注册完成后输出：已注册 agents 列表、MessageRouter 实例 ID

## 下次复现时的排查要点

查看日志中的关键字段：

| 字段 | 含义 | 异常判断 |
|------|------|---------|
| `GroupChatManager_id` | GroupChatManager 实例内存地址 | 如果 MCP 和 API 日志中 id 不同 → 进程隔离 |
| `MessageRouter_id` | MessageRouter 实例内存地址 | 如果创建和发消息时 id 不同 → GroupChat 被替换 |
| `已注册agents` | message_router 中注册的 agent 名称列表 | 如果为空或缺少目标 agent → 注册失败 |
| `内存/磁盘路径` | load_group_chat 走的是内存还是磁盘 | 如果走了磁盘 → 原 GroupChat 被驱逐 |

## 相关文件

- `agents_hub/core/communication/message_router.py`（消息路由校验）
- `agents_hub/core/orchestration/group_chat_manager.py`（GroupChat 管理器单例）
- `agents_hub/core/orchestration/group_chat.py`（GroupChat 生命周期）
- `agents_hub/api/services/group_chat_service.py`（业务编排层）
- `agents_hub/mcp/server.py`（MCP 工具入口）
- `agents_hub/api/app.py`（应用启动，MCP server 初始化）

## 关联 Bug

- [2026-06-06 API 路由创建独立 GroupChatManager 实例](./2026-06-06-api-route-created-separate-group-chat-manager.md) — 症状相似（agents 未注册），但根因不同（已修复的双实例问题）。本次 bug 在双实例修复后仍偶发出现。

## 经验教训

1. **单例模式需要进程级保证**：Python 模块级单例在同一进程内有效，但无法防止多进程场景下的实例分裂
2. **`activate()` 的幂等性设计需要考虑 message_router 状态**：当前设计假设 `_activated=True` 时 agents 一定已注册，但如果 GroupChat 被替换或 message_router 被清空，这个假设不成立
3. **偶发 bug 需要结构化诊断日志**：在关键路径添加实例 ID 和状态快照日志，是定位间歇性问题的有效手段
