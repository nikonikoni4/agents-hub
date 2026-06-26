from agents_hub.exceptions import ExternalServiceError


class FeishuError(ExternalServiceError):
    """飞书 Channel 基础异常"""

    pass


class FeishuAuthError(FeishuError):
    """飞书认证异常（app_id/app_secret 无效、token 过期）"""

    pass


class FeishuAPIError(FeishuError):
    """飞书 API 调用异常"""

    pass


class FeishuConnectionError(FeishuError):
    """飞书 WebSocket 连接异常"""

    pass
