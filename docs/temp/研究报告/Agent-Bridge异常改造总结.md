# Agent Bridge 异常改造总结

> **改造时间**：2026-05-30  
> **改造范围**：`agents_hub/agent_bridge/` 模块的异常处理  
> **改造目标**：添加统一的错误处理，让所有异常继承自顶层 `agents_hub/exceptions.py`

---

## 改造内容

### 1. 新增的文件

| 文件 | 内容 |
|------|------|
| `agents_hub/agent_bridge/exceptions.py` | ✅ 新建异常定义文件 |

### 2. 修改的文件

| 文件 | 改造内容 |
|------|---------|
| `agents_hub/agent_bridge/executors/claude.py` | ✅ 使用 `CLINotFoundError` 和 `CLIExecutionError` |
| `agents_hub/agent_bridge/executors/codex.py` | ✅ 使用 `CLINotFoundError` 和 `CLIExecutionError` |
| `agents_hub/agent_bridge/parsers/claude.py` | ✅ 使用 `ParseError` |
| `agents_hub/agent_bridge/parsers/codex.py` | ✅ 使用 `ParseError` |
| `agents_hub/agent_bridge/bridge.py` | ✅ 添加平台验证和异常处理 |
| `agents_hub/agent_bridge/__init__.py` | ✅ 导出异常类 |

---

## 异常类设计

### 继承关系

```
AgentsHubError (顶层基类)
├── ExternalServiceError (外部服务错误)
│   └── AgentBridgeError (Agent Bridge 错误基类)
│       ├── CLINotFoundError
│       ├── CLIExecutionError
│       ├── ParseError
│       └── AgentTimeoutError (可恢复)
│
└── ValidationError (验证错误)
    └── PlatformNotSupportedError
```

---

## 异常类详解

### 1. CLINotFoundError

**继承自**：`AgentBridgeError` → `ExternalServiceError`

**用途**：CLI 命令不存在

**参数**：
- `platform`: 平台名称（"Claude" 或 "Codex"）
- `command`: CLI 命令路径

**使用场景**：
```python
# executors/claude.py
try:
    process = await asyncio.create_subprocess_exec(...)
except FileNotFoundError as e:
    raise CLINotFoundError(
        platform="Claude",
        command=CLAUDE_COMMAND
    ) from e
```

**返回给调用者**：
```json
{
  "error_code": "CLI_NOT_FOUND",
  "message": "Claude CLI 不存在: /usr/local/bin/claude",
  "details": {
    "platform": "Claude",
    "command": "/usr/local/bin/claude"
  },
  "type": "CLINotFoundError"
}
```

---

### 2. CLIExecutionError

**继承自**：`AgentBridgeError` → `ExternalServiceError`

**用途**：CLI 执行失败

**参数**：
- `platform`: 平台名称
- `exit_code`: 退出码
- `stderr`: 错误输出

**使用场景**：
```python
# executors/claude.py
await process.wait()
if process.returncode != 0:
    stderr = await process.stderr.read()
    raise CLIExecutionError(
        platform="Claude",
        exit_code=process.returncode,
        stderr=stderr.decode('utf-8')
    )
```

**返回给调用者**：
```json
{
  "error_code": "CLI_EXECUTION_ERROR",
  "message": "Claude CLI 执行失败 (exit code: 1)",
  "details": {
    "platform": "Claude",
    "exit_code": 1,
    "stderr": "Error: Invalid session ID"
  },
  "type": "CLIExecutionError"
}
```

---

### 3. ParseError

**继承自**：`AgentBridgeError` → `ExternalServiceError`

**用途**：解析 CLI 输出失败

**参数**：
- `platform`: 平台名称
- `raw_line`: 原始输出（截取前 200 字符）
- `reason`: 失败原因

**使用场景**：
```python
# parsers/claude.py
try:
    event = json.loads(raw_line)
except json.JSONDecodeError as e:
    raise ParseError(
        platform="Claude",
        raw_line=raw_line,
        reason=f"JSON decode error: {str(e)}"
    ) from e
```

**返回给调用者**：
```json
{
  "error_code": "PARSE_ERROR",
  "message": "Claude 输出解析失败: JSON decode error: ...",
  "details": {
    "platform": "Claude",
    "raw_line": "{invalid json...",
    "reason": "JSON decode error: Expecting value: line 1 column 1 (char 0)"
  },
  "type": "ParseError"
}
```

---

### 4. PlatformNotSupportedError

**继承自**：`ValidationError`

**用途**：平台不支持

**参数**：
- `platform`: 请求的平台名称
- `supported_platforms`: 支持的平台列表

**使用场景**：
```python
# bridge.py
if config.platform not in self._executors:
    supported = [p.value for p in self._executors.keys()]
    raise PlatformNotSupportedError(
        platform=config.platform.value,
        supported_platforms=supported
    )
```

**返回给调用者**：
```json
{
  "error_code": "PLATFORM_NOT_SUPPORTED",
  "message": "平台 'unknown' 不支持",
  "details": {
    "platform": "unknown",
    "supported_platforms": ["claude", "codex"]
  },
  "type": "PlatformNotSupportedError"
}
```

---

### 5. AgentTimeoutError

**继承自**：`AgentBridgeError` + `RecoverableError`

**用途**：Agent 执行超时（可恢复）

**参数**：
- `platform`: 平台名称
- `timeout_seconds`: 超时时间（秒）

**特点**：
- 继承自 `RecoverableError`，可以自动重试
- 默认 `retry_after = 5.0` 秒

**使用场景**：
```python
# 未来在 bridge.py 中添加超时控制
async with asyncio.timeout(timeout_seconds):
    async for event in self.execute_stream(...):
        yield event
```

**返回给调用者**：
```json
{
  "error_code": "AGENT_TIMEOUT",
  "message": "Claude Agent 执行超时 (30.0秒)",
  "details": {
    "platform": "Claude",
    "timeout_seconds": 30.0
  },
  "type": "AgentTimeoutError"
}
```

---

## 错误处理策略

### 1. Executor 层（executors/）

**策略**：只抛出，不捕获

```python
# ❌ 错误：捕获并记录日志
try:
    process = await asyncio.create_subprocess_exec(...)
except FileNotFoundError:
    logger.error("CLI not found")
    # 吞掉异常或返回 None

# ✅ 正确：抛出具体异常
try:
    process = await asyncio.create_subprocess_exec(...)
except FileNotFoundError as e:
    raise CLINotFoundError(platform="Claude", command=CLAUDE_COMMAND) from e
```

---

### 2. Parser 层（parsers/）

**策略**：解析失败抛出异常

```python
# ❌ 错误：返回 None
try:
    event = json.loads(raw_line)
except json.JSONDecodeError:
    return None  # 丢失了错误信息

# ✅ 正确：抛出 ParseError
try:
    event = json.loads(raw_line)
except json.JSONDecodeError as e:
    raise ParseError(
        platform="Claude",
        raw_line=raw_line,
        reason=f"JSON decode error: {str(e)}"
    ) from e
```

---

### 3. Bridge 层（bridge.py）

**策略**：验证输入，捕获并处理 ParseError

```python
# 验证平台
if config.platform not in self._executors:
    raise PlatformNotSupportedError(...)

# 捕获 ParseError，记录日志，跳过该行
try:
    parsed_event = parser.parse_event(raw_line)
except ParseError:
    logger.warning(f"Skipping unparseable line from {config.platform.value}")
    continue  # 跳过该行，继续处理

# CLI 错误直接向上传递
except (CLINotFoundError, CLIExecutionError):
    raise
```

---

### 4. 边界层（MCP Server / API Server）

**策略**：统一捕获，转换为响应格式

```python
# MCP Server 或 API Server
try:
    result = await agent_bridge.execute(prompt, config)
    return {"success": True, "data": result}

except CLINotFoundError as e:
    logger.error(f"CLI 不存在: {e}", extra={"details": e.details})
    return {
        "success": False,
        "error": e.to_dict(),
        "suggestion": f"请安装 {e.details['platform']} CLI"
    }

except CLIExecutionError as e:
    logger.error(f"CLI 执行失败: {e}", extra={"details": e.details})
    return {
        "success": False,
        "error": e.to_dict(),
        "suggestion": "请检查 CLI 配置和权限"
    }

except PlatformNotSupportedError as e:
    logger.warning(f"平台不支持: {e}", extra={"details": e.details})
    return {
        "success": False,
        "error": e.to_dict(),
        "suggestion": f"支持的平台: {', '.join(e.details['supported_platforms'])}"
    }

except AgentTimeoutError as e:
    logger.warning(f"执行超时: {e}", extra={"details": e.details})
    return {
        "success": False,
        "error": e.to_dict(),
        "suggestion": "请稍后重试或增加超时时间"
    }

except Exception as e:
    logger.critical(f"未预期错误: {e}", exc_info=True)
    return {
        "success": False,
        "error": {"error_code": "UNKNOWN_ERROR", "message": "系统错误"}
    }
```

---

## 测试状态

### ⚠️ 已知的测试问题（与改造无关）

```bash
tests/unit/agent_bridge/test_bridge.py::test_execute_stream_calls_correct_executor FAILED
tests/unit/agent_bridge/test_bridge.py::test_execute_returns_result FAILED
```

**失败原因**：
- 测试 mock 返回的是字典，而不是 `StreamEvent` 对象
- 这是测试本身的问题，与异常改造无关

**修复方案**：
- 更新测试，让 mock 返回正确的 `StreamEvent` 对象
- 或者更新代码，兼容字典和对象两种格式

---

## 改造前后对比

### 改造前

```python
# executors/claude.py
except FileNotFoundError:
    logger.error("Claude CLI not found. Please ensure 'claude' is installed and in PATH.")
    raise  # 抛出原始异常，没有上下文信息

# parsers/claude.py
except json.JSONDecodeError:
    return None  # 吞掉异常，丢失错误信息
```

**问题**：
- ❌ 没有统一的错误码
- ❌ 没有携带上下文信息
- ❌ 无法转换为 JSON 响应
- ❌ 解析错误被吞掉，无法追踪

---

### 改造后

```python
# executors/claude.py
except FileNotFoundError as e:
    raise CLINotFoundError(
        platform="Claude",
        command=CLAUDE_COMMAND
    ) from e

# parsers/claude.py
except json.JSONDecodeError as e:
    raise ParseError(
        platform="Claude",
        raw_line=raw_line,
        reason=f"JSON decode error: {str(e)}"
    ) from e
```

**优势**：
- ✅ 统一的错误码（`CLI_NOT_FOUND`、`PARSE_ERROR`）
- ✅ 携带上下文信息（平台、命令、原始输出）
- ✅ 支持 `to_dict()` 转换为 JSON 响应
- ✅ 保留异常链（`from e`）
- ✅ 符合项目的错误处理规范

---

## 下一步计划

### 1. 修复测试

- [ ] 更新 `tests/unit/agent_bridge/test_bridge.py`
- [ ] 让 mock 返回正确的 `StreamEvent` 对象

### 2. 添加超时控制

- [ ] 在 `bridge.py` 中添加超时控制
- [ ] 使用 `asyncio.timeout()` 或 `asyncio.wait_for()`
- [ ] 抛出 `AgentTimeoutError`

### 3. 继续改造其他模块

- [ ] `agents_hub/core/foundation/exceptions.py`
- [ ] `agents_hub/core/communication/exceptions.py`
- [ ] `agents_hub/core/agent/exceptions.py`
- [ ] `agents_hub/core/context/exceptions.py`
- [ ] `agents_hub/core/orchestration/exceptions.py`
- [ ] `agents_hub/mcp/exceptions.py`
- [ ] `agents_hub/api/exceptions.py`

---

## 总结

✅ **改造完成**：`agents_hub/agent_bridge/` 模块的异常处理已全部改造完成

✅ **符合规范**：所有异常都继承自顶层 `AgentsHubError`，携带上下文信息，支持 JSON 转换

✅ **分层清晰**：
- Executor 层：只抛出，不捕获
- Parser 层：解析失败抛出异常
- Bridge 层：验证输入，捕获 ParseError
- 边界层：统一捕获，转换为响应格式

🎯 **下一步**：修复测试，添加超时控制，继续改造其他模块
