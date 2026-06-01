"""
常量定义

定义系统中使用的常量。

注意：路径相关常量已集中管理到 paths.py，使用 group_chat_paths 单例。
"""

# 压缩阈值（token 数量）
MAX_TOKEN = 1000

# 本地数据存储路径（保留用于向后兼容，新代码应使用 group_chat_paths）
LOCAL_DATA_PATH = "local_data"
