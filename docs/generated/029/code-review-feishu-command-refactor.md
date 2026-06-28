# Code Review Report

**审查范围**: 飞书命令系统重构（.scratch/feishu-command-refactor）
**审查时间**: 2026-06-27
**变更文件**: 4 个文件，743 行新增，824 行删除

| 文件 | 变更行数 | 类型 |
|------|---------|------|
| `agents_hub/channels/feishu/commander.py` | +71/-234 | 主体重写 |
| `tests/channels/feishu/test_commander.py` | +284/-80 | 完全重写 |
| `tests/channels/feishu/test_session.py` | +344/-143 | 完全重写 |
| `tests/integration/test_feishu_e2e.py` | +44/-367 | 部分更新 |

## 架构上下文

### 相关 ADR
- 无已记录的 ADR

### 相关 Spec
- `docs/specs/2026-06-27-feishu-channel.md`: 飞书 Channel 模块规格（**严重过时**）
- `docs/coding-rules/backend-singleton.md`: 后端单例规则（**未更新**）
- `docs/coding-rules/testing.md`: 测试规则

### 决策覆盖
- 代码变更涉及重大架构决策（命令系统从 9 个精简为 3 个），但**未在任何文档中记录此决策**
- Spec 仍描述旧命令系统，与代码实现完全脱节

---

## 审查结果

Found **15** issues:

---

### Issue 1: `switch_to_*` 方法与 `get_or_create_state` 嵌套锁导致死锁
- **类型**: Performance / Bug
- **置信度**: 95
- **位置**: `session.py:143-155`
- **详情**: `_operation_lock` 是 `threading.Lock()`（不可重入锁）。所有 `switch_to_*` 方法在获取锁后调用 `get_or_create_state`，后者内部也尝试获取同一个锁，形成死锁。
  ```python
  def switch_to_idle(self, feishu_chat_id: str) -> None:
      with self._operation_lock:            # 第一次获取
          state = self.get_or_create_state(feishu_chat_id)  # 内部再次获取 → 死锁
  ```
- **修复**: 将 `_operation_lock` 改为 `threading.RLock()`，或将 `get_or_create_state` 的内部逻辑提取为无锁的 `_get_or_create_state_unlocked` 方法。

---

### Issue 2: Spec 命令列表与代码严重不一致
- **类型**: Architecture / Documentation
- **置信度**: 98
- **位置**: `docs/specs/2026-06-27-feishu-channel.md:88-99`
- **详情**: Spec 定义 8 个命令（`/help, /a, /assistant, /agents, /ag, /groups, /g, /status, /back`），代码只实现 3 个（`/start, /back, /default`）。`/start` 和 `/default` 在 spec 中不存在。
- **依据**: `CLAUDE.md` "修改或为某个模块增加功能前：先读对应的 spec"

---

### Issue 3: 状态机实现与 Spec 定义根本性分歧
- **类型**: Architecture
- **置信度**: 97
- **位置**: `commander.py:73-95`
- **详情**: Spec 的状态机定义 `idle → single_chat`（通过 `/ag`）和 `idle → group_chat`（通过 `/g`）的直接路径。代码完全删除了这两条路径，`single_chat` 和 `group_chat` 只能通过助手模式间接进入。这是一个**未记录的架构决策变更**。

---

### Issue 4: `_forward_to_group_chat` 中群聊删除后引用空字符串
- **类型**: Code Quality / Bug
- **置信度**: 99
- **位置**: `commander.py:195-198`
- **详情**: `switch_to_idle()` 会清空 `state.session_name` 和 `state.session_id`。但由于 `state` 是引用，调用后第 198 行的 `state.session_name` 已是空字符串，导致错误消息显示为空。
  ```python
  feishu_session_manager.switch_to_idle(state.feishu_chat_id)  # 清空 state
  return f"群聊 '{state.session_name}' 已删除"  # state.session_name 已为空
  ```
- **修复**: 在调用 `switch_to_idle` 之前保存 `state.session_name`。

---

### Issue 5: 新增全局单例未更新编码规则文档
- **类型**: Architecture
- **置信度**: 95
- **位置**: `docs/coding-rules/backend-singleton.md`
- **详情**: `feishu_session_manager` 是新增的全局单例，但 `backend-singleton.md` 的单例表格只有 4 个（config, group_chat_paths, group_chat_manager, scheduler_service），缺少 `feishu_session_manager`。
- **依据**: `backend-singleton.md` 规定"如果未来需要新增全局单例，必须更新本文件的单例表格"

---

### Issue 6: Spec 数据模型缺少新增字段
- **类型**: Documentation
- **置信度**: 95
- **位置**: `docs/specs/2026-06-27-feishu-channel.md:128-146`
- **详情**: Spec 中 `FeishuSessionState` 数据模型未包含代码中实际存在的两个字段：`default_agent: str` 和 `single_chat_history: list[dict[str, str]]`。

---

### Issue 7: Flow 文档引用不存在的函数
- **类型**: Documentation
- **置信度**: 97
- **位置**: `docs/flows/2026-06-27-feishu-message-lifecycle.md`
- **详情**: Flow 文档引用已删除的函数（`_dispatch_command`, `_forward_message`, `_cmd_agent`, `_cmd_group`）和旧命令（`/a, /ag, /g`）。

---

### Issue 8: 魔法数字 9、10、50
- **类型**: Code Quality
- **置信度**: 90
- **位置**: `commander.py:88`, `session.py:244,253,258`
- **详情**: 3 处魔法数字未定义常量：
  - `content.strip()[9:]` — `/default ` 前缀长度
  - `first_message[:10]` — 消息截断长度
  - `if len(state.single_chat_history) > 50` — 历史上限

---

### Issue 9: 冗余 `get_or_create_state` 调用
- **类型**: Performance
- **置信度**: 80
- **位置**: `commander.py:71,101,125,156`
- **详情**: assistant 模式下每条消息触发 3 次 `get_or_create_state`。`handle()` 已在第 71 行获取状态，但 `_forward_to_assistant`、`_enter_assistant_mode`、`_cmd_default` 内部再次获取，形成冗余。

---

### Issue 10: 可测试性回归 — 从依赖注入退化为全局耦合
- **类型**: Architecture
- **置信度**: 90
- **位置**: `commander.py:14`
- **详情**: 旧代码通过构造函数注入 `session_manager`，新代码直接导入模块级单例 `feishu_session_manager`，测试时必须 mock 全局对象。建议保留构造函数注入选项（参数可选，默认使用全局单例）。

---

### Issue 11: `TestFeishuSessionManagerMethods` 测试的是手动模拟而非实际方法
- **类型**: Testing
- **置信度**: 95
- **位置**: `test_session.py:98-246`
- **详情**: 测试类中所有测试直接操作 `state.session_type = "idle"` 而不是调用 `manager.switch_to_idle()`，绕过了 Manager 的锁逻辑和 `get_or_create_state` 调用。这些测试验证的是 Python 赋值语句是否正确，而非业务代码是否正确。

---

### Issue 12: `test_default_no_agent_name` 断言缺失
- **类型**: Testing
- **置信度**: 95
- **位置**: `test_commander.py:176-189`
- **详情**: 测试 `/default` 无参数时，注释说明了预期行为但没有实际断言结果，测试会通过但没有验证任何行为。

---

### Issue 13: 测试覆盖率缺口 — 错误路径未覆盖
- **类型**: Testing
- **置信度**: 90
- **位置**: 多处
- **详情**: 以下错误路径无测试覆盖：
  - `_forward_to_single_chat` 中 `single_chat_id` 为空（`commander.py:179-181`）
  - `GroupChatNotFoundError` 处理（`commander.py:194-198`）
  - `_forward_to_assistant` 创建新单聊（`commander.py:159-172`）
  - `switch_to_assistant` 方法（`session.py:198-210`）
  - `update_sync_state` 方法（`session.py:212-223`）

---

### Issue 14: `_cmd_default` 冗余状态检查
- **类型**: Code Quality
- **置信度**: 85
- **位置**: `commander.py:128`
- **详情**: `_cmd_default` 仅在 `handle()` 的 `elif state.session_type == "group_chat"` 分支被调用，`if state.session_type != "group_chat"` 检查永远为 False，增加了阅读负担。

---

### Issue 15: 删除 `/status` 命令导致用户无法查看当前绑定
- **类型**: Architecture
- **置信度**: 80
- **位置**: `commander.py`（删除的代码）
- **详情**: Spec 明确定义了 `/status` 命令用于"显示当前状态"。代码删除后，用户在任何状态下都无法查看当前绑定的是哪个会话。

---

## 变更摘要

本次重构将飞书命令系统从 9 个命令精简为 3 个核心命令（`/start, /back, /default`），删除了 `_dispatch_command` 和 `_forward_message` 分发层，改为 `handle()` 中直接根据 `session_type` 路由。同时将 `FeishuCommander` 从依赖注入改为直接使用模块级单例 `feishu_session_manager`。

**主要问题**：
1. **死锁 Bug**（置信度 95）— `switch_to_*` 方法与 `get_or_create_state` 嵌套获取非可重入锁
2. **文本 Bug**（置信度 99）— 群聊删除后引用已被清空的 `state.session_name`
3. **Spec 严重过时**（置信度 97-98）— 命令列表、状态机、数据模型均与代码不一致
4. **测试质量问题**（置信度 90-95）— 测试手动模拟逻辑而非实际方法，错误路径覆盖不足

**建议优先级**：
- P0: 修复死锁（`threading.Lock` → `threading.RLock`）
- P0: 修复群聊删除后的文本 Bug
- P1: 更新 spec 和 flow 文档
- P1: 补全测试断言和错误路径覆盖
- P2: 提取魔法数字为常量
- P2: 更新单例规则文档
