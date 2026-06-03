"""
ConfigService 业务编排层

管理系统配置的读取和修改。
"""

from pathlib import Path

from agents_hub.api.schemas.config import ConfigInfo, ConfigUpdate
from agents_hub.config import config
from agents_hub.core.foundation.exceptions import DockerNotAvailableError
from agents_hub.exceptions import ValidationError


class ConfigService:
    """系统配置服务层"""

    def get_config(self) -> ConfigInfo:
        """获取当前系统配置"""
        return ConfigInfo(
            data_path=str(config.data_path) if config.data_path else None,
            mcp_port=config.mcp_port,
            default_user_name=config.default_user_name,
            use_docker=config.use_docker,
            docker_image=config.docker_image,
        )

    async def update_config(self, update: ConfigUpdate) -> ConfigInfo:
        """修改系统配置（部分更新）

        修改 use_docker 时会检查 Docker Desktop 和镜像状态。

        Args:
            update: 要修改的配置字段

        Returns:
            ConfigInfo: 更新后的完整配置

        Raises:
            ValidationError: 无有效字段
            DockerNotAvailableError: Docker 未运行
            ExternalServiceError: 镜像构建失败
        """
        update_dict = update.model_dump(exclude_none=True)
        if not update_dict:
            raise ValidationError(
                "至少需要提供一个配置字段",
                details={"update": update.model_dump()},
            )

        # 如果修改 use_docker，先检查 Docker 环境
        if "use_docker" in update_dict and update_dict["use_docker"]:
            from agents_hub.agent_bridge.docker.manager import DockerManager

            docker_manager = DockerManager()
            try:
                await docker_manager.ensure_image_ready()
            except DockerNotAvailableError as e:
                raise DockerNotAvailableError(
                    agent_name="config",
                    group_chat_id="",
                    message="Docker 未启动，请先打开 Docker Desktop 并确保镜像已安装",
                ) from e

        # 逐字段更新
        if "data_path" in update_dict:
            config.set_data_path(Path(update_dict["data_path"]))

        if "mcp_port" in update_dict:
            config.mcp_port = update_dict["mcp_port"]

        if "default_user_name" in update_dict:
            config.default_user_name = update_dict["default_user_name"]

        if "use_docker" in update_dict:
            config.use_docker = update_dict["use_docker"]

        return self.get_config()
