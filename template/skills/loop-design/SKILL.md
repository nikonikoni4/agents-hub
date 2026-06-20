---
name: loop-design
description: |
  指导 Manager 设计和创建 Loop 循环。当 Manager 需要创建自动化循环（如 Executor-Reviewer、Writer-Editor 模式）时使用。
  提供完整的设计流程：需求澄清 → 节点设计 → 用户确认 → Subagent 验证 → 创建循环。
  确保循环提示词质量，避免因上下文设计不当导致循环失败。
  触发词：创建循环、loop、循环设计、迭代执行、自动审查。
---

# Loop 循环设计指南

## 设计流程

```
需求澄清 → 节点流程设计 → 用户确认流程 → 提示词设计 → Subagent 验证 → 用户确认提示词 → 创建循环
```

## 步骤 1：需求澄清

逐个询问用户以下问题，每次只问一个问题，确保理解对齐后才进入下一步。

### 澄清清单

1. **问题定义**：这个循环要解决什么问题？
2. **参与角色**：需要哪些 Agent 参与？每个 Agent 的核心职责是什么？
3. **退出条件**：循环的退出条件是什么？由谁来判断？
4. **循环轮数**：预期的循环轮数大概是多少？
5. **特殊约束**：有没有特殊的约束或要求？

### 询问原则

- 每次只问一个问题
- 等用户回答后，复述理解并确认
- 如果用户回答模糊，追问具体细节
- 所有问题澄清后，输出需求总结让用户确认

### 需求总结模板

```markdown
## 需求总结

- **问题**：{问题描述}
- **参与角色**：{角色1}、{角色2}、...
- **退出条件**：{退出条件}
- **预期轮数**：{轮数}
- **特殊约束**：{约束}

请确认以上理解是否正确。
```

## 步骤 2：节点流程设计

基于需求澄清的结果，设计节点流程。

### 节点流程模板

```markdown
## 节点流程

### 节点列表
1. {节点1名称} (normal) - {职责简述}
2. {节点2名称} (terminator) - {职责简述}

### 数据流转
{节点1} → {节点2} → {节点1} → ...

### 退出条件
由 {TERMINATOR节点} 判断，当 {条件} 时退出循环。
```

### 设计要点

- 每个节点的职责要清晰、不重叠
- TERMINATOR 节点通常负责审查/判断
- 考虑上下游节点的数据流转

## 步骤 3：用户确认节点流程

将节点流程发送给用户确认，等待用户确认后再进行下一步。

### 确认模板

```markdown
## 节点流程确认

请确认以下节点流程是否正确：

### 节点列表
1. {节点1} (normal) - {职责}
2. {节点2} (terminator) - {职责}

### 数据流转
{节点1} → {节点2} → {节点1} → ...

### 退出条件
由 {节点2} 判断，当 {条件} 时退出。

请确认是否正确，或提出修改意见。
```

## 步骤 4：提示词设计

用户确认节点流程后，为每个节点设计提示词。

### 节点设计模板

为每个节点填写以下内容：

```markdown
## 节点: {节点名称}

### 职责定位
- 在这个循环中我要做什么：{具体职责}
- 我的核心任务：{任务描述}

### 输入分析
- 我需要接收什么信息：{输入信息}
- 上游节点会给我什么：{上游输出}

### 输出定义
- 我需要输出什么：{输出内容}
- 输出格式要求：{格式要求}
- 必需字段：{字段列表}

### 质量标准
- 什么样的输出是合格的：{合格标准}
- 什么样的输出需要重试：{重试条件}
```

### 提示词编写要点

**role_description 编写**：
- 明确节点在循环中的职责
- 说明输入来源和输出目标
- 避免与 Agent 本身的 role 描述冲突

**output_schema_prompt 编写**：
- 使用 Markdown 格式
- 包含清晰的标题和填写说明
- 与 output_schema_fields 完全一致

**output_schema_fields 编写**：
- 必须与 output_schema_prompt 中的标题完全匹配
- 用于系统校验输出格式

### 输出格式示例

```markdown
请按以下格式输出：

## 实现代码
（粘贴修改后的代码路径）

## 修改说明
（说明本次修改了哪些内容，为什么这样修改）
```

对应 `output_schema_fields`：`["## 实现代码", "## 修改说明"]`

## 步骤 5：Subagent 验证

为每个节点派发验证任务，使用 [subagent-template.md](references/subagent-template.md)。

### 验证流程

1. 为每个节点创建一个验证任务
2. Subagent 只看到单个节点的信息（模拟执行者视角）
3. 收集所有 Subagent 的反馈
4. 整合反馈，修正设计

### 验证要点

- **职责清晰度**：执行者是否能准确理解要做什么？
- **输入充分性**：是否有足够信息完成任务？
- **输出可执行性**：输出格式是否清晰可执行？
- **上下游配合**：输入输出是否匹配？

### 验证结果处理

- 如果所有节点验证通过，进入下一步
- 如果有问题，修正设计后重新验证

## 步骤 6：用户确认提示词

将设计好的提示词发送给用户确认。

### 确认模板

```markdown
## 提示词确认

请确认以下节点提示词是否正确：

### 节点 1: {节点名称}

**职责描述**:
{role_description}

**输出格式**:
{output_schema_prompt}

**必需字段**:
{output_schema_fields}

---

### 节点 2: {节点名称}

**职责描述**:
{role_description}

**输出格式**:
{output_schema_prompt}

**必需字段**:
{output_schema_fields}

---

请确认是否正确，或提出修改意见。
```

## 步骤 7：创建循环

用户确认提示词后，调用 `create_loop` 工具创建循环。

### 创建参数

```python
{
    "nodes": [
        {
            "node_type": "normal",
            "agent_name": "{agent_name}",
            "role_description": "{role_description}",
            "output_schema_prompt": "{output_schema_prompt}",
            "output_schema_fields": ["{field1}", "{field2}"]
        },
        {
            "node_type": "terminator",
            "agent_name": "{agent_name}",
            "role_description": "{role_description}",
            "output_schema_prompt": "{output_schema_prompt}",
            "output_schema_fields": ["{field1}", "{field2}"]
        }
    ],
    "max_iterations": {max_iterations},
    "initial_task": "{initial_task}"
}
```

### 创建后操作

1. 返回 loop_id 给用户
2. 询问是否立即启动（调用 start_loop）
3. 如果启动，告知用户循环已开始运行

## 常见循环模式

详见 [common-patterns.md](references/common-patterns.md)

## 快速检查清单

详见 [checklist.md](references/checklist.md)
