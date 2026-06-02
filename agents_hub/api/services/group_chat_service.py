"""
GroupChatService 业务编排层

协调 GroupChatManager、Team、RoleManager，提供群聊生命周期管理和查询接口
"""

import json
import shutil
from pathlib import Path
from uuid import uuid4

from agents_hub.api.schemas.group_chats import (
    GroupChatInfo,
    GroupChatMember,
    GroupChatSummary,
)
from agents_hub.core.context.group_metadata import GroupMetadata
from agents_hub.core.foundation import GroupChatNotFoundError, GroupChatType, group_chat_paths
from agents_hub.core.orchestration import GroupChat, GroupChatManager, Team
from agents_hub.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
    StateError,
    ValidationError,
)


class GroupChatService:
    """群聊应用服务层

    轻量业务编排层，不持有状态，所有状态在 GroupChatManager 中
    """

    def __init__(self, group_chat_manager: GroupChatManager):
        """
        Args:
            group_chat_manager: 全局单例 GroupChatManager（依赖注入）
        """
        self.group_chat_manager = group_chat_manager

    async def create_group_chat(
        self,
        team_members: list[str],
        project_path: str,
        group_chat_name: str | None = None,
    ) -> GroupChatInfo:
        """创建并启动新群聊

        Args:
            team_members: 团队成员角色名列表
            project_path: 项目路径
            group_chat_name: 群聊名称（可选，默认使用 group_chat_id）

        Returns:
            GroupChatInfo: 群聊详细信息

        Raises:
            ValidationError: team_members 为空
            ResourceNotFoundError: role 不存在或 project_path 不存在
            StateError: 启动失败
        """
        # 1. 验证 team_members 非空
        if not team_members:
            raise ValidationError(
                "team_members 不能为空",
                details={"team_members": team_members},
            )

        # 2. 创建 Team 对象（验证 roles 存在）
        try:
            team = Team(team_members_name=team_members, team_name="default_team")
        except ValueError as e:
            raise ResourceNotFoundError(
                str(e),
                details={"team_members": team_members},
            ) from e

        # 3. 生成 group_chat_id
        group_chat_id = str(uuid4())

        # 4. 创建 GroupChat 实例
        group_chat = GroupChat(
            team=team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=project_path,
            group_chat_id=group_chat_id,
            group_chat_name=group_chat_name,
        )

        # 5. 调用 GroupChat.start()
        try:
            await group_chat.start()
        except Exception as e:
            raise StateError(
                f"群聊启动失败: {e}",
                details={
                    "group_chat_id": group_chat_id,
                    "project_path": project_path,
                },
            ) from e

        # 6. 注册到 GroupChatManager
        self.group_chat_manager.register(group_chat_id, group_chat)

        # 7. 返回 GroupChatInfo
        return await self._build_group_chat_info_from_instance(group_chat)

    async def load_group_chat(self, group_chat_id: str) -> GroupChatInfo:
        """加载群聊（从内存或磁盘）

        Args:
            group_chat_id: 群聊 ID

        Returns:
            GroupChatInfo: 群聊详细信息

        Raises:
            ResourceNotFoundError: 群聊不存在或 role 已被删除
            StateError: 加载失败
        """
        try:
            group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
        except GroupChatNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e
        except ValueError as e:
            # Team 验证失败（role 已被删除）
            raise ResourceNotFoundError(
                f"群聊加载失败，role 不存在: {e}",
                details={"group_chat_id": group_chat_id},
            ) from e
        except Exception as e:
            raise StateError(
                f"群聊加载失败: {e}",
                details={"group_chat_id": group_chat_id},
            ) from e

        return await self._build_group_chat_info_from_instance(group_chat)

    async def delete_group_chat(self, group_chat_id: str, keep_data: bool = False) -> None:
        """删除群聊

        Args:
            group_chat_id: 群聊 ID
            keep_data: True=仅从内存移除，False=完全删除（内存+磁盘）

        Raises:
            ResourceNotFoundError: 群聊不存在（仅当 keep_data=False 且磁盘也不存在时）
            ExternalServiceError: 文件删除失败
        """
        project_path = None

        # 1. 如果 keep_data=False，先读取 metadata（在 unregister 之前）
        if not keep_data:
            # 尝试从内存中的 GroupChat 实例读取
            group_chat = self.group_chat_manager._group_chats.get(group_chat_id)
            if group_chat:
                metadata = await group_chat.group_chat_context.repository.load_group_metadata()
                project_path = metadata.project_path
            else:
                # 从磁盘读取 - 通过 list_all_group_chats 查找
                all_chats = self.group_chat_manager.list_all_group_chats()
                for metadata_dict in all_chats:
                    if metadata_dict["group_chat_id"] == group_chat_id:
                        project_path = metadata_dict["project_path"]
                        break

        # 2. 从内存中移除
        await self.group_chat_manager.unregister(group_chat_id)

        # 3. 如果 keep_data=False 且有 project_path，删除磁盘数据
        if not keep_data and project_path:
            try:
                group_chat_dir = Path(group_chat_paths.base_dir(group_chat_id, project_path))
                if group_chat_dir.exists():
                    shutil.rmtree(group_chat_dir)
            except (PermissionError, OSError) as e:
                raise ExternalServiceError(
                    f"文件删除失败: {e}",
                    details={
                        "group_chat_id": group_chat_id,
                        "group_chat_dir": str(group_chat_dir),
                    },
                ) from e

    async def list_group_chats(self, is_active_only: bool = False) -> list[GroupChatSummary]:
        """列出所有群聊

        Args:
            is_active_only: True=只返回活跃群聊，False=返回所有群聊

        Returns:
            list[GroupChatSummary]: 群聊摘要列表
        """
        # 1. 调用 GroupChatManager.list_all_group_chats()
        all_metadata = self.group_chat_manager.list_all_group_chats()

        # 2. 转换为 GroupChatSummary 列表
        summaries: list[GroupChatSummary] = []
        for metadata_dict in all_metadata:
            # 转换为 GroupMetadata 对象
            metadata = GroupMetadata(**metadata_dict)

            # 检查是否在内存中（活跃状态）
            is_active = self.group_chat_manager.is_active_group(metadata.group_chat_id)

            # 3. 如果 is_active_only=True，过滤出活跃的
            if is_active_only and not is_active:
                continue

            summaries.append(
                GroupChatSummary(
                    group_chat_id=metadata.group_chat_id,
                    group_chat_name=metadata.group_chat_name,
                    project_path=metadata.project_path,
                    is_active=is_active,
                    created_at=metadata.created_at,
                )
            )

        return summaries

    async def get_group_chat_info(self, group_chat_id: str) -> GroupChatInfo:
        """获取群聊详细信息

        Args:
            group_chat_id: 群聊 ID

        Returns:
            GroupChatInfo: 群聊详细信息

        Raises:
            ResourceNotFoundError: 群聊不存在
        """
        try:
            group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
        except GroupChatNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e

        is_active = self.group_chat_manager.is_active_group(group_chat_id)
        metadata = await group_chat.group_chat_context.repository.load_group_metadata()
        return GroupChatInfo(
            group_chat_id=metadata.group_chat_id,
            group_chat_name=metadata.group_chat_name,
            project_path=metadata.project_path,
            created_at=metadata.created_at,
            group_type=metadata.group_type,
            is_active=is_active,
        )

    async def get_group_chat_members(self, group_chat_id: str) -> list[GroupChatMember]:
        """获取群聊成员列表

        Args:
            group_chat_id: 群聊 ID

        Returns:
            list[GroupChatMember]: 成员列表

        Raises:
            ResourceNotFoundError: 群聊不存在或 session_state 文件不存在
            StateError: JSON 格式错误或数据损坏
        """
        # 1. 读取 metadata 获取 project_path
        try:
            group_chat = await self.group_chat_manager.load_group_chat_from_disk(group_chat_id)
            metadata = await group_chat.group_chat_context.repository.load_group_metadata()
            project_path = metadata.project_path
        except FileNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e

        # 2. 构建 agent_session_state.json 文件路径
        group_chat_dir = Path(group_chat_paths.base_dir(group_chat_id, project_path))
        session_state_file = group_chat_dir / "agent_session_state.json"

        # 3. 验证文件存在性
        if not session_state_file.exists():
            raise ResourceNotFoundError(
                f"session_state 文件不存在: {session_state_file}",
                details={
                    "group_chat_id": group_chat_id,
                    "session_state_file": str(session_state_file),
                },
            )

        # 4. 读取并解析 JSON（带异常捕获）
        try:
            with session_state_file.open("r", encoding="utf-8") as f:
                session_data = json.load(f)
        except json.JSONDecodeError as e:
            raise StateError(
                f"session_state JSON 格式错误: {e}",
                details={
                    "group_chat_id": group_chat_id,
                    "session_state_file": str(session_state_file),
                },
            ) from e

        # 5. 使用 Pydantic 模型验证并转换
        members: list[GroupChatMember] = []
        for agent_name, agent_data in session_data.items():
            member = GroupChatMember(
                name=agent_name,
                main_session=agent_data.get("main_session"),
                btw_session=agent_data.get("btw_session", []),
                cwd=agent_data.get("cwd"),
                use_docker=agent_data.get("use_docker", False),
            )
            members.append(member)

        return members

    async def _build_group_chat_info_from_instance(self, group_chat: GroupChat) -> GroupChatInfo:
        """从内存中的 GroupChat 实例构建 GroupChatInfo"""
        metadata = await group_chat.group_chat_context.repository.load_group_metadata()
        return GroupChatInfo(
            group_chat_id=metadata.group_chat_id,
            group_chat_name=metadata.group_chat_name,
            project_path=metadata.project_path,
            created_at=metadata.created_at,
            group_type=metadata.group_type,
            is_active=True,
        )
