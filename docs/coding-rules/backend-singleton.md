---
created_at: 2026-06-06
updated_at: 2026-06-06
---

# 后端单例规则

> 上级规则：[docs/coding-rules/backend-style.md](backend-style.md)

## 当前系统中的全局单例

后端只有以下 3 个全局单例，**任何模块都必须通过 import 使用，禁止自行实例化**：

| 单例变量 | 类 | 定义文件 | 导入方式 |
|----------|-----|---------|---------|
| `config` | `Config` | `agents_hub/config/config.py:272` | `from agents_hub.config import config` |
| `group_chat_paths` | `GroupChatPaths` | `agents_hub/core/foundation/paths.py:252` | `from agents_hub.core.foundation import group_chat_paths` |
| `group_chat_manager` | `GroupChatManager` | `agents_hub/core/orchestration/group_chat_manager.py:396` | `from agents_hub.core.orchestration import group_chat_manager` |

除以上 3 个外，**不存在其他全局单例**。`APIRouter` 等模块级实例是框架惯例，不在此列。

## 核心规则

### ❌ 禁止自行实例化单例类

```python
# ❌ 错误：直接实例化，创建了独立的第二个实例
from agents_hub.core.orchestration.group_chat_manager import GroupChatManager
manager = GroupChatManager()  # 与全局单例是两个不同对象

# ❌ 错误：同理
from agents_hub.config.config import Config
my_config = Config()

# ❌ 错误：同理
from agents_hub.core.foundation.paths import GroupChatPaths
paths = GroupChatPaths()
```

```python
# ✅ 正确：始终 import 已有的全局实例
from agents_hub.core.orchestration import group_chat_manager
from agents_hub.config import config
from agents_hub.core.foundation import group_chat_paths
```

### ❌ 禁止在 `__init__` 参数中 new 单例类

```python
# ❌ 错误：依赖注入时传入新实例
def get_service():
    return GroupChatService(group_chat_manager=GroupChatManager())

# ✅ 正确：注入全局单例
def get_service():
    return GroupChatService(group_chat_manager=group_chat_manager)
```

### ❌ 禁止用类名做类型注解时暗示可以实例化

```python
# ⚠️ 注意：类型注解用类名是正确的，但不要因此产生"可以 new"的误解
def __init__(self, manager: GroupChatManager):  # 类型注解 OK
    self.manager = manager  # 应该传入全局单例
```

## 为什么 `GroupChatManager` 没有 `__new__` 防护

`Config` 和 `GroupChatPaths` 通过 `__new__` 实现了真正的单例（多次 `ClassName()` 返回同一对象）。`GroupChatManager` 没有这个防护，仅靠"模块只加载一次"保证唯一性。这意味着：

- `GroupChatManager()` 每次调用都会创建**全新实例**，各自持有独立的 `_group_chats` 和 `_tokens`
- 曾因此 bug 调试 6 小时（见 `docs/history-bugs/2026-06-06-api-route-created-separate-group-chat-manager.md`）

## 新增单例时的规则

如果未来需要新增全局单例，**必须**：

1. 在类中实现 `__new__` 防护，确保多次实例化返回同一对象
2. 在对应的 `__init__.py` 中导出实例
3. 更新本文件的单例表格
