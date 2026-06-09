"""文件存储服务

负责文件的上传、获取、删除和清理。
存储路径：{data_path}/teams/{team_id}/{group_chat_id}/file_snapshots/
"""

import uuid
from datetime import datetime
from pathlib import Path

from agents_hub.api.schemas.group_chats import UploadedFileInfo
from agents_hub.config import config


class FileService:
    """文件存储服务"""

    def _get_storage_path(self, team_id: str, group_chat_id: str) -> Path:
        """获取文件存储路径"""
        return config.data_path / "teams" / team_id / group_chat_id / "file_snapshots"

    def _generate_filename(self, original_filename: str) -> str:
        """生成新文件名：{原文件名}_{时间戳}_{UUID前16位}.{扩展名}"""
        name = Path(original_filename).stem
        ext = Path(original_filename).suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        uuid_short = uuid.uuid4().hex[:16]
        return f"{name}_{timestamp}_{uuid_short}{ext}"

    async def upload_file(
        self,
        team_id: str,
        group_chat_id: str,
        file_content: bytes,
        original_filename: str,
        content_type: str,
    ) -> UploadedFileInfo:
        """上传文件

        Args:
            team_id: 团队 ID
            group_chat_id: 群聊 ID
            file_content: 文件内容（字节）
            original_filename: 原始文件名
            content_type: 文件 MIME 类型

        Returns:
            UploadedFileInfo: 上传后的文件信息
        """
        new_filename = self._generate_filename(original_filename)

        storage_path = self._get_storage_path(team_id, group_chat_id)
        storage_path.mkdir(parents=True, exist_ok=True)

        file_path = storage_path / new_filename
        file_path.write_bytes(file_content)

        return UploadedFileInfo(
            file_name=original_filename,
            file_path=str(file_path.relative_to(config.data_path)),
            file_type=content_type,
            file_size=len(file_content),
        )

    def _validate_path(self, file_path: str) -> Path:
        """验证并规范化文件路径，防止路径遍历攻击

        Args:
            file_path: 相对于 data_path 的文件路径

        Returns:
            规范化后的完整路径

        Raises:
            ValueError: 如果路径试图访问 data_path 之外的文件
        """
        full_path = (config.data_path / file_path).resolve()
        if not full_path.is_relative_to(config.data_path.resolve()):
            raise ValueError(f"路径越界: {file_path}")
        return full_path

    def get_file_path(self, file_path: str) -> Path | None:
        """获取文件完整路径

        Args:
            file_path: 相对于 data_path 的文件路径

        Returns:
            Path 如果文件存在，否则 None

        Raises:
            ValueError: 如果路径试图访问 data_path 之外的文件
        """
        full_path = self._validate_path(file_path)
        if full_path.exists():
            return full_path
        return None

    def delete_file(self, file_path: str) -> bool:
        """删除文件

        Args:
            file_path: 相对于 data_path 的文件路径

        Returns:
            是否成功删除

        Raises:
            ValueError: 如果路径试图访问 data_path 之外的文件
        """
        full_path = self._validate_path(file_path)
        if full_path.exists():
            full_path.unlink()
            return True
        return False

    def cleanup_orphan_files(self, team_id: str, group_chat_id: str, days: int = 7) -> int:
        """清理孤儿文件（超过指定天数未修改的文件）

        Args:
            team_id: 团队 ID
            group_chat_id: 群聊 ID
            days: 天数阈值，默认 7 天

        Returns:
            清理的文件数量
        """
        storage_path = self._get_storage_path(team_id, group_chat_id)
        if not storage_path.exists():
            return 0

        count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)

        for file_path in storage_path.iterdir():
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                count += 1

        return count
