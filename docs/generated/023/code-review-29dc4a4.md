# Code Review Report

**审查范围**: 9048d91..29dc4a4 (fix: 修复代码审查发现的 5 个关键问题)
**审查时间**: 2026-06-24
**变更文件**: 7 个，+196 行 / -73 行
**审查方式**: 8 个并行 Agent 独立审查

## 关键问题修复验证

| # | 原始问题 | 修复状态 |
|---|---------|---------|
| 1 | Mock 断言结构性缺陷 | ✅ 已修复 - 测试正确验证 append_results 批量调用 |
| 2 | asyncio.create_task 缺少异常监控 | ✅ 已修复 - 保存引用到 _compensation_task + add_done_callback |
| 3 | _write_json 静默吞掉 OSError | ⚠️ 部分修复 - 移除 try/except 但未转换为领域异常 |
| 4 | group_chat_id 未校验归属 | ✅ 已修复 - 添加校验并在角色权限校验之前 |
| 5 | 循环内逐个读写 result.json | ✅ 已修复 - 改为 append_results 批量写入 |

## 审查结果

Found 7 secondary issues (置信度 >= 80):

### Issue 1: server.py 模块文档列表不完整
- **类型**: Documentation
- **置信度**: 95
- **位置**: `agents_hub/mcp/server.py:5-18`
- **详情**: 标题改为 "15 个工具" 但编号列表只枚举了 14 个，缺少 `get_memory_context`。

### Issue 2: _write_json 非原子写入
- **类型**: Best Practices
- **置信度**: 95
- **位置**: `agents_hub/scheduler/state_manager.py:107-109`
- **详情**: 直接 `open(path, "w")` 覆写，进程崩溃时文件可能损坏。应使用 write-to-temp-then-rename。

### Issue 3: _write_json 未转换为领域异常
- **类型**: Code Comments Compliance
- **置信度**: 90
- **位置**: `agents_hub/scheduler/state_manager.py:107-109`
- **详情**: CLAUDE.md 要求"中间层捕获外部服务错误，转换为领域异常后抛出"。当前直接抛出原始 OSError。

### Issue 4: _on_task_done 回调缺少 traceback
- **类型**: Best Practices
- **置信度**: 90
- **位置**: `agents_hub/scheduler/scheduler_service.py:94`
- **详情**: `logger.error("补偿执行任务异常退出: %s", exc)` 没有 `exc_info`，异常栈丢失。

### Issue 5: shutdown() 不取消正在运行的 _compensation_task
- **类型**: Best Practices
- **置信度**: 85
- **位置**: `agents_hub/scheduler/scheduler_service.py:96-104`
- **详情**: `shutdown()` 只关闭 scheduler，不取消独立的补偿任务。进程退出时 orphan task 可能导致意外行为。

### Issue 6: _write_json 异常传播导致容错退化
- **类型**: Architecture
- **置信度**: 85
- **位置**: `agents_hub/scheduler/scheduler_service.py:159`
- **详情**: 批量写入失败时整个结果丢失，违背"单群聊失败不影响其他群聊"的容错策略。建议对 append_results 单独 try/except。

### Issue 7: TestWriteJsonRaises 测试的是静态方法而非集成路径
- **类型**: Testing
- **置信度**: 85
- **位置**: `tests/scheduler/test_state_manager.py:103-109`
- **详情**: 直接调用 `_write_json` 而非通过 `append_results` 触发，无法验证异常沿集成路径传播。

## 变更摘要

- `server.py`: 添加 group_chat_id 归属校验 + 模块文档更新
- `scheduler_service.py`: 保存 _compensation_task 引用 + add_done_callback + 批量写入
- `state_manager.py`: 移除 _write_json 的 try/except + append_results 批量方法 + 魔法数字常量化
- 测试: 6 个文件更新，新增 _on_task_done 测试、group_chat_id 校验测试、写入异常传播测试
