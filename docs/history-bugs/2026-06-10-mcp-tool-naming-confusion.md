# MCP 工具命名导致 Agent 无法正确调用

- updated_at: 2026-06-10
- 触发规则: Agent 处理任务时无法正确调用 speak_in_group_chat 和 finish_agent_call 工具
- 状态: 已缓解，待观察

## 问题描述

MCP 工具使用从 Agent 平台角度编写的名称（`speak_in_group_chat`、`finish_agent_call`），而不是从 Agent 自身上下文编写的名称，导致 Agent 不知道这些工具到底是干什么的，经常无法正常调用。

### 具体表现
- Agent 处理完任务后不调用闭环工具，导致系统判定连续出错而自动停止
- Agent 不理解 "speak_in_group_chat" 的含义，不知道何时该调用
- Agent 不理解 "finish_agent_call" 的含义，不知道这是任务结束的标志

## 解决方案

将工具名称从平台视角改为 Agent 视角：

| 原名称 | 新名称 | 描述 |
|--------|--------|------|
| `speak_in_group_chat` | `report_progress` | 复杂任务过程汇报 |
| `finish_agent_call` | `complete_task` | 最终任务总结 |

### 修改内容
1. `agents_hub/mcp/server.py` - 函数名、注册、docstring
2. `agents_hub/mcp/__init__.py` - 导入和导出名称
3. `local_data/agents/manager/work_root/CLAUDE.md` - 工具使用说明

## 当前效果

改名后测试效果有所改善，Agent 能够更准确地调用工具。但整个系统的不确定性还是比较大。

## 后续改进方向

### 问题本质
闭环取决于 Agent 调用工具，如果 Agent 调用工具不稳定，就会导致闭环失败。这是一个悖论。

### 降级方案：从显式工具调用 → 输出标签识别

**核心思路**：不需要使用显式的闭环工具，而是通过识别 Agent 最终输出中的标签来判断是否闭环。

**方案细节**：
1. 让 Agent 最终输出一个 XML 包裹的标签（如 `<task_complete>`），在里面进行最终结果的输出或总结
2. 如果 Agent 没有这个标签，才让它调用闭环工具

**优势**：
- 系统通过识别 Agent 自己的回复有没有这个标签来判断闭环，而不是依赖工具调用
- 有稳定的回复：如果标签不存在，可以直接把 Agent 的输出发出来
- 降级能力强：虽然上下文会杂一点，但至少系统是稳定的

**实现思路**：
```python
# 伪代码
if has_task_complete_tag(result.text):
    # 解析标签内容，提取总结
    summary = parse_task_complete_tag(result.text)
    # 执行闭环逻辑
    close_agent_call(call_id, summary)
else:
    # 降级：直接使用 Agent 的输出作为结果
    # 或者提醒 Agent 调用闭环工具
    remind_agent_to_close(call_id)
```

## 相关决策

- ADR 0006: 群聊发言从隐式自动写入改为显式工具调用
- 工具改名是 ADR 0006 的后续优化
