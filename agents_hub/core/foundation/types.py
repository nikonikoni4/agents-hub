"""Foundation 层类型定义"""

from typing import TypedDict


class FileMetadata(TypedDict, total=False):
    """文件元数据结构"""

    path: str
    status: str
    additions: int
    deletions: int
    snapshot_id: str
    diff_available: bool
    diff_error: str | None
