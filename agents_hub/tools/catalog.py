"""工具目录 - 硬编码所有可用工具的分组、名称和描述"""

from dataclasses import dataclass


@dataclass
class ToolInfo:
    name: str
    description: str


@dataclass
class ToolGroup:
    name: str
    icon: str
    tools: list[ToolInfo]


ALL_TOOLS: list[ToolGroup] = [
    ToolGroup(
        name="文件操作",
        icon="📁",
        tools=[
            ToolInfo("Read", "读取文件内容"),
            ToolInfo("Write", "创建或覆盖文件"),
            ToolInfo("Edit", "精确替换文件内容"),
            ToolInfo("Glob", "按模式查找文件"),
            ToolInfo("NotebookEdit", "编辑 Jupyter Notebook"),
        ],
    ),
    ToolGroup(
        name="执行",
        icon="⚡",
        tools=[
            ToolInfo("Bash", "执行 shell 命令（Linux/macOS）"),
            ToolInfo("PowerShell", "执行 PowerShell 命令（Windows）"),
            ToolInfo("Agent", "启动子代理执行任务"),
        ],
    ),
    ToolGroup(
        name="搜索",
        icon="🔍",
        tools=[
            ToolInfo("Grep", "搜索文件内容"),
            ToolInfo("WebSearch", "网页搜索"),
            ToolInfo("WebFetch", "获取网页内容"),
        ],
    ),
    ToolGroup(
        name="任务管理",
        icon="📋",
        tools=[
            ToolInfo("TodoWrite", "创建和管理待办事项"),
            ToolInfo("TaskOutput", "获取后台任务输出"),
            ToolInfo("TaskStop", "停止后台任务"),
        ],
    ),
    ToolGroup(
        name="系统",
        icon="⚙️",
        tools=[
            ToolInfo("CronCreate", "创建定时任务"),
            ToolInfo("CronDelete", "删除定时任务"),
            ToolInfo("CronList", "列出定时任务"),
            ToolInfo("ScheduleWakeup", "调度唤醒"),
            ToolInfo("EnterPlanMode", "进入计划模式"),
            ToolInfo("ExitPlanMode", "退出计划模式"),
            ToolInfo("EnterWorktree", "进入工作树"),
            ToolInfo("ExitWorktree", "退出工作树"),
            ToolInfo("AskUserQuestion", "向用户提问"),
            ToolInfo("ListMcpResourcesTool", "列出 MCP 资源"),
            ToolInfo("ReadMcpResourceTool", "读取 MCP 资源"),
            ToolInfo("Skill", "调用已安装的 Skill"),
        ],
    ),
    ToolGroup(
        name="MCP (agents-hub)",
        icon="🔌",
        tools=[
            ToolInfo("call_agent", "派活给团队成员"),
            ToolInfo("health_check", "健康检查端点"),
            ToolInfo("create_group_chat", "创建新群聊"),
            ToolInfo("speak_in_group_chat", "向群聊发送进展信息"),
            ToolInfo("finish_agent_call", "结束 AgentCall"),
            ToolInfo("check_agent_call", "查询 AgentCall 状态"),
            ToolInfo("assign_tasks_to_team", "覆盖式更新任务列表"),
            ToolInfo("archive_task_list", "归档当前 ACTIVE 列表"),
            ToolInfo("create_agent", "创建新的成员角色"),
            ToolInfo("request_permission", "请求权限"),
        ],
    ),
]


def get_all_tool_names() -> list[str]:
    """获取所有工具名称的扁平列表"""
    return [tool.name for group in ALL_TOOLS for tool in group.tools]
