# Issue 02: 配置项扩展

Status: ready-for-agent

## What to build

在 `config` 模块中新增定时任务执行时间的配置项。

新增配置项：
- `memory_task_cron_hour`：记忆任务执行小时（0-23），默认 10
- `memory_task_cron_minute`：记忆任务执行分钟（0-59），默认 0
- `memory_task_cron_time`：便捷属性，返回 (hour, minute) 元组

## Acceptance criteria

- [ ] 在 `agents_hub/config/config.py` 的 `_default_config` 中添加 `memory_task_cron_hour` 和 `memory_task_cron_minute`
- [ ] 在 `SystemConfig` 类中添加对应的 `@property` 访问器
- [ ] 在 `Config` 聚合类中添加 `memory_task_cron_time` 便捷属性
- [ ] SchedulerService 启动时读取配置的执行时间
- [ ] 配置值范围校验：`memory_task_cron_hour` 必须在 0-23 范围内，`memory_task_cron_minute` 必须在 0-59 范围内，超出范围时使用默认值（10:00）并记录警告

## Blocked by

None - can start immediately

## Architecture reference

架构约束文件：`.scratch/memory-assistant-scheduler/architecture.md`

## Implementation notes

参考 `agents_hub/config/config.py` 中现有的 `mcp_port` 属性实现模式。

配置项会自动从 config.yaml 加载（`_load_config()` 方法会合并 YAML 值）。
