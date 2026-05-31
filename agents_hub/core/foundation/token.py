"""Token 生成和剥离工具

用于 Agent Token 身份模型：
- generate_token(): 生成 32 字符 hex token
- redact_token(): 从文本中剥离 token（替换为 [REDACTED]）
"""

import re
import secrets

# Token 格式：tok_<32位hex>
TOKEN_PATTERN = re.compile(r"tok_[a-f0-9]{32}")


def generate_token() -> str:
    """生成 32 位 hex token

    Returns:
        格式为 tok_<32位hex> 的 token 字符串

    Example:
        >>> token = generate_token()
        >>> token.startswith("tok_")
        True
        >>> len(token)
        36
    """
    return f"tok_{secrets.token_hex(16)}"


def redact_token(text: str) -> str:
    """替换文本中的 token 为 [REDACTED]

    用于防止 token 泄漏到群聊消息中。

    Args:
        text: 可能包含 token 的文本

    Returns:
        替换后的文本

    Example:
        >>> redact_token("Your token is tok_a1b2c3d4e5f6789012345678901234")
        'Your token is [REDACTED]'
    """
    return TOKEN_PATTERN.sub("[REDACTED]", text)
