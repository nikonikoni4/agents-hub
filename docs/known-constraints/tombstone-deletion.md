# JSONL 墓碑记录删除限制

## 问题背景

JSONL（JSON Lines）是追加写入格式，每行一个 JSON 对象。这种格式天然不支持直接删除中间行或原地修改已有记录。

## 设计方案

使用墓碑记录（Tombstone）实现标记删除：

- 删除时追加一条 `{ "loop_id": "...", "_deleted": true }` 记录
- 读取时遇到墓碑记录，跳过对应 `loop_id` 的所有历史记录
- 同一 `loop_id` 多条记录取最新（墓碑记录优先级最高）

## 适用范围

| 数据文件 | 说明 |
|---------|------|
| `loops.jsonl` | Loop 循环定义 |
| `loop_executions.jsonl` | Loop 执行实例 |

## 限制

1. **文件只增不减**：删除操作不会减少文件体积，墓碑记录永久保留
2. **遍历开销**：读取时需要遍历完整文件，通过集合记录已删除 ID 过滤
3. **无软删除恢复**：一旦写入墓碑记录，无法撤销（需要重新创建）

## 实现位置

- 墓碑写入：`LoopManager._persist_deletion()`
- 墓碑过滤：`LoopManager._read_jsonl_loops()` 中的 `deleted_ids` 集合
