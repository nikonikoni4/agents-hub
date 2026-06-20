---
version: 1.0
created_at: 2026-06-20
updated_at: 2026-06-20
last_updated: 记录快速重复停止/启动群聊成员导致 stop_member 中 AgentMemberInfo 缺失并抛 KeyError 的问题
abstract: 记录 GroupChat.stop_member 在运行态 Agent 存在但 runtime 成员状态缺失时抛 KeyError，导致停止成员接口返回 500 的问题和修复方案。
severity: 中（用户停止成员操作失败，接口返回 500）
frequency: 偶发（快速重复停止/启动时触发）
---

# GroupChat stop_member 成员状态缺失导致 KeyError

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 Bug 记录 |

## Bug 简述

快速重复点击群聊成员停止/启动时，`GroupChat.stop_member()` 可能遇到运行态 Agent 对象仍存在，但 `runtime.agent_member_infos` 中对应 `AgentMemberInfo` 短暂缺失的状态不一致窗口，最终在停止接口中抛出 `KeyError: 'codex'`，导致 API 返回 500。

典型报错：

```text
Unhandled error on POST /api/v1/group-chats/d7fa3e44-27fe-4eee-99c3-b81822ba1343/members/codex/stop
...
File "agents_hub/core/orchestration/group_chat.py", line 951, in stop_member
    agent_info = self.runtime.get_agent_member_info(agent_name)
KeyError: 'codex'
```

## 复用场景

该问题可复用于所有“运行对象存在，但 runtime 持久化状态记录缺失”的生命周期操作：

- `GroupChat.stop_member()`：停止成员前需要先写 `status="stopped"`
- `GroupChat.start_member()`：启动成员前需要读取当前状态是否为 `stopped`
- `GroupChat.reset_member()`：重置成员时会先停止、再清空 session 和上下文状态
- 任何由前端快速重复点击触发的状态切换接口

判断准则：如果操作对象来自 `self.manager` / `self.workers`，状态来自 `runtime.state.agent_member_infos`，这两个来源就可能在并发或重载时短暂不一致。

## 代码位置

| 文件 | 位置 | 说明 |
|------|------|------|
| `agents_hub/api/routes/group_chat.py` | `stop_member()` | HTTP 入口：`POST /group-chats/{id}/members/{agent_name}/stop` |
| `agents_hub/api/services/group_chat_service.py` | `GroupChatService.stop_member()` | 加载群聊并调用 core 层停止逻辑 |
| `agents_hub/core/orchestration/group_chat.py` | `GroupChat.stop_member()` | 问题发生点：读取并更新 `AgentMemberInfo.status` |
| `agents_hub/core/context/group_chat_runtime.py` | `get_agent_member_info()` / `get_or_create_agent_member_info()` | 成员状态读取与恢复入口 |

## 发生原因

日志显示在 `2026-06-20 21:56:41` 同一秒内发生了多条相互交错的生命周期操作：

1. 第一次停止请求终止 Codex CLI 进程
2. Codex 执行流同时收到终止后的 CLI 错误，并尝试把 Agent 状态写为 `error`
3. Agent run task 被取消，队列中仍有未处理消息
4. 另一个停止请求几乎同时进入 `stop_member("codex")`
5. `stop_member()` 已通过 `_find_agent("codex")` 找到运行态 Worker
6. 但读取 `runtime.get_agent_member_info("codex")` 时成员状态记录不可用，抛出 `KeyError`

根因不是 `codex` 名称错误，而是两个状态来源缺少防御：

- 运行态来源：`self.workers["codex"]`
- 成员状态来源：`runtime.state.agent_member_infos["codex"]`

正常情况下二者应一致，但快速 stop/start、CLI 终止回调、Agent 自身异常状态回写会在 `await` 让出点交错，形成短暂不一致窗口。

## 最佳方案

在 `GroupChat.stop_member()` 中把“运行态 Agent 存在但成员状态缺失”当成可恢复的不一致状态处理：

1. 先通过 `_find_agent(agent_name)` 判断 Agent 是否真实存在；不存在仍抛 `AgentNotFoundError`
2. 读取 `AgentMemberInfo` 时兜住 `None` 和 `KeyError`
3. 如果成员状态缺失，记录 warning，并使用 `runtime.get_or_create_agent_member_info(agent_name)` 恢复状态条目
4. 补齐 `cwd` 默认值，继续标记 `status="stopped"` 并持久化
5. 继续执行原有停止流程：终止 CLI 进程、停止 run loop、取消 task、清理队列、注销 MessageRouter

核心修复：

```python
try:
    agent_info = self.runtime.get_agent_member_info(agent_name)
except KeyError:
    agent_info = None
if agent_info is None:
    logger.warning(
        "停止 Agent 时发现运行态存在但成员状态缺失，自动恢复: group=%s, agent=%s",
        self.group_chat_id,
        agent_name,
    )
    agent_info = self.runtime.get_or_create_agent_member_info(agent_name)
    agent_info.cwd = agent_info.cwd or self.runtime.project_path
agent_info.status = "stopped"
await self.runtime.save_agent_members(context=f"Stop agent {agent_name}")
```

## 验证方式

新增回归测试：

```text
tests/core/orchestration/test_group_chat_member_lifecycle.py
```

测试场景：

1. 构造 `GroupChat` 最小对象
2. `workers` 中存在 `codex`
3. `runtime.get_agent_member_info("codex")` 抛 `KeyError`
4. 调用 `stop_member("codex")`
5. 验证返回 `status="stopped"`，并且 runtime 中恢复了 `codex` 的 `AgentMemberInfo`

已通过：

```bash
python -m pytest tests\core\orchestration\test_group_chat_member_lifecycle.py -q
```

## 经验教训

1. 成员生命周期操作不能假设运行态对象和 runtime 状态永远同步。
2. 用户可快速重复触发 stop/start，后端必须把这些接口设计为并发容错。
3. “状态缺失”不应总是 500：如果 Agent 对象仍存在，可以恢复 runtime 状态后继续清理。
4. 停止流程的第一步必须尽快写入 `stopped`，阻止新消息投递；但写状态本身也需要容错。
5. 排查这类问题时，应同时看 spec/flow、主日志和 agent_member 持久化文件，确认是名称错误还是状态来源不一致。

## 相关 Bug

- `2026-06-05-group-chat-runtime-state-concurrency.md`：Runtime 内存状态并发问题
- `2026-06-14-manager-run-task-silent-death.md`：stop/start 后 run task 异常和消息队列堆积
- `2026-06-20-codex-process-wait-blocking.md`：Codex 进程停止/等待异常导致任务无法闭环
