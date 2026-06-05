# Bug: API 路由创建独立 GroupChatManager 实例导致双 Manager 状态分裂

**日期**：2026-06-06  
**状态**：已修复  
**影响范围**：`api/routes/group_chat.py`, `GroupChatManager`, 消息路由, Token 解析, Agent 生命周期  
**调试耗时**：~6 小时

## 问题描述

API 路由 `group_chat.py` 中没有使用全局单例 `group_chat_manager`，而是在路由文件中单独创建了一个新的 `GroupChatManager()` 实例。导致系统中同时存在两个独立的 Manager：

- **Manager A**（全局单例）：Core 内部、MCP server 使用
- **Manager B**（路由局部）：API 接口使用

## 根本原因

`GroupChatManager` 不是真正的单例模式（没有 `__new__` 拦截），它依赖"所有模块 import 同一个模块级实例"来保证唯一性。API 路由中 `GroupChatManager()` 直接构造新实例，打破了这个约定。

```python
# ❌ 错误写法 — 每次 import 创建新实例，_group_chats 和 _tokens 都是空的
from agents_hub.core.orchestration.group_chat_manager import GroupChatManager
group_chat_manager = GroupChatManager()

# ✅ 正确写法 — 使用全局单例
from agents_hub.core.orchestration import group_chat_manager
```

## 实际影响

### 1. 重启后两套 Agent 并行运行（核心问题）

服务重启后两个 Manager 的内存都是空的，各自从磁盘加载 GroupChat：

```
API send_message → Manager B 从磁盘加载 → 启动 agent.run()（GroupChat_GB2）
MCP call_agent   → Manager A 从磁盘加载 → 启动 agent.run()（GroupChat_GA2）
```

同一个群聊产生两组独立的 Agent，各自有独立的 `MessageRouter` 和 `message_queue`。用户发的消息只进 GB2 的队列，Agent 间的 MCP 调用走 GA2，两边消息互相不可见。

### 2. 消息投递到错误队列

Manager B 从磁盘加载的 GroupChat 创建了全新的 Worker 对象和 message_queue。API `send_message` 投递消息到新队列，但实际在运行 `agent.run()` 循环的是 Manager A 中的 Agent（监听旧队列），消息永远收不到。

### 3. Token 索引不一致

`_generate_and_register_tokens` 和 `_restore_and_register_tokens` 内部硬编码使用全局单例注册 token。Manager B 的 `_tokens` 字典始终为空，通过 Manager B 进行 token 解析会失败。

### 4. 状态修改只生效一半

`toggle_use_docker` 等操作通过 Manager B 更新了磁盘，但 Manager A 中已加载的 GroupChat 内存状态还是旧的，Agent 执行时读到的配置可能不对。

## 修复方案

**文件**：`agents_hub/api/routes/group_chat.py`

将路由中的独立实例改为使用全局单例：

```python
# 修复前
from agents_hub.core.orchestration.group_chat_manager import GroupChatManager
group_chat_manager = GroupChatManager()  # ❌ 新实例

# 修复后
from agents_hub.core.orchestration import group_chat_manager as _group_chat_manager  # ✅ 全局单例

def get_group_chat_service() -> GroupChatService:
    return GroupChatService(group_chat_manager=_group_chat_manager)
```

## 影响

### 修复前
- 重启后 API 和 MCP 各自从磁盘加载出两套独立的 GroupChat
- 用户发消息后 Agent 无响应（消息进了错误的队列）
- MCP 工具调用间歇性失败
- 资源泄漏：重复的 Agent 任务持续消耗内存和 CPU
- 调试极其困难：症状分散，日志中看不出两个 Manager 的区别

### 修复后
- 所有组件共享同一个 GroupChatManager 实例
- 群聊状态全局一致，消息路由正确
- 重启后只有一组 Agent 实例

## 相关文件

- `agents_hub/api/routes/group_chat.py`（问题文件）
- `agents_hub/core/orchestration/group_chat_manager.py`（全局单例定义）
- `agents_hub/core/orchestration/__init__.py`（单例导出）
- `agents_hub/api/services/group_chat_service.py`（依赖注入入口）

## 经验教训

1. **全局单例必须有防呆机制**：仅靠"大家 import 同一个模块"不够安全，应该用 `__new__` 或模块级 `__init__` guard 保证唯一性
2. **AI 倾向于就地创建实例**：AI 生成代码时习惯就近 import 并直接实例化，而非查找项目中已有的全局单例。这类 bug 极难通过代码审查发现，因为语法完全正确
3. **状态分裂类 bug 调试成本极高**：两个独立实例各自行为正常，但组合在一起才出问题，传统的单步调试很难定位
