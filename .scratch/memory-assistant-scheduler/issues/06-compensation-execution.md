# Issue 06: 补偿执行逻辑

Status: ready-for-agent

## What to build

实现启动时的补偿执行逻辑，确保系统重启后不会遗漏记忆收集。

补偿逻辑：
1. 启动时检查 `.schedule_state.json` 的 memory_task 字段
2. 如果今天已过配置时间且未执行，则异步补偿执行一次
3. 补偿执行完成后更新状态文件

## Acceptance criteria

- [ ] 在 `SchedulerService.start()` 中实现补偿执行检查
- [ ] 读取 `.schedule_state.json` 的 memory_task 字段
- [ ] 判断今天是否已执行（比较日期）
- [ ] 判断当前时间是否已过配置的执行时间
- [ ] 如果需要补偿，使用 `asyncio.create_task` 异步执行
- [ ] 补偿执行完成后更新 `.schedule_state.json`
- [ ] 记录补偿执行的日志

## Blocked by

- Issue 01: 调度器基础框架
- Issue 02: 配置项扩展
- Issue 03: 状态管理

## Architecture reference

架构约束文件：`.scratch/memory-assistant-scheduler/architecture.md`

## Implementation notes

参考 `D:\desktop\软件开发\LifeWatch-AI\lifeprism\server\services\schedule_service.py` 的 `_add_system_jobs` 方法。

补偿逻辑伪代码：
```python
now = datetime.now()
target_hour, target_minute = config.memory_task_cron_time

if now.hour > target_hour or (now.hour == target_hour and now.minute >= target_minute):
    if state_manager.should_execute_today():
        logger.info("已过今日 %d:%02d，异步执行一次 memory_task", target_hour, target_minute)
        asyncio.create_task(self._execute_memory_task())
```

错误处理：
- 补偿执行本身失败时（`_execute_memory_task` 抛异常），异常会被 `asyncio.create_task` 捕获并记录到日志
- 不需要重试机制，因为定时任务会在下一个触发时间自动执行
- 补偿执行和定时触发不会重叠：APScheduler 的 CronTrigger 只在指定时间触发
