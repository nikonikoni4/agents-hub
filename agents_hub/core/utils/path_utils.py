"""
路径处理工具函数
"""

import re


def sanitize_project_path(project_path: str) -> str:
    """
    将 project_path 转换为安全的存储路径名称。
    将 / : \\ 等 Windows 文件夹命名非法字符转化为 -

    Args:
        project_path: 原始项目路径字符串

    Returns:
        转换后的安全路径名称
    """
    # 将 / : \\ 替换为 -
    sanitized = re.sub(r"[/:\\]", "-", project_path)
    # 移除开头和结尾的 -
    sanitized = sanitized.strip("-")
    # 将连续的 - 合并为单个 -
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized
