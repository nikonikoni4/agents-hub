---
name: utils-test-write
description: 为 Python 函数/模块编写契约驱动的单元测试。支持两种模式：(1) 直接写测试 - 用于单个函数或少量测试（1-3个函数）；(2) MD checklist 模式 - 用于整个模块或大量测试（5+个函数）。触发词：写测试、测试、生成测试、为XX写测试、为XX模块写测试、先写测试规格、编写单元测试。
---

# 单元测试编写 Skill

## 核心原则

**契约驱动，而非覆盖率驱动**

测试函数承诺做什么（契约），而不是如何做（实现）。

---

## 使用模式

### 模式 1：直接写测试（少量测试）

**适用场景**：
- 单个函数
- 1-3 个函数
- 测试量少

**触发词**：
- "为 MessageRouter.clear() 写测试"
- "测试 Agent.stop()"
- "为 clear 方法生成测试"

**流程**：
1. 读取函数代码
2. 识别契约（内部思考，不输出）
3. 生成测试代码（带详细 docstring）
4. 运行测试
5. 报告结果

---

### 模式 2：MD checklist 模式（大量测试）

**适用场景**：
- 整个模块
- 5+ 个函数
- 测试量大

**触发词**：
- "为 MessageRouter 模块写测试"
- "为整个 GroupChat 写测试"
- "先写测试规格"

**流程**：
1. 读取模块代码
2. 识别所有需要测试的函数
3. 为每个函数识别契约
4. 生成 `test_<module>.md`（checklist）
5. 等待用户审查
6. 逐个生成测试代码
7. 每完成一个测试，更新 MD（打勾 ✅）
8. 全部完成后，询问是否删除 MD

---

## 何时使用 MD Checklist 模式？

**判断标准**：一次性编写的测试量

- **测试量少**（1-3 个函数）→ 模式 1（直接写测试）
- **测试量多**（5+ 个函数）→ 模式 2（MD checklist）

**MD 的定位**：
- ✅ 中间过程的 checklist（任务管理）
- ✅ 审查契约的工具（防止遗漏）
- ❌ 不是最终文档（最终看 docstring）

**MD 的生命周期**：
1. **创建**：`tests/unit/test_<module>.md`
2. **使用**：作为 checklist，逐个打勾
3. **完成**：删除或归档到 `docs/temp/`

---

## 测试编写规则

详细规则参考：`references/test-rules.md`

### 快速参考

#### 1. 识别契约
问自己：这个函数承诺做什么？

示例：`MessageRouter.clear()` 的契约：
- 清空所有队列中的消息
- 清空 agent 注册表
- 可以多次调用不报错（幂等性）

#### 2. 每个契约一个测试
一个测试只验证一个契约点。

#### 3. 详细的 docstring
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

#### 4. 测试命名
格式：`test_<function>_<契约描述>`

✅ 好的命名：
- `test_clear_empties_all_queues`
- `test_stop_wakes_blocked_run`

❌ 坏的命名：
- `test_clear_1`（无语义）
- `test_clear_works`（太模糊）

#### 5. 测试结构
准备 → 执行 → 验证

```python
async def test_clear_empties_all_queues():
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

---

## MD Checklist 格式

```markdown
# <Module> 测试规格

## 契约定义

### <FunctionName>

**契约点**：
1. [契约 1]
2. [契约 2]

**异常情况**：
- [异常 1]

**边界情况**：
- [边界 1]

---

## 测试用例

### <FunctionName>

#### 正常流程
- [ ] `test_<function>_<契约描述>` - 验证契约 1
- [ ] `test_<function>_<契约描述>` - 验证契约 2

#### 异常情况
- [ ] `test_<function>_<异常描述>` - 验证异常处理

#### 边界情况
- [ ] `test_<function>_<边界描述>` - 验证边界条件
```

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

## 工作流程

### 模式 1：直接写测试

```
用户："为 MessageRouter.clear() 写测试"
↓
1. Read 函数代码
2. 识别契约（内部思考）
3. Write 测试代码（tests/unit/test_message_router.py）
4. Bash 运行测试（pytest tests/unit/test_message_router.py -v）
5. 报告结果
```

### 模式 2：MD checklist

```
用户："为 MessageRouter 模块写测试"
↓
1. Read 模块代码
2. 识别所有函数和契约
3. Write test_message_router.md（checklist）
4. 等待用户审查
↓
用户："开始写测试"
↓
5. 逐个生成测试代码
6. 每完成一个，Edit MD（打勾 ✅）
7. Bash 运行测试
8. 全部完成后，询问是否删除 MD
```

---

## 注意事项

1. **测试框架**：默认使用 pytest + pytest-asyncio
2. **测试文件位置**：`tests/unit/test_<module>.py`
3. **MD 文件位置**：`tests/unit/test_<module>.md`（临时）
4. **最终文档**：测试代码的 docstring（不是 MD）
5. **运行命令**：`pytest tests/unit/test_<module>.py -v`

---

## 详细规则

完整的测试编写规则、反模式、示例，请参考：
- `references/test-rules.md`
