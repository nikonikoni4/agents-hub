# Manager Agent sleep 轮询循环 Bug + 任务回执异步性问题

- updated_at: 2026-06-14
- 严重程度: 高（问题2）、低（问题1）
- 状态: 已记录，待修复

## 问题 1：任务回执异步性（非 Bug，架构改进点）

### 触发规则
Manager 通过 `call_agent` 发送任务给 Worker，Worker 完成后发回执（新的 AgentCall）给 Manager。但 Manager 正在 CLI 中处理当前任务（await 状态），无法同时接收新消息。

### 现象
- Manager 发送任务给 Worker（call_id #1）
- Worker 完成后发回执给 Manager（call_id #2）
- Manager 通过 `check_agent_call` 轮询 #1 状态，直到完成
- 但 #2 回执必须等 Manager 处理完当前任务才能接收

### 影响
- 结果最终正确，但存在延迟
- Manager 无法实时接收 Worker 的回执消息

### 根因
CLI 处理任务时是阻塞的（await），无法同时处理新消息。这是系统设计的特点，非 Bug。

### 建议改进方向
- 考虑异步消息队列机制
- 或允许 Manager 在等待期间接收并处理新消息

---

## 问题 2：sleep 轮询循环 Bug（严重）

### 触发规则
Manager 调用 `report_progress` 或 `complete_task` 后，错误地使用 `sleep` + 循环来等待消息。

### 现象
```python
# 错误行为示例
report_progress(...)
while True:
    sleep(10)
    # 检查是否有新消息
```

Manager 陷入无限循环，反复执行 `sleep 10`，上下文被大量重复内容占用。

### 影响
- 资源浪费（无限循环）
- 上下文空间被占用
- 无法接收新消息（因为还在处理中）

### 根因
Manager 错误地认为需要"等待"消息，实际上消息是通过 `runtime` 中的 `incoming_message` 推送的，不需要主动轮询。

### 正确行为
```python
# 正确行为
report_progress(...)  # 或 complete_task(...)
# 直接结束，等待系统推送新消息
```

### 修复方案
1. **不要在群聊中轮询等待消息** - 调用 `complete_task` 后直接结束，等待系统推送
2. **对于 agent 任务轮询** - 使用 `check_agent_call` 检查状态是可以的，但应该有超时退出机制

### 相关记忆
- 已记录到 `feedback_no_polling_in_groupchat.md`

### 模型因素
此问题可能与模型的"安全行为"模式有关，模型倾向于重复执行已知操作而不是等待。建议：
- 限制工具调用频率
- 添加 heartbeat 机制
- 在系统提示中明确说明"不要轮询等待消息"
