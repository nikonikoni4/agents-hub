# tests/core/foundation/test_token.py
import re

from agents_hub.core.foundation.token import generate_token, redact_token


def test_generate_token_format() -> None:
    """Token 格式应为 tok_<32位hex>"""
    token = generate_token()
    assert token.startswith("tok_")
    assert len(token) == 36  # "tok_" (4) + 32 hex
    assert re.match(r"^tok_[a-f0-9]{32}$", token)


def test_generate_token_uniqueness() -> None:
    """每次生成的 token 应该不同"""
    tokens = [generate_token() for _ in range(100)]
    assert len(set(tokens)) == 100


def test_redact_token_single() -> None:
    """应该替换单个 token"""
    text = "Your token is tok_a1b2c3d4e5f67890123456789012abcd here"
    result = redact_token(text)
    assert result == "Your token is [REDACTED] here"


def test_redact_token_multiple() -> None:
    """应该替换多个 token"""
    text = "tok_a1b2c3d4e5f67890123456789012abcd and tok_b2c3d4e5f6a17890123456789012efab"
    result = redact_token(text)
    assert result == "[REDACTED] and [REDACTED]"


def test_redact_token_no_match() -> None:
    """不匹配的文本应该保持不变"""
    text = "No tokens here, just tok_short or tok_toolong123456789012345678901234567890"
    result = redact_token(text)
    assert result == text
