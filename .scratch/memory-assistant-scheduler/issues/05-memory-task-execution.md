# Issue 05: 记忆任务执行

Status: ready-for-agent

## What to build

实现 `MemoryTask` 类，遍历群聊列表并执行记忆收集。

核心流程：
1. 遍历 index.json 中的群聊列表
2. 对每个需要更新的群聊，使用 `agent_platform_client.execute` 执行记忆助手
3. 构建 prompt（任务描述 + agent token）
4. 记忆助手执行完成后更新 index.json 的 last_updated
5. 记录执行结果到 result.json（保留最近 10 条）
6. history.jsonl 保留最近 1000 条记录

## Acceptance criteria

- [ ] 实现 `MemoryTask` 类
- [ ] 遍历 index.json 中的群聊列表，判断是否需要更新
- [ ] 使用 `agent_platform_client.execute` 执行记忆助手（非流式）
- [ ] 构建 prompt 包含任务描述和 agent token
- [ ] 执行完成后更新 index.json 的 last_updated（仅成功时更新）
- [ ] 记录执行结果到 result.json（成功和失败都记录）
- [ ] history.jsonl 保留最近 1000 条记录
- [ ] 单群聊执行失败时跳过并继续处理下一个群聊

## Blocked by

- Issue 01: 调度器基础框架
- Issue 02: 配置项扩展
- Issue 03: 状态管理
- Issue 04: MCP 工具 - get_memory_context

## Architecture reference

架构约束文件：`.scratch/memory-assistant-scheduler/architecture.md`

## Implementation notes

参考 `agents_hub/api/services/single_chat_service.py` 中的 `_build_prompt` 方法。

Prompt 构建：
```python
def _build_memory_prompt(group_chat_id: str, last_updated: str | None) -> str:
    task = f"请处理群聊 {group_chat_id} 的记忆收集。"
    if last_updated:
        task += f"上次更新时间：{last_updated}"
    else:
        task += "这是首次执行，需要处理所有历史消息。"
    return f"{task}\n\n[系统提示] 你的 agent token 是: {config.assistant_token}"
```

错误处理策略：
- 单群聊执行失败时，捕获异常，记录错误到 result.json，跳过该群聊继续处理下一个
- 只有成功执行的群聊才更新 index.json 的 last_updated
- 所有群聊处理完毕后，在 result.json 中记录汇总信息

```python
async def execute(self, group_chat_id: str, last_updated: str | None) -> str:
    try:
        # ... 执行记忆收集 ...
        return "记忆收集完成"
    except Exception as e:
        logger.error("群聊 %s 记忆收集失败: %s", group_chat_id, str(e))
        return f"执行失败: {str(e)}"
```

为什么选择 `execute`（非流式）而非 `execute_stream`（流式）：
- 记忆收集任务不需要实时输出，只需要最终结果
- `execute` 接口更简单，无需处理流式事件

关键依赖：
- `agents_hub.agent_bridge.agent_platform_client`：Agent 执行客户端
- `agents_hub.roles.RoleManager`：获取记忆助手的 RoleConfig
