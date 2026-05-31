"""
Token 生成和剥离工具测试

契约驱动测试：
- generate_token(): 生成 tok_<32hex> 格式的 token
- redact_token(): 替换文本中的 token 为 [REDACTED]
"""

import re

from agents_hub.core.foundation.token import TOKEN_PATTERN, generate_token, redact_token


# ============================================================================
# generate_token() 测试
# ============================================================================


def test_generate_token_format() -> None:
    """
    契约：generate_token() 返回格式为 tok_<32位hex> 的字符串

    验证方式：
    1. 调用 generate_token()
    2. 验证以 "tok_" 开头
    3. 验证长度为 36（4 + 32）
    4. 验证格式匹配正则 ^tok_[a-f0-9]{32}$

    如果失败，说明：token 生成逻辑错误或格式变更
    """
    token = generate_token()
    assert token.startswith("tok_"), f"Token 应以 'tok_' 开头，实际: {token}"
    assert len(token) == 36, f"Token 长度应为 36，实际: {len(token)}"
    assert re.match(r"^tok_[a-f0-9]{32}$", token), f"Token 格式不匹配: {token}"


def test_generate_token_uniqueness() -> None:
    """
    契约：每次生成的 token 应该不同（100 次无重复）

    验证方式：
    1. 生成 100 个 token
    2. 转为 set 去重
    3. 验证 set 长度仍为 100

    如果失败，说明：随机数生成器有问题或 token 空间太小
    """
    tokens = [generate_token() for _ in range(100)]
    unique_tokens = set(tokens)
    assert len(unique_tokens) == 100, f"100 个 token 中有 {100 - len(unique_tokens)} 个重复"


# ============================================================================
# redact_token() 测试
# ============================================================================


def test_redact_token_single() -> None:
    """
    契约：redact_token() 替换单个 token 为 [REDACTED]

    验证方式：
    1. 准备包含单个 token 的文本
    2. 调用 redact_token()
    3. 验证 token 被替换为 [REDACTED]

    如果失败，说明：正则匹配或替换逻辑错误
    """
    text = "Your token is tok_a1b2c3d4e5f67890123456789012abcd here"
    result = redact_token(text)
    assert result == "Your token is [REDACTED] here", f"替换结果不正确: {result}"


def test_redact_token_multiple() -> None:
    """
    契约：redact_token() 替换多个 token 为 [REDACTED]

    验证方式：
    1. 准备包含两个 token 的文本
    2. 调用 redact_token()
    3. 验证两个 token 都被替换

    如果失败，说明：正则未使用全局匹配
    """
    text = "tok_a1b2c3d4e5f67890123456789012abcd and tok_b2c3d4e5f6a17890123456789012efab"
    result = redact_token(text)
    assert result == "[REDACTED] and [REDACTED]", f"多 token 替换结果不正确: {result}"


def test_redact_token_no_match() -> None:
    """
    契约：不匹配的文本保持不变

    验证方式：
    1. 准备格式错误的 token（太短或太长）
    2. 调用 redact_token()
    3. 验证文本保持不变

    如果失败，说明：正则匹配过于宽松
    """
    text = "No tokens here, just tok_short or tok_toolong123456789012345678901234567890"
    result = redact_token(text)
    assert result == text, f"不应修改的文本被修改了: {result}"


def test_redact_token_empty_string() -> None:
    """
    契约：空字符串返回空字符串

    验证方式：
    1. 调用 redact_token("")
    2. 验证返回 ""

    如果失败，说明：边界条件处理错误
    """
    result = redact_token("")
    assert result == "", f"空字符串应返回空字符串，实际: {result}"


# ============================================================================
# TOKEN_PATTERN 常量测试
# ============================================================================


def test_token_pattern_matches_valid_token() -> None:
    """
    契约：TOKEN_PATTERN 能匹配有效的 token 格式

    验证方式：
    1. 使用 generate_token() 生成一个 token
    2. 验证 TOKEN_PATTERN 能匹配它

    如果失败，说明：TOKEN_PATTERN 正则与 generate_token() 不一致
    """
    token = generate_token()
    assert TOKEN_PATTERN.fullmatch(token), f"TOKEN_PATTERN 无法匹配有效 token: {token}"


def test_token_pattern_rejects_invalid_format() -> None:
    """
    契约：TOKEN_PATTERN 拒绝无效格式

    验证方式：
    1. 测试太短的 token
    2. 测试太长的 token
    3. 测试包含非 hex 字符的 token

    如果失败，说明：正则过于宽松
    """
    assert not TOKEN_PATTERN.fullmatch("tok_abc"), "太短的 token 应被拒绝"
    assert not TOKEN_PATTERN.fullmatch("tok_" + "a" * 33), "太长的 token 应被拒绝"
    assert not TOKEN_PATTERN.fullmatch("tok_" + "g" * 32), "非 hex 字符应被拒绝"
