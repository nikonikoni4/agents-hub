"""配置 API 路由"""

from fastapi import APIRouter, Depends

from agents_hub.api.schemas.config import ConfigInfo, ConfigUpdate
from agents_hub.api.services.config_service import ConfigService

router = APIRouter(prefix="/config", tags=["config"])


def get_config_service() -> ConfigService:
    """获取 ConfigService 实例（依赖注入）"""
    return ConfigService()


@router.get("", response_model=ConfigInfo)
async def get_config(service: ConfigService = Depends(get_config_service)):
    """获取当前系统配置"""
    return service.get_config()


@router.put("", response_model=ConfigInfo)
async def update_config(
    request: ConfigUpdate,
    service: ConfigService = Depends(get_config_service),
):
    """修改系统配置（部分更新）"""
    return await service.update_config(request)
