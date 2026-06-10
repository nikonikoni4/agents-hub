from agents_hub.exceptions import ExternalServiceError


class WechatError(ExternalServiceError):
    """微信 Channel 基础异常"""
    pass


class WechatAuthError(WechatError):
    """微信认证异常（QR 登录、token 管理）"""
    pass


class WechatAPIError(WechatError):
    """微信 API 调用异常"""
    pass
