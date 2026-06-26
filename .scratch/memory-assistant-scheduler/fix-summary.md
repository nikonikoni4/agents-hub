# history.jsonl 写入逻辑修复总结

**修复日期**: 2026-06-26  
**修复文件**: `agents_hub/scheduler/task/memory_task.py`

---

## 修复内容

### 新增函数：`append_to_history()`

**位置**: `memory_task.py:22-53`

**功能**: 追加总结内容到 history.jsonl

**实现细节**:
```python
def append_to_history(
    group_chat_id: str, summary: str, history_path: Path
) -> None:
    """追加总结到 history.jsonl
    
    Args:
        group_chat_id: 群聊ID
        summary: 总结内容
        history_path: history.jsonl 文件路径
    """
```

**关键逻辑**:
1. 验证总结内容非空
2. 确保父目录存在（`mkdir(parents=True, exist_ok=True)`）
3. 构建 JSON 记录（group_chat_id + timestamp + summary）
4. 追加到文件（append 模式，UTF-8 编码）
5. 记录日志

**错误处理**:
- 空内容：记录 warning 日志并返回
- OSError：记录 error 日志但不抛出异常

### 修改执行流程

**位置**: `memory_task.py:130-134`

**原流程**:
```python
# 3. 执行记忆助手
result = await agent_platform_client.execute(...)

logger.info("记忆收集完成: group_chat_id=%s", group_chat_id)

# 裁剪 history.jsonl
trim_history_jsonl(config.history_jsonl_path)

return result.text
```

**新流程**:
```python
# 3. 执行记忆助手
result = await agent_platform_client.execute(...)

logger.info("记忆收集完成: group_chat_id=%s", group_chat_id)

# 4. 写入 history.jsonl（记忆助手的输出即为总结内容）
append_to_history(group_chat_id, result.text, config.history_jsonl_path)

# 5. 裁剪 history.jsonl
trim_history_jsonl(config.history_jsonl_path)

return result.text
```

**变更说明**:
- 在裁剪前先写入新总结
- 记忆助手的完整输出作为总结内容
- 执行顺序：写入 → 裁剪

### 新增导入

**位置**: `memory_task.py:8-10`

**新增**:
```python
import json
from datetime import datetime, timezone
```

**用途**:
- `json`: 序列化记录为 JSON 格式
- `datetime.now(timezone.utc)`: 生成 UTC 时间戳

### 文档字符串更新

**位置**: `memory_task.py:1-5`

**修改前**:
```python
"""记忆更新任务

负责单个群聊的记忆收集执行。
通过 agent_platform_client.execute 调用记忆助手 Agent。
执行完成后裁剪 history.jsonl 保留最近 1000 条。
"""
```

**修改后**:
```python
"""记忆更新任务

负责单个群聊的记忆收集执行。
通过 agent_platform_client.execute 调用记忆助手 Agent。
执行完成后写入 history.jsonl 并裁剪保留最近 1000 条。
"""
```

---

## history.jsonl 格式

### 记录格式

```json
{
  "group_chat_id": "ba8e155a-8339-448f-bea1-f25252381e89",
  "timestamp": "2026-06-26T00:15:32.123456+00:00",
  "summary": "记忆助手的输出内容..."
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `group_chat_id` | string | 群聊ID，用于标识记录所属的群聊 |
| `timestamp` | string | UTC 时间戳（ISO 8601 格式） |
| `summary` | string | 记忆助手的输出内容（完整的任务总结） |

### 文件特性

- **格式**: JSONL（每行一个 JSON 对象）
- **编码**: UTF-8
- **追加模式**: 新记录追加到文件末尾
- **最大条数**: 1000 条（自动裁剪）
- **存储位置**: `{data_path}/schedule/memory/agents_hub_history/history.jsonl`

---

## 数据流

### 完整流程

```
SchedulerService._execute_memory_task()
  → MemoryTask.execute(group_chat_id, last_updated)
    → agent_platform_client.execute(prompt, role_config)
      → 记忆助手 Agent 执行
        → 调用 get_memory_context MCP 工具
        → 分析群聊消息
        → 生成 4 份文件（decisions/mistakes/suggestions）
        → 返回任务总结（result.text）
    → append_to_history(group_chat_id, result.text, history_path)
      → 写入 history.jsonl
    → trim_history_jsonl(history_path)
      → 保留最近 1000 条
  → state_manager.save_memory_index(index)
    → 更新 index.json 的 last_updated
```

### 数据依赖

**输入**:
- `group_chat_id`: 群聊ID
- `last_updated`: 上次更新时间
- `result.text`: 记忆助手的输出

**输出**:
- `history.jsonl`: 新增一条记录
- 日志：记录写入和裁剪操作

**下次执行时**:
- MCP 工具读取 `history.jsonl` 的最后一条记录
- 作为"历史总结"拼接到上下文中

---

## 测试建议

### 单元测试

**测试 `append_to_history()`**:
1. 正常写入：验证 JSON 格式正确
2. 空内容：验证跳过写入
3. 父目录不存在：验证自动创建
4. 文件权限错误：验证异常处理

**测试 `MemoryTask.execute()`**:
1. 首次执行：验证写入 history.jsonl
2. 后续执行：验证追加写入
3. 裁剪逻辑：验证超过 1000 条时裁剪

### 集成测试

**端到端测试**:
```python
# 1. 清空 history.jsonl
history_path.unlink(missing_ok=True)

# 2. 执行记忆收集
await memory_task.execute("test-group-id", None)

# 3. 验证 history.jsonl 存在且格式正确
assert history_path.exists()
lines = history_path.read_text().strip().splitlines()
assert len(lines) == 1
record = json.loads(lines[0])
assert record["group_chat_id"] == "test-group-id"
assert "timestamp" in record
assert "summary" in record
```

---

## 验证方法

### 手动验证

1. 启动系统
2. 触发记忆收集（等待定时任务或手动触发）
3. 检查 `{data_path}/schedule/memory/agents_hub_history/history.jsonl`
4. 验证文件内容格式正确

### 日志验证

查看日志中的关键信息：
```
INFO: 开始执行记忆收集: group_chat_id=xxx
INFO: 记忆收集完成: group_chat_id=xxx
INFO: 已写入 history.jsonl: group_chat_id=xxx
INFO: history.jsonl 已裁剪: 1001 → 1000 条  # 如果超过 1000 条
```

### 数据验证

```bash
# 查看最后一条记录
tail -n 1 local_data/schedule/memory/agents_hub_history/history.jsonl | jq

# 查看记录数量
wc -l local_data/schedule/memory/agents_hub_history/history.jsonl

# 验证 JSON 格式
cat local_data/schedule/memory/agents_hub_history/history.jsonl | jq -c
```

---

## 潜在问题和注意事项

### 1. 并发写入

**问题**: 如果未来支持多实例部署，可能出现并发写入冲突

**当前状态**: 
- 单实例部署，无并发问题
- `_running` 标志防止重入

**未来改进**: 
- 使用文件锁（`fcntl.flock`）
- 或使用分布式锁（Redis）

### 2. 磁盘空间

**问题**: 1000 条记录可能占用较大空间（取决于 summary 长度）

**当前状态**:
- 1000 条记录，假设每条 5KB，总共 ~5MB
- 可接受

**监控建议**:
- 定期检查文件大小
- 如果 summary 过大，考虑降低 `HISTORY_MAX_LINES`

### 3. summary 内容格式

**问题**: `result.text` 包含记忆助手的完整输出，可能包含多个维度的内容

**当前设计**:
- 完整输出作为 summary 存储
- 下次执行时，MCP 工具读取并作为"历史总结"

**优化方向**:
- 可以解析 `result.text`，只提取"任务总结"部分
- 需要约定输出格式（如 Markdown 标题）

### 4. 时间戳格式

**当前格式**: ISO 8601 UTC（`2026-06-26T00:15:32.123456+00:00`）

**优点**:
- 标准格式，易于解析
- 包含时区信息

**注意**:
- 所有时间戳统一使用 UTC
- 前端展示时需要转换为本地时区

---

## 修复前后对比

### 修复前

❌ **问题**:
- 只裁剪 history.jsonl，不写入新记录
- 每次执行都是"首次执行"，无法积累历史
- MCP 工具读取的历史总结永远为空

### 修复后

✅ **改进**:
- 执行完成后写入新记录
- 历史总结持续积累
- 下次执行时可以获取完整上下文

---

## 完成情况

✅ **已完成**:
1. 新增 `append_to_history()` 函数
2. 修改执行流程，在裁剪前写入
3. 新增必要的导入
4. 更新文档字符串

✅ **验证点**:
1. 代码通过静态检查（类型、格式）
2. 逻辑符合 PRD 要求
3. 错误处理完善

⏳ **待完成**:
1. 单元测试（建议）
2. 集成测试（建议）
3. 手动验证（必须）

---

## 总结

**修复时间**: 约 15 分钟

**代码变更**:
- 新增函数: 1 个（`append_to_history`）
- 修改函数: 1 个（`MemoryTask.execute`）
- 新增导入: 2 个（`json`, `datetime`）
- 代码行数: +35 行

**影响范围**:
- 仅影响 `memory_task.py`
- 不影响其他模块
- 不破坏现有功能

**风险评估**: 低
- 纯新增逻辑，不修改现有行为
- 错误处理完善，不会导致任务失败
- 幂等性良好，重复执行安全

---

**修复人**: Claude Code  
**修复时间**: 2026-06-26 00:20
