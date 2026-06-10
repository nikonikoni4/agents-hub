from dataclasses import dataclass, field


@dataclass
class WechatConfig:
    """微信 channel 配置

    Attributes:
        base_url: 微信 ilinkai API 基础 URL
        poll_timeout: 长轮询超时时间（秒）
        allow_from: 允许接收消息的用户列表，["*"] 允许所有，空列表拒绝所有
        reply_text: 自动回复内容
    """

    base_url: str = "https://ilinkai.weixin.qq.com"
    poll_timeout: int = 35
    allow_from: list[str] = field(default_factory=list)
    reply_text: str = "你好"
