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
