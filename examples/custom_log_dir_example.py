"""
自定义日志目录示例

演示如何为不同的模块使用不同的日志目录。
"""

from pathlib import Path

from agents_hub.utils.logger import get_logger, get_specialized_logger, setup_logging


def main():
    # 1. 初始化全局日志系统
    setup_logging(Path("logs"), global_log_filename="app.log")

    # 2. 全局 logger（写入 logs/app.log）
    global_logger = get_logger("main")
    global_logger.info("应用启动")

    # 3. 默认路径的 specialized logger（写入 logs/agent_calls.log）
    agent_logger = get_specialized_logger(
        name="agent_call_manager",
        log_filename="agent_calls.log",
    )
    agent_logger.info("全局 Agent 调用")

    # 4. 自定义路径：每个群聊有独立目录
    group_chat_123_logger = get_specialized_logger(
        name="group_chat.123",
        log_filename="chat.log",
        log_dir=Path("logs/group_chats/123"),
    )
    group_chat_123_logger.info("群聊 123 的消息")

    group_chat_456_logger = get_specialized_logger(
        name="group_chat.456",
        log_filename="chat.log",
        log_dir=Path("logs/group_chats/456"),
    )
    group_chat_456_logger.info("群聊 456 的消息")

    # 5. 自定义路径：按日期分类
    today_logger = get_specialized_logger(
        name="daily_report",
        log_filename="report.log",
        log_dir=Path("logs/daily/2026-05-31"),
    )
    today_logger.info("今日报告")

    print("\n生成的日志文件结构:")
    print("logs/")
    print("├── app.log                    # 全局日志")
    print("├── agent_calls.log            # 默认路径的专用日志")
    print("├── group_chats/")
    print("│   ├── 123/")
    print("│   │   └── chat.log           # 群聊 123 的日志")
    print("│   └── 456/")
    print("│       └── chat.log           # 群聊 456 的日志")
    print("└── daily/")
    print("    └── 2026-05-31/")
    print("        └── report.log         # 按日期分类的日志")


if __name__ == "__main__":
    main()
