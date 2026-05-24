"""Role 类 - 单个角色的配置管理"""

import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from agents_hub.agent_bridge.config import AgentPlatform, RoleConfig
from agents_hub.agents.models import RoleInfo, SkillInfo
from agents_hub.agents.exceptions import SkillNotFoundError, SkillAlreadyExistsError


class Role:
    """单个角色的配置管理

    管理 local_data/agents/<role_name>/ 下的角色配置，
    包括 role.json 元数据、work_root 工作目录和 skills 子目录。
    """

    def __init__(self, role_dir: Path):
        """
        Args:
            role_dir: 角色目录路径 (local_data/agents/<role_name>)
        """
        self.role_dir = role_dir
        self._role_json_path = role_dir / "role.json"
        self._work_root = role_dir / "work_root"

    def _read_role_json(self) -> Dict[str, Any]:
        """读取 role.json"""
        return json.loads(self._role_json_path.read_text(encoding="utf-8"))

    def _write_role_json(self, data: Dict[str, Any]) -> None:
        """写入 role.json"""
        self._role_json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_info(self) -> RoleInfo:
        """返回角色摘要信息"""
        data = self._read_role_json()
        return RoleInfo(
            name=data["name"],
            platform=AgentPlatform(data["platform"]),
            avatar=data.get("avatar"),
            abilities=data.get("abilities", []),
            type=data.get("type"),
            scope=data.get("scope"),
        )

    def update_name(self, new_name: str) -> None:
        """更新角色名称，同步修改目录名和 role.json"""
        data = self._read_role_json()
        data["name"] = new_name
        self._write_role_json(data)

        # 重命名目录
        new_dir = self.role_dir.parent / new_name
        self.role_dir.rename(new_dir)
        self.role_dir = new_dir

    def update_avatar(self, avatar_path: str) -> None:
        """更新头像，将旧头像移入 history"""
        data = self._read_role_json()

        # 如果有旧头像，移入 history
        if data.get("avatar"):
            avatar_dir = self.role_dir / "avatar"
            history_files = list(avatar_dir.glob("history_*.png"))
            next_num = len(history_files) + 1
            old_avatar = avatar_dir / data["avatar"]
            if old_avatar.exists():
                old_avatar.rename(avatar_dir / f"history_{next_num:02d}.png")

        data["avatar"] = avatar_path
        self._write_role_json(data)

    def update_abilities(self, abilities: List[str]) -> None:
        """更新能力标签列表"""
        data = self._read_role_json()
        data["abilities"] = abilities
        self._write_role_json(data)

    def list_skills(self) -> List[SkillInfo]:
        """列出角色已启用的 skills"""
        skills_dir = self._work_root / "skills"
        if not skills_dir.exists():
            return []

        skills = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_json = skill_dir / "skill.json"
                if skill_json.exists():
                    data = json.loads(skill_json.read_text(encoding="utf-8"))
                    skills.append(SkillInfo(
                        id=data["id"],
                        name=data["name"],
                        description=data["description"]
                    ))
        return skills

    def add_skill(self, skill_id: str, global_skills_dir: Optional[Path] = None) -> None:
        """添加 skill，从全局 skill 库复制到 work_root/skills/

        Args:
            skill_id: skill 标识
            global_skills_dir: 全局 skill 库路径，默认为 local_data/skills

        Raises:
            SkillAlreadyExistsError: skill 已存在于角色中
            SkillNotFoundError: skill 在全局库中不存在
        """
        target_dir = self._work_root / "skills" / skill_id
        if target_dir.exists():
            raise SkillAlreadyExistsError(f"Skill '{skill_id}' already exists in role")

        if global_skills_dir is None:
            global_skills_dir = self.role_dir.parent.parent / "skills"

        global_skill_dir = global_skills_dir / skill_id
        if not global_skill_dir.exists():
            raise SkillNotFoundError(f"Skill '{skill_id}' not found in global skill library")

        shutil.copytree(global_skill_dir, target_dir)

        # 更新 role.json
        data = self._read_role_json()
        if "skills" not in data:
            data["skills"] = []
        data["skills"].append(skill_id)
        self._write_role_json(data)

    def remove_skill(self, skill_id: str) -> None:
        """移除 skill，从 work_root/skills/ 删除

        Args:
            skill_id: skill 标识

        Raises:
            SkillNotFoundError: skill 不存在于角色中
        """
        skill_dir = self._work_root / "skills" / skill_id
        if not skill_dir.exists():
            raise SkillNotFoundError(f"Skill '{skill_id}' not found in role")

        shutil.rmtree(skill_dir)

        # 更新 role.json
        data = self._read_role_json()
        if "skills" in data and skill_id in data["skills"]:
            data["skills"].remove(skill_id)
            self._write_role_json(data)

    def get_permissions_config(self) -> Dict[str, Any]:
        """读取平台特定的权限配置，返回原始字典

        Returns:
            权限配置字典，如果配置文件不存在则返回空字典
        """
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])

        if platform == AgentPlatform.CLAUDE:
            settings_path = self._work_root / "settings.json"
        else:
            settings_path = self._work_root / "config.toml"

        if not settings_path.exists():
            return {}

        if platform == AgentPlatform.CLAUDE:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            # Codex 使用 TOML，这里简化处理
            return {}

    def update_permissions_config(self, config: Dict[str, Any]) -> None:
        """更新平台特定的权限配置

        Args:
            config: 新的权限配置字典
        """
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])

        if platform == AgentPlatform.CLAUDE:
            settings_path = self._work_root / "settings.json"
            settings_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        else:
            # Codex 使用 TOML，这里简化处理
            pass

    def get_role_config(self) -> RoleConfig:
        """构造给 agent_bridge 使用的 RoleConfig

        Returns:
            RoleConfig 实例，包含平台类型和对应的配置目录路径
        """
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])

        return RoleConfig(
            platform=platform,
            codex_home=str(self._work_root) if platform == AgentPlatform.CODEX else None,
            claude_config_dir=str(self._work_root) if platform == AgentPlatform.CLAUDE else None
        )
