"""团队管理器"""

import json
import threading

from agents_hub.config import config
from agents_hub.roles import RoleManager
from agents_hub.teams.exceptions import (
    EmptyTeamMembersError,
    InvalidTeamMembersError,
    TeamAlreadyExistsError,
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
