"""
GroupChatService 业务编排层

协调 GroupChatManager、Team、RoleManager，提供群聊生命周期管理和查询接口。

职责边界：
- 本层负责 参数校验 → 组装领域对象 → 调用核心层 → 转换为 API Schema 返回
- 不持有任何运行时状态，所有状态由 GroupChatManager（内存）和磁盘（JSON 文件）管理
- 异常统一转换为 exceptions 模块中的 API 异常，对上层屏蔽核心层细节
"""

import shutil
from pathlib import Path
from uuid import uuid4

from agents_hub.api.schemas.group_chats import (
    GroupChatInfo,
    GroupChatMember,
    GroupChatSummary,
    MessageInfo,
)
from agents_hub.config import config
from agents_hub.core.context.group_metadata import GroupMetadata
from agents_hub.core.foundation import (
    AgentMessage,
    GroupChatNotFoundError,
    GroupChatType,
    MessageType,
    group_chat_paths,
)
from agents_hub.core.foundation.exceptions import DockerNotAvailableError
from agents_hub.core.orchestration import GroupChat, GroupChatManager, Team
from agents_hub.exceptions import (
    ExternalServiceError,
    ResourceNotFoundError,
    StateError,
    ValidationError,
)


class GroupChatService:
    """群聊应用服务层

    轻量业务编排层，不持有状态，所有状态在 GroupChatManager 中。
    生命周期：create → (内存+磁盘) → get/list/load → (内存) → delete → (可选保留磁盘)
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
            GroupChatInfo（群聊完整信息）:
                - group_chat_id: str, 群聊唯一标识（UUID）
                - group_chat_name: str | None, 群聊显示名称
                - project_path: str, 关联的项目路径
                - created_at: datetime, 创建时间
                - group_type: GroupChatType, 编排模式
                    · MANAGER_ORCHESTRATE — 管理者动态分配任务
                    · SEQUENCE_EXECUTE — 流水线顺序执行
                - is_active: bool, agent 是否已激活（run() 任务是否在运行）

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
            GroupChatInfo: 字段同 create_group_chat（group_chat_id, group_chat_name,
                project_path, created_at, group_type, is_active）

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

        # 1. 如果 keep_data=False，先读取 project_path（在 unregister 之前）
        if not keep_data:
            # 尝试从内存中的 GroupChat 实例读取
            group_chat = self.group_chat_manager._group_chats.get(group_chat_id)
            if group_chat:
                project_path = group_chat.runtime.get_project_path()
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
            list[GroupChatSummary]（群聊摘要，用于列表页）:
                - group_chat_id: str, 群聊唯一标识
                - group_chat_name: str | None, 群聊显示名称
                - project_path: str, 关联的项目路径
                - is_active: bool, agent 是否已激活（run() 任务是否在运行）
                - created_at: datetime, 创建时间
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
            GroupChatInfo: 字段同 create_group_chat（group_chat_id, group_chat_name,
                project_path, created_at, group_type, is_active）

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

        info = group_chat.runtime.get_info_dict(
            is_active=self.group_chat_manager.is_active_group(group_chat_id)
        )
        return GroupChatInfo(**info)

    async def get_group_chat_members(self, group_chat_id: str) -> list[GroupChatMember]:
        """获取群聊成员列表

        Args:
            group_chat_id: 群聊 ID

        Returns:
            list[GroupChatMember]（群聊成员，从 agent_member.json 读取）:
                - name: str, 角色名称（如 "pm", "architect"）
                - main_session: str | None, 主会话 ID
                - btw_session: list[str], 额外的临时会话 ID 列表
                - cwd: str | None, 该成员的工作目录
                - use_docker: bool, 是否使用 Docker 隔离运行（默认 False）

        Raises:
            ResourceNotFoundError: 群聊不存在或 session_state 文件不存在
            StateError: JSON 格式错误或数据损坏
        """
        try:
            group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
        except GroupChatNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e

        return [GroupChatMember(**member) for member in group_chat.runtime.get_member_dicts()]

    async def get_messages(
        self,
        group_chat_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[MessageInfo]:
        """获取群聊消息历史

        Args:
            group_chat_id: 群聊 ID
            limit: 返回消息数量上限（默认 50）
            offset: 跳过前 N 条消息（默认 0）

        Returns:
            list[MessageInfo]（消息列表）:
                - speaker: str, 发送者名称（agent 角色名或 "user"）
                - content: str, 消息内容
                - timestamp: str, 时间戳
                - platform: str, 来源平台

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

        return [
            MessageInfo(**message)
            for message in group_chat.runtime.get_message_dicts(limit=limit, offset=offset)
        ]

    async def send_message(
        self,
        group_chat_id: str,
        content: str,
        send_to: str,
    ) -> None:
        """向群聊发送消息

        Args:
            group_chat_id: 群聊 ID
            content: 消息内容
            send_to: 目标角色名

        Raises:
            ResourceNotFoundError: 群聊不存在
            ValidationError: send_to 不是群成员，或 content 中包含 @
        """
        # 1. content 中不能有 @
        if "@" in content:
            raise ValidationError(
                "消息内容中不能包含 @ 符号",
                details={"content": content},
            )

        # 2. 激活群聊（懒加载）
        try:
            await self.group_chat_manager.activate_group_chat(group_chat_id)
        except GroupChatNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e

        # 3. 获取 GroupChat 实例并校验 send_to 是群聊成员
        group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
        members = list(group_chat.team_members_name)
        if group_chat.manager:
            members.append(group_chat.manager.name)
        if send_to not in members:
            raise ValidationError(
                f"目标角色 '{send_to}' 不是群聊成员",
                details={"send_to": send_to, "available_members": members},
            )

        # 4. 创建 AgentCall
        call = group_chat.agent_call_manager.create_call(
            send_from=config.default_user_name,
            send_to=send_to,
            content=content,
            message_type=MessageType.TASK,
        )

        # 5. 构建并发送 AgentMessage
        message = AgentMessage(
            call_id=call.call_id,
            content=content,
            send_from=config.default_user_name,
            send_to=send_to,
            message_type=MessageType.TASK,
        )
        group_chat.message_router.send_message(message)

    async def toggle_use_docker(
        self,
        group_chat_id: str,
        role_name: str,
        use_docker: bool,
    ) -> GroupChatMember:
        """切换指定成员的 Docker 沙箱开关

        流程：验证 role_name 存在 → 检查 Docker+镜像 → 更新内存 → 持久化

        Args:
            group_chat_id: 群聊 ID
            role_name: 角色名称
            use_docker: 是否启用 Docker 沙箱

        Returns:
            GroupChatMember: 更新后的成员信息

        Raises:
            ResourceNotFoundError: 群聊或角色不存在
            DockerNotAvailableError: Docker 未运行或镜像不存在
            ExternalServiceError: 镜像构建失败
        """
        # 1. 加载群聊，获取 group_chat 实例
        try:
            group_chat = await self.group_chat_manager.load_group_chat(group_chat_id)
        except GroupChatNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e

        # 2. 验证 role_name 是群聊成员
        all_members = list(group_chat.team_members_name)
        if group_chat.manager:
            all_members.append(group_chat.manager.name)
        if role_name not in all_members:
            raise ResourceNotFoundError(
                f"角色 '{role_name}' 不是群聊 '{group_chat_id}' 的成员",
                details={
                    "role_name": role_name,
                    "available_members": all_members,
                },
            )

        # 3. 如果开启 Docker，先检查全局开关
        if use_docker and not config.use_docker:
            raise ValidationError(
                "全局 Docker 功能已禁用，请先在系统配置中启用 use_docker",
                details={"config_use_docker": config.use_docker},
            )

        # 4. 如果开启 Docker，检查 Docker Desktop 和镜像
        if use_docker:
            from agents_hub.agent_bridge.docker.manager import DockerManager

            docker_manager = DockerManager()
            try:
                await docker_manager.ensure_image_ready()
            except DockerNotAvailableError as e:
                raise DockerNotAvailableError(
                    agent_name=role_name,
                    group_chat_id=group_chat_id,
                    message="Docker 未启动，请先打开 Docker Desktop 并确保镜像已安装",
                ) from e

        # 5. 使用 runtime 命令更新 use_docker
        updated_info = await group_chat.runtime.set_agent_use_docker(role_name, use_docker)
        return GroupChatMember(
            name=role_name,
            main_session=updated_info.main_session or None,
            btw_session=updated_info.btw_session,
            cwd=updated_info.cwd or None,
            use_docker=updated_info.use_docker,
        )

    async def _build_group_chat_info_from_instance(self, group_chat: GroupChat) -> GroupChatInfo:
        """从内存中的 GroupChat 实例构建 GroupChatInfo"""
        info = group_chat.runtime.get_info_dict(is_active=group_chat._activated)
        return GroupChatInfo(**info)
