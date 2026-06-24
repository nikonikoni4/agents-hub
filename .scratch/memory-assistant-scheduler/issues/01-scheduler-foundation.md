# Issue 01: 调度器基础框架

Status: ready-for-agent

## What to build

创建 `agents_hub/scheduler/` 模块，实现基于 APScheduler 的定时调度服务。

核心组件：
- `SchedulerService` 单例类，封装 AsyncIOScheduler
- 集成到 FastAPI lifespan（startup 启动、shutdown 关闭）
- 注册 CronTrigger 每天定时触发（时间从 config 读取）
- 添加 APScheduler 依赖到 pyproject.toml

## Acceptance criteria

- [ ] 创建 `agents_hub/scheduler/` 目录结构（__init__.py、scheduler_service.py、state_manager.py、task/）
- [ ] 实现 `SchedulerService` 单例类，支持 `start()` 和 `shutdown()` 方法
- [ ] 在 `agents_hub/api/app.py` 的 lifespan 中集成 SchedulerService
- [ ] 在 `pyproject.toml` 中添加 `apscheduler>=3.10.0` 依赖
- [ ] SchedulerService 启动时注册 CronTrigger 任务

## Blocked by

None - can start immediately

## Architecture reference

架构约束文件：`.scratch/memory-assistant-scheduler/architecture.md`

## Implementation notes

参考实现：`D:\desktop\软件开发\LifeWatch-AI\lifeprism\server\services\schedule_service.py`

关键设计点：
- 使用 `AsyncIOScheduler`（异步调度器）
- 单例模式确保全局唯一（使用模块级变量 `scheduler_service = SchedulerService()`）
- `start()` 和 `shutdown()` 方法具有幂等性

接口签名：
```python
class SchedulerService:
    def start(self) -> None:  # 启动调度器，已启动时跳过
    def shutdown(self) -> None:  # 关闭调度器，未启动时跳过
    async def _execute_memory_task(self) -> None:  # 执行记忆任务
```

lifespan 集成位置（参考 `agents_hub/api/app.py`）：
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 现有初始化 ...
    mcp_task = asyncio.create_task(mcp.run_async(...))
    # ← 在这里调用 scheduler_service.start()
    yield
    # ← 在这里调用 scheduler_service.shutdown()
    # ... 现有清理 ...
    mcp_task.cancel()
```

错误处理：
- `start()`: 如果调度器已启动，记录警告并跳过
- `shutdown()`: 如果调度器未启动，记录警告并跳过
- APScheduler 内部异常会记录到日志
