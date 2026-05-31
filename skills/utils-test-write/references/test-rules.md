# 单元测试编写详细规则

本文档包含完整的测试编写规则、反模式、示例和最佳实践。

---

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

---

## 完整示例

### 示例 1：简单函数测试

```python
# tests/unit/test_message_router.py

import asyncio
import pytest
from agents_hub.core.communication import MessageRouter
from agents_hub.core.foundation import AgentMessage


class TestMessageRouterClear:
    """测试 MessageRouter.clear() 的所有契约"""
    
    @pytest.mark.asyncio
    async def test_empties_all_queues(self):
        """
        契约：clear() 应该清空所有队列中的消息
        
        验证方式：
        1. 注册 3 个 agent，保存队列引用
        2. 向每个 agent 发送消息
        3. 调用 clear()
        4. 验证所有队列都空了
        
        如果失败，说明：
        - clear() 没有清空某些队列
        - 清空逻辑有 bug
        """
        router = MessageRouter()
        
        # 注册 agent 并保存队列引用
        queues = {}
        for name in ["A", "B", "C"]:
            queue = asyncio.Queue()
            router.register(name, queue)
            queues[name] = queue
        
        # 发送消息
        router.send_message(AgentMessage(
            call_id="test", send_from="A", send_to="B", content="test"
        ))
        
        # 验证消息已发送
        assert queues["B"].qsize() > 0
        
        # 执行清空
        router.clear()
        
        # 验证：所有队列都空了
        assert queues["B"].qsize() == 0
        assert queues["C"].qsize() == 0
        assert queues["A"].qsize() == 0
    
    @pytest.mark.asyncio
    async def test_removes_all_agents(self):
        """
        契约：clear() 应该清空 agent 注册表
        
        验证方式：
        1. 注册 3 个 agent
        2. 调用 clear()
        3. 验证发送消息会失败
        
        如果失败，说明：
        - clear() 没有清空注册表
        """
        router = MessageRouter()
        for name in ["A", "B", "C"]:
            router.register(name, asyncio.Queue())
        
        router.clear()
        
        # 验证：发送消息应该失败
        with pytest.raises(Exception):
            router.send_message(AgentMessage(
                call_id="test", send_from="A", send_to="B", content="test"
            ))
    
    @pytest.mark.asyncio
    async def test_idempotent(self):
        """
        契约：clear() 可以多次调用不报错（幂等性）
        
        验证方式：
        1. 注册 3 个 agent
        2. 连续调用 clear() 3 次
        3. 验证不抛出异常
        
        如果失败，说明：
        - clear() 不是幂等的
        """
        router = MessageRouter()
        for name in ["A", "B", "C"]:
            router.register(name, asyncio.Queue())
        
        # 多次调用不应该报错
        router.clear()
        router.clear()
        router.clear()
```

### 示例 2：边界情况测试

```python
class TestMessageRouterClearEdgeCases:
    """测试 MessageRouter.clear() 的边界情况"""
    
    @pytest.mark.asyncio
    async def test_empty_router(self):
        """
        边界情况：空 router 调用 clear()
        
        验证：不应该报错
        """
        router = MessageRouter()
        router.clear()  # 应该不报错
    
    @pytest.mark.asyncio
    async def test_empty_queues(self):
        """
        边界情况：队列为空时调用 clear()
        
        验证：不应该报错
        """
        router = MessageRouter()
        for name in ["A", "B", "C"]:
            router.register(name, asyncio.Queue())
        
        # 没有发送消息，队列是空的
        router.clear()  # 应该不报错
```
