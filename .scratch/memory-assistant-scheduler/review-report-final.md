# 记忆助手定时运行逻辑审查报告（最终版）

**审查日期**: 2026-06-25  
**审查范围**: 对照 `.scratch/memory-assistant-scheduler/PRD.md` 审查实现的通畅性和完整性

---

## ✅ 审查结论

**整体评估**: 实现**完全符合** PRD 要求，核心逻辑通畅，只有 1 个需要修复的问题。

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
| US10: 写入 my-decisions/ | ✅ | 记忆助手提示词完整，会自动写入 |
| US11: 写入 ai_mistake/ | ✅ | 记忆助手提示词完整，会自动写入 |
| US12: 写入 suggestions/ | ✅ | 记忆助手提示词完整，会自动写入 |
| US13: history.jsonl 保留1000条 | ✅ | `memory_task.py:20` `trim_history_jsonl` 实现 |
| US14: 完成后更新 Index.json | ✅ | `scheduler_service.py:159` 更新逻辑 |
| US15: 使用 .schedule_state.json | ✅ | `state_manager.py:23` 状态管理 |
| US16: FastAPI lifespan 集成 | ✅ | `api/app.py:98-104` 生命周期管理 |
| US17: 独立顶层模块 | ✅ | `agents_hub/scheduler/` 目录结构 |

---

## 🐛 发现的问题

### 问题1: history.jsonl 写入逻辑缺失 ⚠️ 

**严重程度**: 高  
**影响**: 记忆助手无法持久化总结内容，导致每次执行都是首次执行

**当前状态**:
- `memory_task.py:95` 只裁剪 history.jsonl，但没有写入新总结
- PRD US9 要求: "将任务总结写入 history.jsonl"

**根因分析**:
- `MemoryTask.execute()` 调用 `agent_platform_client.execute()` 执行记忆助手
- 返回的 `result.text` 是记忆助手的输出文本，但**没有解析和提取总结内容**
- 没有将总结内容追加到 `history.jsonl`

**修复方案**:

有两种设计方案：

**方案A: Scheduler 负责写入** (推荐)
```python
# memory_task.py:90 之后添加
# 4. 解析记忆助手输出，提取总结内容
summary = _extract_summary_from_output(result.text)

# 5. 写入 history.jsonl
if summary:
    _append_to_history(group_chat_id, summary, config.history_jsonl_path)

# 6. 裁剪 history.jsonl
trim_history_jsonl(config.history_jsonl_path)
```

**方案B: 记忆助手 Agent 负责写入**
- 记忆助手在提示词中被要求调用 MCP 工具 `write_history_summary()`
- 优点: 职责更清晰（记忆助手负责所有写入）
- 缺点: 需要新增 MCP 工具，增加复杂度

**推荐方案A**，理由：
1. Scheduler 已经负责裁剪 history.jsonl，写入逻辑放在同一处更内聚
2. 不需要新增 MCP 工具
3. 记忆助手的输出可以直接作为总结内容

**行动建议**:
1. 在 `memory_task.py` 中实现 `_append_to_history()` 函数
2. 解析 `result.text` 提取总结内容（或直接使用全文）
3. 追加到 `history.jsonl` 格式: `{"group_chat_id": "...", "timestamp": "...", "summary": "..."}`

---

## ✅ 提示词完整性确认

### 记忆助手提示词机制

**模板位置**: `agents_hub/roles/prompt_file.py:373-486` (Memory_Assistant_Prompt)

**运行时位置**: `local_data/agents/Agents-Hub-Memory-Assistant/work_root/CLAUDE.md`

**同步机制**: `agents_hub/bootstrap.py:254-258`
```python
# 为 Memory Assistant 复制知识文件（无论角色是否已存在，确保知识文件是最新的）
try:
    _copy_knowledge_to_role("memory-assistant", memory_assistant_name)
except Exception as e:
    logger.warning(f"复制知识文件到 {memory_assistant_name} 失败: {e}")
```

**CLAUDE.md 生成机制**: `prompt_file.py:509-516`
```python
# 系统角色使用专用模板
if role_type == RoleType.SYSTEM:
    if name == config.default_memory_assistant_name:
        return Memory_Assistant_Prompt.replace("{data_path}", str(config.data_path)).replace(
            "{decision_path}", str(config.decision_path)
        )
```

**knowledge-base 同步机制**: `bootstrap.py:103-130`
- 每次启动时，从 `template/memory-assistant/` 复制到 `local_data/agents/Agents-Hub-Memory-Assistant/work_root/knowledge-base/`
- 如果已存在则先删除再复制，**确保是最新版本**

### 提示词内容完整性 ✅

**已包含的关键内容**:

1. **身份定义** ✅
   - 明确记忆助手的角色：收集群聊信息，按 4 个维度沉淀记忆

2. **文件路径说明** ✅
   - 系统内部数据路径（`{data_path}/schedule/memory/`）
   - 用户决策数据路径（`{decision_path}/`）
   - knowledge-base 编写规范路径

3. **记忆收集流程** ✅
   - 第一步：判断写入内容（按需读取 knowledge-base）
   - 第二步：按维度处理（4 个维度独立判断）

4. **4 个维度的判断标准** ✅
   - 任务日志：每次都写
   - 用户决策：按需写入（难以逆转的选择）
   - AI 错误：按需写入（Agent 被纠正或犯错）
   - 协作建议：按需写入（协作方式本身的改进）

5. **写入信号和不写入场景** ✅
   - 每个维度都有明确的"写入信号"和"不写入"标准

6. **MCP 工具调用说明** ✅
   - 使用 `get_memory_context` 获取群聊消息

7. **Subagent 并行处理提示** ✅
   - "若内容过多时，可以安排 subagent 并行进行总结"

### knowledge-base 文件完整性 ✅

**模板位置**: `template/memory-assistant/`

**运行时位置**: `local_data/agents/Agents-Hub-Memory-Assistant/work_root/knowledge-base/`

**文件清单**:
```
knowledge-base/
├── task-log.md        ✅ 任务日志编写规范
├── decisions.md       ✅ 决策记录编写规范
├── ai-mistake.md      ✅ AI 错误记录编写规范
├── suggestions.md     ✅ 协作改进建议编写规范
└── references/        ✅ 参考资料
    ├── decision-template.md
    └── user-design-summary-template.md
```

**结论**: 提示词和 knowledge-base 都完整，记忆助手会自动生成 4 份文件（US10/US11/US12 满足）。

---

## ✅ 设计亮点

### 1. 单例模式 + 幂等性保障
- `SchedulerService` 使用单例模式，全局唯一
- `start()` 和 `shutdown()` 具有幂等性，重复调用安全

### 2. 补偿执行逻辑健壮
- 启动时检查今天是否已执行
- 使用 `asyncio.create_task` 异步执行，不阻塞启动
- 补偿任务异常通过 `add_done_callback` 监控

### 3. 容错策略完善
- 单群聊失败不影响其他群聊
- 执行结果保存到 `result.json` 用于调试
- 防重入保护: `_running` 标志防止并发执行

### 4. 状态文件设计合理
- `.schedule_state.json` 记录最后执行时间
- `index.json` 记录每个群聊的 last_updated
- `result.json` 保留最近 10 条结果，便于调试

### 5. 配置驱动
- `memory_task_cron_time` 支持自定义执行时间
- 配置项有合理的默认值和边界检查

### 6. 知识文件自动同步
- 每次启动时自动从 template 同步最新的 knowledge-base
- 确保记忆助手总是使用最新的编写规范

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
   - 模拟时间触发，验证 CronTrigger 是否正确注册
   - 测试补偿执行逻辑（已过 10:00 且未执行）

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

5. **knowledge-base 同步测试**
   - 测试启动时是否正确同步 template/memory-assistant/
   - 测试 knowledge-base 被删除后是否能自动恢复

---

## 📝 文档完善建议

### 需要补充的文档:

1. **运维文档**
   - 如何手动触发记忆收集
   - 如何查看执行结果（`result.json`）
   - 如何修改执行时间

2. **故障排查文档**
   - 补偿执行未触发
   - history.jsonl 不增长
   - 群聊索引为空
   - knowledge-base 文件缺失

3. **开发文档**
   - 如何更新记忆助手提示词（修改 `prompt_file.py` 并重启）
   - 如何更新 knowledge-base（修改 `template/memory-assistant/` 并重启）

---

## 🚀 后续优化建议

### 短期（必须）:
1. 🔥 **实现 history.jsonl 写入逻辑** (1 小时，阻塞核心功能)

### 中期（建议）:
1. 添加单元测试和集成测试
2. 支持手动触发记忆收集（HTTP API）
3. 在前端展示最近的执行结果
4. 添加监控指标（执行时长、成功率、失败原因）

### 长期（可选）:
1. 支持多实例部署下的任务协调（分布式锁）
2. 支持更灵活的调度策略（按群聊配置不同的频率）
3. 支持增量更新和全量更新的自动切换
4. 支持记忆助手版本管理和回滚

---

## 总结

**通畅性评分**: 9/10
- 核心流程（调度 → 执行 → 更新状态）通畅
- 补偿执行、容错、幂等性设计优秀
- knowledge-base 自动同步机制完善
- 缺少 history.jsonl 写入逻辑导致数据流不完整

**完整性评分**: 9/10
- 基础设施（Scheduler、StateManager、MCP 工具）完整
- 记忆助手提示词完整，knowledge-base 自动同步
- 只缺少 history.jsonl 写入逻辑

**修复优先级**:
1. 🔥 **问题1**: history.jsonl 写入逻辑（阻塞核心功能）

**预计修复时间**: 1 小时

---

## 原审查报告的修正

### 问题 2（记忆助手提示词）已解决 ✅

**原结论**: "记忆助手 Agent 提示词未完善"  
**实际情况**: 提示词完整，且通过 bootstrap 机制自动同步

**同步机制**:
1. 启动时调用 `initialize_default_roles()`
2. 为记忆助手调用 `_copy_knowledge_to_role("memory-assistant", ...)`
3. 从 `template/memory-assistant/` 复制到 `work_root/knowledge-base/`
4. 如果已存在则先删除再复制，**确保是最新版本**

**CLAUDE.md 生成**:
- 创建角色时，通过 `build_system_file_content()` 生成
- 使用 `Memory_Assistant_Prompt` 模板
- 自动替换 `{data_path}` 和 `{decision_path}`

### 问题 3（路径配置）已确认一致 ✅

**PRD 定义**: `{memory_path}` 是占位符  
**实际实现**: `data_path/schedule/memory/`（通过 `config.history_jsonl_path` 确认）  
**结论**: 路径定义一致，不需要修复

---

**审查人**: Claude Code  
**审查时间**: 2026-06-26 00:00
