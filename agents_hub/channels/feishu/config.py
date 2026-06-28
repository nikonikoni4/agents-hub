from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents_hub.config.config import SystemConfig


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
    bot_names: list[str] = field(default_factory=list)

    @classmethod
    def from_system_config(cls, system_config: SystemConfig) -> FeishuConfig:
        """从 SystemConfig 创建 FeishuConfig。

        Args:
            system_config: 系统配置实例

        Returns:
            FeishuConfig 实例
        """
        feishu_data = system_config.feishu_config
        return cls(
            app_id=feishu_data.get("app_id", ""),
            app_secret=feishu_data.get("app_secret", ""),
            encrypt_key=feishu_data.get("encrypt_key", ""),
            verification_token=feishu_data.get("verification_token", ""),
            group_policy=feishu_data.get("group_policy", "mention"),
            domain=feishu_data.get("domain", "feishu"),
            bot_names=feishu_data.get("bot_names", []),
        )
