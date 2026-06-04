"""
群聊路径集中管理

统一管理群聊相关文件路径，避免路径散落在各处导致不一致。
所有路径规则在此处定义，修改时只需改一处。
"""

from pathlib import Path

from agents_hub.core.utils import sanitize_project_path


class GroupChatPaths:
    """
    群聊相关路径集中管理（单例）

    职责：
    1. 统一路径构建规则，避免各模块自行拼接导致不一致
    2. 集中管理所有群聊相关文件的路径定义
    3. 提供清晰的路径结构文档，便于理解和维护

    使用方式：
        from agents_hub.core.foundation.paths import group_chat_paths

        msg_file = group_chat_paths.messages_file("gc123", "D:/projects/agents-hub")
        # → local_data/teams/D-projects-agents-hub/gc123/gc123.jsonl
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def base_dir(
        self, group_chat_id: str, project_path: str, base_path: str = "local_data/teams"
    ) -> Path:
        """
        群聊基础目录

        Args:
            group_chat_id: 群聊唯一标识
            project_path: 项目路径，会被 sanitize 为安全的目录名
            base_path: 群聊数据根目录，默认 "local_data/teams"

        Returns:
            <base_path>/<sanitized_project>/<group_chat_id>/
        """
        sanitized = sanitize_project_path(project_path)
        return Path(base_path) / sanitized / group_chat_id

    def messages_file(self, group_chat_id: str, project_path: str) -> Path:
        """
        群聊消息历史文件

        存储内容：
        - meta_data 记录（创建时间、更新时间、压缩位置）
        - 所有群聊消息（agent_name、content、timestamp、platform）

        为什么单独保存：
        - 消息是群聊的核心数据，需要持久化存储
        - 支持增量加载（从 last_compacted_loc 开始）
        - JSONL 格式便于追加写入和流式读取

        路径格式：local_data/teams/<project>/<id>/<id>.jsonl
        """
        return self.base_dir(group_chat_id, project_path) / f"{group_chat_id}.jsonl"

    def agent_member_file_path(
        self, group_chat_id: str, project_path: str, base_path: str = "local_data/teams"
    ) -> Path:
        """
        Agent session 状态文件

        存储内容：
        - 每个 agent 的 main_session ID（主会话）
        - 每个 agent 的 btw_session ID 列表（旁听会话）
        - 每个 agent 的 context_state（已加载的压缩索引和消息索引）
        - 每个 agent 的 token

        为什么单独保存：
        - session 状态是 agent 运行时的关键信息
        - 需要支持 agent 重启后恢复状态
        - 与消息历史分离，避免单文件过大

        路径格式：<base_path>/<project>/<id>/agent_member.json
        """
        return self.base_dir(group_chat_id, project_path, base_path) / "agent_member.json"

    def compact_history_file(self, group_chat_id: str, project_path: str) -> Path:
        """
        上下文压缩历史文件

        存储内容：
        - 每次压缩的时间戳
        - 整体摘要（summary）
        - 针对每个 agent 的个性化摘要

        为什么单独保存：
        - 压缩历史用于增量加载，避免重复压缩
        - 支持 agent 从断点继续加载上下文
        - 与消息历史分离，便于管理压缩策略

        路径格式：local_data/teams/<project>/<id>/memory/compact_history.jsonl
        """
        return self.base_dir(group_chat_id, project_path) / "memory" / "compact_history.jsonl"

    def metadata_file(
        self, group_chat_id: str, project_path: str, base_path: str = "local_data/teams"
    ) -> Path:
        """
        群聊元数据文件

        存储内容：
        - group_chat_id：群聊唯一标识
        - group_chat_name：群聊名称
        - project_path：项目路径（作为 agent 默认 cwd）
        - created_at：创建时间
        - group_type：群聊类型

        为什么单独保存：
        - 元数据在 GroupChat.start() 时立即创建，独立于消息历史
        - 消息历史在首次消息时才创建，延迟创建避免空文件
        - project_path 需要持久化，作为 agent 的默认工作目录

        路径格式：<base_path>/<project>/<id>/group_metadata.json
        """
        return self.base_dir(group_chat_id, project_path, base_path) / "group_metadata.json"

    def agent_calls_log(self, group_chat_id: str, project_path: str) -> Path:
        """
        Agent 调用日志文件

        存储内容：
        - 跨 agent 调用的创建、状态变更、错误、清理等日志
        - 用于调试和监控 agent 间的协作

        为什么单独保存：
        - agent 调用是核心协作机制，需要独立追踪
        - 便于排查 agent 间通信问题
        - 与业务日志分离，避免干扰

        路径格式：local_data/teams/<project>/<id>/agent_calls.log
        """
        return self.base_dir(group_chat_id, project_path) / "agent_calls.log"

    def agent_calls_data(self, group_chat_id: str, project_path: str) -> Path:
        """
        Agent 调用持久化数据文件

        存储内容：
        - AgentCall 对象的 JSONL 序列化数据
        - 包含调用 ID、类型、状态、结果、时间戳等

        为什么单独保存：
        - 调用数据需要持久化，支持系统重启后恢复
        - JSONL 格式便于追加写入和查询
        - 与日志分离，日志用于调试，数据用于业务

        路径格式：local_data/teams/<project>/<id>/agent_calls.jsonl
        """
        return self.base_dir(group_chat_id, project_path) / "agent_calls.jsonl"

    def find_project_path_by_group_chat_id(
        self, group_chat_id: str, base_path: str = "local_data/teams"
    ) -> str | None:
        """
        通过 group_chat_id 查找对应的 project_path

        扫描 local_data/teams/ 目录结构，找到包含指定 group_chat_id 的项目路径。

        Args:
            group_chat_id: 群聊 ID
            base_path: 群聊数据根目录，默认 "local_data/teams"

        Returns:
            找到的 project_path，未找到返回 None
        """
        import json

        base = Path(base_path)
        if not base.exists():
            return None

        # 扫描 teams/*/<group_chat_id>/group_metadata.json
        for project_dir in base.iterdir():
            if not project_dir.is_dir():
                continue

            group_dir = project_dir / group_chat_id
            if not group_dir.is_dir():
                continue

            metadata_file = group_dir / "group_metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, encoding="utf-8") as f:
                    data = json.load(f)

                # 验证 group_chat_id 一致性
                if data.get("group_chat_id") == group_chat_id:
                    return data.get("project_path")
            except Exception:
                continue

        return None

    def tasks_log(self, group_chat_id: str, project_path: str) -> Path:
        """
        任务管理日志文件

        存储内容：
        - 任务的创建、更新、归档等操作日志
        - 用于追踪任务生命周期

        为什么单独保存：
        - 任务是业务层概念，需要独立追踪
        - 便于排查任务分配和执行问题
        - 与 agent 调用日志分离，职责清晰

        路径格式：local_data/teams/<project>/<id>/tasks.log
        """
        return self.base_dir(group_chat_id, project_path) / "tasks.log"

    def tasks_data(self, group_chat_id: str, project_path: str) -> Path:
        """
        任务持久化数据文件

        存储内容：
        - Task 对象的 JSONL 序列化数据
        - 包含任务 ID、描述、状态、负责人、时间戳等

        为什么单独保存：
        - 任务数据需要持久化，支持系统重启后恢复
        - JSONL 格式便于追加写入和查询
        - 与日志分离，日志用于调试，数据用于业务

        路径格式：local_data/teams/<project>/<id>/tasks.jsonl
        """
        return self.base_dir(group_chat_id, project_path) / "tasks.jsonl"


# 全局单例实例
group_chat_paths = GroupChatPaths()
