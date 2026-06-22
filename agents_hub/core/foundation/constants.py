"""
常量定义

定义系统中使用的常量。

注意：路径相关常量已集中管理到 paths.py，使用 group_chat_paths 单例。
"""

# 压缩阈值（token 数量）
MAX_TOKEN = 1000

# 自动上下文压缩阈值（K tokens），当 agent context_usage 超过此值时自动触发压缩
AUTO_COMPACT_THRESHOLD = 200

# 本地数据存储路径（保留用于向后兼容，新代码应使用 group_chat_paths）
LOCAL_DATA_PATH = "local_data"

# Heartbeat 和清理配置常量
HEARTBEAT_INTERVAL_SECONDS: int = 1200  # Heartbeat 间隔（20 分钟）
NOTIFICATION_RETENTION_SECONDS: int = 10 * 60  # NOTIFICATION类型完成后5min内清除
