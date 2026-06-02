"""Role 类 - 单个角色的配置管理。"""

import json
import shutil
from pathlib import Path
from typing import Any

from agents_hub.config.types import AgentPlatform
from agents_hub.roles.exceptions import SkillAlreadyExistsError, SkillNotFoundError
from agents_hub.roles.models import RoleConfig, RoleInfo, RoleType, SkillInfo


class Role:
    """单个角色的配置管理。

    管理 local_data/agents/<role_name>/ 下的角色配置，
    包括 role.json 元数据、work_root 工作目录和 skills 子目录。

    Attributes:
        role_dir: 角色目录的路径。
    """

    def __init__(self, role_dir: Path) -> None:
        """初始化 Role 实例。

        Args:
            role_dir: 角色目录路径 (local_data/agents/<role_name>)。
        """
        self.role_dir = role_dir

    @property
    def _role_json_path(self) -> Path:
        """获取 role.json 文件路径。

        Returns:
            role.json 文件的完整路径。
        """
        return self.role_dir / "role.json"

    @property
    def _work_root(self) -> Path:
        """获取 work_root 目录路径。

        Returns:
            work_root 目录的完整路径。
        """
        return self.role_dir / "work_root"

    def _read_role_json(self) -> dict[str, Any]:
        """读取 role.json 文件内容。

        Returns:
            role.json 的内容，解析为字典。

        Raises:
            FileNotFoundError: role.json 文件不存在。
            json.JSONDecodeError: role.json 文件格式错误。
        """
        return json.loads(self._role_json_path.read_text(encoding="utf-8"))

    def _write_role_json(self, data: dict[str, Any]) -> None:
        """写入 role.json 文件。

        Args:
            data: 要写入的数据字典。
        """
        self._role_json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_info(self) -> RoleInfo:
        """获取角色摘要信息。

        从 role.json 读取角色数据并返回 RoleInfo 实例。
        type 字段会从字符串转换为 RoleType 枚举。

        Returns:
            角色摘要信息实例。
        """
        data = self._read_role_json()
        type_str = data.get("type")
        role_type = RoleType(type_str) if type_str else None
        return RoleInfo(
            name=data["name"],
            platform=AgentPlatform(data["platform"]),
            avatar=data.get("avatar"),
            abilities=data.get("abilities", []),
            type=role_type,
            description=data.get("description"),
            scope=data.get("scope"),
        )

    def update_name(self, new_name: str) -> None:
        """更新角色名称。

        同时修改 role.json 中的 name 字段和角色目录名。
        更新后 self.role_dir 会指向新目录。

        Args:
            new_name: 新的角色名称。
        """
        data = self._read_role_json()
        data["name"] = new_name
        self._write_role_json(data)

        new_dir = self.role_dir.parent / new_name
        self.role_dir.rename(new_dir)
        self.role_dir = new_dir

    def update_description(self, description: str) -> None:
        """更新角色职责描述。

        Args:
            description: 新的角色职责描述。
        """
        data = self._read_role_json()
        data["description"] = description
        self._write_role_json(data)

    def update_avatar(self, avatar_filename: str) -> None:
        """更新角色头像文件名引用。

        只更新 role.json 中的 avatar 字段，头像文件统一存放在 assets/ 目录。

        Args:
            avatar_filename: 头像文件名（位于 assets/ 目录下）。
        """
        data = self._read_role_json()
        data["avatar"] = avatar_filename
        self._write_role_json(data)

    def update_abilities(self, abilities: list[str]) -> None:
        """更新能力标签列表。

        Args:
            abilities: 新的能力标签列表。
        """
        data = self._read_role_json()
        data["abilities"] = abilities
        self._write_role_json(data)

    def list_skills(self) -> list[SkillInfo]:
        """列出角色已启用的 skills。

        扫描 work_root/skills/ 目录，读取每个 skill 的 skill.json 文件。

        Returns:
            SkillInfo 列表，如果没有 skill 则返回空列表。
        """
        skills_dir = self._work_root / "skills"
        if not skills_dir.exists():
            return []

        skills = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_json = skill_dir / "skill.json"
                if skill_json.exists():
                    data = json.loads(skill_json.read_text(encoding="utf-8"))
                    skills.append(
                        SkillInfo(id=data["id"], name=data["name"], description=data["description"])
                    )
        return skills

    def add_skill(self, skill_id: str, global_skills_dir: Path | None = None) -> None:
        """添加 skill 到角色。

        优先通过符号链接（symlink）将全局 skill 链接到角色的 work_root/skills/ 目录，
        链接失败时降级为复制目录。不修改 role.json。

        Args:
            skill_id: skill 的唯一标识符。
            global_skills_dir: 全局 skill 库路径，默认为 local_data/skills。

        Raises:
            SkillAlreadyExistsError: skill 已存在于角色中。
            SkillNotFoundError: skill 在全局库中不存在。
        """
        target_dir = self._work_root / "skills" / skill_id
        if target_dir.exists() or target_dir.is_symlink():
            role_name = self._read_role_json()["name"]
            raise SkillAlreadyExistsError(skill_id=skill_id, role_name=role_name)

        if global_skills_dir is None:
            global_skills_dir = self.role_dir.parent.parent / "skills"

        global_skill_dir = global_skills_dir / skill_id
        if not global_skill_dir.exists():
            raise SkillNotFoundError(skill_id=skill_id)

        try:
            target_dir.symlink_to(global_skill_dir, target_is_directory=True)
        except OSError:
            shutil.copytree(global_skill_dir, target_dir)

    def remove_skill(self, skill_id: str) -> None:
        """从角色中移除 skill。

        删除 work_root/skills/ 下的 skill 目录，
        不影响全局 skill。

        Args:
            skill_id: skill 的唯一标识符。

        Raises:
            SkillNotFoundError: skill 不存在于角色中。
        """
        skill_dir = self._work_root / "skills" / skill_id
        if not skill_dir.exists() and not skill_dir.is_symlink():
            raise SkillNotFoundError(skill_id=skill_id)

        if skill_dir.is_symlink():
            skill_dir.unlink()
        else:
            shutil.rmtree(skill_dir)

    def get_permissions_config(self) -> dict[str, Any]:
        """获取平台特定的权限配置。

        对于 Claude 平台，读取 work_root/settings.json；
        对于 Codex 平台，当前返回空字典（待实现）。

        Returns:
            权限配置字典，如果配置文件不存在则返回空字典。
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
            return {}

    def update_permissions_config(self, config: dict[str, Any]) -> None:
        """更新平台特定的权限配置。

        对于 Claude 平台，写入 work_root/settings.json；
        对于 Codex 平台，当前为空操作（待实现）。

        Args:
            config: 新的权限配置字典。
        """
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])

        if platform == AgentPlatform.CLAUDE:
            settings_path = self._work_root / "settings.json"
            settings_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            pass

    def get_role_config(self) -> RoleConfig:
        """构造给 agent_bridge 使用的 RoleConfig。

        根据角色的平台类型，设置对应的配置目录路径。

        Returns:
            RoleConfig 实例，包含角色名称、平台类型和配置目录路径。
        """
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])
        type_str = data.get("type")
        role_type = RoleType(type_str) if type_str else RoleType.TEAM_MEMBER
        return RoleConfig(
            name=data["name"],
            platform=platform,
            description=data.get("description"),
            work_root=str(self._work_root),
            role_type=role_type,
        )
