# 群聊删除时文件被占用导致 502 错误

**日期**：2026-06-19
**状态**：已修复
**影响范围**：Windows 环境下群聊删除功能

---

## 问题描述

删除群聊时，API 返回 502 Bad Gateway 错误，日志显示：

```
[WinError 32] 另一个程序正在使用此文件，进程无法访问。
'D:\desktop\软件开发\agents-hub\local_data\teams\...\agent_calls.log'
```

第二次尝试删除时，错误指向 `tasks.log` 文件。

---

## 根本原因

1. `AgentCallManager` 和 `TaskManager` 在初始化时通过 `get_specialized_logger()` 创建了 `RotatingFileHandler`
2. `RotatingFileHandler` 会保持文件句柄打开状态
3. `GroupChat.cleanup()` 方法没有关闭这些 handler
4. 在 Windows 上，打开的文件无法被删除，导致 `shutil.rmtree()` 失败

---

## 修复方案

### 1. 添加 close() 方法

在 `AgentCallManager` 和 `TaskManager` 中添加 `close()` 方法：

```python
def close(self):
    """关闭 logger 所有 handler，释放文件句柄"""
    for handler in self.logger.handlers[:]:
        handler.close()
        self.logger.removeHandler(handler)
```

### 2. 在 cleanup 中调用 close()

在 `GroupChat.cleanup()` 中添加关闭 logger 的步骤：

```python
# 3. 停止 AgentCallManager 清理任务
await self.agent_call_manager.stop_cleanup()

# 3.5 关闭 AgentCallManager，释放文件句柄
self.agent_call_manager.close()

# 3.6 关闭 TaskManager，释放文件句柄
self.task_manager.close()
```

---

## 修改的文件

1. `agents_hub/core/communication/agent_call_manager.py`：添加 `close()` 方法
2. `agents_hub/core/communication/task_manager.py`：添加 `close()` 方法
3. `agents_hub/core/orchestration/group_chat.py`：在 cleanup 中调用 `close()` 方法

---

## 经验教训

1. **Windows 文件锁定**：在 Windows 上，打开的文件无法被删除，必须显式关闭所有文件句柄
2. **资源清理顺序**：清理资源时，必须先停止所有写入操作，再关闭文件句柄，最后删除文件
3. **Logger 生命周期**：Python 的 logging 模块不提供自动关闭机制，需要手动管理 handler 的生命周期

---

## 相关文档

- **Flow 文档**：`docs/flows/logger-file-handle-lifecycle.md` - Logger 文件句柄生命周期管理
- **上下文反馈**：`docs/context_feedback/2026-06-19-group-chat-file-lock-fix.md` - 问题发现和修复过程
