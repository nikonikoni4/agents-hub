"""状态文件管理

管理调度器的持久化状态文件：
- .schedule_state.json：调度状态（最后一次执行时间）
- index.json：群聊记忆索引（last_updated）
- result.json：执行结果日志（最近 10 条）
"""

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class StateManager:
    """状态文件管理"""

    def __init__(self, data_path: Path) -> None:
        self._schedule_state_path = data_path / "schedule" / ".schedule_state.json"
        self._memory_index_path = data_path / "schedule" / "memory" / "index.json"
        self._result_path = data_path / "schedule" / "memory" / "result.json"

    def load_schedule_state(self) -> dict:
        """加载 .schedule_state.json，文件不存在时返回空字典"""
        data = self._read_json(self._schedule_state_path)
        return data if isinstance(data, dict) else {}

    def save_schedule_state(self, state: dict) -> None:
        """保存 .schedule_state.json"""
        self._write_json(self._schedule_state_path, state)

    def load_memory_index(self) -> dict:
        """加载 index.json，文件不存在时返回空字典"""
        data = self._read_json(self._memory_index_path)
        return data if isinstance(data, dict) else {}

    def save_memory_index(self, index: dict) -> None:
        """保存 index.json"""
        self._write_json(self._memory_index_path, index)

    def should_execute_today(self) -> bool:
        """判断今天是否需要执行记忆任务

        比较 .schedule_state.json 的 memory_task 字段日期与今天。
        日期不同或字段不存在时返回 True。
        """
        state = self.load_schedule_state()
        last_run = state.get("memory_task")
        if not last_run:
            return True

        try:
            last_date = datetime.fromisoformat(last_run).date()
            return last_date != date.today()
        except (ValueError, TypeError):
            return True

    def append_result(self, group_chat_id: str, result: str, success: bool) -> None:
        """追加执行结果到 result.json（保留最近 10 条）"""
        results = self._read_json(self._result_path)
        if not isinstance(results, list):
            results = []

        results.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "group_chat_id": group_chat_id,
                "success": success,
                "result": result,
            }
        )

        # 保留最近 10 条
        if len(results) > 10:
            results = results[-10:]

        self._write_json(self._result_path, results)

    @staticmethod
    def _read_json(path: Path) -> dict | list:
        """读取 JSON 文件，不存在或解析失败时返回空字典"""
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("读取状态文件失败: %s, 错误: %s", path, e)
            return {}

    @staticmethod
    def _write_json(path: Path, data: dict | list) -> None:
        """写入 JSON 文件，自动创建父目录"""
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("写入状态文件失败: %s, 错误: %s", path, e)
