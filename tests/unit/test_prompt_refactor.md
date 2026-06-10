# 提示词重构 测试规格

## 契约定义

### render_for_llm

**契约点**：
1. 输出包含 call_id
2. 输出包含 message_type
3. 输出包含 send_from、send_to、content
4. 处理 files 附件

**边界情况**：
- files 为空或 None
- content 为空

---

### build_user_prompt

**契约点**：
1. 输出包含 runtime XML（type、agent_token、group_chat_id、team_members、agent_call）
2. 输出包含历史上下文（如果有的话）
3. 输出包含 incoming_message
4. LEADER 角色包含 team_workboard

**边界情况**：
- 无历史上下文
- 无 agent_call_manager
- 无 task_manager

---

### create_role（写入系统提示文件）

**契约点**：
1. Claude 平台写入 CLAUDE.md
2. Codex 平台写入 AGENTS.md
3. 文件内容包含 platform_info、tool_usage、identity、role_instruction
4. LEADER 角色使用 Manager 模板
5. TEAM_MEMBER 角色使用 Worker 模板

**异常情况**：
- 角色已存在时抛出 RoleAlreadyExistsError

---

## 测试用例

### render_for_llm

#### 正常流程
- [x] `test_render_for_llm_contains_call_id` - 验证输出包含 call_id
- [x] `test_render_for_llm_contains_message_type` - 验证输出包含 message_type
- [x] `test_render_for_llm_contains_basic_fields` - 验证输出包含 send_from、send_to、content
- [x] `test_render_for_llm_with_files` - 验证处理文件附件

#### 边界情况
- [x] `test_render_for_llm_without_files` - 验证无附件时正常工作
- [x] `test_render_for_llm_empty_content` - 验证空内容时正常工作
- [x] `test_render_for_llm_notification_type` - 验证 NOTIFICATION 类型正确显示

---

### build_user_prompt

#### 正常流程
- [x] `test_build_user_prompt_contains_runtime` - 验证输出包含 runtime XML
- [x] `test_build_user_prompt_contains_incoming_message` - 验证输出包含 incoming_message
- [x] `test_build_user_prompt_team_member_no_workboard` - 验证 TEAM_MEMBER 不包含 workboard
- [x] `test_build_user_prompt_contains_team_members` - 验证输出包含 team_members（排除自己）

---

### create_role（写入系统提示文件）

#### 正常流程
- [x] `test_create_role_writes_claude_md` - 验证 Claude 平台写入 CLAUDE.md
- [x] `test_create_role_writes_agents_md` - 验证 Codex 平台写入 AGENTS.md
- [x] `test_create_role_leader_uses_manager_template` - 验证 LEADER 使用 Manager 模板
- [x] `test_create_role_team_member_uses_worker_template` - 验证 TEAM_MEMBER 使用 Worker 模板

#### 异常情况
- [x] `test_create_role_already_exists_raises` - 验证角色已存在时抛出异常
