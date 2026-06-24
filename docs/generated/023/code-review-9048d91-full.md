# Code Review Report

**审查范围**: 31f3f44..9048d91 (feat: 定时记忆助手调度系统)
**审查时间**: 2026-06-24
**变更文件**: 17 个（11 个源码 + 6 个测试），+1368 行
**审查方式**: 8 个并行 Agent 独立审查（Security / Performance / Architecture / Code Quality / Best Practices / Testing / Documentation / Code Comments Compliance）

## 架构上下文

### 相关 ADR
- 无直接相关 ADR

### 相关 Spec
- `.scratch/memory-assistant-scheduler/architecture.md`: 调度器架构约束
- `.scratch/memory-assistant-scheduler/issues/01-06`: 6 个 issue 定义

### 相关编码规则
- `docs/coding-rules/backend-singleton.md`: 单例规则
- `docs/coding-rules/backend-concurrency.md`: 并发安全规则
- `docs/coding-rules/backend-style.md`: 错误处理规范
- `agents_hub/CLAUDE.md`: 日志记录规范

## 审查结果

Found 15 issues (置信度 >= 80):

### Issue 1: Mock 断言结构性缺陷 - 测试通过但未验证实际行为
- **类型**: Testing
- **置信度**: 95
- **位置**: `tests/scheduler/test_scheduler_service.py` (多处)
- **详情**: `_execute_memory_task` 测试中，`StateManager` 被 patch 为类，每次调用创建新 MagicMock 实例。测试配置的 `mock_sm` 从未被源码使用，对其断言（如 `save_memory_index.assert_called_once()`）永远通过但未验证任何实际行为。受影响测试：`test_executes_for_group_chats_needing_update`、`test_single_failure_continues_others`、`test_empty_index_does_nothing`、`test_skips_when_should_not_execute`。
- **依据**: 测试代码审查

### Issue 2: asyncio.create_task 未保存引用且缺少异常监控
- **类型**: Performance / Code Quality / Best Practices
- **置信度**: 95
- **位置**: `agents_hub/scheduler/scheduler_service.py:82`
- **详情**: `asyncio.create_task(self._execute_memory_task())` 创建的任务未保存引用（可能被 GC 回收），且未添加 `add_done_callback` 监控异常退出。`backend-concurrency.md` 明确要求"所有 asyncio.create_task() 创建的任务，必须添加 add_done_callback 监控异常退出"。
- **依据**: `docs/coding-rules/backend-concurrency.md`

### Issue 3: server.py 模块文档未更新工具数量
- **类型**: Documentation
- **置信度**: 95
- **位置**: `agents_hub/mcp/server.py:2`
- **详情**: 模块文档写 "MCP Server 和 14 个工具"，新增 `get_memory_context` 后实际已有 15 个注册工具。
- **依据**: 文档与代码一致性

### Issue 4: late import datetime as dt 冗余且不一致
- **类型**: Code Quality / Best Practices
- **置信度**: 95
- **位置**: `agents_hub/mcp/server.py:1486`
- **详情**: 函数内 `from datetime import datetime as dt`，但文件顶部第 36 行已有 `from datetime import datetime`。`as dt` 别名与同文件其他代码不一致。
- **依据**: PEP 8 / 编码一致性

### Issue 5: 硬编码路径 "agents_hub_history" 重复
- **类型**: Code Quality (DRY)
- **置信度**: 95
- **位置**: `agents_hub/scheduler/task/memory_task.py:95` 和 `agents_hub/mcp/server.py:1512`
- **详情**: 两处都硬编码了 `config.memory_path / "agents_hub_history" / "history.jsonl"`，应提取到 config 或公共常量。
- **依据**: DRY 原则

### Issue 6: _write_json 静默吞掉 OSError
- **类型**: Code Comments Compliance / Best Practices
- **置信度**: 92
- **位置**: `agents_hub/scheduler/state_manager.py:97-100`
- **详情**: 写入失败时仅 `logger.error` 记录，不抛出异常。调用方无法感知写入失败，可能导致内存中认为状态已更新但磁盘未写入。CLAUDE.md 要求"中间层捕获外部服务错误，转换为领域异常后抛出；不做兜底"。
- **依据**: `agents_hub/CLAUDE.md` 错误处理分层规则

### Issue 7: group_chat_id 未校验与 token 的归属关系
- **类型**: Architecture / Security
- **置信度**: 90
- **位置**: `agents_hub/mcp/server.py:1498-1534`
- **详情**: Token 解析得到 `_resolved_group_chat_id`，但 `get_group_chat_messages` 使用调用方传入的 `group_chat_id`。如果记忆助手 token 被泄露，可传入任意 `group_chat_id` 读取其他群聊消息。
- **依据**: 架构约束文件验证逻辑

### Issue 8: 循环内逐个读写 result.json
- **类型**: Performance
- **置信度**: 90
- **位置**: `agents_hub/scheduler/scheduler_service.py:130-143`
- **详情**: `_execute_memory_task` 循环中每处理一个群聊就调用 `state_manager.append_result()`，每次都读取+写入整个 `result.json`。N 个群聊产生 N 次文件 IO。
- **依据**: 性能优化

### Issue 9: 魔法数字 10
- **类型**: Code Quality
- **置信度**: 90
- **位置**: `agents_hub/scheduler/state_manager.py:76`
- **详情**: `if len(results) > 10` 中的 `10` 是魔法数字，应提取为模块级常量 `MAX_RESULT_ENTRIES = 10`。
- **依据**: 编码规范

### Issue 10: late import json
- **类型**: Code Quality / Best Practices
- **置信度**: 90
- **位置**: `agents_hub/mcp/server.py:1515`
- **详情**: `import json` 在函数体内导入，`json` 是标准库模块，应在文件顶部导入。
- **依据**: PEP 8

### Issue 11: 循环内使用 INFO 日志
- **类型**: Code Comments Compliance
- **置信度**: 90
- **位置**: `agents_hub/scheduler/task/memory_task.py:77, 92`
- **详情**: `MemoryTask.execute()` 每次执行输出 2 条 INFO，被循环调用时产生 2N 条 INFO。CLAUDE.md 禁止"循环内使用 INFO（应该汇总后记录）"。
- **依据**: `agents_hub/CLAUDE.md` 日志记录规范

### Issue 12: 测试缺少重入保护覆盖
- **类型**: Testing
- **置信度**: 90
- **位置**: `agents_hub/scheduler/scheduler_service.py:101-103`
- **详情**: `_execute_memory_task` 的 `_running` 重入保护逻辑没有测试覆盖。
- **依据**: 测试覆盖率

### Issue 13: 使用 execute 而非 execute_stream 偏离架构约束
- **类型**: Architecture
- **置信度**: 85
- **位置**: `agents_hub/scheduler/task/memory_task.py:87-90`
- **详情**: 架构约束文件指定使用 `agent_platform_client.execute_stream`（流式），但实现使用了 `execute`（非流式）。如果是有意变更，应记录原因。
- **依据**: `.scratch/memory-assistant-scheduler/architecture.md`

### Issue 14: 字符串匹配判断成功/失败
- **类型**: Code Quality
- **置信度**: 85
- **位置**: `agents_hub/scheduler/scheduler_service.py:134`
- **详情**: `is_success = not result_text.startswith("执行失败:")` 通过字符串前缀判断，如果错误消息格式变化会静默失效。应使用结构化返回值。
- **依据**: 可维护性

### Issue 15: 硬编码系统 token
- **类型**: Security
- **置信度**: 85
- **位置**: `agents_hub/config/config.py:332`
- **详情**: `assistant_token` 返回硬编码字符串 `"agents-hub-system"`，无法在不修改代码的情况下轮换。
- **依据**: 安全审查

### Issue 16: history.jsonl 一次性读取
- **类型**: Performance
- **置信度**: 85
- **位置**: `agents_hub/mcp/server.py:1518` 和 `agents_hub/scheduler/task/memory_task.py:31`
- **详情**: `read_text().strip().splitlines()` 将整个文件加载到内存，但 `get_memory_context` 只使用最后一行，`trim_history_jsonl` 只保留最后 1000 行。
- **依据**: 性能优化

### Issue 17: 单例表格缺少行号
- **类型**: Documentation
- **置信度**: 95
- **位置**: `docs/coding-rules/backend-singleton.md:19`
- **详情**: `scheduler_service` 行的"定义文件"列缺少行号，应为 `agents_hub/scheduler/scheduler_service.py:162`。
- **依据**: 文档格式一致性

### Issue 18: 测试缺少顶层异常处理覆盖
- **类型**: Testing
- **置信度**: 85
- **位置**: `agents_hub/scheduler/scheduler_service.py:155-158`
- **详情**: `_execute_memory_task` 的 `try/except Exception` 和 `finally: self._running = False` 没有测试覆盖。
- **依据**: 测试覆盖率

### Issue 19: 补偿逻辑边界时间未测试
- **类型**: Testing
- **置信度**: 80
- **位置**: `agents_hub/scheduler/scheduler_service.py:74`
- **详情**: 缺少 `hour=10, minute=0`（恰好相等）和 `hour=10, minute=30`（同一小时更晚）的测试。
- **依据**: 边界条件覆盖

### Issue 20: trim_history_jsonl 非原子写入
- **类型**: Best Practices
- **置信度**: 80
- **位置**: `agents_hub/scheduler/task/memory_task.py:26-34`
- **详情**: `write_text` 直接覆盖原文件，进程崩溃时文件可能损坏。应使用"写入临时文件 + rename"的原子写入模式。
- **依据**: 数据安全

### Issue 21: 配置校验失败静默回退无日志
- **类型**: Best Practices
- **置信度**: 80
- **位置**: `agents_hub/config/config.py:206-211`
- **详情**: `memory_task_cron_time` 超范围时静默返回 `(10, 0)`，未记录警告日志。
- **依据**: 错误处理规范

## 问题汇总

| 置信度 | 数量 | 关键问题 |
|--------|------|----------|
| 95 | 5 | Mock 断言缺陷、asyncio.create_task、文档未更新、late import、路径重复 |
| 90-92 | 6 | _write_json 吞异常、group_chat_id 越权、循环内 IO、魔法数字、late import json、循环内 INFO |
| 85 | 6 | 架构偏离、字符串匹配、硬编码 token、history.jsonl 读取、单例表格行号、异常处理测试 |
| 80 | 4 | 补偿边界测试、非原子写入、配置校验日志、trim 循环调用 |

## 变更摘要

**新建模块 `agents_hub/scheduler/`**：
- `scheduler_service.py`：SchedulerService 单例，封装 AsyncIOScheduler，含补偿执行逻辑
- `state_manager.py`：StateManager 管理 3 个状态 JSON 文件
- `task/memory_task.py`：MemoryTask 执行记忆收集 + history.jsonl 裁剪

**MCP 工具**：
- `server.py`：新增 get_memory_context（Token + 角色校验 + 上下文拼接）

**Config 扩展**：
- memory_task_cron_hour/minute + 范围校验 + memory_task_cron_time 属性

**Lifespan 集成**：app.py 中 scheduler_service.start()/shutdown()

**依赖**：pyproject.toml 添加 apscheduler>=3.10.0

**文档**：backend-singleton.md 单例表格新增 scheduler_service

**测试**：39 个全部通过（但存在 Mock 结构性缺陷）
