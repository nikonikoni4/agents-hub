"""团队管理器"""

import json
import threading

from agents_hub.config import config
from agents_hub.roles import RoleManager
from agents_hub.teams.exceptions import (
    EmptyTeamMembersError,
    InvalidTeamMembersError,
    TeamAlreadyExistsError,
    TeamNotFoundError,
)
from agents_hub.teams.models import TeamInfo


class TeamManager:
    """团队管理器

    职责：
    1. 团队的 CRUD 操作
    2. teams.json 的读写和并发控制
    3. 成员验证（调用 RoleManager 验证 role 是否存在）
    """

    def __init__(self):
        self.teams_file = config.data_path / "teams" / "teams.json"
        self._lock = threading.Lock()
        self.role_manager = RoleManager()

    def create_team(self, name: str, members: list[str]) -> TeamInfo:
        """创建团队

        Args:
            name: 团队名称
            members: 成员角色名称列表

        Returns:
            创建的团队信息

        Raises:
            EmptyTeamMembersError: 成员列表为空
            InvalidTeamMembersError: 成员包含不存在的角色
            TeamAlreadyExistsError: 团队名称已存在
        """
        # 验证成员列表
        self._validate_members(members)

        with self._lock:
            # 确保目录和文件存在
            self._ensure_teams_file()

            # 加载现有团队
            teams = self._load_teams()

            # 检查名称是否已存在
            if any(t["name"] == name for t in teams):
                raise TeamAlreadyExistsError(name)

            # 添加新团队
            team_data = {"name": name, "members": members}
            teams.append(team_data)

            # 保存
            self._save_teams(teams)

            return TeamInfo(name=name, members=members)

    def get_team(self, name: str) -> TeamInfo:
        """获取团队

        Args:
            name: 团队名称

        Returns:
            团队信息

        Raises:
            TeamNotFoundError: 团队不存在
        """
        with self._lock:
            self._ensure_teams_file()
            teams = self._load_teams()

            for team in teams:
                if team["name"] == name:
                    return TeamInfo(**team)

            available_teams = [t["name"] for t in teams]
            raise TeamNotFoundError(name, available_teams)

    def list_teams(self) -> list[TeamInfo]:
        """列出所有团队

        Returns:
            团队列表
        """
        with self._lock:
            self._ensure_teams_file()
            teams = self._load_teams()
            return [TeamInfo(**t) for t in teams]

    def update_team(
        self, name: str, new_name: str | None, new_members: list[str] | None
    ) -> TeamInfo:
        """更新团队

        Args:
            name: 团队名称
            new_name: 新的团队名称，为 None 时保持原名称
            new_members: 新的成员列表，为 None 时保持原成员列表

        Returns:
            更新后的团队信息

        Raises:
            TeamNotFoundError: 团队不存在
            TeamAlreadyExistsError: 新名称与其他团队冲突
            InvalidTeamMembersError: 成员包含不存在的角色
            EmptyTeamMembersError: 成员列表为空
        """
        # 如果要更新成员，先验证
        if new_members is not None:
            self._validate_members(new_members)

        with self._lock:
            self._ensure_teams_file()
            teams = self._load_teams()

            # 查找目标团队
            target_index = None
            for i, team in enumerate(teams):
                if team["name"] == name:
                    target_index = i
                    break

            if target_index is None:
                available_teams = [t["name"] for t in teams]
                raise TeamNotFoundError(name, available_teams)

            # 如果要更新名称，检查冲突
            if new_name is not None and new_name != name:
                for i, team in enumerate(teams):
                    if i != target_index and team["name"] == new_name:
                        raise TeamAlreadyExistsError(new_name)

            # 更新团队数据
            updated_name = new_name if new_name is not None else name
            updated_members = (
                new_members if new_members is not None else teams[target_index]["members"]
            )

            teams[target_index] = {"name": updated_name, "members": updated_members}

            # 保存
            self._save_teams(teams)

            return TeamInfo(name=updated_name, members=updated_members)

    def delete_team(self, name: str) -> None:
        """删除团队

        Args:
            name: 团队名称

        Raises:
            TeamNotFoundError: 团队不存在
        """
        with self._lock:
            self._ensure_teams_file()
            teams = self._load_teams()

            # 查找目标团队
            target_index = None
            for i, team in enumerate(teams):
                if team["name"] == name:
                    target_index = i
                    break

            if target_index is None:
                available_teams = [t["name"] for t in teams]
                raise TeamNotFoundError(name, available_teams)

            # 删除团队
            teams.pop(target_index)

            # 保存
            self._save_teams(teams)

    def _validate_members(self, members: list[str]) -> None:
        """验证成员列表

        Args:
            members: 成员角色名称列表

        Raises:
            EmptyTeamMembersError: 成员列表为空
            InvalidTeamMembersError: 成员包含不存在的角色
        """
        if not members:
            raise EmptyTeamMembersError()

        available_roles = self.role_manager.list_role_names()
        invalid_members = [m for m in members if m not in available_roles]

        if invalid_members:
            raise InvalidTeamMembersError(invalid_members, available_roles)

    def _ensure_teams_file(self) -> None:
        """确保 teams 目录和文件存在"""
        self.teams_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.teams_file.exists():
            self._save_teams([])

    def _load_teams(self) -> list[dict]:
        """从 JSON 加载团队列表"""
        with open(self.teams_file, encoding="utf-8") as f:
            return json.load(f)

    def _save_teams(self, teams: list[dict]) -> None:
        """保存团队列表到 JSON"""
        with open(self.teams_file, "w", encoding="utf-8") as f:
            json.dump(teams, f, indent=2, ensure_ascii=False)
