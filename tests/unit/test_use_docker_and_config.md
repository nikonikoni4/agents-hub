# use_docker 配置 + Config API 测试规格

## 契约定义

### 1. use_docker 持久化（group_chat_repository）

**契约点**：
1. save_agent_member 序列化 use_docker 字段
2. load_agent_member_infos 反序列化 use_docker 字段
3. use_docker 缺失时默认 False（向后兼容旧数据）

**Bad Cases**：
- 旧数据没有 use_docker 字段 → 默认 False
- use_docker=False 值正确 round-trip（不会被过滤）

---

### 2. DockerManager.ensure_image_ready()

**契约点**：
1. Docker 运行 + 镜像存在 → 正常返回
2. Docker 未运行 → 抛出 DockerNotAvailableError
3. Docker 运行 + 镜像不存在 → 从 Dockerfile 构建
4. Docker 运行 + 镜像不存在 + Dockerfile 不存在 → 抛出 ExternalServiceError
5. Docker 运行 + 镜像不存在 + 构建失败 → 抛出 ExternalServiceError

**Bad Cases**：
- Docker 命令超时或抛异常
- 构建过程中进程返回非零退出码

---

### 3. GroupChatService.toggle_use_docker()

**契约点**：
1. 成员存在 + 全局开 + Docker 可用 → 更新内存 + 持久化 + 返回 GroupChatMember
2. 群聊不存在 → ResourceNotFoundError
3. 角色不是群成员 → ResourceNotFoundError
4. 全局 use_docker=False + 请求开启 → ValidationError
5. Docker 未启动 → DockerNotAvailableError
6. 关闭 use_docker（use_docker=False）→ 跳过 Docker 检查，直接更新
7. 角色无 session_info → 新建 AgentMemberInfo

**Bad Cases**：
- 关闭 Docker 时不检查全局开关（应该允许关闭）
- 角色名大小写/空格不匹配
- 群聊在内存中但 session_id 为空

---

### 4. ConfigService

**契约点**：
1. get_config 返回当前配置
2. update_config 部分更新单个字段
3. update_config 无有效字段 → ValidationError
4. update_config use_docker=True → 检查 Docker 环境
5. update_config use_docker=False → 跳过 Docker 检查

**Bad Cases**：
- update 全空 body → ValidationError
- use_docker=True 但 Docker 未启动 → 502
- use_docker=True 但镜像不存在且构建失败 → 502

---

### 5. SystemConfig use_docker 属性

**契约点**：
1. 默认值 False
2. setter 触发 _save_config()
3. Config 快捷访问属性一致

---

## 测试用例

### 1. use_docker 持久化

#### 向后兼容
- [ ] `test_load_agent_member_infos_missing_use_docker_defaults_false` - 旧数据无 use_docker 字段时默认 False

#### 正常流程
- [ ] `test_save_and_load_use_docker_round_trip` - use_docker=True 正确序列化/反序列化
- [ ] `test_save_use_docker_false_round_trip` - use_docker=False 正确 round-trip

---

### 2. DockerManager.ensure_image_ready()

#### 正常流程
- [ ] `test_ensure_image_ready_docker_running_and_image_exists` - Docker 运行 + 镜像存在 → 无异常

#### 异常情况
- [ ] `test_ensure_image_ready_docker_not_running` - Docker 未运行 → DockerNotAvailableError
- [ ] `test_ensure_image_ready_image_missing_no_dockerfile` - 镜像不存在 + 无 Dockerfile → ExternalServiceError
- [ ] `test_ensure_image_ready_image_missing_build_fails` - 镜像构建失败 → ExternalServiceError

#### 正常流程（构建）
- [ ] `test_ensure_image_ready_image_missing_builds_successfully` - 镜像不存在 + 构建成功

---

### 3. GroupChatService.toggle_use_docker()

#### 正常流程
- [ ] `test_toggle_use_docker_enable_success` - 开启 Docker：全局开 + Docker 可用 → 成功
- [ ] `test_toggle_use_docker_disable_success` - 关闭 Docker：跳过检查 → 成功
- [ ] `test_toggle_use_docker_creates_session_if_missing` - 角色无 session → 新建

#### 异常情况（Bad Cases 重点）
- [ ] `test_toggle_use_docker_chat_not_found` - 群聊不存在 → 404
- [ ] `test_toggle_use_docker_role_not_member` - 角色不是群成员 → 404
- [ ] `test_toggle_use_docker_global_disabled` - 全局 use_docker=False + 请求开启 → 400
- [ ] `test_toggle_use_docker_docker_not_running` - Docker 未启动 → 502
- [ ] `test_toggle_use_docker_disable_skips_docker_check` - 关闭时即使 Docker 不可用也不报错

---

### 4. ConfigService

#### 正常流程
- [ ] `test_get_config_returns_current` - get_config 返回正确值
- [ ] `test_update_config_single_field` - 更新单个字段
- [ ] `test_update_config_use_docker_false_skips_check` - 关闭 use_docker 跳过检查

#### 异常情况（Bad Cases 重点）
- [ ] `test_update_config_empty_body_raises` - 空 body → ValidationError
- [ ] `test_update_config_use_docker_true_docker_not_running` - 开启但 Docker 未运行 → 502
- [ ] `test_update_config_use_docker_true_build_fails` - 开启但镜像构建失败 → 502
