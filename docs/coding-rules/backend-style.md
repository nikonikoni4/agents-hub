---
created_at: 2026-05-27
updated_at: 2026-05-27
---

# 后端编码风格规范

## 数据类型文件命名规范

### 命名规则

| 文件名 | 用途 | 内容类型 | 何时使用 |
|--------|------|----------|----------|
| **`types.py`** | 基础类型定义 | Enum、TypeAlias、常量 | 被多个模块共享的基础类型 |
| **`models.py`** | 业务数据模型 | dataclass、TypedDict、领域特定的 Enum | 模块内的数据结构和业务实体 |
| **`schemas.py`** | 配置和验证 | Pydantic BaseModel/BaseSettings | 用户配置项、API 请求/响应格式 |

### 判断标准

**使用 `types.py` 当：**
- 类型被多个模块共享（如 `AgentPlatform` 被 `agent_bridge` 和 `roles` 使用）
- 定义系统级常量（如 CLI 路径）
- 定义跨模块的基础枚举

**使用 `models.py` 当：**
- 定义模块内的业务实体（如 `RoleConfig`、`RoleInfo`）
- 定义数据传输对象（如 `StreamEvent`、`AgentResult`）
- 定义领域特定的枚举（如 `AgentEventType` 只在 `agent_bridge` 内使用）

**使用 `schemas.py` 当：**
- 定义需要验证的配置项（Pydantic）
- 定义 API 的请求/响应格式
- 定义需要序列化/反序列化的数据结构

### 示例

```python
# config/types.py - 跨模块共享
class AgentPlatform(Enum):
    CLAUDE = "claude"
    CODEX = "codex"

CODEX_COMMAND = "path/to/codex"

# agent_bridge/models.py - 模块内数据模型
class AgentEventType(Enum):  # 只在 agent_bridge 内使用
    INIT = "init"
    TEXT_DELTA = "text_delta"

class StreamEvent(TypedDict):
    type: AgentEventType
    platform: AgentPlatform  # 从 config.types 导入

# config/schemas.py - 配置验证（未来）
class Config(BaseSettings):
    timeout: int = 30
    max_retries: int = 3
```

### 依赖方向

```
各模块的 models.py ──> config/types.py (基础类型)
                  ──> config/schemas.py (配置)
```

**原则：** 避免循环依赖，基础类型放在 `config/types.py`，让其他模块依赖它。

## 错误处理

### 核心原则

1. **统一继承**：所有异常继承自 `agents_hub/exceptions.py` 的基类
2. **边界处理**：内部函数只抛出，边界统一捕获转换
3. **携带上下文**：传递 `error_code`、`details`、原始异常链

### 异常定义规范

```python
# ✅ 正确：继承顶层基类，携带上下文
from agents_hub.exceptions import ResourceNotFoundError

class RoleNotFoundError(ResourceNotFoundError):
    def __init__(self, role_name: str, available_roles: list[str] | None = None):
        super().__init__(
            message=f"Role '{role_name}' 不存在",
            error_code="ROLE_NOT_FOUND",
            details={
                "role_name": role_name,
                "available_roles": available_roles or []
            }
        )
```

### 抛出异常规范

```python
# ✅ 正确：传递上下文信息
available_roles = self.list_role_names()
raise RoleNotFoundError(role_name=name, available_roles=available_roles)

# ❌ 错误：只传递字符串消息
raise RoleNotFoundError(f"Role '{name}' not found")
```

### 边界处理规范

```python
# MCP Server / API Server 边界
try:
    result = do_something()
    return {"success": True, "data": result}

except ValidationError as e:
    logger.warning(f"验证错误: {e}", extra={"details": e.details})
    return {"success": False, "error": e.to_dict()}

except ResourceNotFoundError as e:
    logger.warning(f"资源不存在: {e}", extra={"details": e.details})
    return {"success": False, "error": e.to_dict()}

except Exception as e:
    logger.critical(f"未预期错误: {e}", exc_info=True)
    return {"success": False, "error": {"error_code": "UNKNOWN_ERROR", "message": "系统错误"}}
```

### 异常分类

| 基类 | 用途 | 处理策略 |
|------|------|---------|
| `ValidationError` | 输入验证错误 | 返回详细错误信息 |
| `ResourceNotFoundError` | 资源不存在 | 返回 404，提示可用资源 |
| `StateError` | 状态错误 | 返回当前状态和期望状态 |
| `ExternalServiceError` | 外部服务错误 | 区分可恢复/不可恢复 |

### 禁止事项

- ❌ 使用 `except Exception` 捕获所有错误（边界除外）
- ❌ 吞掉异常（`except: pass`）
- ❌ 丢失异常链（不使用 `from e`）
- ❌ 只传递字符串消息，不携带上下文