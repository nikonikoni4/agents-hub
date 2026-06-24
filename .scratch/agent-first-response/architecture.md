# 架构约束：群聊 Agent 流式首响

## 模块职责边界

### 涉及模块

| 模块 | 职责 | 修改范围 |
|------|------|----------|
| `agents_hub/core/agent/base_agent.py` | Agent 执行逻辑 | 新增 `execute_with_first_response()` 方法 |
| `agents_hub/agent_bridge/bridge.py` | Agent 平台适配层 | 无需修改，复用 `execute_stream()` |
| `agents_hub/core/foundation/models.py` | 基础数据结构 | 无需修改 |

### 不涉及模块

- 前端（复用现有消息展示逻辑）
- MCP Server（不涉及工具调用）
- API Server（不涉及接口变更）

## 数据流

```
用户 @agent 发送消息
  ↓
GroupChat.send_message_to_agent()
  ↓
Agent._process_message()
  ↓
execute_with_first_response()  ← 新增方法
  ↓
agent_platform_client.execute_stream()  ← 复用
  ↓
遍历事件流：
  - 累积文本内容到 first_text_buffer
  - 检测首句完成条件：
    · Claude: event.type == content_block_stop 且 block.type == text
    · Codex: event.type == item.completed 且 item.type == agent_message
  - 首句完成 → runtime.add_message() 写入群聊历史 + 触发前端刷新
  - 继续收集剩余内容到 remaining_text
  ↓
返回 AgentResult(text=first_text + remaining_text)
```

## 依赖关系

```
execute_with_first_response()
  ├── depends on: agent_platform_client.execute_stream()
  ├── depends on: runtime.add_message()
  └── called by: Agent._process_message()
```

## 接口契约

### execute_with_first_response() 方法签名

```python
async def execute_with_first_response(
    self,
    prompt: str,
    use_docker: bool = False,
    group_chat_id: str | None = None,
    system_prompt: str | None = None,
) -> AgentResult:
```

**参数说明**：
- `prompt`: 用户输入（已渲染的 LLM 输入字符串）
- `use_docker`: 是否使用 Docker 沙箱执行
- `group_chat_id`: 群聊 ID（Docker 模式下必填）
- `system_prompt`: 系统提示词（可选）

**返回值**：`AgentResult`，与 `execute()` 一致

**行为契约**：
1. 内部调用 `execute_stream()` 获取流式事件
2. 检测首句完成条件，发送首次响应
3. 继续收集剩余内容
4. 返回完整结果（首次响应 + 剩余内容）

### 首句检测条件

| 平台 | 检测条件 | 说明 |
|------|----------|------|
| Claude | `event.type == content_block_stop` 且 `block.type == text` | 第一个文本块完成 |
| Codex | `event.type == item.completed` 且 `item.type == agent_message` | 第一条 Agent 消息完成 |

**边界情况**：
- 如果 Agent 输出没有文本内容（只有工具调用），则不发送首次响应
- 如果流式执行中途失败，仍然发送已捕获的首次响应

## 实现位置

### 新增方法位置

在 `agents_hub/core/agent/base_agent.py` 中，在 `execute()` 方法之后新增 `execute_with_first_response()` 方法。

### 修改调用位置

在 `agents_hub/core/agent/base_agent.py` 的 `_process_message()` 方法中，将：
```python
result = await self.execute(...)
```
改为：
```python
result = await self.execute_with_first_response(...)
```

## 关键实现细节

### 首次响应发送机制

```python
# 首句完成时
runtime.add_message(
    content=first_text,
    sender_name=self.name,
    message_type="first_response",  # 标记为首响
)
```

### 最终结果发送机制

复用现有的 `_fallback_close_task()` 逻辑，确保消息正确保存。

## 相关文档

- **PRD**：`.scratch/agent-first-response/PRD.md`
- **Agent Bridge Spec**：`docs/specs/2026-05-23-agent-bridge.md`
- **AgentCall 生命周期**：`docs/flows/agent-call-lifecycle.md`
- **Core Agent & Orchestration Spec**：`docs/specs/2026-05-31-core-agent-orchestration.md`
