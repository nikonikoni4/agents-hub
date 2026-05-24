"""RoleManager 类 - 角色生命周期管理"""

import json
import re
import shutil
from pathlib import Path
from typing import List, Optional

from agents_hub.agent_bridge.config import AgentPlatform
from agents_hub.agents.models import RoleInfo, RoleType
from agents_hub.agents.role import Role
from agents_hub.agents.exceptions import RoleNotFoundError, RoleAlreadyExistsError, PlatformConfigNotFoundError


class RoleManager:
    """角色生命周期管理"""

    def __init__(self, agents_dir: Path):
        """
        Args:
            agents_dir: agents 目录路径 (local_data/agents)
        """
        self.agents_dir = agents_dir

    def _validate_role_name(self, name: str) -> None:
        """验证角色名称是否为合法的目录名

        Args:
            name: 角色名称

        Raises:
            ValueError: 名称不合法
        """
        if not name:
            raise ValueError("Role name cannot be empty")
        if name.startswith('.') or name.startswith('-'):
            raise ValueError(f"Role name cannot start with '.' or '-'")
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValueError(f"Invalid role name: '{name}'. Only alphanumeric, underscore and hyphen allowed.")

    def list_roles(self) -> List[RoleInfo]:
        """扫描 local_data/agents/*/role.json，返回所有角色摘要列表"""
        roles = []
        if not self.agents_dir.exists():
            return roles

        for role_dir in self.agents_dir.iterdir():
            if role_dir.is_dir():
                role_json = role_dir / "role.json"
                if role_json.exists():
                    try:
                        data = json.loads(role_json.read_text(encoding="utf-8"))
                        # 将 type 字符串转换为 RoleType 枚举
                        type_str = data.get("type")
                        role_type = RoleType(type_str) if type_str else None
                        roles.append(RoleInfo(
                            name=data["name"],
                            platform=AgentPlatform(data["platform"]),
                            avatar=data.get("avatar"),
                            abilities=data.get("abilities", []),
                            type=role_type,
                            scope=data.get("scope"),
                        ))
                    except (json.JSONDecodeError, KeyError) as e:
                        # 跳过损坏的 role.json
                        continue
        return roles

    def get_role(self, name: str) -> Role:
        """按名称加载单个角色，返回 Role 实例"""
        self._validate_role_name(name)

        role_dir = self.agents_dir / name
        if not role_dir.exists():
            raise RoleNotFoundError(f"Role '{name}' not found")

        role_json = role_dir / "role.json"
        if not role_json.exists():
            raise RoleNotFoundError(f"Role '{name}' not found (missing role.json)")

        return Role(role_dir)

    def create_role(
        self,
        name: str,
        platform: AgentPlatform,
        avatar: Optional[str] = None,
        abilities: Optional[List[str]] = None,
        type: Optional[str] = None,
        scope: Optional[List[str]] = None,
    ) -> Role:
        """创建新角色，初始化目录结构和 role.json"""
        # 验证名称合法性
        self._validate_role_name(name)

        role_dir = self.agents_dir / name
        if role_dir.exists():
            raise RoleAlreadyExistsError(f"Role '{name}' already exists")

        # 创建目录结构
        role_dir.mkdir(parents=True)
        avatar_dir = role_dir / "avatar"
        avatar_dir.mkdir()
        work_root = role_dir / "work_root"
        work_root.mkdir()
        (work_root / "skills").mkdir()

        try:
            # 根据 platform 复制配置
            if platform == AgentPlatform.CLAUDE:
                self._init_claude_config(work_root)
            else:
                self._init_codex_config(work_root)
        except Exception:
            # 初始化失败时清理已创建的目录
            shutil.rmtree(role_dir, ignore_errors=True)
            raise

        # 写入 role.json
        role_json = {
            "name": name,
            "platform": platform.value,
            "avatar": avatar,
            "abilities": abilities or [],
            "type": type,
            "scope": scope,
            "skills": [],
        }
        (role_dir / "role.json").write_text(
            json.dumps(role_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return Role(role_dir)

    def delete_role(self, name: str) -> None:
        """删除角色及其目录"""
        self._validate_role_name(name)

        role_dir = self.agents_dir / name
        if not role_dir.exists():
            raise RoleNotFoundError(f"Role '{name}' not found")

        shutil.rmtree(role_dir)

    def _init_claude_config(self, work_root: Path) -> None:
        """初始化 Claude 平台配置"""
        home_claude = Path.home() / ".claude"
        if not home_claude.exists():
            raise PlatformConfigNotFoundError(f"Claude config directory not found: {home_claude}")

        # 复制 settings.json
        settings_src = home_claude / "settings.json"
        if settings_src.exists():
            shutil.copy2(settings_src, work_root / "settings.json")

        # 创建空白 CLAUDE.md
        (work_root / "CLAUDE.md").write_text("", encoding="utf-8")

    def _init_codex_config(self, work_root: Path) -> None:
        """初始化 Codex 平台配置"""
        home_codex = Path.home() / ".codex"
        if not home_codex.exists():
            raise PlatformConfigNotFoundError(f"Codex config directory not found: {home_codex}")

        # 复制配置文件
        for file_name in ["auth.json", "config.toml"]:
            src = home_codex / file_name
            if src.exists():
                shutil.copy2(src, work_root / file_name)

        # 复制 rules 目录
        rules_src = home_codex / "rules"
        if rules_src.exists():
            shutil.copytree(rules_src, work_root / "rules")

        # 创建空白 AGENTS.md
        (work_root / "AGENTS.md").write_text("", encoding="utf-8")
