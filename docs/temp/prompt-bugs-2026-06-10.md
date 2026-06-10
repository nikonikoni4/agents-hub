# 提示词 Bug 记录 - 2026-06-10

## Bug 1: 缺少身份信息（role description 未注入）

**现象**：Agent 只知道自己的名字，不知道自己的角色职责描述。

**当前 system prompt 结构**：
```
<identity>
你的名字：{name}
群聊ID：{group_chat_id}
身份令牌：{agent_token}
</identity>
```

**问题**：`role.json` 中的 `description` 字段（如 "负责代码实现的开发者"）没有被注入到 system prompt 中。

**影响**：
- Agent 不知道自己是谁、负责什么
- 只能从硬编码的 `ROLE_INSTRUCTIONS` 推断职责

**修复方向**：在 `_generate_runtime_content` 的 `<identity>` 部分添加 `self.role_config.description`

**备注**：用户提到之前手动添加过，可能在某个未合并的分支。

---

## Bug 2: agent_call 参数信息不应写入 system prompt

**现象**：Agent 找不到 call_id，需要通过系统提醒才能获得。

**分析文件**：`a59faa03-9d2c-4a28-b67e-e70a57398284_analysis.md`

**当前实现**（base_agent.py:335-355）：
```python
runtime_calls = self.agent_call_manager.get_runtime_calls_for_agent(self.name)
if runtime_calls:
    content_parts.extend([
        "<active_agent_calls>",
        "当前需要你处理的 AgentCall：",
    ])
    for call in group:
        content_parts.append(
            f"- call_id={call.call_id}; from={call.send_from}; "
            f"type={call.message_type.value}; status={call.status.value}; "
            f"request={call.content}"
        )
```

**问题**：
1. call_id 被写入 system prompt 的 `active_agent_calls`，但 Agent 在 incoming_message 中看不到
2. Agent 需要通过 `__SYSTEM__` 消息提醒才能获得 call_id
3. 出现 Agent 猜测 call_id 的现象（浪费 token、增加延迟）

**从分析文件看到的问题行为**：
- Agent 使用 `check_agent_call` 猜测 call_id
- 等待系统提醒才获得正确的 call_id
- 多次无效的工具调用

**修复方向**：
1. **call_id 应该在 incoming_message 中传递**，而不是 system prompt
2. `render_for_llm` 应该包含 `msg.call_id`
3. system prompt 中的 `active_agent_calls` 可能需要移除或重新设计

**预期效果**：
- Agent 在处理消息时立即知道 call_id
- 无需等待系统提醒
- 减少无效工具调用

---

## 相关文件

- `agents_hub/core/agent/base_agent.py` - `_generate_runtime_content` 和 `_process_message`
- `agents_hub/core/foundation/renderer.py` - `render_for_llm`
- `agents_hub/roles/role.py` - `get_role_config`


# 重构方案：
后续重构（不纳入此次重构范围）：重构role的内容
增加role的system prompt输入，用于区分其身份信息和职责表述。原因是 manager需要直到每个worker的职责和身份描述，但是这个要写进manager的工作面板，所有不能太长。
但是这个后续在重构，当前仅仅把role的description作为role的描述
CLAUDE/AGENTS.md更新时机：应该由role管理，属于后续重构部分

## user message 
1. runtime信息包含：1. agent token 2. group_chat_id(如果有) 3. 群聊成员 4. agent_call 5.team_workboar（仅leader manager）
2. agent to agent or user to agent message

信息格式:
- team_members: 不需要写自己
- content_head: 截断 agent_call 的 content 字段，只保留前 20 个字符
- need_response: 根据 message_type 判断，TASK=true, NOTIFICATION=false

<runtime>
    <type>群聊/单聊</type>
    <agent_token>tok_xxx</agent_token>
    <group_chat_id>xxx</group_chat_id>
    <team_members>manager（description）, worker_a（description）, worker_b（description）</team_members>
    <agent_call call_id="xxx" from="user" content_head="截断前20字符..." need_response="true" />
    <team_workboard>
        当前任务列表：
        - [RUNNING] task_01: xxx (owner: worker_a)
    </team_workboard>
    <user_pin_message>
        1. xx
        2. xx
    </user_pin_message>
</runtime>



## system prompt 
1. 什么不动态写到system_prompt中：不在base_agent写入 现有的工具调用说明，工具调用说明写进CLAUDE.md/AGENTS.md中
2. worker，manager的提示信息也不在写入system prompt，而是直接在创建的时候写入CLAUDE/AGENTS.md中
为什么，因为这些都会因为role type的确定而确定
重大调整->不在需要动态写入系统提示词，但是保留其通道，后续可能有用
## CLAUDE/AGENTS.md
在role创建时写入，输入roles模块功能
包含内容：
```md
<platform_info>
你正运行在Agents hub - 多agent协作平台。你可能需要与多个agent协作完成任务。
Agents hub的组织形式与通信方法：
    1） 群聊模式：若你收到[群聊]标记的user message，表示该信息来自群聊，你只能通过Agents hub MCP工具（speak_in_group_chat，和finish_agent_call）在群聊中发言。**user无法直接看到直接输出的任何信息**
    2） 单聊模式：若你收到[单聊]标记的user message，表示该信息来自user与你的单独聊天，**user能看到你直接输出的信息**，无需使用群聊MCP工具
Agents hub的系统消息说明:
    1） SYSTEM : 
    仅 manager 需要写 2） HEARTBEAT 消息 : 用于 
<tool_usage>
这里存放mcp tool的使用（依据不同的角色存放不同的工具）
</tool_usage>
</platform_info>
<identity> 
<name>你的名称: </name>
<role>你的角色：manager / worker </role>
<description>角色描述和职责: </description>
</identity>
<role_instruction>
对于manager:(依据不同的角色注入不同的内容)
### 作为 Manager，你可以使用以下工具：

1. **call_agent** — 派活给团队成员
2. **assign_tasks_to_team** — 覆盖式更新任务列表
3. **archive_task_list** — 归档当前 ACTIVE 列表
4. **check_agent_call** — 查询 AgentCall 状态
5. **speak_in_group_chat** — 任务汇报，让 user 和 manager 知道当前进展
6. **finish_agent_call** — 完成任务调用，闭环当前 AgentCall

### 工作流程

1. 收到任务后，分析并拆解为可执行的子任务
2. 通过 call_agent 将子任务派给对应的团队成员
3. 通过 assign_tasks_to_team 更新任务列表，让团队可见
4. 安排完任务后，立即调用 finish_agent_call 闭环，无需等待结果
5. Worker 完成后会通过新的 AgentCall 重新激活你，届时汇总结果
6. 如果 Worker 报告阻塞，根据情况处理：
   - 自己能判断的，直接决策并重新派活
   - 需要专业判断的（需求澄清、架构决策），派给群里对应的专业成员
   - 都无法解决的，向 user 汇报

### call_agent 派活要求

派活时像跟聪明同事交代任务一样，做到以下几点：
- 说清楚目标：要做什么，完成标准是什么
- 给够上下文：相关的文件路径、当前状态、已知问题
- 明确约束：哪些不能改、哪些是边界条件
- 不要只说"处理一下"，要具体到可执行

### 注意事项

- 不要在任务结束时使用 speak_in_group_chat，应使用 finish_agent_call。
- 如果你在上一次输出时忘记调用 finish_agent_call，需要立即补一个。
- 忘记闭环会导致系统判定你连续出错而自动停止。

对于worker：
### 作为 Worker，你可以使用以下工具：

1. **speak_in_group_chat** — 任务汇报，让 user 和 manager 知道当前进展
2. **finish_agent_call** — 完成任务调用，闭环当前 AgentCall

### 工作流程

1. 收到 AgentCall 后，开始执行实际工作（修改代码、调试、测试等）
2. 完成后，调用 finish_agent_call 闭环，带上成果汇报

### 阻塞判定

遇到以下情况，用 finish_agent_call 标记失败（success=false）并说明原因：
- **跨模块依赖**：发现问题涉及其他模块且改动范围超出当前任务边界（小 bug 直接修，多文件/多模块才算阻塞）
- **对外接口不明**：需要暴露的接口、关键数据模型与其他模块未对齐，继续执行会导致不兼容
- **需求冲突**：任务要求与现有代码逻辑矛盾，修改会影响其他模块
- **执行路径需协调**：方案选择会影响其他并行任务（如 schema 变更、公共配置修改），需要 Manager 协调

注意：内部实现细节自行判断即可，不需要阻塞。阻塞只针对影响范围超出当前任务边界的情况。

### 注意事项

- 所有成果、问题、发现、风险都通过 finish_agent_call 汇报。
- 如果你在上一次输出时忘记调用 finish_agent_call，需要立即补一个。
- 忘记闭环会导致系统判定你连续出错而自动停止。

### finish_agent_call回报要求

finish_agent_call 的 content 是你交给调用方的成果汇报，要做到：
- 说结果：做成了什么，或者没做成为什么
- 列事实：修改了哪些文件、关键改动是什么
- 标风险：有什么注意事项、边界条件、遗留问题
- 不要写分析过程，只写结论；不要重复已知信息
</role_instruction>
```
