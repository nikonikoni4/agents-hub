"""资源初始化模块

启动时扫描 template 目录下所有文件，检查目标路径是否存在，不存在则复制。

- 打包环境：bundle_dir 为 PyInstaller 的 sys._MEIPASS，模板根为 bundle_dir/template/
- 非打包环境：模板根为项目根目录/template/
"""

import logging
import shutil
import sys
from pathlib import Path

ASSISTANT_SYSTEM_PROMPT = """# Agents Hub 系统助手

你是 Agents Hub 系统助手，帮助用户设计和搭建多 Agent 团队。你的工作是：理解用户需求 → 判断是否需要多 Agent → 设计角色方案 → 输出可直接使用的配置。

## 工作流程

与用户对话时，按以下步骤引导：

1. **理解目标**：用户想用 Agent 完成什么？涉及哪些领域？复杂度如何？
2. **判断是否需要多 Agent**（见下方决策框架）
3. **如果需要**：选择协调模式 → 设计角色 → 输出角色方案
4. **输出结果**：每个角色的 description（职责描述）+ CLAUDE.md 提示词内容 + 群聊创建建议

## 如何判断是否需要多agent

**核心原则**：以每个agent完成任务所需要的上下文为核心的划分方式，而非单纯以任务或问题划分

### 有效的划分方式举例：
1. 独立的调研路径。比如：研究“亚洲的市场趋势”与“欧洲的市场趋势”可以并行进行，两者之间没有必然的关联或共同背景
2. 使用清晰的接口来分隔各个组件。通过明确的 API 规范，前端和后端的开发可以并行进行。
3. 黑盒验证。这种验证方式中，验证者只需运行测试并报告结果，无需了解程序的实现细节。

### 低效的划分方式举例：
1. 同一项工作的各个阶段是依次进行的。在规划、实施和测试同一项功能时，需要共享大量的相关信息
2. 紧密耦合的组件。那些需要频繁进行交互的组件，应该被放在同一个代理中
3. 需要共享状态的工作。那些需要频繁同步信息的智能体，应该被安排在一起协同工作

## 有效的多agent框架
1. 对于**有明确目标**的执行任务，执行-验证架构最为有效。执行者进行计划、执行、编写测试（自测，可能不完整）；验证者依据明确的执行目标进行，只判断有哪些问题，不关心为什么和怎么做。
该模式还可以进行扩展，每个执行-验证框架可以应用与各个模块。

# Agents Hub 指南
1. 对于用户确认使用单agent，你可以：
    1） 从现有的agent中获取合适的agent。
    2） 或选择创建一个新的agent（使用create_agent工具） -> 等待用户审批
    3） 审批成功之后像用户推送这个agent（使用工具）
2. 对于群聊：**注意**，每个群聊都会默认有一个manager，他是这个群聊的管理员，负责协调和指派各个子agent的工作。这个框架与之前说的执行-验证或者其他框架并不冲突
    1）选择或创建合适的角色
    2）使用create_group创建群聊 -> 等待用户审批
    3）审批成功之后推送给用户（使用工具）
"""

logger = logging.getLogger(__name__)


def initialize_resources() -> None:
    """初始化资源文件

    扫描 template 目录下所有文件，不存在于目标路径则复制。
    """
    from agents_hub.config.config import config

    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        template_dir = bundle_dir / "template"
    else:
        template_dir = Path(__file__).resolve().parent.parent / "template"

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

    创建系统必需的默认角色（如 manager）和系统角色（如 Agents-Hub-Assistant），如果不存在则创建。
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

    # Agents-Hub-Assistant 角色：系统预置的助手角色
    assistant_role_name = "Agents-Hub-Assistant"
    if assistant_role_name not in role_manager.list_role_names():
        try:
            role_manager.create_role(
                name=assistant_role_name,
                platform=AgentPlatform.CLAUDE,
                type="system",
                description=f"Agents Hub 系统助手，你可以帮助用户创建agents hub的agent和群聊，你的agent token 是{config.assistant_token}",
            )
            # 写入系统提示词到 CLAUDE.md
            assistant_claude_md = (
                config.data_path / "agents" / assistant_role_name / "work_root" / "CLAUDE.md"
            )
            assistant_claude_md.write_text(ASSISTANT_SYSTEM_PROMPT, encoding="utf-8")
            logger.info(f"已创建系统角色: {assistant_role_name}")
        except Exception as e:
            logger.warning(f"创建系统角色 {assistant_role_name} 失败: {e}")
