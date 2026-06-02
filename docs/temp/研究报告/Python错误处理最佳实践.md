# Python 错误处理最佳实践研究报告

> **目标读者**：agents-hub 项目开发者  
> **目的**：学习 Python 错误处理的最佳实践，为项目设计完善的错误处理架构  
> **创建时间**：2026-05-30

---

## 目录

1. [核心原则](#核心原则)
2. [异常层次结构设计](#异常层次结构设计)
3. [错误分类策略](#错误分类策略)
4. [异常处理模式](#异常处理模式)
   - 模式 1：边界处理
   - 模式 1b：FastAPI 全局异常处理器
5. [日志记录最佳实践](#日志记录最佳实践)
6. [错误处理反模式](#错误处理反模式)
7. [针对 agents-hub 的建议](#针对-agents-hub-的建议)

---

## 核心原则

### 1. 异常是异常，不是返回值

**原则**：用异常表示"不应该发生的情况"，用返回值表示"正常的分支"

```python
# ❌ 错误示范 - 用返回值表示错误
def get_user(user_id: str) -> dict | None:
    if user_id not in users:
        return None  # 用户不存在是异常情况，不是正常分支
    return users[user_id]

# ✅ 正确示范 - 用异常表示错误
def get_user(user_id: str) -> dict:
    if user_id not in users:
        raise UserNotFoundError(user_id)
    return users[user_id]
```

**为什么？**
- 异常会强制调用者处理错误情况
- 返回值容易被忽略（忘记检查 None）
- 异常可以携带更多上下文信息

---

### 2. 在边界处理

**原则**：内部函数抛出异常，在系统边界统一捕获并转换

```python
# 内部函数 - 只抛出，不捕获
def _validate_message(message: AgentMessage):
    if not message.content:
        raise InvalidMessageError("消息内容不能为空")
    if message.send_from not in agents:
        raise AgentNotFoundError(message.send_from)

# 边界函数 - 统一捕获并转换
def call_agent_api(request: dict) -> dict:
    """MCP Tool 入口，必须返回结构化响应"""
    try:
        message = parse_request(request)
        _validate_message(message)
        result = _do_call_agent(message)
        return {"success": True, "data": result}
    
    except InvalidMessageError as e:
        return {"success": False, "error": e.to_dict()}
    
    except AgentNotFoundError as e:
        return {"success": False, "error": e.to_dict()}
```

**边界在哪里？**
- MCP Tool 入口（`call_agent`）
- REST API 端点（FastAPI 路由）
- Agent.run() 循环
- 文件操作函数

---

### 3. 保留上下文

**原则**：异常应该携带足够的信息用于调试和日志记录

```python
# ❌ 错误示范 - 信息不足
raise ValueError("Agent 不存在")

# ✅ 正确示范 - 携带上下文
raise AgentNotFoundError(
    agent_name="worker1",
    available_agents=["小李", "小赵", "Leader"],
    group_chat_id="abc123"
)
```

**上下文包括什么？**
- 错误发生时的参数值
- 相关的业务对象 ID
- 可用的替代选项
- 原始异常（异常链）

---

### 4. 分类处理

**原则**：不同类型的错误用不同的处理策略

| 错误类型 | 处理策略 | 示例 |
|---------|---------|------|
| **可恢复错误** | 自动重试（带退避） | API 限流、临时网络故障 |
| **业务错误** | 返回给调用者处理 | Agent 不存在、权限不足 |
| **验证错误** | 返回详细提示 | 参数格式错误、数据不符合约束 |
| **系统错误** | 记录日志、通知管理员 | 数据库连接失败、磁盘满 |

---

### 5. 对用户友好

**原则**：错误信息应该清晰、可操作

```python
# ❌ 错误示范 - 信息模糊
{"error": "Invalid input"}

# ✅ 正确示范 - 清晰 + 可操作
{
    "error_code": "AGENT_NOT_FOUND",
    "message": "Agent 'worker1' 不存在，请检查 agent 名称是否正确",
    "details": {
        "agent_name": "worker1",
        "available_agents": ["小李", "小赵", "Leader"]
    },
    "suggestion": "请使用 list_agents 查看可用的 agent 列表"
}
```

---

## 异常层次结构设计

### 设计原则

**核心思想**：建立清晰的异常继承树，让调用者可以选择捕获的粒度

```
AgentsHubError (基类)
├── ValidationError (验证错误)
├── ResourceNotFoundError (资源不存在)
├── StateError (状态错误)
├── ExternalServiceError (外部服务错误)
└── SystemError (系统错误)
```

**为什么分层？**
- **粗粒度捕获**：`except ValidationError` 捕获所有验证错误
- **细粒度捕获**：`except AgentNotFoundError` 捕获特定错误
- **全局捕获**：`except AgentsHubError` 捕获所有业务异常

---

### 基础异常类设计

```python
class AgentsHubError(Exception):
    """所有 agents-hub 异常的基类
    
    设计要点：
    1. 提供统一的错误信息格式
    2. 支持错误码（用于 API/MCP 响应）
    3. 携带上下文信息（便于调试和日志）
    4. 保留原始异常链
    """
    def __init__(
        self, 
        message: str, 
        error_code: str | None = None,
        details: dict | None = None,
        cause: Exception | None = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause  # 保留原始异常
        super().__init__(message)
    
    def __str__(self) -> str:
        """人类可读的错误信息"""
        base = f"[{self.error_code}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.cause:
            base += f" | Caused by: {type(self.cause).__name__}: {self.cause}"
        return base
    
    def to_dict(self) -> dict:
        """转换为字典（用于 JSON 响应）"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }
```

**关键设计点**：

1. **error_code**：用于 API 响应，客户端可以根据错误码做不同处理
2. **details**：携带上下文信息，便于调试
3. **cause**：保留原始异常，形成异常链
4. **to_dict()**：方便转换为 JSON 响应

---

### 具体异常类示例

```python
# 1. 验证错误
class ValidationError(AgentsHubError):
    """验证错误（用户输入、参数格式等）"""
    pass

class InvalidMessageError(ValidationError):
    """消息格式错误"""
    def __init__(self, reason: str, message_data: dict | None = None):
        super().__init__(
            message=f"消息格式错误: {reason}",
            error_code="INVALID_MESSAGE",
            details={"reason": reason, "message_data": message_data}
        )

# 2. 资源不存在错误
class ResourceNotFoundError(AgentsHubError):
    """资源不存在错误"""
    pass

class AgentNotFoundError(ResourceNotFoundError):
    """Agent 不存在"""
    def __init__(self, agent_name: str, available_agents: list[str] | None = None):
        super().__init__(
            message=f"Agent '{agent_name}' 不存在",
            error_code="AGENT_NOT_FOUND",
            details={
                "agent_name": agent_name,
                "available_agents": available_agents or []
            }
        )

class GroupChatNotFoundError(ResourceNotFoundError):
    """GroupChat 不存在"""
    def __init__(self, group_chat_id: str):
        super().__init__(
            message=f"GroupChat '{group_chat_id}' 不存在",
            error_code="GROUP_CHAT_NOT_FOUND",
            details={"group_chat_id": group_chat_id}
        )

# 3. 状态错误
class StateError(AgentsHubError):
    """状态错误（如在错误的状态下执行操作）"""
    pass

class InvalidStateTransitionError(StateError):
    """无效的状态转换"""
    def __init__(self, from_state: str, to_state: str, reason: str):
        super().__init__(
            message=f"无法从 {from_state} 转换到 {to_state}: {reason}",
            error_code="INVALID_STATE_TRANSITION",
            details={"from_state": from_state, "to_state": to_state, "reason": reason}
        )

# 4. 外部服务错误
class ExternalServiceError(AgentsHubError):
    """外部服务错误（LLM API、文件系统等）"""
    pass

class LLMAPIError(ExternalServiceError):
    """LLM API 错误"""
    pass

class RateLimitError(LLMAPIError):
    """API 限流（可恢复）"""
    def __init__(self, retry_after: float = 5.0):
        super().__init__(
            message=f"API 限流，请 {retry_after} 秒后重试",
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after  # 用于重试逻辑

class FileSystemError(ExternalServiceError):
    """文件系统错误"""
    def __init__(self, operation: str, path: str, reason: str):
        super().__init__(
            message=f"文件系统错误: {operation} '{path}' 失败 - {reason}",
            error_code="FILE_SYSTEM_ERROR",
            details={"operation": operation, "path": path, "reason": reason}
        )

# 5. 系统错误
class SystemError(AgentsHubError):
    """系统级错误，需要管理员处理"""
    pass

class DatabaseConnectionError(SystemError):
    """数据库连接失败"""
    pass
```

---

## 错误分类策略

### 按"谁应该处理"分类

这是最实用的分类方式，直接指导错误处理策略。

#### 1. 可恢复错误（Recoverable Error）

**特征**：系统可以自动重试解决

**处理策略**：自动重试（带指数退避）

**示例**：
- API 限流（429 错误）
- 临时网络故障
- 队列临时满

```python
class RecoverableError(AgentsHubError):
    """可以通过重试解决的错误"""
    def __init__(self, message: str, retry_after: float = 1.0, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after  # 建议的重试延迟（秒）
```

---

#### 2. 业务错误（Business Error）

**特征**：业务逻辑错误，需要调用者处理

**处理策略**：返回结构化错误信息给调用者

**示例**：
- Agent 不存在
- 权限不足
- 操作超时

```python
class BusinessError(AgentsHubError):
    """业务逻辑错误，需要调用者处理"""
    pass
```

---

#### 3. 验证错误（Validation Error）

**特征**：输入参数不符合要求

**处理策略**：返回详细的错误信息，帮助调用者修正

**示例**：
- 参数缺失或格式错误
- 数据不符合约束
- 消息内容为空

```python
class ValidationError(AgentsHubError):
    """验证错误，需要明确提示"""
    pass
```

---

#### 4. 系统错误（System Error）

**特征**：系统级故障，需要人工介入

**处理策略**：记录日志、通知管理员、返回通用错误信息（不暴露内部细节）

**示例**：
- 数据库连接失败
- 磁盘空间不足
- 配置文件损坏

```python
class SystemError(AgentsHubError):
    """系统级错误，需要管理员处理"""
    pass
```

---

## 异常处理模式

### 模式 1：边界处理（Boundary Handling）

**核心思想**：在系统边界捕获所有异常，转换为统一格式

**适用场景**：MCP Tool 入口、REST API 端点

```python
def call_agent(group_chat_id: str, send_from: str, send_to: str, content: str) -> dict:
    """MCP Tool 入口，必须返回结构化响应"""
    try:
        # 业务逻辑
        result = _do_call_agent(group_chat_id, send_from, send_to, content)
        return {
            "success": True,
            "data": result
        }
    
    except ValidationError as e:
        # 验证错误 - 返回 400 类错误
        logger.warning(f"验证错误: {e}", extra={"details": e.details})
        return {
            "success": False,
            "error": e.to_dict(),
            "suggestion": "请检查输入参数是否正确"
        }
    
    except ResourceNotFoundError as e:
        # 资源不存在 - 返回 404 类错误
        logger.warning(f"资源不存在: {e}", extra={"details": e.details})
        return {
            "success": False,
            "error": e.to_dict(),
            "suggestion": "请使用 list_agents 查看可用资源"
        }
    
    except RecoverableError as e:
        # 可恢复错误 - 返回 503 类错误
        logger.error(f"临时错误: {e}", extra={"details": e.details})
        return {
            "success": False,
            "error": e.to_dict(),
            "suggestion": f"请稍后重试（建议 {e.retry_after} 秒后）"
        }
    
    except SystemError as e:
        # 系统错误 - 返回 500 类错误
        logger.critical(f"系统错误: {e}", exc_info=True, extra={"details": e.details})
        # 发送告警通知管理员
        alert_admin(e)
        return {
            "success": False,
            "error": {
                "error_code": "INTERNAL_ERROR",
                "message": "系统内部错误，请联系管理员"
            }
        }
    
    except Exception as e:
        # 未预期的错误 - 记录完整堆栈
        logger.critical(f"未预期错误: {e}", exc_info=True)
        alert_admin(e)
        return {
            "success": False,
            "error": {
                "error_code": "UNKNOWN_ERROR",
                "message": "未知错误，请联系管理员"
            }
        }
```

**关键点**：
1. **只在边界捕获**：内部函数抛出异常，边界统一处理
2. **分类处理**：不同类型的错误返回不同的响应和建议
3. **日志级别**：ValidationError 用 WARNING，SystemError 用 CRITICAL
4. **隐藏细节**：SystemError 不暴露内部实现细节给调用者

---

### 模式 1b：FastAPI 全局异常处理器（Global Exception Handler）

**核心思想**：将边界处理从"每个端点写 try/except"提升为"在 app 层统一注册"，消除路由层的重复代码。

**适用场景**：FastAPI REST API 层

#### 为什么不用路由层 try/except？

```python
# ❌ 每个端点都重复一遍 — 违反 DRY
@router.get("/skills/{skill_name}")
def get_skill(skill_name: str):
    try:
        ...
    except InvalidSkillError as e:
        raise HTTPException(status_code=400, detail=e.to_dict()) from e
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict()) from e

@router.delete("/skills/{skill_name}")
def delete_skill(skill_name: str):
    try:
        ...
    except InvalidSkillError as e:       # 重复
        raise HTTPException(status_code=400, detail=e.to_dict()) from e
    except SkillNotFoundError as e:      # 重复
        raise HTTPException(status_code=404, detail=e.to_dict()) from e
```

**问题**：
- 同样的映射逻辑在每个端点重复
- 新增端点容易忘记加 try/except
- 新增异常类型时需要改所有端点

#### 全局处理器方案

```python
# ✅ 在 app.py 注册一次，所有路由自动生效

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from agents_hub.exceptions import (
    AgentsHubError, ValidationError, ResourceNotFoundError,
    StateError, ExternalServiceError
)

logger = logging.getLogger(__name__)

# 异常类型 → HTTP 状态码映射
_STATUS_MAP: dict[type[AgentsHubError], int] = {
    ValidationError: 400,
    ResourceNotFoundError: 404,
    StateError: 409,
    ExternalServiceError: 502,
}

def _resolve_status(exc: AgentsHubError) -> int:
    """根据异常类型映射 HTTP 状态码（子类优先匹配）"""
    for exc_cls, status in _STATUS_MAP.items():
        if isinstance(exc, exc_cls):
            return status
    return 500

app = FastAPI()

@app.exception_handler(AgentsHubError)
async def agents_hub_error_handler(request: Request, exc: AgentsHubError) -> JSONResponse:
    """处理所有 agents-hub 领域异常"""
    status = _resolve_status(exc)
    return JSONResponse(status_code=status, content=exc.to_dict())

@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底：捕获所有未处理异常，防止内部信息泄露"""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error_code": "INTERNAL_ERROR", "message": "服务器内部错误", "type": "InternalError"},
    )
```

#### 路由层变得干净

```python
# ✅ 路由只关心业务逻辑，错误处理全部交给全局处理器
@router.get("/skills/{skill_name}", response_model=SkillResponse)
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    skill = service.get_skill(skill_name)
    return SkillResponse.from_domain(skill)
```

#### 关键设计点

1. **`_STATUS_MAP` 状态码映射**：集中定义异常类型与 HTTP 状态码的对应关系，新增异常类型只需加一行映射
2. **`isinstance` 匹配**：子类自动继承父类的映射（`SkillNotFoundError` 继承 `ResourceNotFoundError` → 404）
3. **两层 handler**：
   - `AgentsHubError` handler：处理所有已知业务异常，返回结构化错误（`to_dict()`）
   - `Exception` handler：兜底捕获未知异常，记录日志，返回通用 500，不泄露内部信息
4. **路由层零错误处理**：try/except、HTTPException、异常导入全部移除

#### 与模式 1（边界处理）的关系

| 对比项 | 模式 1（路由层 try/except） | 模式 1b（全局 handler） |
|--------|---------------------------|----------------------|
| 作用域 | 单个端点 | 所有路由 |
| 代码重复 | 每个端点重复 | 注册一次 |
| 新增端点 | 需要加 try/except | 自动生效 |
| 定制能力 | 每个端点可定制 | 统一处理 |
| 推荐场景 | MCP Tool 入口、需要特殊处理的端点 | REST API 层 |

**实际项目中的组合**：REST API 用全局 handler，MCP Tool 入口用模式 1（因为 MCP 返回格式与 HTTP 不同）。

---

### 模式 2：异常链（Exception Chaining）

**核心思想**：保留原始异常信息，方便调试

**适用场景**：包装底层异常为业务异常

```python
# ❌ 错误示范 - 丢失原始异常
def save_file(path: str, content: str):
    try:
        with open(path, 'w') as f:
            f.write(content)
    except OSError:
        raise FileSystemError(f"无法写入文件 {path}")  # 丢失了原始错误信息

# ✅ 正确示范 - 保留异常链
def save_file(path: str, content: str):
    try:
        with open(path, 'w') as f:
            f.write(content)
    except OSError as e:
        raise FileSystemError(
            operation="write",
            path=path,
            reason=str(e)
        ) from e  # ✅ Python 的异常链语法
```

**为什么重要？**
- 调试时可以看到完整的错误链：`FileSystemError → PermissionError → [Errno 13]`
- 日志中可以记录完整的堆栈信息
- `from e` 语法会设置 `__cause__` 属性

---

### 模式 3：重试装饰器（Retry Decorator）

**核心思想**：自动重试可恢复错误

**适用场景**：调用外部服务（LLM API、网络请求）

```python
import asyncio
from functools import wraps
from typing import TypeVar, Callable

T = TypeVar('T')

def retry_on_recoverable(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    max_backoff: float = 60.0
):
    """重试装饰器，只重试 RecoverableError"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            attempt = 0
            last_error = None
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                
                except RecoverableError as e:
                    attempt += 1
                    last_error = e
                    
                    if attempt >= max_attempts:
                        logger.error(f"重试 {max_attempts} 次后仍失败: {e}")
                        raise
                    
                    # 指数退避
                    delay = min(e.retry_after * (backoff_factor ** (attempt - 1)), max_backoff)
                    logger.warning(
                        f"遇到可恢复错误，{delay}秒后重试 (第{attempt}/{max_attempts}次): {e}"
                    )
                    await asyncio.sleep(delay)
                
                except Exception:
                    # 非可恢复错误，直接抛出
                    raise
            
            raise last_error  # 不应该到这里
        
        return wrapper
    return decorator

# 使用示例
@retry_on_recoverable(max_attempts=3)
async def call_llm_api(prompt: str) -> str:
    """调用 LLM API，自动重试限流错误"""
    response = await llm_client.generate(prompt)
    if response.status == 429:
        raise RateLimitError("API 限流", retry_after=5.0)
    return response.text
```

**关键点**：
1. **只重试可恢复错误**：其他错误直接抛出
2. **指数退避**：避免频繁重试加重服务负担
3. **最大退避时间**：避免等待时间过长
4. **记录日志**：每次重试都记录日志

---

### 模式 4：上下文管理器（Context Manager）

**核心思想**：自动管理资源和状态，即使发生异常

**适用场景**：Agent 执行、文件操作、数据库事务

**工作流程**（类似 pytest fixture）：

```
1. Setup（进入时）   → 准备资源、更新状态
2. yield（暂停）     → 执行业务逻辑
3. Teardown（退出时）→ 清理资源、更新状态
```

**示例**：

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def agent_execution_context(agent_name: str, call_id: str):
    """Agent 执行上下文，自动管理状态和清理"""
    # 1. Setup：进入时执行
    call_manager.update_status(call_id, CallStatus.RUNNING)
    logger.info(f"开始执行 Agent {agent_name}")
    
    try:
        yield  # 2. 暂停，执行业务逻辑
        
        # 3a. Teardown（成功）：业务逻辑执行完成后
        call_manager.update_status(call_id, CallStatus.COMPLETED)
        logger.info(f"Agent {agent_name} 执行成功")
    
    except Exception as e:
        # 3b. Teardown（失败）：发生异常时
        call_manager.update_status(call_id, CallStatus.FAILED)
        call_manager.set_error(call_id, str(e))
        logger.error(f"Agent {agent_name} 执行失败: {e}", exc_info=True)
        raise
    
    finally:
        # 3c. Teardown（总是执行）：无论成功失败
        logger.debug(f"清理 Agent {agent_name} 的资源")

# 使用示例
async def execute_agent(agent_name: str, call_id: str, prompt: str):
    async with agent_execution_context(agent_name, call_id):
        result = await agent.execute(prompt)  # 这里可能抛出异常
        return result
```

**为什么使用上下文管理器？**

1. **集中管理"前置-后置"逻辑**：状态管理代码只写一次，避免重复
2. **保证清理代码一定执行**：即使发生异常，`finally` 块也会执行
3. **代码更简洁**：业务逻辑和资源管理分离，调用代码只关注业务

**对比传统写法**：

```python
# ❌ 不用上下文管理器 - 每次都要写 try-except-finally
async def execute_agent():
    call_manager.update_status(call_id, CallStatus.RUNNING)
    try:
        result = await agent.execute(prompt)
        call_manager.update_status(call_id, CallStatus.COMPLETED)
        return result
    except Exception as e:
        call_manager.update_status(call_id, CallStatus.FAILED)
        raise
    finally:
        cleanup()

# ✅ 使用上下文管理器 - 简洁且不易出错
async def execute_agent():
    async with agent_execution_context(agent_name, call_id):
        result = await agent.execute(prompt)
        return result
```

---

### 模式 5：错误恢复策略

**核心思想**：根据错误类型选择不同的恢复策略

```python
async def process_message_with_recovery(agent: Agent, message: AgentMessage):
    """处理消息，带错误恢复"""
    try:
        # 尝试执行
        result = await agent.execute(message.content)
        return result
    
    except RecoverableError as e:
        # 可恢复错误 - 自动重试（已由装饰器处理）
        raise
    
    except ValidationError as e:
        # 验证错误 - 返回错误信息给发送者
        logger.warning(f"消息验证失败: {e}")
        await send_error_to_sender(message.send_from, e)
        return None
    
    except AgentExecutionError as e:
        # Agent 执行失败 - 尝试降级方案
        logger.error(f"Agent 执行失败，尝试降级方案: {e}")
        try:
            # 降级方案：使用备用 Agent
            backup_agent = get_backup_agent(agent.name)
            result = await backup_agent.execute(message.content)
            logger.info(f"降级方案成功，使用备用 Agent: {backup_agent.name}")
            return result
        except Exception as fallback_error:
            logger.error(f"降级方案也失败: {fallback_error}")
            raise
    
    except SystemError as e:
        # 系统错误 - 记录日志，通知管理员
        logger.critical(f"系统错误: {e}", exc_info=True)
        alert_admin(e)
        raise
```

---

## 日志记录最佳实践

### 结构化日志

**核心思想**：日志应该是机器可读的，方便后续分析

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_error(
        self, 
        error: Exception, 
        context: dict | None = None,
        include_traceback: bool = True
    ):
        """记录错误，包含上下文信息"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        
        # 如果是自定义异常，添加额外信息
        if isinstance(error, AgentsHubError):
            log_data["error_code"] = error.error_code
            log_data["details"] = error.details
        
        self.logger.error(
            json.dumps(log_data, ensure_ascii=False),
            exc_info=include_traceback
        )
    
    def log_call(
        self,
        call_id: str,
        agent_name: str,
        status: str,
        duration: float | None = None
    ):
        """记录 Agent 调用"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "event": "agent_call",
            "call_id": call_id,
            "agent_name": agent_name,
            "status": status,
            "duration": duration
        }
        self.logger.info(json.dumps(log_data, ensure_ascii=False))

# 使用示例
logger = StructuredLogger("agents_hub.core")

try:
    result = call_agent(...)
except AgentNotFoundError as e:
    logger.log_error(e, context={
        "group_chat_id": group_chat_id,
        "send_from": send_from,
        "send_to": send_to
    })
```

---

### 日志级别使用指南

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| **DEBUG** | 详细的调试信息 | 函数参数、中间变量值 |
| **INFO** | 正常的业务流程 | Agent 开始执行、消息发送成功 |
| **WARNING** | 可恢复的异常情况 | 验证错误、资源不存在、重试 |
| **ERROR** | 需要关注的错误 | Agent 执行失败、外部服务错误 |
| **CRITICAL** | 系统级严重错误 | 数据库连接失败、磁盘满 |

```python
# 示例
logger.debug(f"调用参数: agent_name={agent_name}, prompt={prompt[:50]}")
logger.info(f"Agent {agent_name} 开始执行任务")
logger.warning(f"Agent {agent_name} 不存在，使用默认 Agent")
logger.error(f"Agent {agent_name} 执行失败: {error}", exc_info=True)
logger.critical(f"数据库连接失败，系统无法继续运行", exc_info=True)
```

---

## 错误处理反模式

### ❌ 反模式 1：吞掉异常

```python
# 错误示范
try:
    result = do_something()
except Exception:
    pass  # ❌ 完全忽略错误，问题会在后续代码中爆发

# 正确示范
try:
    result = do_something()
except Exception as e:
    logger.warning(f"操作失败，使用默认值: {e}")
    result = default_value
```

**为什么错误？**
- 隐藏了真正的问题
- 后续代码可能因为缺少 `result` 而崩溃
- 无法追踪问题根源

---

### ❌ 反模式 2：捕获过于宽泛

```python
# 错误示范
try:
    result = do_something()
except Exception:  # ❌ 捕获所有异常，包括 KeyboardInterrupt、SystemExit
    handle_error()

# 正确示范
try:
    result = do_something()
except (ValueError, TypeError) as e:  # ✅ 只捕获预期的异常
    handle_error(e)
```

**为什么错误？**
- 捕获了不应该捕获的异常（如 `KeyboardInterrupt`）
- 掩盖了代码中的 bug（如 `AttributeError`）

---

### ❌ 反模式 3：异常作为控制流

```python
# 错误示范
try:
    user = users[user_id]  # ❌ 用 KeyError 判断用户是否存在
except KeyError:
    user = create_user(user_id)

# 正确示范
user = users.get(user_id)  # ✅ 用返回值判断
if user is None:
    user = create_user(user_id)
```

**为什么错误？**
- 异常处理比正常流程慢
- 代码意图不清晰
- 违反了"异常是异常"的原则

---

### ❌ 反模式 4：丢失异常链

```python
# 错误示范
try:
    result = call_api()
except RequestException:
    raise CustomError("API 调用失败")  # ❌ 丢失了原始异常

# 正确示范
try:
    result = call_api()
except RequestException as e:
    raise CustomError("API 调用失败") from e  # ✅ 保留异常链
```

---

### ❌ 反模式 5：在循环中捕获异常

```python
# 错误示范
for item in items:
    try:
        process(item)
    except Exception:
        continue  # ❌ 一个错误会导致后续所有项都被跳过

# 正确示范
for item in items:
    try:
        process(item)
    except ProcessError as e:
        logger.warning(f"处理 {item} 失败: {e}")
        continue  # ✅ 只跳过当前项
```

---

## 针对 agents-hub 的建议

### 异常层次结构

基于你的架构，建议的异常层次：

```
AgentsHubError (基类)
├── ValidationError (验证错误)
│   ├── InvalidMessageError
│   ├── InvalidParameterError
│   └── EmptyContentError
│
├── ResourceNotFoundError (资源不存在)
│   ├── AgentNotFoundError
│   ├── GroupChatNotFoundError
│   ├── RoleNotFoundError
│   └── SessionNotFoundError
│
├── StateError (状态错误)
│   ├── InvalidStateTransitionError
│   ├── AgentNotReadyError
│   └── CallAlreadyCompletedError
│
├── CommunicationError (通信错误)
│   ├── MessageDeliveryError
│   ├── QueueFullError
│   └── TimeoutError
│
├── ExternalServiceError (外部服务错误)
│   ├── LLMAPIError
│   │   ├── RateLimitError (可恢复)
│   │   ├── LLMTimeoutError (可恢复)
│   │   └── InvalidResponseError
│   │
│   ├── FileSystemError
│   │   ├── FileNotFoundError
│   │   ├── PermissionDeniedError
│   │   └── DiskFullError
│   │
│   └── AgentBridgeError
│       ├── PlatformNotSupportedError
│       └── CLIExecutionError
│
└── SystemError (系统错误)
    ├── ConfigurationError
    ├── DatabaseError
    └── MemoryError
```

---

### 在不同层的处理策略

| 层级 | 策略 | 说明 |
|------|------|------|
| **Foundation 层** | 定义异常类 | 不捕获，只定义 |
| **Communication 层** | 抛出具体异常 | 如 `MessageDeliveryError` |
| **Context 层** | 抛出具体异常 | 如 `FileSystemError` |
| **Agent 层** | 捕获并转换 | 转换为 `AgentExecutionError` |
| **Orchestration 层** | 捕获并记录 | 记录日志，继续运行 |
| **MCP Server** | 边界处理 | 转换为 MCP 响应格式 |
| **API Server** | 边界处理 | 转换为 HTTP 响应格式 |

---

### 具体实现建议

#### 1. Foundation 层（`core/foundation/exceptions.py`）

```python
"""
定义所有异常类，不包含业务逻辑
"""

class AgentsHubError(Exception):
    """基类"""
    # ... (前面已定义)

class ValidationError(AgentsHubError):
    """验证错误"""
    pass

# ... 其他异常类
```

---

#### 2. Communication 层（`core/communication/message_router.py`）

```python
def send_message(self, message: AgentMessage):
    """发送消息，抛出具体异常"""
    try:
        self._validate_message(message)
        self._agents_queue[message.send_to].put_nowait(message)
    
    except asyncio.QueueFull:
        raise MessageDeliveryError(
            reason="目标 Agent 的消息队列已满",
            send_from=message.send_from,
            send_to=message.send_to
        )
    
    except (AgentNotFoundError, InvalidMessageError):
        raise  # 直接向上传递
    
    except Exception as e:
        raise MessageDeliveryError(
            reason=f"未知错误: {str(e)}",
            send_from=message.send_from,
            send_to=message.send_to
        ) from e
```

---

#### 3. Agent 层（`core/agent/base_agent.py`）

```python
async def _process_message(self, msg: AgentMessage) -> AgentResult:
    """处理消息，捕获并转换异常"""
    try:
        if msg.session_type == SessionType.MAIN:
            return await self.execute(msg.content)
        else:
            return await self.btw_execute(msg.content)
    
    except Exception as e:
        raise AgentExecutionError(
            agent_name=self.name,
            reason=str(e)
        ) from e
```

---

#### 4. MCP Server（`mcp/server.py`）

```python
@mcp.tool(annotations={"title": "Call Agent"})
def call_agent_tool(
    group_chat_id: str,
    send_from: str,
    send_to: str,
    content: str,
    need_response: bool = True,
    timeout_seconds: int = None
) -> Dict[str, Any]:
    """MCP Tool 入口，边界处理"""
    try:
        result = call_agent(
            group_chat_id=group_chat_id,
            send_from=send_from,
            send_to=send_to,
            content=content,
            need_response=need_response,
            timeout_seconds=timeout_seconds
        )
        return {
            "success": True,
            "data": {
                "call_id": result.call_id,
                "status": "pending"
            }
        }
    
    except ValidationError as e:
        logger.warning(f"验证错误: {e}", extra={"details": e.details})
        return {
            "success": False,
            "error": e.to_dict(),
            "suggestion": "请检查输入参数是否正确"
        }
    
    except ResourceNotFoundError as e:
        logger.warning(f"资源不存在: {e}", extra={"details": e.details})
        return {
            "success": False,
            "error": e.to_dict(),
            "suggestion": "请使用 list_agents 查看可用资源"
        }
    
    except CommunicationError as e:
        logger.error(f"通信错误: {e}", extra={"details": e.details})
        return {
            "success": False,
            "error": e.to_dict(),
            "suggestion": "消息投递失败，请稍后重试"
        }
    
    except SystemError as e:
        logger.critical(f"系统错误: {e}", exc_info=True, extra={"details": e.details})
        alert_admin(e)
        return {
            "success": False,
            "error": {
                "error_code": "INTERNAL_ERROR",
                "message": "系统内部错误，请联系管理员"
            }
        }
    
    except Exception as e:
        logger.critical(f"未预期错误: {e}", exc_info=True)
        alert_admin(e)
        return {
            "success": False,
            "error": {
                "error_code": "UNKNOWN_ERROR",
                "message": "未知错误，请联系管理员"
            }
        }
```

---

#### 5. Agent.run() 循环（`core/agent/base_agent.py`）

```python
async def run(self):
    """持续监听私有队列，处理收到的消息"""
    while self._run:
        try:
            msg = await self.message_queue.get()
            
            # 处理消息
            result = await self._process_message(msg)
            
            # 添加到 GroupChat
            self.group_chat_context.group_chat_session.add_message(result)
            self.group_chat_context.save_group_chat_session()
            
            # 如果是 TASK 类型，需要回复
            if msg.message_type == MessageType.TASK:
                reply = AgentMessage(
                    send_from=self.name,
                    send_to=msg.send_from,
                    content=result.text,
                    message_type=MessageType.NOTIFICATION
                )
                self.message_router.send_message(reply)
        
        except AgentExecutionError as e:
            # Agent 执行失败 - 记录日志，继续处理下一条消息
            logger.error(f"Agent {self.name} 执行失败: {e}", exc_info=True)
            # 如果是 TASK 类型，通知发送者
            if msg.message_type == MessageType.TASK:
                error_msg = AgentMessage(
                    send_from=self.name,
                    send_to=msg.send_from,
                    content=f"执行失败: {e.message}",
                    message_type=MessageType.NOTIFICATION
                )
                self.message_router.send_message(error_msg)
        
        except Exception as e:
            # 未预期的错误 - 记录日志，继续运行
            logger.critical(f"Agent {self.name} 遇到未预期错误: {e}", exc_info=True)
            # 不中断循环，继续处理下一条消息
```

---

### 错误处理检查清单

在实现错误处理时，检查以下几点：

- [ ] **异常类定义**
  - [ ] 所有异常继承自 `AgentsHubError`
  - [ ] 每个异常都有 `error_code`
  - [ ] 每个异常都携带 `details`
  - [ ] 实现了 `to_dict()` 方法

- [ ] **异常抛出**
  - [ ] 使用具体的异常类（不是 `Exception`）
  - [ ] 使用 `from e` 保留异常链
  - [ ] 携带足够的上下文信息

- [ ] **异常捕获**
  - [ ] 只在边界捕获
  - [ ] 按类型分类处理
  - [ ] 不捕获过于宽泛的异常
  - [ ] 不吞掉异常

- [ ] **日志记录**
  - [ ] 使用正确的日志级别
  - [ ] 记录上下文信息
  - [ ] 系统错误记录完整堆栈（`exc_info=True`）
  - [ ] 使用结构化日志

- [ ] **用户友好**
  - [ ] 错误信息清晰
  - [ ] 提供可操作的建议
  - [ ] 不暴露内部实现细节

---

## 实战案例

### 案例 1：文件操作错误处理

```python
async def save_group_chat_session(self):
    """保存群聊会话，完善的错误处理"""
    try:
        # 确保目录存在
        os.makedirs(self.group_chat_session_path, exist_ok=True)
        
        # 更新时间戳
        self.group_chat_session.updated_at = datetime.now()
        
        # 写入文件
        with open(self.messages_file, 'w', encoding='utf-8') as f:
            # 写入 meta_data
            meta_data = {
                '_type': 'meta_data',
                'last_compact_loc': self.group_chat_session.last_compacted_loc,
                'created_at': self.group_chat_session.created_at.isoformat(),
                'updated_at': self.group_chat_session.updated_at.isoformat(),
                'name': self.group_chat_session.name
            }
            f.write(json.dumps(meta_data, ensure_ascii=False) + '\n')
            
            # 写入消息
            for msg in self.group_chat_session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + '\n')
    
    except PermissionError as e:
        raise FileSystemError(
            operation="write",
            path=self.messages_file,
            reason="权限不足"
        ) from e
    
    except OSError as e:
        if e.errno == 28:  # No space left on device
            raise FileSystemError(
                operation="write",
                path=self.messages_file,
                reason="磁盘空间不足"
            ) from e
        else:
            raise FileSystemError(
                operation="write",
                path=self.messages_file,
                reason=str(e)
            ) from e
    
    except Exception as e:
        raise FileSystemError(
            operation="write",
            path=self.messages_file,
            reason=f"未知错误: {str(e)}"
        ) from e
```

---

### 案例 2：LLM API 调用错误处理

```python
@retry_on_recoverable(max_attempts=3)
async def call_llm_with_retry(prompt: str, role_config: RoleConfig) -> AgentResult:
    """调用 LLM API，带重试和完善的错误处理"""
    try:
        response = await agent_platform_client.execute(prompt, role_config)
        return response
    
    except RateLimitError as e:
        # 限流错误 - 由装饰器自动重试
        logger.warning(f"LLM API 限流: {e}")
        raise
    
    except TimeoutError as e:
        # 超时错误 - 可恢复
        logger.warning(f"LLM API 超时: {e}")
        raise LLMTimeoutError("LLM API 超时", retry_after=2.0) from e
    
    except InvalidResponseError as e:
        # 响应格式错误 - 不可恢复
        logger.error(f"LLM 返回无效响应: {e}")
        raise
    
    except Exception as e:
        # 未预期的错误
        logger.error(f"LLM API 调用失败: {e}", exc_info=True)
        raise LLMAPIError(f"LLM API 调用失败: {str(e)}") from e
```

---

### 案例 3：消息压缩错误处理

```python
async def compact_messages(self, agent_info: dict[str, str]):
    """压缩群聊消息历史，带重试和降级"""
    # 获取未压缩的消息
    uncompacted_messages = self.group_chat_session.get_uncompact_messages()
    
    if not uncompacted_messages:
        return
    
    # 估算 token 数量
    token_count = estimate_prompt_tokens(uncompacted_messages)
    
    if token_count < MAX_TOKEN:
        logger.info(f"未压缩消息 token 数量为 {token_count}，小于阈值，跳过压缩")
        return
    
    logger.info(f"未压缩消息 token 数量为 {token_count}，开始压缩...")
    
    # 构建压缩提示词
    compact_prompt = build_compact_prompt(uncompacted_messages, agent_info)
    
    # 重试 3 次
    for attempt in range(3):
        try:
            # 调用 LLM 进行压缩
            compact_result = await llm_call.execute(compact_prompt)
            
                        # 解析 JSON 结果
            compact_data = parse_compact_result(compact_result.text)
            
            # 保存压缩记录
            await save_compact_record(compact_data)
            
            # 更新 last_compacted_loc
            self.group_chat_session.last_compacted_loc = len(self.group_chat_session.messages)
            self.save_group_chat_session()
            
            logger.info(f"压缩完成，已压缩 {len(uncompacted_messages)} 条消息")
            return
        
        except json.JSONDecodeError as e:
            logger.warning(f"第 {attempt + 1} 次压缩失败，JSON 解析错误: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
            else:
                # 3 次都失败，使用降级方案
                logger.error(f"压缩 3 次都失败，使用降级方案")
                await self._fallback_compact(uncompacted_messages)
                return
        
        except LLMAPIError as e:
            logger.error(f"第 {attempt + 1} 次压缩失败，LLM API 错误: {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                raise CompactionError(f"压缩失败: {str(e)}") from e
        
        except Exception as e:
            logger.error(f"压缩过程发生未预期错误: {e}", exc_info=True)
            raise CompactionError(f"压缩失败: {str(e)}") from e

async def _fallback_compact(self, messages: list[dict]):
    """降级方案：简单截断"""
    logger.warning("使用降级方案：保留最近 50% 的消息")
    keep_count = len(messages) // 2
    self.group_chat_session.last_compacted_loc += keep_count
    self.save_group_chat_session()
```

---

## 总结

### 核心要点

1. **异常层次结构**
   - 建立清晰的继承树
   - 按"谁应该处理"分类
   - 携带足够的上下文信息

2. **异常处理模式**
   - 边界处理：在系统边界统一捕获
   - 异常链：保留原始异常信息
   - 重试装饰器：自动重试可恢复错误
   - 上下文管理器：自动管理资源和状态

3. **日志记录**
   - 使用结构化日志
   - 选择正确的日志级别
   - 记录上下文信息

4. **避免反模式**
   - 不吞掉异常
   - 不捕获过于宽泛的异常
   - 不用异常作为控制流
   - 不丢失异常链

5. **用户友好**
   - 清晰的错误信息
   - 可操作的建议
   - 不暴露内部细节

---

### 实施步骤

对于 agents-hub 项目，建议按以下步骤实施：

1. **第一阶段：定义异常类**（1-2 天）
   - 在 `core/foundation/exceptions.py` 中定义所有异常类
   - 实现 `AgentsHubError` 基类
   - 实现各个子类

2. **第二阶段：修改现有代码**（3-5 天）
   - 将 `raise ValueError` 替换为具体的异常类
   - 在边界处添加统一的异常处理
   - 添加异常链（`from e`）

3. **第三阶段：完善日志**（1-2 天）
   - 实现结构化日志
   - 在关键位置添加日志记录
   - 配置日志级别和输出格式

4. **第四阶段：测试和优化**（2-3 天）
   - 编写错误处理的单元测试
   - 测试各种异常场景
   - 优化错误信息和建议

---

### 参考资源

- [PEP 3134 - Exception Chaining](https://www.python.org/dev/peps/pep-3134/)
- [Python Logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [Effective Python: 90 Specific Ways to Write Better Python](https://effectivepython.com/)
- [Python Best Practices for Error Handling](https://realpython.com/python-exceptions/)

---

## 附录：完整代码示例

### A. 完整的异常类定义

```python
# agents_hub/core/foundation/exceptions.py

from typing import Any

class AgentsHubError(Exception):
    """所有 agents-hub 异常的基类"""
    
    def __init__(
        self, 
        message: str, 
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        super().__init__(message)
    
    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.cause:
            base += f" | Caused by: {type(self.cause).__name__}: {self.cause}"
        return base
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "type": self.__class__.__name__
        }


# ==================== 验证错误 ====================
class ValidationError(AgentsHubError):
    """验证错误"""
    pass


class InvalidMessageError(ValidationError):
    """消息格式错误"""
    def __init__(self, reason: str, message_data: dict | None = None):
        super().__init__(
            message=f"消息格式错误: {reason}",
            error_code="INVALID_MESSAGE",
            details={"reason": reason, "message_data": message_data}
        )


class InvalidParameterError(ValidationError):
    """参数错误"""
    def __init__(self, param_name: str, reason: str):
        super().__init__(
            message=f"参数 '{param_name}' 错误: {reason}",
            error_code="INVALID_PARAMETER",
            details={"param_name": param_name, "reason": reason}
        )


# ==================== 资源不存在错误 ====================
class ResourceNotFoundError(AgentsHubError):
    """资源不存在错误"""
    pass


class AgentNotFoundError(ResourceNotFoundError):
    """Agent 不存在"""
    def __init__(self, agent_name: str, available_agents: list[str] | None = None):
        super().__init__(
            message=f"Agent '{agent_name}' 不存在",
            error_code="AGENT_NOT_FOUND",
            details={
                "agent_name": agent_name,
                "available_agents": available_agents or []
            }
        )


class GroupChatNotFoundError(ResourceNotFoundError):
    """GroupChat 不存在"""
    def __init__(self, group_chat_id: str):
        super().__init__(
            message=f"GroupChat '{group_chat_id}' 不存在",
            error_code="GROUP_CHAT_NOT_FOUND",
            details={"group_chat_id": group_chat_id}
        )


# ==================== 通信错误 ====================
class CommunicationError(AgentsHubError):
    """通信错误"""
    pass


class MessageDeliveryError(CommunicationError):
    """消息投递失败"""
    def __init__(self, reason: str, send_from: str, send_to: str):
        super().__init__(
            message=f"消息投递失败: {reason}",
            error_code="MESSAGE_DELIVERY_FAILED",
            details={"send_from": send_from, "send_to": send_to, "reason": reason}
        )


# ==================== 外部服务错误 ====================
class ExternalServiceError(AgentsHubError):
    """外部服务错误"""
    pass


class LLMAPIError(ExternalServiceError):
    """LLM API 错误"""
    pass


class RateLimitError(LLMAPIError):
    """API 限流（可恢复）"""
    def __init__(self, retry_after: float = 5.0):
        super().__init__(
            message=f"API 限流，请 {retry_after} 秒后重试",
            error_code="RATE_LIMIT",
            details={"retry_after": retry_after}
        )
        self.retry_after = retry_after


class FileSystemError(ExternalServiceError):
    """文件系统错误"""
    def __init__(self, operation: str, path: str, reason: str):
        super().__init__(
            message=f"文件系统错误: {operation} '{path}' 失败 - {reason}",
            error_code="FILE_SYSTEM_ERROR",
            details={"operation": operation, "path": path, "reason": reason}
        )


# ==================== 系统错误 ====================
class SystemError(AgentsHubError):
    """系统级错误"""
    pass
```

---

### B. 重试装饰器完整实现

```python
# agents_hub/utils/retry.py

import asyncio
import logging
from functools import wraps
from typing import TypeVar, Callable, Type

from agents_hub.core.foundation.exceptions import RecoverableError

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_on_recoverable(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    max_backoff: float = 60.0,
    recoverable_exceptions: tuple[Type[Exception], ...] = (RecoverableError,)
):
    """
    重试装饰器，只重试可恢复错误
    
    Args:
        max_attempts: 最大重试次数
        backoff_factor: 退避因子（指数退避）
        max_backoff: 最大退避时间（秒）
        recoverable_exceptions: 可恢复的异常类型
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            attempt = 0
            last_error = None
            
            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                
                except recoverable_exceptions as e:
                    attempt += 1
                    last_error = e
                    
                    if attempt >= max_attempts:
                        logger.error(
                            f"重试 {max_attempts} 次后仍失败: {e}",
                            extra={"function": func.__name__, "attempts": attempt}
                        )
                        raise
                    
                    # 计算退避时间
                    if isinstance(e, RecoverableError) and hasattr(e, 'retry_after'):
                        base_delay = e.retry_after
                    else:
                        base_delay = 1.0
                    
                    delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_backoff)
                    
                    logger.warning(
                        f"遇到可恢复错误，{delay:.1f}秒后重试 (第{attempt}/{max_attempts}次): {e}",
                        extra={"function": func.__name__, "attempt": attempt, "delay": delay}
                    )
                    
                    await asyncio.sleep(delay)
                
                except Exception:
                    # 非可恢复错误，直接抛出
                    raise
            
            raise last_error  # 不应该到这里
        
        return wrapper
    return decorator
```

---

**报告完成！** 🎉

这份研究报告涵盖了 Python 错误处理的核心原则、设计模式、最佳实践，以及针对 agents-hub 项目的具体建议。你可以根据这份报告来设计和实现项目的错误处理架构。
