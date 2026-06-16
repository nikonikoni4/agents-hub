---
version: 1.0
created_at: 2026-06-16
updated_at: 2026-06-16
last_updated: 创建文档：Agent 错误状态前端反馈机制
abstract: 记录 CLI 错误时前端无法感知的问题，以及通过增加 error 状态和 tooltip 显示错误详情的解决方案
---

# Agent 错误状态前端反馈机制

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建文档初稿 |

## 问题描述

当 Agent 在执行过程中遇到错误（CLI 执行失败、解析错误、超时等）时，前端无法感知 agent 的真实状态，导致用户体验差。

### 具体表现

1. **前端状态卡住**：agent 出错后，前端状态一直显示 `busy`，用户无法判断是"正在思考"还是"已经失败"
2. **无错误反馈**：用户看不到任何错误信息，不知道发生了什么
3. **无法采取行动**：用户不知道是否需要重试、暂停或重启 agent

### 触发场景

- **并发限制**：多用户同时使用，模型服务返回限流错误
- **网络波动**：网络不稳定导致连接中断
- **大文件卡住**：生成超大文件时 CLI 参数限制触发（参见 [2026-06-16-large-tool-call-hang.md](./2026-06-16-large-tool-call-hang.md)）
- **CLI 执行失败**：进程返回非零退出码
- **解析错误**：无法解析 CLI 输出

## 影响范围

- **用户体验**：失去对 agent 状态的掌控感，无法判断是否需要人工介入
- **调试困难**：无错误信息，难以定位问题和反馈 bug
- **资源浪费**：用户可能长时间等待一个已经失败的 agent

## 解决方案

### 设计原则

1. **不做智能判断**：不尝试从 stderr 推断"是否可重试"，因为 CLI 错误输出格式不确定
2. **保守假设**：出错就认为需要人工介入，由用户决定如何处理
3. **完整信息记录**：保存足够的错误上下文，方便调试和反馈

### 后端改动

#### 1. 数据模型增强

**AgentMemberInfo**（`agents_hub/core/context/group_chat_session.py`）：
```python
@dataclass
class AgentMemberInfo:
    status: str = "idle"  # 增加 "error" 状态
    error_info: dict[str, Any] | None = None  # 错误信息
```

**错误信息结构**：
```python
{
    "type": "CLIExecutionError",  # 异常类型
    "message": "...",              # 错误消息
    "exit_code": 1,                # CLI 退出码（如果有）
    "stderr": "...(前500字符)"     # stderr 输出
}
```

#### 2. 错误捕获与状态更新

**BaseAgent._execute_message()**（`agents_hub/core/agent/base_agent.py`）：
- 在 `except Exception` 块中调用 `_set_error_status(e)` 设置错误状态
- 更新 `_sync_status()` 方法，防止 error 状态被 finally 块覆盖

**_set_error_status() 方法**：
- 从异常对象提取 `type`、`message`、`exit_code`、`stderr`
- 更新 `agent_member_info.status = "error"`
- 更新 `agent_member_info.error_info = {...}`
- 持久化到 `agent_member.json`

#### 3. 持久化支持

**GroupChatRepository**（`agents_hub/core/context/group_chat_repository.py`）：
- `load_agent_member_infos()` 加载 `error_info` 字段
- `save_agent_member()` 保存 `error_info` 字段

**GroupChatRuntime**（`agents_hub/core/context/group_chat_runtime.py`）：
- `get_member_dicts()` 返回 `error_info` 字段

#### 4. API Schema 更新

**GroupChatMember**（`agents_hub/api/schemas/group_chats.py`）：
```python
class GroupChatMember(BaseModel):
    status: str = "idle"  # idle/busy/stopped/error
    error_info: dict | None = None
```

### 前端改动

#### 1. 类型定义

**GroupChatMemberApiItem**（`frontend/src/shared/types/api-schemas.ts`）：
```typescript
export interface GroupChatMemberApiItem {
  status: 'idle' | 'busy' | 'stopped' | 'error';
  error_info?: {
    type: string;
    message: string;
    exit_code?: number;
    stderr?: string;
  } | null;
}
```

#### 2. UI 显示

**RightSidebar 成员列表**（`frontend/src/layouts/RightSidebar/RightSidebar.tsx`）：
- 增加 `error` 状态判断
- 显示红色 "❌ 错误" 标签
- 使用 `title` 属性显示错误详情（鼠标悬停时 tooltip）
- tooltip 内容：错误类型 + 错误消息 + stderr（如果有）

**CSS 样式**（`frontend/src/layouts/RightSidebar/RightSidebar.module.css`）：
```css
.statusError {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  cursor: help;  /* 提示用户可以悬停查看详情 */
}
```

#### 3. 用户操作

- **重置按钮**：已有的"重置"按钮可用于清理错误状态，恢复到 idle
- **停止按钮**：可用于强制停止错误状态的 agent
- **WebSocket 刷新**：agent 进入 error 状态时，后端触发 refresh 信号，前端立即更新

## 实施细节

### 状态转换规则

```
idle → busy → completed → idle
     ↓
     error → (用户重置) → idle
```

**关键点**：
- `error` 和 `stopped` 状态不能被自动覆盖（防止 finally 块误改状态）
- 只有用户显式操作（重置/启动）才能从 error 状态恢复

### 错误信息提取

**从 AgentBridge 异常提取**：
```python
if hasattr(exc, "details") and isinstance(exc.details, dict):
    if "exit_code" in exc.details:
        error_info["exit_code"] = exc.details["exit_code"]
    if "stderr" in exc.details:
        error_info["stderr"] = exc.details["stderr"][:500]  # 截取前 500 字符
```

**支持的异常类型**：
- `CLIExecutionError`：CLI 进程返回非零退出码
- `CLINotFoundError`：CLI 命令不存在
- `ParseError`：无法解析 CLI 输出
- `AgentTimeoutError`：执行超时
- 其他通用异常：记录 `type` 和 `message`

## 验证方法

### 手动测试

1. **触发 CLI 错误**：
   - 修改 CLI 命令参数，故意触发错误
   - 观察前端右侧栏成员状态是否变为 "❌ 错误"
   
2. **查看错误详情**：
   - 鼠标悬停在错误标签上
   - 检查 tooltip 是否显示错误类型、消息和 stderr

3. **重置操作**：
   - 点击"重置"按钮
   - 观察状态是否恢复到 idle

### 自动化测试

```python
# 测试 AgentMemberInfo 数据结构
pytest tests/core/context/test_group_chat_session.py -v
```

## 优先级

**高** - 直接影响用户体验和平台可信度

## 相关文档

- [CLI 断开导致前端卡住](./2026-06-15-cli-disconnect-frontend-stuck.md) - 网络错误导致的类似问题
- [大参数工具调用导致模型卡住](./2026-06-16-large-tool-call-hang.md) - CLI 参数限制触发的错误场景

## 后续优化

1. **错误分类**：将常见错误分类（网络、限流、参数错误），提供针对性建议
2. **自动重试**：对于可恢复错误（如网络超时），提供自动重试机制
3. **错误统计**：记录错误频率和类型，用于监控和优化
4. **前端错误展示优化**：考虑使用更友好的 UI（卡片、弹窗）代替简单的 tooltip

## 记录信息

- 记录时间：2026-06-16
- 问题来源：用户反馈
- 状态：已解决
- 实施者：AI 协作
