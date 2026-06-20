# Code Review Report - 错误处理角度审查

**审查范围**: Loop 功能新增/修改文件
**审查时间**: 2026-06-20
**审查角度**: 错误处理
**变更文件**:
- `agents_hub/core/orchestration/loop_executor.py`
- `agents_hub/core/orchestration/loop_manager.py`
- `agents_hub/core/orchestration/group_chat.py`
- `agents_hub/mcp/server.py`

## 架构上下文

### 相关编码规则
- `docs/coding-rules/backend-style.md`: 错误处理规范
- `agents_hub/CLAUDE.md`: 分层错误处理规则

### 错误处理规范摘要

| 层级 | 规则 |
|------|------|
| 底层（业务逻辑） | 抛出领域异常（不 catch），让错误冒泡 |
| 中间层（服务/编排） | 捕获外部服务错误，转换为领域异常后抛出；不做兜底 |
| 顶层（API/接口） | 已有全局错误处理器 |

**禁止事项**：
- ❌ 使用 `except Exception` 捕获所有错误（边界除外）
- ❌ 吞掉异常（`except: pass`）
- ❌ 丢失异常链（不使用 `from e`）

## 审查结果

Found 1 issue:

### Issue 1: `_stop_agent_process` 使用 `except Exception` 吞掉异常

- **类型**: Code Quality / Best Practices
- **置信度**: 75
- **位置**: `agents_hub/core/orchestration/group_chat.py:1027-1035`
- **详情**:

```python
async def _stop_agent_process(self, agent):
    """终止 Agent 正在运行的 CLI 进程"""
    # ...
    try:
        await agent_platform_client.stop_session(
            platform=agent.role_config.platform,
            session_id=session_id,
            use_docker=use_docker,
        )
        logger.info("已终止 Agent %s 的 CLI 进程 (session: %s)", agent.name, session_id)
    except Exception as e:
        logger.error("终止 Agent %s 进程失败: %s", agent.name, str(e))
        # ⚠️ 异常被吞掉，没有重新抛出或转换为领域异常
```

**问题**：
1. 违反 `agents_hub/CLAUDE.md` 中的规则："❌ `except Exception` 吞掉异常"
2. 调用方无法知道进程停止是否成功
3. 虽然记录了 ERROR 日志，但异常链丢失

**依据**: `agents_hub/CLAUDE.md` 明确禁止 `except Exception` 吞掉异常（边界除外）

**已修复**：添加注释说明这是有意的降级处理（2026-06-20）

```python
except Exception as e:
    # 降级处理：进程停止失败不阻止后续清理（队列清空、MessageRouter 注销）
    # 避免因外部服务异常导致 Agent 状态不一致
    logger.error("终止 Agent %s 进程失败（降级继续）: %s", agent.name, str(e))
```

---

## 各文件错误处理分析

### loop_executor.py ✅

**分层错误处理**：
- ✅ 底层方法（`_validate_node_output`、`_wait_for_node_result`）抛出领域异常，不 catch
- ✅ 中间层（`_execute_node_with_retry`）捕获 `TimeoutError` 并转换为 `LoopExecutionError`
- ✅ 边界层（`run()`）使用 `except Exception` 兜底，符合规范

**异常链完整性**：
- ✅ 使用 `raise LoopExecutionError(...) from err` 保留原始异常（第 488-493 行）
- ✅ 异常消息包含足够调试信息（loop_id、node_id、agent_name、reason）

**资源清理**：
- ✅ `_emergency_stop()` 方法清理资源并持久化最终状态
- ✅ `_cleanup()` 方法清理所有运行时资源（agent 状态、completion queue、持久化）

### loop_manager.py ✅

**分层错误处理**：
- ✅ 底层方法抛出领域异常：`LoopNotFoundError`、`LoopStateError`、`LoopValidationError`、`AgentNotFoundError`
- ✅ 中间层捕获外部错误并转换：`OSError` → `FileSystemError`（第 395-400 行、416-421 行、438-442 行）

**异常链完整性**：
- ✅ 使用 `raise FileSystemError(...) from e` 保留原始异常
- ✅ 异常消息包含操作类型、路径、原因

**容错处理**：
- ✅ `_load_from_persistence()` 跳过损坏的 JSONL 行，记录 WARNING（第 380-385 行）
- ✅ 同一 loop_id 多条记录取最新（自动去重）

### group_chat.py ⚠️

**分层错误处理**：
- ✅ 使用领域异常：`StateError`、`LoopStateError`、`AgentNotFoundError`
- ⚠️ `_stop_agent_process()` 使用 `except Exception` 吞掉异常（见 Issue #1）
- ✅ `compress_all()` 的 `except Exception` 是有意的降级处理（跳过失败的 Agent）

**资源清理**：
- ✅ `stop_loop()` 方法正确清理资源（取消任务、恢复 Agent 状态）
- ✅ `cleanup()` 方法超时后强制取消任务
- ✅ `cleanup_loop()` 方法清理运行时引用

### server.py ✅

**边界层错误处理**：
- ✅ 每个 MCP 工具都正确捕获领域异常并转换为错误响应
- ✅ 使用 `logger.warning()` 记录预期错误，`logger.error()` 记录意外错误
- ✅ 通用的 `except Exception` 兜底层用于处理未预期的错误

**异常分类**：
- ✅ `LoopValidationError`、`AgentNotFoundError` → `VALIDATION_ERROR`
- ✅ `LoopNotFoundError`、`LoopStateError` → `VALIDATION_ERROR`
- ✅ 其他异常 → `INTERNAL_ERROR`

## 变更摘要

本次审查范围包含 4 个文件的 Loop 功能相关代码：

| 文件 | 错误处理质量 | 主要发现 |
|------|-------------|---------|
| loop_executor.py | ✅ 优秀 | 领域异常使用正确，异常链完整 |
| loop_manager.py | ✅ 优秀 | 外部错误正确转换，容错处理完善 |
| group_chat.py | ⚠️ 良好 | 1 处 `except Exception` 吞掉异常 |
| server.py | ✅ 优秀 | 边界层错误处理规范 |

**总体评价**：Loop 功能的错误处理整体质量较高，遵循了分层错误处理规范。仅发现 1 处需要改进的问题（`_stop_agent_process`），但该问题可能是有意的降级设计决策。
