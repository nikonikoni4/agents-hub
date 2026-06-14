# 后端 Logger 使用规范审查报告

> 审查日期: 2026-06-14
> 审查范围: core, api, mcp, realtime, roles
> 规范来源: `agents_hub/CLAUDE.md` 日志记录章节

---

## 规范摘要

| 级别 | 适用场景 |
|------|---------|
| **INFO** | 消息投递、Agent 启动/停止/注册/注销、群聊激活/加载、跨边界调用、AgentCall 创建/完成 |
| **ERROR** | raise 前必须记录，包含操作标识 + 失败原因 + 当前状态 |
| **WARN** | 批量操作部分失败、降级方案、可疑状态 |
| **DEBUG** | 幂等性检查、辅助函数、详细参数、内部状态 |

**禁止项**: 关键流程用 DEBUG、raise 前无日志、ERROR 缺上下文、循环内 INFO、辅助函数 INFO、`except Exception` 吞异常

---

## 总览

| 模块 | 问题总数 | CRITICAL | HIGH | MEDIUM | LOW |
|------|---------|----------|------|--------|-----|
| core | 27 | 4 (print) | 19 (ERROR缺失) | 3 (级别不当) | 1 (循环内INFO) |
| api | 32 | 0 | 23 (ERROR缺失+DEBUG误用) | 9 (INFO缺失+误用) | 7 (f-string) |
| mcp | 41 | 0 | 23 (ERROR+WARNING缺失) | 15 (INFO缺失) | 3 (循环内+辅助函数) |
| realtime | 3 | 0 | 0 | 2 (级别不当) | 1 (风格不一致) |
| roles | 24 | 0 | 17 (ERROR缺失) | 6 (INFO缺失) | 1 (WARN缺失) |
| **合计** | **127** | **4** | **82** | **35** | **13** |

---

## 一、core 模块

### CRITICAL: print 代替 logger

| 文件 | 行号 | 问题 | 建议 |
|------|------|------|------|
| `agent/base_agent.py` | 146 | `btw_execute` 使用 print 输出调试信息 | → `logger.debug` |
| `agent/base_agent.py` | 159 | `main_session_id` 使用 print 输出警告 | → `logger.warning` |
| `agent/base_agent.py` | 162 | `main_session_id` 使用 print 输出警告 | → `logger.warning` |
| `orchestration/group_chat.py` | 233 | `_init_agents` 使用 print 输出警告 | → `logger.warning` |

### HIGH: raise 前缺少 ERROR 日志 (19处)

| 文件 | 行号 | 说明 |
|------|------|------|
| `orchestration/group_chat.py` | 668 | `stop_member` raise AgentNotFoundError |
| `orchestration/group_chat.py` | 858 | `reset_member` raise AgentNotFoundError |
| `context/agent_context.py` | 75 | raise StateError("GroupChatSession 未加载") |
| `orchestration/group_chat_manager.py` | 335-336 | raise FileNotFoundError |
| `orchestration/group_chat_manager.py` | 340 | raise FileNotFoundError |
| `orchestration/group_chat_manager.py` | 354-356 | raise ValueError (metadata ID 不一致) |
| `orchestration/group_chat_manager.py` | 364 | raise FileNotFoundError |
| `orchestration/group_chat_manager.py` | 371 | raise ValueError |
| `context/group_chat_repository.py` | 83 | raise FileSystemError (读 session) |
| `context/group_chat_repository.py` | 139-141 | raise FileSystemError (写 session) |
| `context/group_chat_repository.py` | 165-166 | raise FileSystemError (读 agent_member) |
| `context/group_chat_repository.py` | 242-243 | raise FileSystemError (写 agent_member) |
| `context/group_chat_repository.py` | 265-266 | raise FileSystemError (读 compact_history) |
| `context/group_chat_repository.py` | 289-290 | raise FileSystemError (写 compact_history) |
| `context/group_chat_repository.py` | 309-310 | raise FileSystemError (写 metadata) |
| `context/group_chat_repository.py` | 333 | raise FileSystemError (读 metadata) |
| `context/group_chat_runtime.py` | 558 | raise CompactionError (LLM 调用失败) |
| `context/group_chat_runtime.py` | 575 | raise CompactionError (JSON 解析失败) |
| `context/group_chat_runtime.py` | 577 | raise CompactionError (JSON 未找到) |
| `context/group_chat_runtime.py` | 618 | `_persist` 持久化失败 raise |

### MEDIUM: 级别不当 (3处)

| 文件 | 行号 | 当前 → 建议 | 说明 |
|------|------|-------------|------|
| `context/group_chat_runtime.py` | 594-598 | INFO → DEBUG | `_notify_change` 是内部辅助函数 |
| `context/group_chat_runtime.py` | 602 | INFO → DEBUG | `on_change 回调执行成功` 是内部确认 |
| `agent/base_agent.py` | 628-633 | WARNING → INFO | `run()` finally 块是正常退出路径 |

### LOW: 循环内 INFO (1处)

| 文件 | 行号 | 说明 |
|------|------|------|
| `orchestration/group_chat.py` | 453 | `compress_all` 循环内 `logger.info("压缩 Agent: %s")` → DEBUG 或循环外汇总 |

### 做得好

- `message_router.py`、`agent_call_manager.py`、`task_manager.py` 完全符合规范
- 关键流程（消息投递、AgentCall、群聊激活/加载、Agent 启动/停止）均使用 INFO
- ERROR 包含足够上下文

---

## 二、api 模块

### HIGH: raise 前缺少 ERROR 日志 (20处)

**group_chat_service.py (13处)**:

| 行号 | 函数 | 说明 |
|------|------|------|
| 110-113 | `create_group_chat` | team_members 为空 raise ValidationError |
| 120-127 | `create_group_chat` | invalid_members raise ResourceNotFoundError |
| 131-133 | `create_group_chat` | 路径非绝对 raise ValidationError |
| 137-140 | `create_group_chat` | 路径不存在 raise ResourceNotFoundError |
| 326-329 | `get_group_chat_info` | raise ResourceNotFoundError |
| 357-360 | `get_group_chat_members` | raise ResourceNotFoundError |
| 389-393 | `get_messages` | raise ResourceNotFoundError |
| 443-447 | `send_message` | 校验 send_to 失败 raise 前用 DEBUG |
| 588-594 | `toggle_use_docker` | role 不是群成员 raise ResourceNotFoundError |
| 598-601 | `toggle_use_docker` | 全局 Docker 禁用 raise ValidationError |
| 892-899 | `get_file_snapshot_content` | raise ResourceNotFoundError |
| 998-1001 | `pin_message` | 消息不存在 raise MessageNotFoundError |
| 1183-1186 | `update_permission_status` | 消息不存在 raise MessageNotFoundError |

**single_chat_service.py (2处)**:

| 行号 | 函数 | 说明 |
|------|------|------|
| 159-163 | `create_single_chat` | fork/continue 缺少 group_chat_id raise ValidationError |
| 223-227 | `get_single_chat` | 单聊不存在 raise ResourceNotFoundError |

**其他 service 文件 (5处)**:

| 文件 | 说明 |
|------|------|
| `team_service.py` | create/get/update/delete_team 共 5 处 raise 前无日志 |
| `role_service.py` | add_role_skill 第 89-93 行 raise 前无日志 |
| `config_service.py` | update_config 46-49 行、DockerNotAvailableError 59-63 行 |

### HIGH: 关键流程使用 DEBUG (3处)

| 文件 | 行号 | 当前 → 建议 | 说明 |
|------|------|-------------|------|
| `group_chat_service.py` | 188 | DEBUG → INFO | `load_group_chat` 加载群聊 |
| `group_chat_service.py` | 211 | DEBUG → INFO | `load_group_chat` 加载成功 |
| `group_chat_service.py` | 443 | DEBUG → ERROR | `send_message` 校验失败应为 ERROR |

### MEDIUM: 关键操作缺少 INFO (7处)

| 行号 | 函数 | 说明 |
|------|------|------|
| 1045-1079 | `add_group_chat_members` | 添加群成员无日志 |
| 975-1022 | `pin_message` | 置顶消息无日志 |
| 1024-1041 | `unpin_message` | 取消置顶无日志 |
| 1146-1217 | `update_permission_status` | 权限变更无日志 |
| 1259-1309 | `upload_file` | 文件上传无日志 |
| 277-334 | `send_message_stream` | 消息投递无日志 |

### MEDIUM: 查询方法误用 INFO (2处)

| 行号 | 函数 | 当前 → 建议 |
|------|------|-------------|
| 1093 | `get_agent_calls` | INFO → DEBUG |
| 1125 | `get_tasks` | INFO → DEBUG |

### LOW: f-string 日志格式 (7处)

`realtime/manager.py` 全部使用 f-string 格式化日志（22, 34, 41, 47, 55, 64, 67行），建议改为 `%s` 占位符。

---

## 三、mcp 模块

**现状**: 整个模块只有 **2 处** logger 调用（server.py 653行 warning、659行 debug），严重不符合规范。

### HIGH: except Exception 缺少 ERROR 日志 (9处)

所有工具函数的 `except Exception as e` 捕获后直接返回错误响应，**异常被吞掉**：

| 行号 | 函数 |
|------|------|
| 252 | `call_agent` |
| 316 | `assign_tasks_to_team` |
| 377 | `archive_task_list` |
| 459 | `check_agent_call` |
| 520 | `report_progress` |
| 702 | `complete_task` |
| 783 | `request_permission` |
| 858 | `create_group_chat` |
| 923 | `create_agent` |

### HIGH: 领域异常缺少 WARNING 日志 (13处)

规范要求领域异常用 `logger.warning` 记录，当前全部静默返回：

| 行号 | 异常类型 |
|------|---------|
| 210, 291, 354, 425, 499, 577, 752 | GroupChatNotFoundError |
| 242 | AgentNotFoundError |
| 840 | ValidationError |
| 846 | ResourceNotFoundError |
| 852 | StateError |
| 911 | ValueError |
| 917 | RoleAlreadyExistsError |

### MEDIUM: 缺失 INFO 日志

**跨边界调用入口 (10处)**:

| 行号 | 函数 |
|------|------|
| 196 | `call_agent` |
| 277 | `assign_tasks_to_team` |
| 340 | `archive_task_list` |
| 411 | `check_agent_call` |
| 488 | `report_progress` |
| 564 | `complete_task` |
| 738 | `request_permission` |
| 815 | `create_group_chat` |
| 890 | `create_agent` |
| 936 | `health_check` |

**AgentCall 创建/完成 (3处)**: 152行、219行、660行

**消息投递 (2处)**: 166行、236行

### MEDIUM: DEBUG 用于关键流程

| 行号 | 当前 → 建议 |
|------|-------------|
| 659 | DEBUG → INFO（AgentCall 闭环） |

### LOW: 循环内 WARNING (1处)

| 行号 | 说明 |
|------|------|
| 653 | 循环内逐条 warning → 循环外汇总 |

---

## 四、realtime 模块

### MEDIUM: 级别不当 (2处)

| 文件 | 行号 | 当前 → 建议 | 说明 |
|------|------|-------------|------|
| `manager.py` | 55 | ERROR → WARN | 循环内批量部分失败应用 WARN |
| `manager.py` | 66-69 | INFO → WARN/分级 | 有失败时应用 WARN，无失败时 INFO |

### LOW: 风格不一致 (1处)

| 文件 | 行号 | 说明 |
|------|------|------|
| `manager.py` | 8 | 使用 `logging.getLogger` 而非项目封装的 `get_logger` |

### 做得好

- `dependencies.py` 的 INFO 记录跨边界调用符合规范
- `connect`/`disconnect` 的 INFO 记录状态变化符合规范

---

## 五、roles 模块

### HIGH: raise 前缺少 ERROR 日志 (17处)

**role_manager.py (14处)**:

| 行号 | 说明 |
|------|------|
| 60 | raise ValueError("Role name cannot be empty") |
| 62 | raise ValueError("Role name cannot start with '.'") |
| 64 | raise ValueError("Role name cannot end with space") |
| 66 | raise ValueError("Cannot contain spaces") |
| 68 | raise ValueError("Cannot contain: \\ / : * ? ...") |
| 95 | raise ValueError("Windows reserved name") |
| 114-116 | raise ValueError("names cannot be prefixes") |
| 201 | raise RoleNotFoundError (role_dir 不存在) |
| 206 | raise RoleNotFoundError (role.json 不存在) |
| 273 | raise RoleAlreadyExistsError |
| 306-308 | except Exception: shutil.rmtree → raise |
| 340 | raise RoleNotFoundError (delete_role) |
| 358 | raise PlatformConfigNotFoundError (Claude) |
| 378 | raise PlatformConfigNotFoundError (Codex) |

**role.py (3处)**:

| 行号 | 说明 |
|------|------|
| 207 | raise SkillAlreadyExistsError |
| 214 | raise SkillNotFoundError (全局库不存在) |
| 232 | raise SkillNotFoundError (角色中不存在) |

### MEDIUM: 关键操作缺少 INFO (6处)

| 文件 | 行号 | 说明 |
|------|------|------|
| `role_manager.py` | ~264 | `create_role` 开始创建无入口日志 |
| `role_manager.py` | ~323 | `create_role` 成功完成无日志 |
| `role_manager.py` | ~342 | `delete_role` 删除角色无日志 |
| `role.py` | 110 | `update_name` 重命名目录无日志 |
| `role.py` | 216 | `add_skill` 成功复制后无日志 |
| `role.py` | 234 | `remove_skill` 删除后无日志 |

### MEDIUM: role.py 整个文件未定义 logger

该文件包含 `add_skill`、`remove_skill`、`update_name` 等状态变更操作和多个 raise，但完全没有 logger。

### LOW: 降级处理缺少 WARN (1处)

| 文件 | 行号 | 说明 |
|------|------|------|
| `role_manager.py` | 152-153 | `list_roles` 中 `except (json.JSONDecodeError, KeyError): continue` 静默跳过损坏的 role.json |

---

## 修复优先级建议

### P0: 立即修复
1. **mcp/server.py** — 所有 `except Exception` 添加 ERROR 日志（9处），领域异常添加 WARNING（13处）
2. **core/context/group_chat_repository.py** — 所有 `raise FileSystemError` 前添加 ERROR 日志（6处）

### P1: 尽快修复
3. **api/group_chat_service.py** — 所有 raise 前添加 ERROR 日志（13处）
4. **roles/role_manager.py** — 所有 raise 前添加 ERROR 日志（14处）
5. **core** — 将 4 处 print 改为 logger

### P2: 计划修复
6. 各模块补充关键操作的 INFO 日志
7. 修正级别不当的调用（DEBUG→INFO, WARNING→INFO 等）
8. realtime/manager.py 统一使用 `get_logger` 和 `%s` 占位符
