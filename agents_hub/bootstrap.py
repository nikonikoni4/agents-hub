"""资源初始化模块

启动时扫描 template 目录下所有文件，检查目标路径是否存在，不存在则复制。

- 打包环境：bundle_dir 为 PyInstaller 的 sys._MEIPASS，模板根为 bundle_dir/template/
- 非打包环境：模板根为项目根目录/template/
"""

import logging
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Manager 角色禁用的工具列表
# 这些工具是 Agents Hub 助手专属，Manager 不需要
MANAGER_DISABLED_TOOLS = [
    "AskUserQuestion",  # 禁止 agent 直接向用户提问
    "create_group_chat",  # 创建新群聊（助手专属）
    "create_agent",  # 创建新的成员角色（助手专属）
]

# Agents Hub 助手禁用的 MCP 工具黑名单
# 只禁用 MCP (agents-hub) 工具组中的工具，保留 create_group_chat 和 create_agent
ASSISTANT_DISABLED_MCP_TOOLS = [
    "AskUserQuestion",  # 禁止 agent 直接向用户提问
    "call_agent",
    "health_check",
    "check_agent_call",
    "assign_tasks_to_team",
    "archive_task_list",
    "create_loop",
    "start_loop",
    "stop_loop",
    "delete_loop",
    "get_loop_status",
]

# Memory Assistant 禁用的 MCP 工具黑名单
# 记忆助手只需要读取数据和写入文件，不需要 Agent 编排和群聊管理能力
MEMORY_ASSISTANT_DISABLED_TOOLS = [
    "AskUserQuestion",
    "create_group_chat",
    "create_agent",
    "call_agent",
    "check_agent_call",
    "assign_tasks_to_team",
    "archive_task_list",
    "create_loop",
    "start_loop",
    "stop_loop",
    "delete_loop",
    "get_loop_status",
    "list_loops",
    "list_loop_executions",
]


def _get_template_dir() -> Path:
    """获取模板目录路径。

    Returns:
        模板目录路径。
    """
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return bundle_dir / "template"
    else:
        return Path(__file__).resolve().parent.parent / "template"


def _copy_skill_to_role(skill_name: str, role_name: str) -> None:
    """将 skill 复制到角色的 skills 目录。

    如果 skill 已存在则覆盖，确保 skill 是最新的。

    Args:
        skill_name: skill 名称（template/skills/ 下的目录名）。
        role_name: 角色名称。
    """
    from agents_hub.config.config import config

    template_dir = _get_template_dir()
    source_skill_dir = template_dir / "skills" / skill_name

    if not source_skill_dir.exists():
        logger.warning(f"Skill 模板不存在，跳过复制: {source_skill_dir}")
        return

    target_skill_dir = config.data_path / "agents" / role_name / "work_root" / "skills" / skill_name

    # 如果目标已存在，先删除再复制（确保是最新的）
    if target_skill_dir.exists():
        shutil.rmtree(target_skill_dir)
        logger.info(f"已删除旧版 skill: {target_skill_dir}")

    # 复制整个 skill 目录
    shutil.copytree(source_skill_dir, target_skill_dir)
    logger.info(f"已复制 skill '{skill_name}' 到角色 '{role_name}': {target_skill_dir}")


def _copy_knowledge_to_role(knowledge_name: str, role_name: str) -> None:
    """将 template 下的知识文件夹复制到角色的 knowledge-base 目录。

    如果已存在则覆盖，确保知识文件是最新的。

    Args:
        knowledge_name: 知识文件夹名称（template/ 下的目录名）。
        role_name: 角色名称。
    """
    from agents_hub.config.config import config

    template_dir = _get_template_dir()
    source_dir = template_dir / knowledge_name

    if not source_dir.exists():
        logger.warning(f"知识文件夹模板不存在，跳过复制: {source_dir}")
        return

    target_dir = config.data_path / "agents" / role_name / "work_root" / "knowledge-base"

    # 如果目标已存在，先删除再复制（确保是最新的）
    if target_dir.exists():
        shutil.rmtree(target_dir)
        logger.info(f"已删除旧版 knowledge-base: {target_dir}")

    # 复制整个知识文件夹
    shutil.copytree(source_dir, target_dir)
    logger.info(f"已复制知识文件夹 '{knowledge_name}' 到角色 '{role_name}': {target_dir}")


def initialize_resources() -> None:
    """初始化资源文件

    扫描 template 目录下所有文件，不存在于目标路径则复制。
    """
    from agents_hub.config.config import config

    template_dir = _get_template_dir()
    data_path = config.data_path

    if not template_dir.exists():
        logger.warning(f"内嵌 template 目录不存在，跳过资源初始化: {template_dir}")
        return

    for source in template_dir.rglob("*"):
        if not source.is_file():
            continue

        rel = source.relative_to(template_dir)
        target = data_path / rel

        if target.exists():
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        logger.info(f"已初始化资源文件: {target}")


def initialize_default_roles() -> None:
    """初始化默认角色

    创建系统必需的默认角色（如 manager）和系统角色（如 Agents-Hub-Assistant、Agents-Hub-Memory-Assistant），如果不存在则创建。
    同时为 manager 角色复制 loop-design skill（无论角色是否已存在，确保 skill 是最新的）。
    """
    from agents_hub.config import RoleType, config
    from agents_hub.config.types import AgentPlatform
    from agents_hub.roles.role_manager import RoleManager

    role_manager = RoleManager()

    # manager 角色：系统默认的管理者角色
    manager_role_name = config.default_manager_name
    if manager_role_name not in role_manager.list_role_names():
        try:
            role_manager.create_role(
                name=manager_role_name,
                platform=AgentPlatform.CLAUDE,
                type=RoleType.LEADER,
                description="你是团队管理者，负责接收 user 的任务，分析拆解后派给团队成员。派活时给够上下文和约束，不要只说处理一下。其他agent完成任务后，汇总结果。遇到 Worker 报告阻塞时，自己能判断的直接决策，需要专业判断的派给对应成员，都无法解决的向 user 汇报。",
            )
            logger.info(f"已创建默认角色: {manager_role_name}")
        except Exception as e:
            logger.warning(f"创建默认角色 {manager_role_name} 失败: {e}")

    # 为 manager 角色设置禁用列表（无论角色是否已存在，确保禁用列表是最新的）
    try:
        manager_role = role_manager.get_role(manager_role_name)
        manager_role.update_disabled_tools(MANAGER_DISABLED_TOOLS)
        logger.info(f"已更新 {manager_role_name} 禁用工具列表: {MANAGER_DISABLED_TOOLS}")
    except Exception as e:
        logger.warning(f"更新 {manager_role_name} 禁用工具列表失败: {e}")

    # 为 manager 角色复制 loop-design skill（无论角色是否已存在，确保 skill 是最新的）
    try:
        _copy_skill_to_role("loop-design", manager_role_name)
    except Exception as e:
        logger.warning(f"复制 loop-design skill 到 {manager_role_name} 失败: {e}")

    # Agents-Hub-Assistant 角色：系统预置的助手角色
    assistant_role_name = config.default_assistant_name
    if assistant_role_name not in role_manager.list_role_names():
        try:
            role_manager.create_role(
                name=assistant_role_name,
                platform=AgentPlatform.CLAUDE,
                type=RoleType.SYSTEM,
                description="Agents Hub 系统助手，你可以帮助用户创建agents hub的agent和群聊",
            )
            logger.info(f"已创建系统角色: {assistant_role_name}")
        except Exception as e:
            logger.warning(f"创建系统角色 {assistant_role_name} 失败: {e}")

    # 为 Agents-Hub-Assistant 设置禁用列表（禁用 MCP 工具中除 create_group_chat 和 create_agent 外的所有工具）
    try:
        assistant_role = role_manager.get_role(assistant_role_name)
        assistant_role.update_disabled_tools(ASSISTANT_DISABLED_MCP_TOOLS)
        logger.info(f"已更新 {assistant_role_name} 禁用工具列表: {ASSISTANT_DISABLED_MCP_TOOLS}")
    except Exception as e:
        logger.warning(f"更新 {assistant_role_name} 禁用工具列表失败: {e}")

    # 为 Agents-Hub-Assistant 复制 agent-trainer skill（无论角色是否已存在，确保 skill 是最新的）
    try:
        _copy_skill_to_role("agent-trainer", assistant_role_name)
    except Exception as e:
        logger.warning(f"复制 agent-trainer skill 到 {assistant_role_name} 失败: {e}")

    # Agents-Hub-Memory-Assistant 角色：系统预置的记忆助手角色
    memory_assistant_name = config.default_memory_assistant_name
    if memory_assistant_name not in role_manager.list_role_names():
        try:
            role_manager.create_role(
                name=memory_assistant_name,
                platform=AgentPlatform.CLAUDE,
                type=RoleType.SYSTEM,
                description="Agents Hub 记忆助手，负责收集群聊信息，编写任务日志、用户决策、AI错误记录和协作改进建议",
            )
            logger.info(f"已创建系统角色: {memory_assistant_name}")
        except Exception as e:
            logger.warning(f"创建系统角色 {memory_assistant_name} 失败: {e}")

    # 为 Memory Assistant 设置禁用列表
    try:
        memory_role = role_manager.get_role(memory_assistant_name)
        memory_role.update_disabled_tools(MEMORY_ASSISTANT_DISABLED_TOOLS)
        logger.info(
            f"已更新 {memory_assistant_name} 禁用工具列表: {MEMORY_ASSISTANT_DISABLED_TOOLS}"
        )
    except Exception as e:
        logger.warning(f"更新 {memory_assistant_name} 禁用工具列表失败: {e}")

    # 为 Memory Assistant 复制知识文件（无论角色是否已存在，确保知识文件是最新的）
    try:
        _copy_knowledge_to_role("memory-assistant", memory_assistant_name)
    except Exception as e:
        logger.warning(f"复制知识文件到 {memory_assistant_name} 失败: {e}")
