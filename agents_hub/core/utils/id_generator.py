"""
ID 生成工具函数
"""

from uuid import uuid4


def generate_group_chat_id() -> str:
    """生成群聊 ID

    Returns:
        str: 格式为 'gc_<uuid>' 的群聊 ID
    """
    return f"gc_{uuid4().hex[:12]}"
