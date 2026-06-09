# Agent context_window 与状态管理 测试规格

## 契约定义

### AgentMemberInfo

**契约点**：
1. `context_window` 默认值为 0
2. `status` 默认值为 "idle"

---

### GroupChatRuntime.update_agent_context_window

**契约点**：
1. 更新指定 agent 的 context_window
2. 自动创建不存在的 agent（get_or_create）
3. 持久化到 repository

**边界情况**：
- agent 不存在时自动创建
- context_window 为 0

---

### GroupChatRuntime.update_agent_status

**契约点**：
1. 更新指定 agent 的 status
2. 自动创建不存在的 agent
3. 持久化到 repository

**边界情况**：
- status 值：idle / busy / chatting

---

### GroupChatRuntime.get_agent_context

**契约点**：
1. 返回所有 agent 的 context_window 列表
2. 每项包含 name 和 context_window

**边界情况**：
- 无 agent 时返回空列表

---

### GroupChatRuntime.get_agent_status

**契约点**：
1. 返回所有 agent 的 status 列表
2. 每项包含 name 和 status

**边界情况**：
- 无 agent 时返回空列表

---

## 测试用例

### AgentMemberInfo 默认值

- [ ] `test_agent_member_info_default_context_window` - context_window 默认为 0
- [ ] `test_agent_member_info_default_status` - status 默认为 "idle"

### update_agent_context_window

- [x] `test_update_context_window_new_agent` - 新 agent 自动创建并设置 context_window
- [x] `test_update_context_window_existing_agent` - 更新已有 agent 的 context_window
- [x] `test_update_context_window_persists` - 更新后持久化到 repository

### update_agent_status

- [x] `test_update_status_to_busy` - 更新为 busy
- [x] `test_update_status_to_chatting` - 更新为 chatting
- [x] `test_update_status_to_idle` - 更新为 idle
- [x] `test_update_status_persists` - 更新后持久化到 repository

### get_agent_context

- [x] `test_get_agent_context_empty` - 无 agent 时返回空列表
- [x] `test_get_agent_context_multiple` - 多个 agent 返回正确列表

### get_agent_status

- [x] `test_get_agent_status_empty` - 无 agent 时返回空列表
- [x] `test_get_agent_status_multiple` - 多个 agent 返回正确列表
