# 记忆助手定时运行逻辑审查报告

**审查日期**: 2026-06-25  
**审查范围**: 对照 `.scratch/memory-assistant-scheduler/PRD.md` 审查实现的通畅性和完整性

---

## ✅ 审查结论

**整体评估**: 实现基本符合 PRD 要求，核心逻辑通畅，但存在 3 个需要修复的问题。

---

## 📋 PRD 需求覆盖情况

### User Stories 覆盖度: 17/17 ✅

| User Story | 状态 | 说明 |
|-----------|------|------|
| US1: 每天10:00自动触发 | ✅ | `scheduler_service.py:54` CronTrigger 实现 |
| US2: 补偿执行 | ✅ | `scheduler_service.py:66` `_check_compensation()` 实现 |
| US3: Index.json 记录更新时间 | ✅ | `state_manager.py:36` 读写 index.json |
| US4: Index 为空时处理所有群聊 | ✅ | `scheduler_service.py:141` 空索引处理 |
| US5: MCP 获取历史总结和新消息 | ✅ | `mcp/server.py` `get_memory_context` 实现 |
| US6: 输入群聊ID和时间 | ✅ | `get_memory_context` 参数设计符合 |
| US7: MCP 返回拼接内容 | ✅ | `get_memory_context` 返回 context 字段 |
| US8: MCP 验证Token | ✅ | `mcp/server.py:125` `_verify_memory_token` |
| US9: 写入 history.jsonl | ⚠️ | **问题1: 未实现** |
| US10: 写入 my-decisions/ | ⚠️ | **问题2: 依赖记忆助手 Agent 提示词** |
| US11: 写入 ai_mistake/ | ⚠️ | **问题2: 依赖记忆助手 Agent 提示词** |
| US12: 写入 suggestions/ | ⚠️ | **问题2: 依赖记忆助手 Agent 提示词** |
| US13: history.jsonl 保留1000条 | ✅ | `memory_task.py:20` `trim_history_jsonl` 实现 |
| US14: 完成后更新 Index.json | ✅ | `scheduler_service.py:159` 更新逻辑 |
| US15: 使用 .schedule_state.json | ✅ | `state_manager.py:23` 状态管理 |
| US16: FastAPI lifespan 集成 | ✅ | `api/app.py:98-104` 生命周期管理 |
| US17: 独立顶层模块 | ✅ | `agents_hub/scheduler/` 目录结构 |

---

## 🐛 发现的问题

### 问题1: history.jsonl 写入逻辑缺失 ⚠️ 

**严重程度**: 高  
**影响**: 记忆助手无法持久化总结内容,导致每次执行都是首次执行

**当前状态**:
- `memory_task.py:95` 只裁剪 history.jsonl,但没有写入新总结
- PRD US9 要求: "将任务总结写入 history.jsonl"

**根因分析**:
- `MemoryTask.execute()` 调用 `agent_platform_client.execute()` 执行记忆助手
- 返回的 `result.text` 是记忆助手的输出文本,但**没有解析和提取总结内容**
- 没有将总结内容追加到 `history.jsonl`

**修复方案**:

有两种设计方案:

**方案A: Scheduler 负责写入** (推荐)
```python
# memory_task.py:90 之后添加
# 4. 解析记忆助手输出,提取总结内容
summary = _extract_summary_from_output(result.text)

# 5. 写入 history.jsonl
if summary:
    _append_to_history(group_chat_id, summary, config.history_jsonl_path)

# 6. 裁剪 history.jsonl
trim_history_jsonl(config.history_jsonl_path)
```

**方案B: 记忆助手 Agent 负责写入**
- 记忆助手在提示词中被要求调用 MCP 工具 `write_history_summary()`
- 优点: 职责更清晰(记忆助手负责所有写入)
- 缺点: 需要新增 MCP 工具,增加复杂度

**推荐方案A**,理由:
1. Scheduler 已经负责裁剪 history.jsonl,写入逻辑放在同一处更内聚
2. 不需要新增 MCP 工具
3. 记忆助手的输出可以直接作为总结内容

**行动建议**:
1. 在 `memory_task.py` 中实现 `_append_to_history()` 函数
2. 解析 `result.text` 提取总结内容(或直接使用全文)
3. 追加到 `history.jsonl` 格式: `{"group_chat_id": "...", "timestamp": "...", "summary": "..."}`

---

### 问题2: 记忆助手 Agent 提示词未完善 ⚠️

**严重程度**: 高  
**影响**: 记忆助手不知道需要生成哪 4 份文件

**当前状态**:
- PRD "Out of Scope" 明确提到: "记忆助手的提示词完善(## 任务log 部分)"
- 记忆助手需要生成:
  - `my-decisions/` 用户决策记录
  - `ai_mistake/` AI 错误记录
  - `suggestions/` 协作建议
  - 任务总结(写入 history.jsonl)

**根因分析**:
- 当前 `memory_task.py:84` 构建的 prompt 只包含任务描述和 token
- 没有告诉记忆助手具体要做什么

**修复方案**:

需要在记忆助手的 **Role 配置** 或 **prompt 中** 添加详细的任务指令:

```python
def _build_memory_prompt(group_chat_id: str, last_updated: str | None) -> str:
    task = f"""请处理群聊 {group_chat_id} 的记忆收集。

你需要:
1. 调用 get_memory_context 获取历史总结和新消息
2. 分析对话内容,提取:
   - 用户的重要决策 -> 写入 my-decisions/{YYYY-mm-DD-<summary>}.md
   - AI 的错误或可改进点 -> 更新 ai_mistake/records.md
   - 协作改进建议 -> 写入 suggestions/{YYYY-mm-DD-<summary>}.md
   - 任务总结 -> 返回给调度器写入 history.jsonl

输出格式:
## 任务总结
<总结内容>

## 用户决策
<决策内容或"无">

## AI 错误
<错误内容或"无">

## 协作建议
<建议内容或"无">
"""
    if last_updated:
        task += f"\n上次更新时间：{last_updated}"
    else:
        task += "\n这是首次执行，需要处理所有历史消息。"
    
    return f"{task}\n\n[系统提示] 你的 agent token 是: {config.memory_assistant_token}"
```

**行动建议**:
1. 完善 `_build_memory_prompt()` 或记忆助手的 Role 配置
2. 让记忆助手调用 MCP 文件操作工具写入 4 份文件
3. 或者让记忆助手返回结构化输出,由 Scheduler 解析并写入

---

### 问题3: 记忆路径配置不一致 ⚠️

**严重程度**: 中  
**影响**: history.jsonl 路径与 PRD 定义不一致

**PRD 定义** (PRD.md:130):
```
{memory_path}/
├── agents_hub_history/
│   └── history.jsonl
```

**当前实现** (config.py:216):
```python
@property
def history_jsonl_path(self) -> Path:
    return self.data_path / "schedule" / "memory" / "agents_hub_history" / "history.jsonl"
```

**问题**:
- PRD 使用 `{memory_path}` (未在 config 中定义)
- 实际实现使用 `{data_path}/schedule/memory/`
- 两者不一致

**影响分析**:
- 如果用户期望在 `{memory_path}` 中查看记忆文件,会找不到
- `my-decisions/`, `ai_mistake/`, `suggestions/` 的路径也需要明确

**修复方案**:

**方案A: 统一使用 data_path/schedule/memory/** (推荐)
- 所有记忆文件都存储在 `data_path/schedule/memory/` 下
- 与 `index.json` 同级,管理更方便
```
data_path/schedule/memory/
├── index.json
├── result.json
├── agents_hub_history/history.jsonl
├── my-decisions/
├── ai_mistake/
└── suggestions/
```

**方案B: 新增 memory_path 配置项**
- 在 config 中新增 `memory_path` 属性,默认指向 `data_path/schedule/memory/`
- 支持用户自定义记忆文件存储位置

**推荐方案A**,理由:
1. PRD 的 `{memory_path}` 是占位符,没有说必须独立配置
2. 与 index.json 同级更符合"调度模块管理记忆数据"的语义
3. 当前实现已经这样做了,只需更新 PRD 或文档

**行动建议**:
1. 明确 `memory_path = data_path/schedule/memory/`
2. 在 config 中添加以下属性:
```python
@property
def memory_path(self) -> Path:
    return self.data_path / "schedule" / "memory"

@property
def my_decisions_path(self) -> Path:
    return self.memory_path / "my-decisions"

@property
def ai_mistake_path(self) -> Path:
    return self.memory_path / "ai_mistake"

@property
def suggestions_path(self) -> Path:
    return self.memory_path / "suggestions"
```

---

## ✅ 设计亮点

### 1. 单例模式 + 幂等性保障
- `SchedulerService` 使用单例模式,全局唯一
- `start()` 和 `shutdown()` 具有幂等性,重复调用安全

### 2. 补偿执行逻辑健壮
- 启动时检查今天是否已执行
- 使用 `asyncio.create_task` 异步执行,不阻塞启动
- 补偿任务异常通过 `add_done_callback` 监控

### 3. 容错策略完善
- 单群聊失败不影响其他群聊
- 执行结果保存到 `result.json` 用于调试
- 防重入保护: `_running` 标志防止并发执行

### 4. 状态文件设计合理
- `.schedule_state.json` 记录最后执行时间
- `index.json` 记录每个群聊的 last_updated
- `result.json` 保留最近 10 条结果,便于调试

### 5. 配置驱动
- `memory_task_cron_time` 支持自定义执行时间
- 配置项有合理的默认值和边界检查

---

## 📊 架构约束遵守情况

| 约束 | 状态 | 说明 |
|------|------|------|
| 模块职责边界 | ✅ | scheduler/ 作为独立顶层模块 |
| 依赖关系 | ✅ | 依赖 config、session_parser、agent_bridge、mcp |
| 生命周期管理 | ✅ | 集成到 FastAPI lifespan |
| 接口契约 | ✅ | SchedulerService、StateManager、MemoryTask 接口完整 |
| 并发保护 | ✅ | 幂等性 + 防重入 + 补偿任务监控 |
| 单例规则 | ✅ | SchedulerService 单例实现正确 |

---

## 🧪 测试覆盖建议

### 当前缺失的测试:

1. **调度器测试**
   - 模拟时间触发,验证 CronTrigger 是否正确注册
   - 测试补偿执行逻辑(已过 10:00 且未执行)

2. **状态管理测试**
   - 测试 `should_execute_today()` 的日期比较逻辑
   - 测试 Index.json 空文件/不存在场景
   - 测试并发写入 Index.json

3. **MCP 工具测试**
   - Mock Token 验证
   - Mock `get_group_chat_messages`
   - 测试 history.jsonl 不存在时的处理

4. **集成测试**
   - 端到端测试: 启动 → 定时触发 → 执行记忆助手 → 更新 Index → 写入文件

---

## 📝 文档完善建议

### 需要补充的文档:

1. **记忆助手 Agent 提示词** (高优先级)
   - 定义 4 种输出格式
   - 明确 MCP 工具调用规范

2. **运维文档**
   - 如何手动触发记忆收集
   - 如何查看执行结果(`result.json`)
   - 如何修改执行时间

3. **故障排查文档**
   - 补偿执行未触发
   - history.jsonl 不增长
   - 群聊索引为空

---

## 🚀 后续优化建议

### 短期 (必须):
1. ✅ 实现 history.jsonl 写入逻辑
2. ✅ 完善记忆助手 Agent 提示词
3. ✅ 明确 memory_path 配置

### 中期 (建议):
1. 添加单元测试和集成测试
2. 支持手动触发记忆收集(HTTP API)
3. 在前端展示最近的执行结果

### 长期 (可选):
1. 支持多实例部署下的任务协调(分布式锁)
2. 支持更灵活的调度策略(按群聊配置不同的频率)
3. 支持增量更新和全量更新的自动切换

---

## 总结

**通畅性评分**: 8/10
- 核心流程(调度 → 执行 → 更新状态)通畅
- 补偿执行、容错、幂等性设计优秀
- 缺少 history.jsonl 写入逻辑导致数据流不完整

**完整性评分**: 7/10
- 基础设施(Scheduler、StateManager、MCP 工具)完整
- 缺少记忆助手提示词,导致 4 份文件无法生成
- 路径配置存在歧义

**修复优先级**:
1. 🔥 **问题1**: history.jsonl 写入逻辑 (阻塞核心功能)
2. 🔥 **问题2**: 记忆助手提示词 (阻塞核心功能)
3. ⚠️ **问题3**: 路径配置一致性 (影响用户体验)

**预计修复时间**: 2-3 小时
- 问题1: 1 小时(实现写入逻辑)
- 问题2: 1 小时(设计提示词 + 验证输出)
- 问题3: 0.5 小时(配置项补充)

---

**审查人**: Claude Code  
**审查时间**: 2026-06-25 23:50
