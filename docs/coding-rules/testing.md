---
created_at: 2026-06-22
updated_at: 2026-06-22
trigger: 编写测试代码时
---

# 测试规则

> 上级规则：[backend-style.md](backend-style.md)

## Mock 只用于外部依赖

**禁止**：
- ❌ Mock 核心业务逻辑（如 `_init_agents`、`add_message`）
- ❌ 测试只验证"调用发生"，未验证"正确性"
- ❌ 过度依赖 Mock 测试，缺少集成测试

**决策表**：

| 测试对象 | 策略 | 原因 |
|----------|------|------|
| 外部依赖（CLI、网络、文件系统） | Mock | 不可控、慢 |
| 核心业务逻辑（_init_agents、add_message） | 真实实现 | 必须验证正确性 |
| 关键路径（崩溃恢复、并发安全） | 集成测试 | Mock 无法覆盖 |

**示例**：
```python
# ❌ Mock 掉核心逻辑
mock_group_chat._init_agents = AsyncMock()
# 测试通过，但实际功能有严重缺陷

# ✅ Mock 只用于外部依赖
# 核心业务逻辑使用真实实现
```

**规则**：
- Mock 只用于外部依赖（数据库、网络、文件系统、CLI 进程）
- 核心业务逻辑必须真实测试
- 测试应验证"功能正确"而非"代码执行"

## 关键路径必须有集成测试

**必须测试的场景类型**：
- 状态变更 + 崩溃恢复（验证持久化完整性）
- 状态变更 + 竞态条件（验证并发安全）
- 并发操作同一资源（验证数据一致性）

**示例**：
```python
# ✅ 集成测试：验证崩溃恢复
async def test_add_member_crash_recovery():
    chat = GroupChat(...)
    await chat.start()

    # 添加成员
    await chat.add_member("new_worker")

    # 模拟崩溃：销毁对象
    del chat

    # 重新加载
    chat = GroupChat.load_from_disk(...)

    # 验证新成员存在
    assert "new_worker" in chat.runtime.get_member_dicts()
```
