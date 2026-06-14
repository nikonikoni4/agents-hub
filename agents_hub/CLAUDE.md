# 后端通用规则

> 上级规则：[../CLAUDE.md]

1. 数据路径统一使用 `config.data_path`
2. 错误处理详见 `docs/coding-rules/backend-style.md`

## 错误处理

**分层规则**：

| 层级 | 规则 |
|------|------|
| 底层（业务逻辑） | 抛出领域异常（如 UserNotFound），不 catch，让错误冒泡 |
| 中间层（服务/编排） | 捕获外部服务错误（IO/网络/数据库），转换为领域异常后抛出；不做兜底 |
| 顶层（API/接口） | 已有全局错误处理器 |

**外部接口层必须捕获并转换**：

```python
# ✅ 正确：捕获 OSError，转换为 FileSystemError
try:
    with open(path, "a", encoding="utf-8") as f:
        f.write(data)
except OSError as e:
    raise FileSystemError(operation="write", path=str(path), reason=str(e)) from e

# ❌ 错误：中间层 catch Exception 并吞掉
async def _sync_status(self, status: str):
    try:
        await self.runtime.update_agent_status(self.name, status)
    except Exception as e:  # 禁止
        self.logger.warning("同步状态失败: %s", str(e))
```

## 日志记录

**触发场景**：数据流处理、生命周期管理、跨边界调用、异常处理（raise 前）

**核心原则**：生产环境 DEBUG 不可见，关键流程必须用 INFO，异常抛出前必须用 ERROR

### INFO：关键流程必须可追踪

**判断标准**：主流程 / 操作失败用户可感知 / 流程出问题必须在日志看到 → INFO

**必须 INFO 的场景**：

```python
logger.info("消息投递: call_id=%s, from=%s, to=%s, type=%s", ...)
logger.info("Agent 启动/停止/注册/注销: name=%s, ...", ...)
logger.info("群聊激活/加载: id=%s, ...", ...)
logger.info("跨边界调用: MCP工具=%s, 进程=%s, ...", ...)
logger.info("AgentCall 创建/完成: call_id=%s, ...", ...)
```

### ERROR：异常抛出前必须记录完整上下文

**规则**：所有 raise 前必须有 ERROR 日志，包含：操作标识 + 失败原因 + 当前状态

```python
# ✅ 正确
logger.error("消息投递失败: call_id=%s, 接收者未注册, 已注册=%s", call_id, list(self._agents_queue.keys()))
raise AgentNotFoundError(send_to)

# ❌ 错误：级别错误 / 缺少上下文 / 没有日志
logger.debug("接收者未注册")
raise AgentNotFoundError(send_to)
```

### WARN vs DEBUG

- **WARN**：批量操作部分失败、降级方案、可疑状态但不影响当前操作
- **DEBUG**：幂等性检查、辅助函数、详细参数、内部状态

## 禁止事项

- ❌ 关键流程（消息投递、状态变化、跨边界）使用 DEBUG
- ❌ 异常抛出前使用 DEBUG 或不记录日志
- ❌ ERROR 日志缺少上下文（只有错误消息）
- ❌ 循环内使用 INFO（应该汇总后记录）
- ❌ 辅助函数使用 INFO（应该用 DEBUG）
- ❌ `except Exception` 吞掉异常
- ❌ 不捕获外部错误，让原始异常直接冒泡