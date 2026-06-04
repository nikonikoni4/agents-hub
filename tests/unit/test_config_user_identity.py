"""Config user identity helpers tests."""

from agents_hub.config.config import Config, SystemConfig


def _reset_config_singletons():
    Config._instance = None
    SystemConfig._instance = None


def test_default_user_name_appends_user_suffix(monkeypatch, tmp_path):
    """Contract: custom user display names are marked with a user suffix."""
    monkeypatch.chdir(tmp_path)
    _reset_config_singletons()

    config = Config()
    config.default_user_name = "Alice"

    assert config.default_user_name == "Alice(user)"


def test_normalize_user_name_removes_user_suffix(monkeypatch, tmp_path):
    """Contract: user display suffix is removed for canonical identity checks."""
    monkeypatch.chdir(tmp_path)
    _reset_config_singletons()

    config = Config()

    assert config.normalize_user_name("Alice(user)") == "Alice"
    assert config.normalize_user_name("Alice (user)") == "Alice"
    assert config.normalize_user_name("  Alice(user)  ") == "Alice"


def test_is_user_name_accepts_configured_name_and_canonical_user(monkeypatch, tmp_path):
    """Contract: user checks accept the configured display name and canonical user aliases."""
    monkeypatch.chdir(tmp_path)
    _reset_config_singletons()

    config = Config()
    config.default_user_name = "Alice"

    assert config.is_user_name("Alice(user)")
    assert config.is_user_name("Alice")
    assert config.is_user_name("user")
    assert not config.is_user_name("worker")
