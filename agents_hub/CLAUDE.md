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

**规则**：在错误首次发现点必须有 ERROR 日志，包含：操作标识 + 失败原因 + 当前状态

**判断流程**：

```
异常即将 raise
    ↓
问：这是错误的首次发现点吗？
    ├─ 是 → 问：调用方能从异常消息获得足够调试信息吗？
    │         ├─ 否 → ✅ 必须记录 ERROR + 完整上下文
    │         └─ 是 → ❌ 不需要（简单参数错误、业务规则）
    └─ 否 → ❌ 不需要（底层已记录，避免重复）
              ⚠️ 建议：加注释说明底层已记录
```

**示例**：

```python
# ✅ 正确：首次发现点，记录完整上下文
def _validate_message(self, message: AgentMessage):
    if message.send_to not in self._agents_queue:
        logger.error(
            "消息校验失败: call_id=%s, 接收者未注册, 已注册=%s",
            message.call_id,
            list(self._agents_queue.keys()),  # ← 关键：当前状态
        )
        raise AgentNotFoundError(message.send_to)

# ✅ 正确：中间层转发，不重复记录
async def send_message(self, message: AgentMessage):
    try:
        self._validate_message(message)  # ← 底层已记录
        ...
    except (AgentNotFoundError, InvalidMessageError):
        # 直接向上传递，_validate_message() 已在首次发现点记录了 ERROR
        raise

# ✅ 正确：简单参数校验，异常消息已足够
def create_call(self, send_from: str, send_to: str):
    if not send_from or not send_to:
        raise ValueError("send_from 和 send_to 不能为空")  # 不需要 log

# ❌ 错误：首次发现点但缺少上下文
logger.debug("接收者未注册")  # 级别错误
raise AgentNotFoundError(send_to)

# ❌ 错误：中间层重复记录
async def send_message(self, message: AgentMessage):
    try:
        self._validate_message(message)
        ...
    except AgentNotFoundError as e:
        logger.error("发送失败: %s", str(e))  # ← 重复记录，污染日志
        raise
```

**记录内容要求**：
- 操作标识：call_id、path、agent_name 等唯一标识
- 失败原因：具体是什么错误
- 当前状态：已注册列表、队列大小、配置值等调试关键信息

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