"""FeishuConfig 配置模型测试"""

from unittest.mock import MagicMock

from agents_hub.channels.feishu.config import FeishuConfig


def test_feishu_config_defaults():
    """测试默认配置值"""
    config = FeishuConfig(app_id="test_id", app_secret="test_secret")

    assert config.app_id == "test_id"
    assert config.app_secret == "test_secret"
    assert config.encrypt_key == ""
    assert config.verification_token == ""
    assert config.group_policy == "mention"
    assert config.domain == "feishu"


def test_feishu_config_custom_values():
    """测试自定义配置值"""
    config = FeishuConfig(
        app_id="cli_xxx",
        app_secret="secret_yyy",
        encrypt_key="enc_key",
        verification_token="verify_token",
        group_policy="open",
        domain="lark",
    )

    assert config.app_id == "cli_xxx"
    assert config.app_secret == "secret_yyy"
    assert config.encrypt_key == "enc_key"
    assert config.verification_token == "verify_token"
    assert config.group_policy == "open"
    assert config.domain == "lark"


def test_from_system_config_with_full_config():
    """测试从 SystemConfig 创建（完整配置）"""
    mock_system = MagicMock()
    mock_system.feishu_config = {
        "app_id": "cli_test",
        "app_secret": "secret_test",
        "encrypt_key": "enc_key",
        "verification_token": "verify_token",
        "group_policy": "open",
        "domain": "lark",
    }

    config = FeishuConfig.from_system_config(mock_system)

    assert config.app_id == "cli_test"
    assert config.app_secret == "secret_test"
    assert config.encrypt_key == "enc_key"
    assert config.verification_token == "verify_token"
    assert config.group_policy == "open"
    assert config.domain == "lark"


def test_from_system_config_with_minimal_config():
    """测试从 SystemConfig 创建（最小配置，使用默认值）"""
    mock_system = MagicMock()
    mock_system.feishu_config = {
        "app_id": "cli_test",
        "app_secret": "secret_test",
    }

    config = FeishuConfig.from_system_config(mock_system)

    assert config.app_id == "cli_test"
    assert config.app_secret == "secret_test"
    assert config.encrypt_key == ""
    assert config.verification_token == ""
    assert config.group_policy == "mention"
    assert config.domain == "feishu"


def test_from_system_config_with_empty_config():
    """测试从 SystemConfig 创建（空配置）"""
    mock_system = MagicMock()
    mock_system.feishu_config = {}

    config = FeishuConfig.from_system_config(mock_system)

    assert config.app_id == ""
    assert config.app_secret == ""
