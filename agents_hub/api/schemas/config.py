"""配置相关的 Pydantic Schema 定义"""

from pydantic import BaseModel, Field


class ConfigInfo(BaseModel):
    """系统配置信息"""

    data_path: str | None = Field(None, description="数据存储路径（None 表示使用默认路径）")
    mcp_port: int = Field(..., description="MCP 服务器运行端口")
    default_user_name: str = Field(..., description="默认用户身份名")
    use_docker: bool = Field(..., description="是否默认使用 Docker 沙箱执行")
    docker_image: str = Field(..., description="Docker 沙箱镜像名称")


class ConfigUpdate(BaseModel):
    """修改系统配置请求（部分更新）"""

    data_path: str | None = Field(None, description="数据存储路径")
    mcp_port: int | None = Field(None, ge=1, le=65535, description="MCP 服务器运行端口")
    default_user_name: str | None = Field(None, min_length=1, description="默认用户身份名")
    use_docker: bool | None = Field(None, description="是否默认使用 Docker 沙箱执行")
