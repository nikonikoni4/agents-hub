# Flow 文档编写指南

**目标**：让 AI Agent 快速定位代码位置并理解业务逻辑，将探索时间从 1-2 小时降至 15-20 分钟。

**最后更新**：2026-06-18

---

## 一、职责范围

### Flow 文档写什么

1. **函数签名 + 行号**（工具查询入口）
2. **高层语义**（函数作用、设计意图）
3. **数据流路径**（数据如何流转、状态如何变化）

### Flow 文档不写什么

1. **详细实现逻辑**（代码本身已经说明）
2. **业务规则定义**（在 Spec 中，Flow 只链接）
3. **完整调用链**（写逻辑步骤，不写函数调用链）

### 与 Spec 的分工

| Spec | Flow |
|------|------|
| "是什么"（状态机定义、业务规则） | "怎么做"（代码路径、函数调用） |
| 平行面（某个模块的接口约束） | 跨平面的线（跨模块的数据流） |

---

## 二、判断标准：5 类必须记录的节点

**核心原则**：只记录影响 Flow 对象的关键节点，不记录所有函数

### 1. 状态明确变化

Flow 对象的核心状态字段变化（如 `status`、`content`），不含辅助字段（`updated_at`）

```python
# ✅ 记录
AgentCall.status: PENDING → RUNNING

# ❌ 不记录
AgentCall.updated_at: 时间戳更新
```

### 2. 跨模块接口

跨第一层级文件夹（`frontend`、`api`、`mcp`、`core`）

```python
# ✅ 记录
api → core  # 跨模块

# ❌ 不记录
core.orchestration → core.foundation  # 同在 core 内
```

### 3. 数据持久化

写入数据库或文件系统，不含日志、缓存

### 4. 分支节点

Flow 对象的业务分支，不是配置分支

```python
# ✅ 记录
if msg.type == "user":
    handle_user_message()

# ❌ 不记录
if settings.DEBUG:
    use_mock_llm()
```

### 5. 重要的业务集合点

多个数据源汇聚 + 需要业务规则判断 + 影响后续流程

---

## 三、文档结构模板

```markdown
---
version:
created_at:
updated_at:
last_updated:
abstract:
---

# 数据流：[Flow 对象名称]

**Flow 对象**：[对象名称]
**对应 Spec**：[链接]

<key_function last_update="ISO时间戳">
- 文件路径
  - 函数签名:行号
</key_function>

## 流程概览
[Mermaid 状态图 + note 标注]

## 数据流节点
**业务场景说明**：[列出主要链路]

## 链路 1：[场景名称]
[节点描述]

## 链路 2：[场景名称]
[节点描述]

## 异常与清理
[异常处理流程]
```

---

## 四、节点描述格式

```
编号. 函数签名()
   一句话描述作用
   状态: X→Y | 持久化: ✅/❌ | 跨模块: 模块1→模块2 或 ❌
   步骤: 逻辑步骤1 → 逻辑步骤2 → 逻辑步骤3
```

**要点**：
- 函数签名：`ClassName.method` 或 `function`（不含文件路径）
- 作用：一句话说明为什么重要
- 步骤：写逻辑，不写调用链

**示例**：
```markdown
3. GroupChatService.send_message()
   后端 API 层，创建 TASK 类型 AgentCall（send_from="user"）
   状态: 无→PENDING | 持久化: ✅ | 跨模块: api→core
   步骤: 加载群聊 → 创建 AgentCall → 投递消息
```

---

## 五、key_function 格式

**作用**：提供函数签名 + 行号，作为工具查询入口

```markdown
<key_function last_update="2026-06-18T09:26:24+08:00">
- frontend/src/layouts/ChatArea/ChatArea.tsx
  - ChatArea.handleSend:377
- agents_hub/api/services/group_chat_service.py
  - GroupChatService.send_message:479
- agents_hub/core/agent/base_agent.py
  - Agent._process_message:202
</key_function>
```

**规则**：
- 文件路径：从仓库根目录开始
- 函数签名：`ClassName.method` 或 `function_name`
- 行号：`:行号`（编辑器可点击）
- 自动同步：读取 flow 文档时 hook 会自动更新行号

---

## 六、编写流程

### 1. 确定 Flow 对象
明确描述哪个对象的流转（如 `AgentCall`、`Message`）

### 2. 识别业务场景
梳理典型流转场景（如"用户发消息"、"Agent 调用 Agent"）

### 3. 收集关键函数
按 5 类节点筛选，记录到 `<key_function>`

### 4. 画流程概览
Mermaid 状态图 + note 标注关键信息

### 5. 编写数据流节点
按业务场景分链路，每个节点 3-4 行

### 6. 补充设计意图
链接到 ADR、Bug 记录、Spec

---

## 七、注意事项

### 1. 按业务场景组织，不按前后端分离
- ✅ `## 链路 1：用户发消息给 Agent`
- ❌ `## 前端部分`、`## 后端部分`

### 2. 步骤写逻辑，不写调用链
- ✅ `加载群聊 → 创建 AgentCall → 投递消息`
- ❌ `call_agent() → load_group_chat() → create_call()`

### 3. 透传函数不记录，用箭头跳过
```markdown
1. API 层
   （透传）→ 核心层处理
```

### 4. 分支节点明确标注
```markdown
6. Agent._process_message()
   完成任务，根据调用方类型决定后续动作
   分支:
   - 调用方是 user → 写入群聊历史
   - 调用方是 agent → 创建 NOTIFICATION
```

### 5. 自动同步说明
读取 `docs/flows/*.md` 时 hook 会自动调用 `sync_docs.py` 更新行号和时间戳，无需手动维护

---

## 八、编写 Checklist

### 开始编写前
- [ ] 确定 Flow 对象
- [ ] 识别所有业务场景
- [ ] 找到对应的 Spec 文档

### 收集节点时
- [ ] 只记录 5 类节点（状态变化、跨模块、持久化、分支、集合点）
- [ ] 不记录透传函数
- [ ] 不记录配置分支、错误处理

### 编写节点时
- [ ] 函数签名格式正确（`ClassName.method`）
- [ ] 一句话描述作用
- [ ] 标注状态变化、持久化、跨模块
- [ ] 步骤写逻辑，不写调用链

### 完成后
- [ ] `key_function` 包含所有关键函数
- [ ] Mermaid 图只画核心状态转换
- [ ] 按业务场景分链路
- [ ] 分支节点明确标注
- [ ] 链接到相关 ADR、Spec

---

## 九、参考示例

完整示例：`docs/flows/test.md`（AgentCall 生命周期）

---

## 十、相关工具

- **查询调用关系**：`scripts/code_search/func_search.py`
- **自动更新行号**：`scripts/docs_update/sync_docs.py`（hook 自动触发）
- **AST 扫描结果**：`agents_hub/ast_scan_result.json`
