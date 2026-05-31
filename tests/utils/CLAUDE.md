# utils test 编写规则

## 核心原则：契约驱动，而非覆盖率驱动

**测试"契约"（函数承诺做什么），而不是"实现"（函数如何做）**

❌ 错误：`assert router._agents_queue == {}`（访问私有属性）
✅ 正确：`assert queue.empty()`（验证行为）

---

## 测试编写流程

### 1. 识别契约
问自己：这个函数承诺做什么？

示例：`MessageRouter.clear()` 的契约：
- 清空所有队列中的消息
- 清空 agent 注册表
- 可以多次调用不报错（幂等性）

### 2. 每个契约写一个测试
一个测试只验证一个契约点。

### 3. 编写详细的 docstring
```python
async def test_function_name():
    """
    契约：[函数承诺做什么]
    
    验证方式：
    1. [准备步骤]
    2. [执行步骤]
    3. [验证步骤]
    
    如果失败，说明：[可能的原因]
    """
```

### 4. 覆盖边界情况
- 空输入（空队列、空注册表）
- 极端情况（大量数据）
- 异常情况（重复调用、并发）

---

## 测试命名规范

**格式**：`test_<function>_<契约描述>`

✅ 好的命名：
- `test_clear_empties_all_queues`
- `test_stop_wakes_blocked_run`

❌ 坏的命名：
- `test_clear_1`（无语义）
- `test_clear_works`（太模糊）

---

## 4 个常见反模式

### 1. 测试"能跑"
❌ `assert True`
✅ `assert all(task.done() for task in tasks)`

### 2. 访问私有属性
❌ `assert router._agents_queue == {}`
✅ `with pytest.raises(Exception): router.send_message(msg)`

### 3. mock 核心逻辑
❌ `mocker.patch('Agent.stop')`（mock 了要测试的东西）
✅ `mocker.patch('anthropic.Anthropic')`（只 mock 外部 API）

### 4. 一个测试验证多个契约
❌ 一个测试里验证清空队列、清空注册表、幂等性
✅ 拆分成 3 个独立测试

---

## Mock 策略

**什么时候 mock**：
- 外部 API（LLM、数据库、网络）
- 文件系统（如果测试不关注文件操作）
- 时间相关（`datetime.now()`）

**什么时候不 mock**：
- 被测试的类本身
- 被测试类的直接依赖
- 数据结构（`Queue`、`dict`、`list`）

---

## 测试结构

**标准结构**：准备 → 执行 → 验证

```python
async def test_clear_empties_all_queues():
    """契约：清空所有队列中的消息"""
    
    # 1. 准备
    router = MessageRouter()
    queue = asyncio.Queue()
    router.register("agent", queue)
    await queue.put("msg")
    
    # 2. 执行
    router.clear()
    
    # 3. 验证
    assert queue.empty(), "队列未清空"
```

**使用辅助函数减少重复**：
```python
def create_router_with_agents(names: list) -> MessageRouter:
    router = MessageRouter()
    for name in names:
        router.register(name, asyncio.Queue())
    return router
```

---

## 测试文件组织

```python
# tests/unit/test_message_router.py

"""
MessageRouter 单元测试

契约：
1. clear() 清空所有队列中的消息
2. clear() 清空 agent 注册表
3. clear() 可以多次调用不报错
"""

class TestMessageRouterClear:
    """测试 MessageRouter.clear() 的所有契约"""
    
    @pytest.mark.asyncio
    async def test_empties_all_queues(self):
        """契约 1：清空所有队列中的消息"""
        # ...
    
    @pytest.mark.asyncio
    async def test_removes_all_agents(self):
        """契约 2：清空 agent 注册表"""
        # ...
    
    @pytest.mark.asyncio
    async def test_idempotent(self):
        """契约 3：可以多次调用不报错"""
        # ...
```

---

## 质量检查清单

- [ ] 每个测试只验证一个契约点
- [ ] 测试名称清晰描述契约
- [ ] docstring 包含契约、验证方式、失败原因
- [ ] 没有访问私有属性
- [ ] 没有 mock 核心逻辑
- [ ] 覆盖了边界情况
- [ ] 重构实现时测试依然有效