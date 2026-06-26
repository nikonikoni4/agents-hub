from dataclasses import dataclass


@dataclass
class FeishuConfig:
    """飞书 Channel 配置

    Attributes:
        app_id: 飞书开放平台应用 ID
        app_secret: 飞书开放平台应用 Secret
        encrypt_key: 事件加密密钥（可选）
        verification_token: 验证 token（可选）
        group_policy: 群聊响应策略，"open" 响应所有消息 / "mention" 只响应 @bot
        domain: 飞书域名，"feishu" 国内版 / "lark" 国际版
    """

    app_id: str
    app_secret: str
    encrypt_key: str = ""
    verification_token: str = ""
    group_policy: str = "mention"
    domain: str = "feishu"
