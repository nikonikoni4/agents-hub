# Code Review Report

**审查范围**: Loop 懒加载机制和内存优化
**审查时间**: 2026-06-21
**变更文件**:
- `agents_hub/core/orchestration/loop_manager.py` — 懒加载、list_loops 重构、单 Loop 保持
- `agents_hub/core/orchestration/group_chat.py` — start_loop 使用懒加载
- `agents_hub/mcp/server.py` — 新增 list_loops MCP 工具
- `tests/core/orchestration/test_loop_manager.py` — 测试适配

## 架构上下文

### 相关 ADR
- ADR-0009 (decided): 运行态 SSOT 以内存为准，文件作为持久化副本
- ADR-0005 (decided): 点对点路由，避免越权访问

### 相关 Spec
- `docs/specs/2026-06-21-loop.md`: Loop 循环执行规格，定义懒加载机制、单 Loop 保持策略、list_loops 接口

### 决策覆盖
- 变更与 Spec 高度一致，懒加载和内存管理策略符合 Spec 定义

## 审查结果

Found 8 issues (去重后):

### Issue 1: GroupChat 直接访问 LoopManager 私有属性
- **类型**: Architecture / Best Practices / Code Quality（三个维度均命中）
- **置信度**: 95
- **位置**: `group_chat.py:463-472`
- **详情**: `create_and_start_loop()` 直接访问 `loop_manager._loops` 私有属性进行遍历和 `.pop()`。LoopManager 应暴露公开方法（如 `clear_other_loops(keep_loop_id: str)`）来封装清理逻辑。当前实现导致单 Loop 保持策略分散在两处：`LoopManager.create_loop()`（line 151）和 `GroupChat.create_and_start_loop()`（line 463），违反 SRP 和 DRY。
- **依据**: core/CLAUDE.md 通信状态访问规则——"禁止直接访问私有属性"

### Issue 2: JSONL 读取逻辑重复 3 次（DRY 违反）
- **类型**: Code Quality
- **置信度**: 95
- **位置**: `loop_manager.py:244-263, 316-338, 595-627`
- **详情**: `get_loop_with_lazy_load()`、`list_loops()`、`_load_from_persistence()` 三个方法独立实现了几乎相同的 JSONL 逐行读取逻辑（打开文件→strip→json.loads→处理墓碑→同 loop_id 取最新）。应抽取共享的 `_read_all_records() -> dict[str, dict]` 内部方法，各调用方按需处理返回值。
- **依据**: CLAUDE.md DRY 原则

### Issue 3: Spec/Flow 文档未同步更新
- **类型**: Documentation
- **置信度**: 95
- **位置**: `docs/specs/2026-06-21-loop.md:143-150`, `docs/flows/loop-lifecycle.md:227,235`
- **详情**:
  - Spec 的 `key_function` 缺少 `list_loops` 工具，且行号全部过时（实际 1098/1161/1199/1237/1275/1316 vs 文档 1046/1100/1150/1200/1250）
  - Flow 文档中 `get_loop_with_lazy_load()` 和 `list_loops()` 仍标记为"需新增"，但已实现
  - `docs/specs/index.md:143` 的 loop spec 摘要缺少 `list_loops`
- **依据**: CLAUDE.md 文档按需加载规则

### Issue 4: get_loop_with_lazy_load 内存命中路径未测试
- **类型**: Testing
- **置信度**: 90
- **位置**: `test_loop_manager.py:412-430`
- **详情**: 所有测试都使用新的 LoopManager 实例，因此 JSONL 加载路径被测试，但内存缓存命中路径（`loop_manager.py:226-228`）从未被覆盖。需要一个在同一 manager 上创建 loop 后调用 `get_loop_with_lazy_load()` 的测试。
- **依据**: 测试覆盖完整性

### Issue 5: MCP 模块 docstring 工具数量过时
- **类型**: Documentation
- **置信度**: 90
- **位置**: `agents_hub/mcp/server.py:2`
- **详情**: 模块 docstring 仍写"MCP Server 和 8 个工具"，但实际已注册 13 个工具（新增 list_loops）。
- **依据**: 文档准确性

### Issue 6: list_loops 墓碑排除未测试
- **类型**: Testing
- **置信度**: 85
- **位置**: `test_loop_manager.py:457-473`
- **详情**: `test_delete_persists_across_restart` 验证了 `get_loop_with_lazy_load()` 在删除后抛异常，但没有测试验证 `list_loops()` 排除已墓碑标记的 loop_id。
- **依据**: 测试覆盖完整性

### Issue 7: list_loops() 类型注解不完整
- **类型**: Best Practices
- **置信度**: 85
- **位置**: `loop_manager.py:290`
- **详情**: `list_loops()` 返回 `list[dict]`，dict 的 key 类型未指定。建议使用 `list[dict[str, Any]]` 或定义 TypedDict 来提供类型安全的调用方访问。
- **依据**: Python 类型注解最佳实践

### Issue 8: JSONDecodeError/KeyError 静默忽略缺少日志
- **类型**: Code Quality / Comment Compliance
- **置信度**: 85
- **位置**: `loop_manager.py:261-262, 338-339`
- **详情**: 损坏的 JSONL 行被静默跳过（无日志），但同文件 `_load_from_persistence()`（line 621-627）对相同场景使用 WARNING 日志。边界数据容错（跳过损坏行）是合理的，但应记录 WARNING 以检测数据完整性问题，保持一致性。
- **依据**: backend-style.md 错误处理规范 + DRY/一致性

## 变更摘要

本次变更为 LoopManager 引入懒加载机制和内存优化：

1. **懒加载**: `LoopManager.__init__()` 不再自动加载历史 Loop，`get_loop_with_lazy_load()` 按需从 JSONL 加载
2. **单 Loop 保持**: `create_loop()` 和 `start_loop()` 清空内存中其他 Loop
3. **JSONL 直读**: `list_loops()` 直接读取 JSONL 文件，返回摘要 dict（含 `in_memory` 标记）
4. **MCP 工具**: 新增 `list_loops` 工具供前端查询历史 Loop

变更行数：+198/-30（453 行 diff），涉及 4 个文件。32/32 单元测试通过。
