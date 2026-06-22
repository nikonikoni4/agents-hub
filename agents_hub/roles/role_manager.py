"""RoleManager 类 - 角色生命周期管理。"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from agents_hub.config import config
from agents_hub.config.types import AgentPlatform
from agents_hub.roles.exceptions import (
    PlatformConfigNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
)
from agents_hub.roles.models import RoleInfo, RoleType
from agents_hub.roles.prompt_file import build_system_file_content
from agents_hub.roles.role import Role
from agents_hub.utils import get_logger

logger = get_logger(__name__)

# 所有角色默认禁用的工具列表
DEFAULT_DISABLED_TOOLS = [
    "AskUserQuestion",  # 禁止 agent 直接向用户提问，应通过群聊消息机制
]

# Worker 角色禁用的工具列表
# 这些工具是 Leader 专属，Worker 不需要也不能使用
WORKER_DISABLED_TOOLS = [
    "call_agent",  # 派活给团队成员
    "create_group_chat",  # 创建新群聊
    "assign_tasks_to_team",  # 覆盖式更新任务列表
    "archive_task_list",  # 归档当前 ACTIVE 列表
    "create_agent",  # 创建新的成员角色
    "create_loop",  # 创建循环定义
    "start_loop",  # 启动循环
    "stop_loop",  # 停止循环
    "delete_loop",  # 删除循环
    "get_loop_status",  # 查询循环状态
]


class RoleManager:
    """角色生命周期管理。

    负责角色的创建、删除、查询和列表功能。
    管理 local_data/agents/ 目录下的所有角色。

    Attributes:
        agents_dir: agents 目录的路径。
    """

    def __init__(self, agents_dir: Path | None = None) -> None:
        """初始化 RoleManager 实例。

        Args:
            agents_dir: agents 目录路径 (local_data/agents)。
        """
        self.agents_dir = agents_dir or config.data_path / "agents"

    def _validate_role_name(self, name: str) -> None:
        """验证角色名称是否为合法的目录名。

        规则：
        - 名称不能为空
        - 名称不能以点号开头（隐藏目录）
        - 名称不能以空格结尾
        - 名称不能包含 Windows 禁止字符: \\ / : * ? " < > |
        - 名称不能是 Windows 保留名: CON, PRN, AUX, NUL, COM1-9, LPT1-9

        Args:
            name: 要验证的角色名称。

        Raises:
            ValueError: 名称不合法时抛出。
        """
        if not name:
            logger.error("角色名验证失败: 名称为空")
            raise ValueError("Role name cannot be empty")
        if name.startswith("."):
            logger.error("角色名验证失败: name=%s, 不能以点号开头", name)
            raise ValueError("Role name cannot start with '.'")
        if name.endswith(" "):
            logger.error("角色名验证失败: name=%s, 不能以空格结尾", name)
            raise ValueError("Role name cannot end with space")
        if " " in name:
            logger.error("角色名验证失败: name=%s, 不能包含空格", name)
            raise ValueError(f"Invalid role name: '{name}'. Cannot contain spaces")
        if re.search(r'[\\/:*?"<>|]', name):
            logger.error("角色名验证失败: name=%s, 不能包含特殊字符", name)
            raise ValueError(f"Invalid role name: '{name}'. Cannot contain: \\ / : * ? \" < > |")
        # Windows 保留名
        reserved = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        if name.upper() in reserved:
            logger.error("角色名验证失败: name=%s, Windows 保留名称", name)
            raise ValueError(f"Invalid role name: '{name}' is a Windows reserved name")

    def _check_name_prefix_conflict(self, name: str) -> None:
        """检查新名称是否与已有角色名称互为前缀。

        规则：新名称 A 与已有名称 B 不能满足 A.startswith(B) 或 B.startswith(A)。
        避免 @name 匹配歧义，例如 nico 与 nico_1 会冲突。

        Args:
            name: 要检查的角色名称。

        Raises:
            ValueError: 名称与已有角色互为前缀时抛出。
        """
        existing_names = self.list_role_names()
        for existing in existing_names:
            if existing == name:
                continue
            if name.startswith(existing) or existing.startswith(name):
                logger.error("角色名冲突: name=%s, 冲突角色=%s, 名称不能互为前缀", name, existing)
                raise ValueError(
                    f"Role name '{name}' conflicts with existing role '{existing}': "
                    f"names cannot be prefixes of each other"
                )

    def list_roles(self) -> list[RoleInfo]:
        """列出所有角色。

        扫描 agents 目录下的所有子目录，读取 role.json 文件。
        损坏的 role.json 会被跳过。

        Returns:
            RoleInfo 列表，如果没有角色则返回空列表。
        """
        roles: list[RoleInfo] = []
        if not self.agents_dir.exists():
            return roles

        for role_dir in self.agents_dir.iterdir():
            if role_dir.is_dir():
                role_json = role_dir / "role.json"
                if role_json.exists():
                    try:
                        data = json.loads(role_json.read_text(encoding="utf-8"))
                        type_str = data.get("type")
                        role_type = RoleType(type_str) if type_str else None
                        roles.append(
                            RoleInfo(
                                name=data["name"],
                                platform=AgentPlatform(data["platform"]),
                                avatar=data.get("avatar"),
                                abilities=data.get("abilities", []),
                                type=role_type,
                                description=data.get("description"),
                                scope=data.get("scope"),
                                disabled_tools=data.get("disabled_tools"),
                            )
                        )
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning("跳过损坏的 role.json: path=%s, error=%s", role_json, e)
                        continue
        return roles

    def list_role_names(self) -> list[str]:
        """列出所有角色的名称。

        Returns:
            角色名称列表，如果没有角色则返回空列表。
        """
        return [role.name for role in self.list_roles()]

    def list_avatars(self) -> list[str]:
        """列出 avatars/ 目录下所有可用头像文件名。

        扫描 data_path/avatars/ 目录，返回所有图片文件的文件名列表。

        Returns:
            头像文件名列表，如果目录不存在或为空则返回空列表。
        """
        assets_dir = config.data_path / "avatars"
        if not assets_dir.exists():
            return []

        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        return [
            f.name
            for f in assets_dir.iterdir()
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

    def get_role(self, name: str) -> Role:
        """按名称获取角色实例。

        Args:
            name: 角色名称。

        Returns:
            Role 实例。

        Raises:
            ValueError: 名称不合法。
            RoleNotFoundError: 角色不存在。
        """
        self._validate_role_name(name)

        role_dir = self.agents_dir / name
        if not role_dir.exists():
            available_roles = self.list_role_names()
            logger.error(
                "获取角色失败: name=%s, 角色目录不存在, 已有角色=%s", name, available_roles
            )
            raise RoleNotFoundError(role_name=name, available_roles=available_roles)

        role_json = role_dir / "role.json"
        if not role_json.exists():
            available_roles = self.list_role_names()
            logger.error(
                "获取角色失败: name=%s, role.json 不存在, 已有角色=%s", name, available_roles
            )
            raise RoleNotFoundError(role_name=name, available_roles=available_roles)

        return Role(role_dir)

    def _is_role_incomplete(self, role_dir: Path, platform: AgentPlatform) -> bool:
        """检查角色目录是否存在但配置不完整。

        完整角色需要：role.json + work_root/ + 平台配置文件。
        - Claude: settings.json
        - Codex: auth.json + config.toml

        Returns:
            True 表示目录存在但配置不完整，需要重建。
        """
        role_json = role_dir / "role.json"
        work_root = role_dir / "work_root"
        if not role_json.exists() or not work_root.exists():
            return True

        if platform == AgentPlatform.CLAUDE:
            return not (work_root / "settings.json").exists()
        else:
            return (
                not (work_root / "auth.json").exists() or not (work_root / "config.toml").exists()
            )

    def create_role(
        self,
        name: str,
        platform: AgentPlatform,
        avatar: str | None = None,
        abilities: list[str] | None = None,
        type: str | RoleType | None = None,
        scope: list[str] | None = None,
        description: str | None = None,
    ) -> Role:
        """创建新角色。

        创建角色目录结构（work_root、skills），复制平台配置，生成 role.json 文件。
        头像统一存放在 assets/ 目录，角色只存储文件名引用。
        如果创建过程中失败，会自动清理已创建的目录。

        Args:
            name: 角色名称，必须是合法的目录名。
            platform: 目标平台类型（claude 或 codex）。
            avatar: 头像文件的相对路径，默认为空。
            abilities: 能力标签列表，默认为空列表。
            type: 角色类型（leader 或 team_member），默认为空。
            scope: 所属群聊列表，默认为空。

        Returns:
            新创建的 Role 实例。

        Raises:
            ValueError: 名称不合法。
            RoleAlreadyExistsError: 角色已存在。
            PlatformConfigNotFoundError: 平台配置目录不存在。
        """
        logger.info("开始创建角色: name=%s, platform=%s", name, platform.value)
        self._validate_role_name(name)
        self._check_name_prefix_conflict(name)

        role_dir = self.agents_dir / name
        if role_dir.exists():
            if self._is_role_incomplete(role_dir, platform):
                logger.info("角色目录存在但配置不完整，重新创建: name=%s", name)
                shutil.rmtree(role_dir)
            else:
                logger.error("创建角色失败: name=%s, 角色已存在", name)
                raise RoleAlreadyExistsError(role_name=name)

        role_dir.mkdir(parents=True)
        work_root = role_dir / "work_root"
        work_root.mkdir()
        (work_root / "skills").mkdir()

        try:
            if platform == AgentPlatform.CLAUDE:
                self._init_claude_config(work_root)
            elif platform == AgentPlatform.CODEX:
                self._init_codex_config(work_root)
            elif platform == AgentPlatform.OPENCODE:
                self._init_opencode_config(work_root)
            self._init_agents_hub_mcp(platform, work_root)

            # 写入系统提示文件（CLAUDE.md / AGENTS.md）
            role_type = (
                type
                if isinstance(type, RoleType)
                else RoleType(type)
                if type
                else RoleType.TEAM_MEMBER
            )
            system_file_content = build_system_file_content(
                name=name,
                role_type=role_type,
                description=description,
            )
            if platform == AgentPlatform.CLAUDE:
                (work_root / "CLAUDE.md").write_text(system_file_content, encoding="utf-8")
            elif platform == AgentPlatform.CODEX:
                (work_root / "AGENTS.md").write_text(system_file_content, encoding="utf-8")
        except Exception as e:
            logger.error("创建角色失败: name=%s, platform=%s, error=%s", name, platform.value, e)
            shutil.rmtree(role_dir, ignore_errors=True)
            raise

        role_json = {
            "name": name,
            "platform": platform.value,
            "description": description,
            "avatar": avatar,
            "abilities": abilities or [],
            "type": type.value if isinstance(type, RoleType) else type,
            "scope": scope,
        }

        # 所有角色默认禁用 AskUserQuestion，Worker 额外禁用 Leader 专属工具
        disabled_tools = list(DEFAULT_DISABLED_TOOLS)
        if role_type == RoleType.TEAM_MEMBER:
            disabled_tools.extend(WORKER_DISABLED_TOOLS)
        role_json["disabled_tools"] = disabled_tools
        (role_dir / "role.json").write_text(
            json.dumps(role_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        logger.info("角色创建成功: name=%s, platform=%s", name, platform.value)
        return Role(role_dir)

    def delete_role(self, name: str) -> None:
        """删除角色及其目录。

        Args:
            name: 角色名称。

        Raises:
            ValueError: 名称不合法。
            RoleNotFoundError: 角色不存在。
        """
        self._validate_role_name(name)

        role_dir = self.agents_dir / name
        if not role_dir.exists():
            available_roles = self.list_role_names()
            logger.error("删除角色失败: name=%s, 角色不存在, 已有角色=%s", name, available_roles)
            raise RoleNotFoundError(role_name=name, available_roles=available_roles)

        logger.info("删除角色: name=%s", name)
        shutil.rmtree(role_dir)

    def _init_claude_config(self, work_root: Path) -> None:
        """初始化 Claude 平台配置。

        从 ~/.claude 复制 settings.json。
        CLAUDE.md 由 create_role() 统一写入。

        Args:
            work_root: 角色的 work_root 目录路径。

        Raises:
            PlatformConfigNotFoundError: ~/.claude 目录不存在。
        """
        home_claude = Path.home() / ".claude"
        if not home_claude.exists():
            logger.error("初始化 Claude 配置失败: 配置目录不存在, path=%s", home_claude)
            raise PlatformConfigNotFoundError(platform="Claude", config_path=str(home_claude))

        settings_src = home_claude / "settings.json"
        if settings_src.exists():
            shutil.copy2(settings_src, work_root / "settings.json")

    def _init_codex_config(self, work_root: Path) -> None:
        """初始化 Codex 平台配置。

        从 ~/.codex 复制 auth.json、config.toml 和 rules/ 目录。
        AGENTS.md 由 create_role() 统一写入。

        Args:
            work_root: 角色的 work_root 目录路径。

        Raises:
            PlatformConfigNotFoundError: ~/.codex 目录不存在。
        """
        home_codex = Path.home() / ".codex"
        if not home_codex.exists():
            logger.error("初始化 Codex 配置失败: 配置目录不存在, path=%s", home_codex)
            raise PlatformConfigNotFoundError(platform="Codex", config_path=str(home_codex))

        for file_name in ["auth.json", "config.toml"]:
            src = home_codex / file_name
            if src.exists():
                shutil.copy2(src, work_root / file_name)

        rules_src = home_codex / "rules"
        if rules_src.exists():
            shutil.copytree(rules_src, work_root / "rules")

    def _init_opencode_config(self, work_root: Path) -> None:
        """初始化 OpenCode 平台配置。

        创建 agents/ 目录用于存放 agent 提示词文件。
        OpenCode 通过 OPENCODE_CONFIG_DIR 环境变量指向 work_root。

        Args:
            work_root: 角色的 work_root 目录路径。
        """
        # 创建 agents 目录用于存放 agent 提示词文件
        agents_dir = work_root / "agents"
        agents_dir.mkdir(exist_ok=True)

    def _init_agents_hub_mcp(self, platform: AgentPlatform, work_root: Path) -> None:
        """Initialize the fixed agents-hub MCP for this role's platform config root."""
        env = os.environ.copy()
        mcp_url = f"http://localhost:{config.mcp_port}/mcp"
        if platform == AgentPlatform.CLAUDE:
            from agents_hub.config.types import CLAUDE_COMMAND

            env["CLAUDE_CONFIG_DIR"] = str(work_root)
            cmd = [
                CLAUDE_COMMAND,
                "mcp",
                "add",
                "--transport",
                "http",
                "agents-hub",
                "--",
                mcp_url,
            ]
            subprocess.run(cmd, check=True, env=env)
        elif platform == AgentPlatform.CODEX:
            from agents_hub.config.types import CODEX_COMMAND

            env["CODEX_HOME"] = str(work_root)
            cmd = [
                CODEX_COMMAND,
                "mcp",
                "add",
                "agents-hub",
                "--url",
                mcp_url,
            ]
            subprocess.run(cmd, check=True, env=env)
        elif platform == AgentPlatform.OPENCODE:
            # OpenCode 使用 opencode.json 配置 MCP
            opencode_json = work_root / "opencode.json"
            mcp_config = {
                "$schema": "https://opencode.ai/config.json",
                "mcp": {
                    "agents-hub": {
                        "type": "remote",
                        "url": mcp_url,
                        "enabled": True,
                    }
                },
            }
            opencode_json.write_text(
                json.dumps(mcp_config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
