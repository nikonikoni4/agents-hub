# MCP 工具系统测试规格

## 契约定义

### 1. token.py - generate_token()

**契约点**：
1. 返回格式为 `tok_<32位hex>` 的字符串
2. 每次生成的 token 唯一（100 次无重复）
3. hex 部分只包含 `[a-f0-9]`

**边界情况**：
- 无（纯随机生成）

---

### 2. token.py - redact_token()

**契约点**：
1. 替换单个 token 为 `[REDACTED]`
2. 替换多个 token 为 `[REDACTED]`
3. 不匹配的文本保持不变（格式错误的 token）

**边界情况**：
- 空字符串
- 无 token 的文本
- 多个 token 连续出现

---

### 3. models.py - TaskStatus / TaskListStatus

**契约点**：
1. TaskStatus 包含 4 个状态：PENDING, RUNNING, COMPLETED, FAILED
2. TaskListStatus 包含 2 个状态：ACTIVE, ARCHIVED
3. 枚举值正确（value 属性）

---

### 4. task.py - Task

**契约点**：
1. 正确创建 Task 实例（所有字段赋值）
2. to_dict() 序列化正确（status 转为 value，datetime 转为 isoformat）
3. from_dict() 反序列化正确（字符串转回枚举和 datetime）

**边界情况**：
- 序列化后反序列化应得到等价对象

---

### 5. task.py - TaskList

**契约点**：
1. 正确创建 TaskList 实例
2. to_dict() 序列化正确（嵌套 Task 列表）
3. from_dict() 反序列化正确（嵌套 Task 列表）
4. archived_at 为 None 时正确处理

**边界情况**：
- 空 tasks 列表
- archived_at 非 None 时正确序列化

---

### 6. task_manager.py - TaskManager

**契约点**：
1. get_active_task_list() 初始返回 None
2. assign_tasks() 创建新任务列表（created=N, updated=0, unchanged=0）
3. assign_tasks() 更新现有任务（created=0, updated=N, unchanged=M）
4. assign_tasks() 混合操作（创建 + 更新 + 保持不变）
5. assign_tasks() 覆盖式更新：旧列表中不在新列表的任务保持不变
6. archive_task_list() 归档当前 ACTIVE 列表
7. archive_task_list() 空列表时返回 archived_count=0
8. 持久化：创建后 tasks.jsonl 存在
9. 持久化：新 TaskManager 实例能加载历史数据
10. 持久化：归档后 tasks.jsonl 包含两行（ACTIVE + ARCHIVED）

**异常情况**：
- get_active_task_list() group_chat_id 不匹配时抛出 ValueError

---

### 7. errors.py - make_error_response()

**契约点**：
1. 基本错误响应格式正确（code, message）
2. 包含 details 时正确返回
3. details 为 None 时不包含 details 字段
4. details 为空字典时包含 details: {}

**边界情况**：
- 复杂嵌套 details

---

### 8. server.py - call_agent()

**契约点**：
1. 正常流程：返回 {"call_id": "..."}
2. 无效 token：返回 INVALID_TOKEN 错误
3. 群聊不存在：返回 GROUP_CHAT_NOT_FOUND 错误
4. Agent 不存在：返回 AGENT_NOT_FOUND 错误

**边界情况**：
- need_response=False 时使用 NOTIFICATION 类型

---

### 9. server.py - assign_tasks_to_team()

**契约点**：
1. Leader 调用：返回 {created, updated, unchanged}
2. 无效 token：返回 INVALID_TOKEN 错误
3. 非 Leader 调用：返回 PERMISSION_DENIED 错误

---

### 10. server.py - archive_task_list()

**契约点**：
1. Leader 调用：返回归档结果
2. 无效 token：返回 INVALID_TOKEN 错误
3. 非 Leader 调用：返回 PERMISSION_DENIED 错误

---

### 11. server.py - check_agent_call()

**契约点**：
1. 正常查询：返回 call 状态信息
2. 无效 token：返回 INVALID_TOKEN 错误
3. call 不存在：返回 AGENT_CALL_NOT_FOUND 错误

---

## 测试用例

### token.py - generate_token()

#### 正常流程
- [x] `test_generate_token_format` - 验证格式 tok_<32hex>
- [x] `test_generate_token_uniqueness` - 验证 100 次无重复

### token.py - redact_token()

#### 正常流程
- [x] `test_redact_token_single` - 替换单个 token
- [x] `test_redact_token_multiple` - 替换多个 token

#### 边界情况
- [x] `test_redact_token_no_match` - 不匹配文本保持不变
- [x] `test_redact_token_empty_string` - 空字符串返回空字符串

### models.py - TaskStatus / TaskListStatus

#### 正常流程
- [x] `test_task_status_values` - 4 个状态值正确
- [x] `test_task_list_status_values` - 2 个状态值正确

### task.py - Task

#### 正常流程
- [x] `test_task_creation` - 正确创建实例
- [x] `test_task_to_dict` - 序列化正确
- [x] `test_task_from_dict` - 反序列化正确
- [x] `test_task_roundtrip` - 序列化后反序列化等价

### task.py - TaskList

#### 正常流程
- [x] `test_task_list_creation` - 正确创建实例
- [x] `test_task_list_to_dict` - 序列化正确
- [x] `test_task_list_from_dict` - 反序列化正确
- [x] `test_task_list_roundtrip` - 序列化后反序列化等价

#### 边界情况
- [x] `test_task_list_empty_tasks` - 空 tasks 列表
- [x] `test_task_list_with_archived_at` - archived_at 非 None

### task_manager.py - TaskManager

#### 正常流程
- [x] `test_get_active_task_list_empty` - 初始返回 None
- [x] `test_assign_tasks_create_new` - 创建新任务列表
- [x] `test_assign_tasks_update_existing` - 更新现有任务
- [x] `test_assign_tasks_mixed_operations` - 混合操作
- [x] `test_coverage_update_semantics` - 覆盖式更新语义
- [x] `test_coverage_update_preserve_old` - 旧任务保持不变
- [x] `test_archive_task_list` - 归档任务列表
- [x] `test_archive_empty_list` - 归档空列表

#### 持久化
- [x] `test_persistence_create` - 创建后文件存在
- [x] `test_persistence_load` - 新实例加载历史数据
- [x] `test_persistence_archive` - 归档后文件正确

#### 异常情况
- [x] `test_get_active_task_list_wrong_id` - group_chat_id 不匹配

### errors.py - make_error_response()

#### 正常流程
- [x] `test_basic_error_response` - 基本格式
- [x] `test_error_response_with_details` - 包含 details
- [x] `test_error_response_with_none_details` - details 为 None
- [x] `test_error_response_with_empty_details` - details 为空字典

#### 边界情况
- [x] `test_error_response_complex_details` - 复杂嵌套 details

### server.py - call_agent()

#### 正常流程
- [x] `test_call_agent_success` - 正常调用

#### 异常情况
- [x] `test_call_agent_invalid_token` - 无效 token
- [x] `test_call_agent_group_chat_not_found` - 群聊不存在
- [x] `test_call_agent_agent_not_found` - Agent 不存在

### server.py - assign_tasks_to_team()

#### 正常流程
- [x] `test_assign_tasks_success` - Leader 调用成功

#### 异常情况
- [x] `test_assign_tasks_invalid_token` - 无效 token
- [x] `test_assign_tasks_permission_denied` - 非 Leader 调用

### server.py - archive_task_list()

#### 正常流程
- [x] `test_archive_task_list_success` - Leader 调用成功

#### 异常情况
- [x] `test_archive_task_list_invalid_token` - 无效 token
- [x] `test_archive_task_list_permission_denied` - 非 Leader 调用

### server.py - check_agent_call()

#### 正常流程
- [x] `test_check_agent_call_success` - 正常查询

#### 异常情况
- [x] `test_check_agent_call_invalid_token` - 无效 token
- [x] `test_check_agent_call_not_found` - call 不存在
