# 飞书命令系统重构 - Bug 记录

## 待修复

### BUG-001: channel.py 直接访问 _states 私有属性，绕过锁保护

**严重程度**：中

**发现时间**：2026-06-27

**问题描述**：

`channel.py` 中 `_sync_missed_messages` 和 `_on_broadcast` 直接访问 `feishu_session_manager._states` 私有属性，绕过了 `FeishuSessionManager` 的封装和 `_operation_lock` 锁保护。

**影响位置**：

1. `channel.py:86` - `_sync_missed_messages` 中 `for state in feishu_session_manager._states.values()`
2. `channel.py:113` - `_sync_missed_messages` 中 `state.last_message_id = msg.get("id", 0)` 直接修改属性
3. `channel.py:122-124` - `_sync_missed_messages` 中 `state.session_type = "idle"` 等直接修改属性
4. `channel.py:365` - `_on_broadcast` 中 `for state in feishu_session_manager._states.values()`

**潜在风险**：

1. **竞态条件**：直接修改 `state` 属性没有 `_operation_lock` 保护，如果另一个线程同时通过 `feishu_session_manager` 的方法修改同一个 state，可能导致数据不一致
2. **迭代崩溃**：`dict.values()` 迭代期间如果 dict 被修改（如另一个线程调用 `get_or_create_state` 创建了新 key），可能抛出 `RuntimeError: dictionary changed size during iteration`

**建议修复方案**：

在 `FeishuSessionManager` 上增加公开方法：

```python
def get_all_states(self) -> list[FeishuSessionState]:
    """获取所有状态的副本（线程安全）"""
    with self._operation_lock:
        return list(self._states.values())

def update_state_field(self, feishu_chat_id: str, **kwargs) -> None:
    """更新状态字段（线程安全）"""
    with self._operation_lock:
        state = self._get_or_create_state_unlocked(feishu_chat_id)
        for key, value in kwargs.items():
            setattr(state, key, value)
```

然后 `channel.py` 改用这些公开方法。
