"""
日志系统

提供全局logger和特定用途的specialized logger。
支持日志文件自动轮转（超过500KB时归档为.old.log）。
"""

import logging
import os
from pathlib import Path

MAX_LOG_MESSAGE_LENGTH = 10000
MAX_LOG_FILE_SIZE = 500 * 1024  # 500KB


class TruncatingFormatter(logging.Formatter):
    """自动截断超长日志消息，防止图片 base64 等大内容撑爆日志"""

    def __init__(self, fmt=None, datefmt=None, max_length=MAX_LOG_MESSAGE_LENGTH):
        super().__init__(fmt, datefmt)
        self.max_length = max_length

    def format(self, record):
        msg = super().format(record)
        if len(msg) > self.max_length:
            msg = msg[: self.max_length] + f"... [截断, 原长 {len(msg)}]"
        return msg


class RotatingFileHandler(logging.FileHandler):
    """
    自定义文件handler，支持基于文件大小的日志轮转

    当日志文件超过 max_bytes 时，自动归档为 .old.log 并清空当前文件。
    """

    def __init__(
        self,
        filename: Path,
        mode: str = "a",
        encoding: str = "utf-8",
        max_bytes: int = MAX_LOG_FILE_SIZE,
    ):
        self.max_bytes = max_bytes
        self.base_filename = filename
        # 转换为字符串，FileHandler 需要字符串路径
        super().__init__(str(filename), mode, encoding)

    def emit(self, record):
        """写入日志前检查文件大小，超限则轮转"""
        try:
            if self.should_rotate():
                self.do_rotate()
        except Exception:
            self.handleError(record)
        super().emit(record)

    def should_rotate(self) -> bool:
        """判断是否需要轮转"""
        if not os.path.exists(self.baseFilename):
            return False
        return os.path.getsize(self.baseFilename) >= self.max_bytes

    def do_rotate(self):
        """执行轮转：当前文件 → .old.log，清空当前文件"""
        self.stream.close()

        old_log = self.base_filename.with_suffix(".old.log")
        # 如果已有 .old.log，直接覆盖
        if old_log.exists():
            old_log.unlink()

        # 重命名当前日志为 .old.log
        os.rename(self.baseFilename, old_log)

        # 重新打开当前日志文件（自动创建新文件）
        self.stream = self._open()


_LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s %(filename)s:%(lineno)d - %(message)s"
_global_log_dir: Path | None = None
_initialized = False


def setup_logging(log_dir: Path, global_log_filename: str = "agents_hub.log", level=logging.DEBUG):
    """
    初始化全局日志系统

    Args:
        log_dir: 日志目录路径
        global_log_filename: 全局日志文件名（默认 "agents_hub.log"）
        level: 日志级别
    """
    global _global_log_dir, _initialized
    if _initialized:
        return

    _global_log_dir = log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    # 配置 root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(TruncatingFormatter(_LOG_FORMAT))
    root_logger.addHandler(console_handler)

    # 全局文件 handler（支持轮转）
    global_log_file = log_dir / global_log_filename
    file_handler = RotatingFileHandler(global_log_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(TruncatingFormatter(_LOG_FORMAT))
    root_logger.addHandler(file_handler)

    _initialized = True


def get_logger(name: str, level: int | None = None) -> logging.Logger:
    """
    获取标准logger

    Args:
        name: logger名称
        level: 日志级别（可选）

    Returns:
        配置好的logger实例
    """
    logger = logging.getLogger(name)
    if level:
        logger.setLevel(level)
    return logger


def get_specialized_logger(
    name: str,
    log_filename: str,
    level: int | None = None,
    also_to_global: bool = True,
    log_dir: Path | None = None,
) -> logging.Logger:
    """
    创建特定用途的logger

    Args:
        name: logger名称（如 "agent_call_manager"）
        log_filename: 专用日志文件名（如 "agent_calls.log"）
        level: 日志级别（可选）
        also_to_global: 是否同时输出到全局日志（默认True）
        log_dir: 自定义日志目录（可选，默认使用全局日志目录）

    Returns:
        配置好的logger实例

    Example:
        >>> # 使用全局日志目录
        >>> logger = get_specialized_logger(
        ...     name="agent_call_manager",
        ...     log_filename="agent_calls.log",
        ...     also_to_global=True
        ... )
        >>> logger.info("创建调用")  # 写入 logs/agent_calls.log

        >>> # 使用自定义目录
        >>> logger = get_specialized_logger(
        ...     name="group_chat_123",
        ...     log_filename="chat.log",
        ...     log_dir=Path("logs/group_chats/123")
        ... )
        >>> logger.info("群聊消息")  # 写入 logs/group_chats/123/chat.log
    """
    if not _global_log_dir:
        raise RuntimeError("必须先调用 setup_logging() 初始化日志系统")

    logger = logging.getLogger(name)
    if level:
        logger.setLevel(level)

    # 防止重复添加handler
    if logger.handlers:
        return logger

    # 确定日志文件路径
    target_dir = log_dir if log_dir else _global_log_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    specialized_file = target_dir / log_filename

    # 专用文件handler（支持轮转）
    file_handler = RotatingFileHandler(specialized_file, mode="a", encoding="utf-8")
    file_handler.setFormatter(TruncatingFormatter(_LOG_FORMAT))
    logger.addHandler(file_handler)

    # 控制是否传播到全局logger
    logger.propagate = also_to_global

    return logger
