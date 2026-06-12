# 后端通用规则

1. 数据路径使用，统一使用配置模块的config.data_path
```python
from agents_hub.config import config
config.data_path
```
2. 编写错误处理里必须查看docs\coding-rules\backend-style.md

## 错误处理

**底层（业务逻辑层）**
- 抛出领域异常（如 UserNotFound、DockerConfigError）
- 不 catch，让错误冒泡

**中间层（服务/编排层）**
- 通常不处理，让错误继续冒泡
- 捕获外部服务错误（IO、网络、数据库），转换为领域异常后抛出
- 不在这里做兜底

**顶层（API/接口层）**
- 已有全局错误处理器

### 外部接口层：捕获并转换

文件 IO、网络请求、数据库操作等外部接口，必须捕获对应错误并转换为领域异常：

```python
# ✅ 正确：捕获 OSError，转换为 FileSystemError
try:
    with open(path, "a", encoding="utf-8") as f:
        f.write(data)
except OSError as e:
    raise FileSystemError(operation="write", path=str(path), reason=str(e)) from e


**禁止**：
- ❌ `except Exception` 吞掉异常
- ❌ 不捕获外部错误，让原始异常直接冒泡（上层无法统一处理）

### 中间层：不做兜底

```python
# ❌ 错误：中间层 catch Exception 并吞掉
async def _sync_status(self, status: str):
    try:
        await self.runtime.update_agent_status(self.name, status)
    except Exception as e:
        self.logger.warning("同步状态失败: %s", str(e))

# ✅ 正确：让异常冒泡
async def _sync_status(self, status: str):
    await self.runtime.update_agent_status(self.name, status)
```
