# Core 模块测试规格

## 契约定义

### 1. Foundation Layer

#### 1.1 models.py

**契约点**：
- 枚举值正确（SessionType, MessageType, CallStatus, GroupChatType）

#### 1.2 message.py - AgentMessage

**契约点**：
- 创建时自动填充 timestamp 默认值
- 创建时自动填充 session_type/message_type 默认值

#### 1.3 exceptions.py

**契约点**：
- AgentsHubError.to_mcp_response() 返回正确格式
- 各子类构造器填充正确的 error_code 和 details
- 异常是 AgentsHubError 的子类（继承链正确）

#### 1.4 renderer.py

**契约点**：
- wrap_xml(tag, content) 正确包裹 XML 标签
- render_for_llm(msg) 输出 `<incoming_message>` 包裹的格式
- render_for_chat(send_from, send_to, content) 输出 `@send_to content` 格式
- parse_chat_input(raw) 正确解析 `@xxx content` 格式
- parse_chat_input(raw) 无 @ 前缀时抛 InvalidMessageError
- parse_chat_input(raw) @ 后无名称时抛 InvalidMessageError

#### 1.5 constants.py

**契约点**：
- MAX_TOKEN 和 LOCAL_DATA_PATH 值正确

---

### 2. Communication Layer

#### 2.1 message_router.py - MessageRouter

**契约点**：
- register() 后 send_message() 能投递到队列
- unregister() 后 send_message() 抛 AgentNotFoundError
- send_message() 空内容抛 InvalidMessageError
- send_message() 未知发送者抛 AgentNotFoundError
- send_message() 未知接收者抛 AgentNotFoundError
- clear() 清空所有队列消息
- clear() 清空注册表（之后 send_message 失败）
- clear() 幂等性（多次调用不报错）

#### 2.2 agent_call.py - AgentCall

**契约点**：
- 创建时 status 默认 PENDING
- is_timeout() 已完成状态返回 False
- is_timeout() 无超时限制返回 False
- is_timeout() 超时返回 True（mock 时间）
- can_be_deleted() PENDING/RUNNING 返回 False
- can_be_deleted() 有 business_task_id 返回 False
- can_be_deleted() NOTIFICATION + COMPLETED + 超过保留时间返回 True
- can_be_deleted() TASK + COMPLETED + 超过保留时间返回 True
- can_be_deleted() FAILED/TIMEOUT + 超过保留时间返回 True

#### 2.3 agent_call_manager.py - AgentCallManager

**契约点**：
- create_call() 创建并返回 AgentCall
- get_call() 存在时返回 AgentCall
- get_call() 不存在时返回 None
- update_status() 更新状态并设置 started_at/completed_at
- set_result() 设置结果并标记 COMPLETED
- set_error() 设置错误并标记 FAILED
- get_stats() 返回正确统计
- 持久化：create_call 后能从文件恢复（集成测试，mock 文件系统）

---

### 3. Context Layer

#### 3.1 group_chat_session.py

**契约点**：
- AgentContextState 默认值正确
- AgentSessionInfo 默认值正确
- GroupChatSession 默认值正确
- GroupChatSession.add_message() 追加消息
- GroupChatSession.get_uncompact_messages() 返回从 last_compacted_loc 开始的消息

#### 3.2 group_chat_repository.py - GroupChatRepository

**契约点**：
- sanitize_project_path() 正确转换特殊字符（已移至 core.utils）
- load_group_chat_session() 文件不存在返回空 session
- save/load agent_session_state 往返一致
- save/load compact_history 往返一致

#### 3.3 group_chat_context.py - GroupChatContext

**契约点**：
- close() 清空引用（幂等性）
- add_message() 未 load 抛 StateError

---

### 4. Agent Layer

#### 4.1 base_agent.py - Agent

**契约点**：
- stop() 设置 _run=False 并发送哨兵消息
- send_message_to_agent() 通过 router 投递消息

#### 4.2 manager.py / worker.py

**契约点**：
- Manager/Worker 是 Agent 子类

---

### 5. Orchestration Layer

#### 5.1 group_chat_manager.py - GroupChatManager

**契约点**：
- register() 后 get_group_chat() 返回正确实例
- get_group_chat() 不存在抛 GroupChatNotFoundError
- register() 无效参数抛 ValueError
- unregister() 幂等性（不存在时静默返回）

#### 5.2 team.py - Team

**契约点**：
- 空 team_members_name 抛 ValueError

---

## 测试用例

### 1. Foundation Layer

#### models.py
- [x] `test_session_type_values` - 验证 SessionType 枚举值
- [x] `test_message_type_values` - 验证 MessageType 枚举值
- [x] `test_call_status_values` - 验证 CallStatus 枚举值
- [x] `test_group_chat_type_values` - 验证 GroupChatType 枚举值

#### message.py - AgentMessage
- [x] `test_agent_message_default_timestamp` - 验证 timestamp 自动填充
- [x] `test_agent_message_default_types` - 验证 session_type/message_type 默认值

#### exceptions.py
- [x] `test_agents_hub_error_to_mcp_response` - 验证 MCP 响应格式
- [x] `test_agents_hub_error_hierarchy` - 验证所有子类继承链
- [x] `test_agent_not_found_error_details` - 验证 AgentNotFoundError 构造
- [x] `test_group_chat_not_found_error_details` - 验证 GroupChatNotFoundError 构造
- [x] `test_message_delivery_error_details` - 验证 MessageDeliveryError 构造
- [x] `test_agent_execution_error_details` - 验证 AgentExecutionError 构造
- [x] `test_agent_timeout_error_details` - 验证 AgentTimeoutError 构造
- [x] `test_invalid_message_error_details` - 验证 InvalidMessageError 构造
- [x] `test_file_system_error_details` - 验证 FileSystemError 构造
- [x] `test_compaction_error_details` - 验证 CompactionError 构造

#### renderer.py
- [x] `test_wrap_xml_basic` - 验证 XML 包裹格式
- [x] `test_render_for_llm_format` - 验证 LLM prompt 格式
- [x] `test_render_for_chat_format` - 验证群聊输出格式
- [x] `test_parse_chat_input_valid` - 验证正常解析
- [x] `test_parse_chat_input_with_content` - 验证带内容解析
- [x] `test_parse_chat_input_no_at_raises` - 验证无 @ 抛异常
- [x] `test_parse_chat_input_empty_name_raises` - 验证空名称抛异常

#### constants.py
- [x] `test_max_token_value` - 验证 MAX_TOKEN 值
- [x] `test_local_data_path_value` - 验证 LOCAL_DATA_PATH 值

---

### 2. Communication Layer

#### message_router.py - MessageRouter
- [x] `test_register_then_send_delivers` - 验证注册后能投递
- [x] `test_unregister_blocks_send` - 验证注销后投递失败
- [x] `test_send_empty_content_raises` - 验证空内容抛异常
- [x] `test_send_unknown_sender_raises` - 验证未知发送者抛异常
- [x] `test_send_unknown_receiver_raises` - 验证未知接收者抛异常
- [x] `test_clear_empties_queues` - 验证清空队列
- [x] `test_clear_removes_registrations` - 验证清空注册表
- [x] `test_clear_idempotent` - 验证幂等性

#### agent_call.py - AgentCall
- [x] `test_default_status_pending` - 验证默认状态
- [x] `test_is_timeout_completed_returns_false` - 验证已完成不超时
- [x] `test_is_timeout_no_limit_returns_false` - 验证无限制不超时
- [x] `test_is_timeout_expired_returns_true` - 验证超时判断
- [x] `test_can_be_deleted_pending_returns_false` - 验证 PENDING 不删除
- [x] `test_can_be_deleted_running_returns_false` - 验证 RUNNING 不删除
- [x] `test_can_be_deleted_with_business_task_returns_false` - 验证有业务任务不删除
- [x] `test_can_be_deleted_notification_completed` - 验证 NOTIFICATION 完成后可删除
- [x] `test_can_be_deleted_task_completed` - 验证 TASK 完成后可删除
- [x] `test_can_be_deleted_failed` - 验证 FAILED 后可删除

#### agent_call_manager.py - AgentCallManager
- [x] `test_create_call_returns_agent_call` - 验证创建调用
- [x] `test_get_call_exists` - 验证获取已存在调用
- [x] `test_get_call_not_exists` - 验证获取不存在调用
- [x] `test_update_status_sets_timestamps` - 验证状态更新设置时间戳
- [x] `test_set_result_marks_completed` - 验证设置结果
- [x] `test_set_error_marks_failed` - 验证设置错误
- [x] `test_get_stats_returns_correct_counts` - 验证统计信息

---

### 3. Context Layer

#### group_chat_session.py
- [x] `test_agent_context_state_defaults` - 验证默认值
- [x] `test_agent_session_info_defaults` - 验证默认值
- [x] `test_group_chat_session_defaults` - 验证默认值
- [x] `test_add_message_appends` - 验证消息追加
- [x] `test_get_uncompact_messages_from_loc` - 验证增量获取

#### group_chat_repository.py
- [x] `test_sanitize_project_path_special_chars` - 验证路径清理（已移至 core.utils）
- [x] `test_sanitize_project_path_consecutive_dashes` - 验证连续横线合并（已移至 core.utils）
- [x] `test_load_session_file_not_exists` - 验证文件不存在返回空
- [x] `test_save_load_session_roundtrip` - 验证 session 往返
- [x] `test_save_load_agent_state_roundtrip` - 验证 agent state 往返
- [x] `test_save_load_compact_history_roundtrip` - 验证 compact history 往返

#### group_chat_context.py
- [x] `test_close_clears_references` - 验证关闭清空引用
- [x] `test_close_idempotent` - 验证幂等性
- [x] `test_add_message_before_load_raises` - 验证未加载抛异常

---

### 4. Agent Layer

#### base_agent.py - Agent
- [x] `test_stop_sets_run_false` - 验证停止标志
- [x] `test_stop_sends_sentinel` - 验证发送哨兵消息
- [x] `test_send_message_to_agent_delegates_to_router` - 验证消息投递

#### manager.py / worker.py
- [x] `test_manager_is_agent_subclass` - 验证继承关系
- [x] `test_worker_is_agent_subclass` - 验证继承关系

---

### 5. Orchestration Layer

#### group_chat_manager.py - GroupChatManager
- [x] `test_register_then_get` - 验证注册后获取
- [x] `test_get_nonexistent_raises` - 验证不存在抛异常
- [x] `test_register_invalid_id_raises` - 验证无效 ID 抛异常
- [x] `test_register_invalid_type_raises` - 验证无效类型抛异常
- [x] `test_unregister_nonexistent_silent` - 验证幂等性
