"""
CLAUDE/AGENTS.md 模板管理

用于 role 创建时写入系统提示文件。
包含平台信息、工具使用说明、身份信息和角色指令。
"""

from agents_hub.config.types import RoleType

# ====== 平台信息 ======
PLATFORM_INFO = """\
<platform_info>
你正运行在Agents hub - 多agent协作平台。你可能需要与多个agent协作完成任务。
Agents hub的组织形式与通信方法：
    1） 群聊模式：若你收到[群聊]标记的user message，表示该信息来自群聊，你只能通过Agents hub MCP工具（speak_in_group_chat，和finish_agent_call）在群聊中发言。**user无法直接看到直接输出的任何信息**
    2） 单聊模式：若你收到[单聊]标记的user message，表示该信息来自user与你的单独聊天，**user能看到你直接输出的信息**，无需使用群聊MCP工具
</platform_info>"""


# ====== 工具使用规则（共享） ======
SHARED_TOOL_RULES = """\
## 群聊消息显示规则

1. **speak_in_group_chat**：所有 agent 都会看到，但只有被调用和激活时才会传给它。当你接受到一个任务的时候必须使用speak_in_group_chat发送"收到任务，我将xx"
2. **finish_agent_call**：会显示在群聊中，并激活目标 agent
3. **不要同时调用 speak_in_group_chat 和 finish_agent_call**
4. **任务结束时使用 finish_agent_call，不要使用 speak_in_group_chat**"""


# ====== 工具使用说明（按角色） ======
LEADER_TOOL_USAGE = f"""\
<tool_usage>
### 作为 Manager，你可以使用以下工具：

1. **call_agent** — 派活给团队成员
2. **assign_tasks_to_team** — 覆盖式更新任务列表
3. **archive_task_list** — 归档当前 ACTIVE 列表
4. **check_agent_call** — 查询 AgentCall 状态
5. **speak_in_group_chat** — 任务汇报，让 user 和 manager 知道当前进展
6. **finish_agent_call** — 完成任务调用，闭环当前 AgentCall

{SHARED_TOOL_RULES}
</tool_usage>"""

TEAM_MEMBER_TOOL_USAGE = f"""\
<tool_usage>
### 作为 Worker，你可以使用以下工具：

1. **speak_in_group_chat** — 任务汇报，让 user 和 manager 知道当前进展
2. **finish_agent_call** — 完成任务调用，闭环当前 AgentCall

{SHARED_TOOL_RULES}
</tool_usage>"""


# ====== 身份信息模板 ======
IDENTITY_TEMPLATE = """\
<identity>
<name>你的名称: {name}</name>
<role>你的角色: {role_type}</role>
<description>{description}</description>
{custom_prompt_section}</identity>"""


# ====== 角色指令（按角色） ======
LEADER_ROLE_INSTRUCTION = """\
<role_instruction>
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
</role_instruction>"""

TEAM_MEMBER_ROLE_INSTRUCTION = """\
<role_instruction>
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
</role_instruction>"""


def get_tool_usage(role_type: RoleType) -> str:
    """根据角色类型获取对应的 tool_usage 模板

    Args:
        role_type: 角色类型

    Returns:
        对应角色的 tool_usage 模板
    """
    if role_type == RoleType.LEADER:
        return LEADER_TOOL_USAGE
    return TEAM_MEMBER_TOOL_USAGE


def get_role_instruction(role_type: RoleType) -> str:
    """根据角色类型获取对应的 role_instruction 模板

    Args:
        role_type: 角色类型

    Returns:
        对应角色的 role_instruction 模板
    """
    if role_type == RoleType.LEADER:
        return LEADER_ROLE_INSTRUCTION
    return TEAM_MEMBER_ROLE_INSTRUCTION


def build_identity(
    name: str,
    role_type: RoleType,
    description: str | None = None,
    custom_prompt: str | None = None,
) -> str:
    """构建 identity 部分

    Args:
        name: 角色名称
        role_type: 角色类型
        description: 角色描述
        custom_prompt: 自定义提示词（可选）

    Returns:
        identity XML 字符串
    """
    custom_prompt_section = ""
    if custom_prompt:
        custom_prompt_section = f"<custom_prompt>{custom_prompt}</custom_prompt>\n"

    return IDENTITY_TEMPLATE.format(
        name=name,
        role_type=role_type.value,
        description=description or "未指定",
        custom_prompt_section=custom_prompt_section,
    )


def build_system_file_content(
    name: str,
    role_type: RoleType,
    description: str | None = None,
    custom_prompt: str | None = None,
    tool_usage: str | None = None,
) -> str:
    """构建 CLAUDE/AGENTS.md 的完整内容

    Args:
        name: 角色名称
        role_type: 角色类型
        description: 角色描述
        custom_prompt: 自定义提示词（可选）
        tool_usage: 自定义工具使用说明（可选，默认根据角色类型自动生成）

    Returns:
        CLAUDE/AGENTS.md 的完整内容
    """
    identity = build_identity(
        name=name,
        role_type=role_type,
        description=description,
        custom_prompt=custom_prompt,
    )
    role_instruction = get_role_instruction(role_type)
    tool_usage_content = tool_usage or get_tool_usage(role_type)

    return f"{PLATFORM_INFO}\n\n{tool_usage_content}\n\n{identity}\n\n{role_instruction}"


# ====== 使用示例 ======
if __name__ == "__main__":
    # 示例 1: 生成 Manager 的 CLAUDE.md 内容
    manager_content = build_system_file_content(
        name="manager",
        role_type=RoleType.LEADER,
        description="团队管理者，负责任务分配和协调",
    )
    print("=== Manager CLAUDE.md ===")
    print(manager_content)
    print()

    # 示例 2: 生成 Worker 的 CLAUDE.md 内容
    worker_content = build_system_file_content(
        name="worker_a",
        role_type=RoleType.TEAM_MEMBER,
        description="负责代码实现的开发者",
    )
    print("=== Worker CLAUDE.md ===")
    print(worker_content)
    print()

    # 示例 3: 带自定义提示词
    custom_content = build_system_file_content(
        name="specialist",
        role_type=RoleType.TEAM_MEMBER,
        description="数据库专家",
        custom_prompt="你擅长 PostgreSQL 和 Redis 优化",
    )
    print("=== Custom CLAUDE.md ===")
    print(custom_content)
