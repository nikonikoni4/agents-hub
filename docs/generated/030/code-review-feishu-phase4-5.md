# Code Review Report

**审查范围**: Phase 4 & 5 — 飞书助手 Agent 配置 + 集成测试
**审查时间**: 2026-06-27
**变更文件**: 7 个文件，773 行新增，9 行删除

| 文件 | 变更行数 | 类型 |
|------|---------|------|
| `agents_hub/mcp/server.py` | +212 | 新增 6 个 MCP 工具 |
| `tests/integration/test_feishu_e2e.py` | +445 | 新增 18 个测试 |
| `agents_hub/bootstrap.py` | +43 | 角色创建 + 禁用列表 |
| `agents_hub/roles/prompt_file.py` | +47 | Feishu Assistant Prompt |
| `agents_hub/mcp/__init__.py` | +17 | 导出新工具 |
| `agents_hub/config/config.py` | +11 | 新增配置项 |
| `agents_hub/channels/feishu/commander.py` | +7/-2 | 消息前缀注入 |

## 架构上下文

### 相关 Spec
- `docs/specs/2026-06-27-feishu-channel.md`: 飞书 Channel 模块规格（**未更新 MCP 工具文档**）
- `docs/specs/2026-06-06-config.md`: 配置模块规格（**未更新 feishu_assistant 配置**）

### 决策覆盖
- 新增 6 个 MCP 工具直接操作 `feishu_session_manager` 全局单例，绕过服务层
- `feishu_chat_id` 通过文本前缀注入传递给 LLM，依赖 LLM 解析

---

## 审查结果

Found **12** issues:

---

### Issue 1: MCP 工具缺乏认证/授权机制
- **类型**: Security
- **置信度**: 90
- **位置**: `mcp/server.py:1562-1753`
- **详情**: 6 个飞书 MCP 工具仅接受 `feishu_chat_id` 参数，无 token 验证。同文件其他工具（1-15）均通过 `_resolve_group_chat()` 或 `_verify_system_token()` 验证身份。任何能访问 MCP server 的 agent 均可：列出所有群聊、读取任意飞书群历史、绑定任意飞书群。
- **修复**: 添加 token 验证或验证调用者是否为 Feishu-Assistant 角色。

---

### Issue 2: `bind_to_single_chat` 裸 `except Exception` 违反编码规则
- **类型**: Code Quality
- **置信度**: 95
- **位置**: `mcp/server.py:1677`
- **详情**: `except Exception:` 无 `as e`，无日志，吞掉所有异常（包括编程错误如 `TypeError`、`AttributeError`），直接返回通用错误。
- **依据**: `agents_hub/CLAUDE.md` 禁止 `except Exception` 吞掉异常；`backend-style.md` 要求捕获具体异常。
- **修复**: 捕获具体异常类型，添加 `logger.warning`。

---

### Issue 3: MCP 工具绕过服务层直接操作全局单例
- **类型**: Architecture
- **置信度**: 90
- **位置**: `mcp/server.py:1562-1753`
- **详情**: 现有工具遵循 `MCP tool → Service → domain objects` 分层，新增飞书工具直接操作 `feishu_session_manager`。`bind_to_group_chat` 等工具在 MCP 层执行状态变更（`switch_to_*`、`save()`），违反 SRP。
- **修复**: 提取 `FeishuSessionService` 封装 `feishu_session_manager`，MCP 工具调用 service。

---

### Issue 4: `list_single_chat_history` 读操作有写副作用
- **类型**: Architecture
- **置信度**: 85
- **位置**: `mcp/server.py:1612`
- **详情**: 调用 `get_or_create_state(feishu_chat_id)` 在 ID 不存在时会静默创建新 `FeishuSessionState` 条目。只读查询工具不应有写副作用。
- **修复**: 使用 `get_state()` 替代 `get_or_create_state()`，或添加存在性检查。

---

### Issue 5: `channel.py` 直接访问 `_states` 私有属性
- **类型**: Architecture
- **置信度**: 85
- **位置**: `channel.py:86,365,385`
- **详情**: 3 处直接访问 `feishu_session_manager._states.values()`，绕过 `_operation_lock` 保护且违反封装。
- **修复**: 添加公开的 `iter_states()` 或 `get_all_states()` 方法。

---

### Issue 6: `_on_broadcast()` 无条件 `save()` 导致多余磁盘写入
- **类型**: Performance
- **置信度**: 85
- **位置**: `channel.py:384-386`
- **详情**: 每次广播都调用 `save()`，即使没有状态被更新。`save()` 序列化所有状态并写入磁盘。
- **修复**: 跟踪是否有状态更新，仅在有变更时保存。

---

### Issue 7: `create_single_chat` MCP 工具未测试
- **类型**: Testing
- **置信度**: 90
- **位置**: `tests/integration/test_feishu_e2e.py`
- **详情**: `TestFeishuMcpTools` 声称测试 6 个工具，实际只测试 5 个。`create_single_chat` 的正常路径和错误路径均无测试。

---

### Issue 8: `TestBackCommand` 三个测试完全冗余
- **类型**: Testing
- **置信度**: 95
- **位置**: `tests/integration/test_feishu_e2e.py`
- **详情**: `test_back_from_assistant`、`test_back_from_group_chat`、`test_back_from_single_chat` 均未设置初始状态，测试的是完全相同的代码路径。`/back` 是最高优先级，不检查当前状态。
- **修复**: 设置不同初始状态，验证 `/back` 后的状态断言（如 `single_chat_id` 保留）。

---

### Issue 9: Spec 缺少 6 个 MCP 工具文档
- **类型**: Documentation
- **置信度**: 95
- **位置**: `docs/specs/2026-06-27-feishu-channel.md`
- **详情**: 新增的 `list_group_chats`、`list_single_chat_history`、`bind_to_group_chat`、`bind_to_single_chat`、`create_single_chat`、`get_current_binding` 工具未在 spec 中记录输入参数、返回值和约束。

---

### Issue 10: Config spec 缺少 `default_feishu_assistant_name`
- **类型**: Documentation
- **置信度**: 95
- **位置**: `docs/specs/2026-06-06-config.md`
- **详情**: 代码新增 `default_feishu_assistant_name` 配置项和 property 访问器，但 config spec 的配置项列表未更新。

---

### Issue 11: FeishuCommander 构造函数签名与 spec 不符
- **类型**: Documentation
- **置信度**: 90
- **位置**: `docs/specs/2026-06-27-feishu-channel.md:76-81`
- **详情**: spec 未反映构造函数从 `FeishuCommander(session_manager, group_chat_service)` 改为 `FeishuCommander(group_chat_service)`。

---

### Issue 12: `create_single_chat` MCP 工具 `except Exception` 无日志
- **类型**: Code Quality
- **置信度**: 85
- **位置**: `mcp/server.py:1718`
- **详情**: `except Exception as e` 有捕获但无日志记录，且所有异常归类为 `VALIDATION_ERROR`，掩盖内部错误。
- **修复**: 添加 `logger.warning`，区分验证错误和内部错误。

---

## 变更摘要

Phase 4 添加了飞书助手 Agent 的完整配置：配置项、Prompt 模板、6 个 MCP 管理工具、角色创建和禁用工具列表。Phase 5 新增 18 个集成测试覆盖助手模式、群聊/单聊模式、`/back` 命令和 MCP 工具。

**主要问题**：
1. **MCP 工具无认证**（置信度 90）— 任何 agent 可操作飞书会话状态
2. **`except Exception` 违规**（置信度 95）— `bind_to_single_chat` 吞掉所有异常
3. **Spec 严重滞后**（置信度 90-95）— MCP 工具、配置项、构造函数签名均未更新
4. **测试缺口**（置信度 90-95）— `create_single_chat` 未测试、`TestBackCommand` 冗余

**建议优先级**：
- P0: 为 MCP 工具添加认证机制
- P0: 修复 `bind_to_single_chat` 的 `except Exception`
- P1: 更新 spec 文档（MCP 工具、配置项、签名变更）
- P1: 补充 `create_single_chat` 测试，修复 `TestBackCommand` 冗余
- P2: 提取 `FeishuSessionService` 封装 MCP 工具
- P2: 修复 `_on_broadcast()` 无条件 `save()`
