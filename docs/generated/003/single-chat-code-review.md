# 单聊通道代码审查报告

- **审查范围**: `377110d..d7cb214`（9 commits, 18 files, +2499/-265 lines）
- **审查日期**: 2026-06-08
- **分支**: `task-12-single-chat`
- **审查方法**: 5 个并行 Agent 独立审查（CLAUDE.md 合规、Bug 扫描、Git 历史、PR 模式、代码注释合规）

---

## 高置信度问题（>= 80 分）

### Issue 1: `_resolve_session_path` 硬编码路径，忽略 `RoleConfig.work_root` [95/100]

**文件**: `agents_hub/api/services/single_chat_service.py` L71-80

**问题**: 设计文档明确规定使用 `RoleConfig.work_root` 作为基础路径，按平台指定搜索目录（Claude: `work_root/projects/`，Codex: `work_root/sessions/`）。但代码硬编码了 `Path.home() / ".claude"` 和 `Path.home() / ".codex"`。

**影响**: 当角色配置了自定义 `work_root` 时，session 文件将无法被找到，导致 `session_path` 始终为 `None`，`get_messages` 始终返回空列表。

**来源**: Bug 扫描 Agent、代码注释合规 Agent

```python
# 当前代码
search_roots = {
    AgentPlatform.CLAUDE: Path.home() / ".claude",
    AgentPlatform.CODEX: Path.home() / ".codex",
}

# 应改为（设计文档要求）
# 接受 work_root 参数，按平台搜索子目录
# Claude: work_root / "projects"
# Codex: work_root / "sessions"
```

**相关**: [设计文档 Session 路径解析](../../superpowers/specs/2026-06-07-single-chat-design.md#session-路径解析)

---

### Issue 2: `except Exception` 捕获所有异常，违反 backend-style.md [90/100]

**文件**: `agents_hub/api/services/single_chat_service.py` L119-125, L340-342

**问题**: backend-style.md 明确禁止使用 `except Exception` 捕获所有错误（边界除外）。两处违规：

1. **L119-125** `create_single_chat`: 将所有异常包装为 `ResourceNotFoundError`，导致 `TypeError`、`OSError` 等意外错误返回误导性 404。
2. **L340-342** `get_messages`: 静默吞掉所有异常并返回空列表，调用方无法区分"无消息"和"解析失败"。

**来源**: CLAUDE.md 合规 Agent、Bug 扫描 Agent、代码注释合规 Agent

```python
# L119-125: 应捕获具体异常
try:
    role = self._role_manager.get_role(request.agent_name)
except Exception as e:  # ❌ 应为 RoleNotFoundError
    raise ResourceNotFoundError(...)

# L340-342: 不应静默吞掉异常
except Exception as e:
    logger.error(...)
    return []  # ❌ 调用方无法区分"无消息"和"加载失败"
```

**规则引用**: `docs/coding-rules/backend-style.md` — "禁止使用 `except Exception` 捕获所有错误（边界除外）"

---

### Issue 3: `parse_codex_session` 将原始 role 字符串直接传入 Literal 类型字段 [85/100]

**文件**: `agents_hub/utils/session_parser.py` L92-103

**问题**: `SessionMessage.role` 是 `Literal["user", "assistant", "system", "tool"]`，但 `parse_codex_session` 直接将 `payload.get("role", "")` 传入构造函数，未做映射或校验。

**影响**: 若 Codex session 包含 `"developer"` 等非预期角色值，Pydantic 将抛出 `ValidationError`。该异常被 Issue 2 的 `except Exception` 静默吞掉，导致 `get_messages` 返回空列表而非报错。

**来源**: Bug 扫描 Agent

```python
# 当前代码 — 直接信任原始数据
role = payload.get("role", "")
result.append(SessionMessage(role=role, ...))

# 对比 parse_claude_session — 硬编码角色值，从不信任原始数据
result.append(SessionMessage(role="user", ...))
result.append(SessionMessage(role="assistant", ...))
```

---

## 中置信度问题（50-79 分）

### Issue 4: `SessionFileNotFoundError` 定义但从未使用 [75/100]

**文件**: `agents_hub/core/foundation/exceptions.py` L74-82

`SessionFileNotFoundError` 已导出到 `__all__`，但整个提交范围内无任何代码抛出它。`_resolve_session_path` 找不到文件时返回 `None`，不抛异常。属于死代码。

---

### Issue 5: `list_agent_state` 直接访问私有属性 `_is_processing` [75/100]

**文件**: `agents_hub/core/orchestration/group_chat.py` L369, L372

core/CLAUDE.md 禁止直接访问私有属性。`list_agent_state` 读取 `self.manager._is_processing` 和 `worker._is_processing`。应改为在 Agent 上暴露公共属性。

---

### Issue 6: SSE 格式化逻辑写在路由层 [50/100]

**文件**: `agents_hub/api/routes/single_chat.py` L58-65

routes/CLAUDE.md 规定"禁止在路由中写业务逻辑"。路由中 `event_generator()` 做了 SSE 协议格式化（`f"data: {json}\n\n"`）。但 SSE 端点本身就是流式包装，属于边界情况。

---

### Issue 7: 流式端点缺少 `response_model` [50/100]

**文件**: `agents_hub/api/routes/single_chat.py` L50

routes/CLAUDE.md 要求"每个端点必须声明 response_model"。SSE 端点无法用 Pydantic model 描述，属于合理例外。

---

### Issue 8: `session_parser.py` 没有定义 logger [50/100]

**文件**: `agents_hub/utils/session_parser.py`

项目模式是每个模块使用 `get_logger(__name__)`，但此文件没有。`load_jsonl` 中 `json.JSONDecodeError` 被静默跳过，无法追踪损坏数据。

---

### Issue 9: `Executor` Protocol 未同步更新 [50/100]

**文件**: `agents_hub/agent_bridge/protocols.py`

`Executor` Protocol 只定义了 `(prompt, config, session_id)` 3 个参数，但实际 executor 已有 5 个参数（含 `cwd`、`fork_from`）。Protocol 形同虚设。

---

### Issue 10: Docker executor 不支持 `fork_from` [50/100]

**文件**: `docker_base.py`, `docker_claude.py`, `docker_codex.py`

`fork_from` 只加到了本地 executor，Docker executor 系列未同步。当前不影响（单聊只用本地 executor），但未来 Docker 模式下调用 fork 会静默失败。

---

## 低置信度问题（< 50 分）

| # | 问题 | 分数 | 文件 |
|---|------|------|------|
| 11 | `SessionFileNotFoundError` 继承层级与同级异常不一致 | 25 | `exceptions.py` |
| 12 | `_resolve_session_path` 使用子串匹配 `*{session_id}*` | 25 | `single_chat_service.py` |
| 13 | `send_message_stream` 中 `session_id` 空字符串判断 | 25 | `single_chat_service.py` |
| 14 | `single_chat_manager` 全局实例在导入时执行 I/O | 25 | `single_chat_service.py` |

---

## 合规项（无问题）

- `fork_from` 参数添加方式正确，使用 keyword + default=None，向后兼容
- `_is_processing` 标志位使用 `try/finally` 保护，异常时正确重置
- `SessionFileNotFoundError` 异常类本身遵循 backend-style.md 模式
- `config.data_path` 使用正确（agents_hub/CLAUDE.md 规则 1）
- 路由层使用 `Depends` 做依赖注入，未直接实例化 Service
- 响应格式使用 `_to_response()` 转换，未直接返回领域模型
- 测试覆盖了 CRUD、404、验证错误等关键场景
