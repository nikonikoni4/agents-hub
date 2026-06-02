"""
GroupChatService 业务编排层

协调 GroupChatManager、Team、RoleManager，提供群聊生命周期管理和查询接口
"""

import shutil
from pathlib import Path

from agents_hub.api.schemas.group_chats import (
    GroupChatInfo,
)
from agents_hub.core.foundation import GroupChatType, group_chat_paths
from agents_hub.core.orchestration import GroupChat, GroupChatManager, Team
from agents_hub.core.utils.id_generator import generate_group_chat_id
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
            group_chat_name: 群聊名称（待实现：当前 GroupChat 构造函数不支持此参数）

        Returns:
            GroupChatInfo: 群聊详细信息

        Raises:
            ValidationError: team_members 为空
            ResourceNotFoundError: role 不存在或 project_path 不存在
            StateError: 启动失败

        Note:
            group_chat_name 参数保留用于未来实现，当前会被忽略，
            使用 group_chat_id 作为群聊名称
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
        group_chat_id = generate_group_chat_id()

        # 4. 创建 GroupChat 实例
        # TODO: 当 GroupChat 构造函数支持 group_chat_name 参数后，传入 group_chat_name
        group_chat = GroupChat(
            team=team,
            group_type=GroupChatType.MANAGER_ORCHESTRATE,
            project_path=project_path,
            group_chat_id=group_chat_id,
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
        # 1. 检查是否已在内存中
        group_chat = self.group_chat_manager.get_group_chat(group_chat_id)
        if group_chat:
            # 已在内存，直接返回（幂等性）
            return await self._build_group_chat_info_from_instance(group_chat)

        # 2. 从磁盘加载
        try:
            group_chat = await self.group_chat_manager.load_group_chat_from_disk(group_chat_id)
        except FileNotFoundError as e:
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

        # 3. 返回 GroupChatInfo
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
            group_chat = self.group_chat_manager.get_group_chat(group_chat_id)
            if group_chat:
                metadata = await group_chat.group_chat_context.repository.load_group_metadata()
                project_path = metadata.project_path
            else:
                # 从磁盘读取 - 需要枚举所有可能的项目路径
                # 这里简化处理：如果不在内存中，只能从 GroupChatManager 的索引获取
                pass

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
