"""
GroupChatService 业务编排层

协调 GroupChatManager、Team、RoleManager，提供群聊生命周期管理和查询接口
"""

from agents_hub.api.schemas.group_chats import (
    GroupChatInfo,
)
from agents_hub.core.foundation import GroupChatType
from agents_hub.core.orchestration import GroupChat, GroupChatManager, Team
from agents_hub.core.utils.id_generator import generate_group_chat_id
from agents_hub.exceptions import (
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
