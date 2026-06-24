# Flow 文档索引

Flow 文档记录系统中核心数据对象的生命周期和状态变化，帮助快速定位代码位置和理解业务逻辑。

## 文档列表

| 文档 | Flow 对象 | 说明 |
|------|----------|------|
| [agent-call-lifecycle.md](agent-call-lifecycle.md) | AgentCall | Agent 调用的生命周期，包括 PENDING/RUNNING/COMPLETED/FAILED 状态流转，user → agent 和 agent → agent 两条链路 |
| [agent-status-lifecycle.md](agent-status-lifecycle.md) | Agent 状态（AgentMemberInfo.status） | Agent 状态的生命周期，包括 idle/busy/stopped/error 四种状态的流转规则、触发位置、与 AgentCall 状态的耦合关系 |
| [group-chat-lifecycle.md](group-chat-lifecycle.md) | GroupChat | 群聊从创建到删除的完整生命周期，包括成员管理、状态变化和资源清理 |
| [logger-file-handle-lifecycle.md](logger-file-handle-lifecycle.md) | Logger FileHandler | Logger 文件句柄的生命周期管理，包括 RotatingFileHandler 的创建、持有和释放，以及与 GroupChat 资源清理的耦合关系 |
| [loop-lifecycle.md](loop-lifecycle.md) | Loop | Loop 循环执行的生命周期，包括创建、启动、执行节点、输出校验、检查退出、停止和清理的完整链路 |
| [2026-06-24-scheduler-lifecycle.md](2026-06-24-scheduler-lifecycle.md) | Scheduler | 定时记忆助手调度系统的生命周期，包括启动补偿、定时执行、记忆任务触发和状态文件管理 |

## 编写规则

编写或修改 Flow 文档时，请遵守 [flow-write-guide.md](../docs-rules/flow-write-guide.md) 中的规则。

## 自动同步机制

Flow 文档中的 `<key_function>` 标签会自动同步函数行号：
- 读取 `docs/flows/*.md` 时会触发 hook 调用同步脚本
- 脚本从 `ast_scan_result.json` 查找函数行号并更新
- 时间戳自动更新为当前时间

**注意**：严格遵守 key_function 标签格式，否则自动同步会失败。
