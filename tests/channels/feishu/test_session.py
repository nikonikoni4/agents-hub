"""飞书 Session 状态管理测试"""

import json
import pytest
import tempfile
import threading
from pathlib import Path

from agents_hub.channels.feishu.session import (
    FeishuSessionState,
    FeishuSessionManager,
)


class TestFeishuSessionState:
    """测试 FeishuSessionState 数据模型"""

    def test_create_state(self):
        """测试创建状态"""
        state = FeishuSessionState(
            feishu_chat_id="oc_xxx",
            session_type="idle",
            session_id="",
            session_name="",
        )

        assert state.feishu_chat_id == "oc_xxx"
        assert state.session_type == "idle"
        assert state.session_id == ""
        assert state.session_name == ""
        assert state.single_chat_id == ""
        assert state.last_message_id == 0
        assert state.default_agent == ""
        assert state.single_chat_history == []

    def test_to_dict(self):
        """测试转字典"""
        state = FeishuSessionState(
            feishu_chat_id="oc_xxx",
            session_type="group_chat",
            session_id="group_123",
            session_name="测试群聊",
            single_chat_id="",
            last_message_id=100,
            default_agent="pm",
        )

        data = state.to_dict()
        assert data["feishu_chat_id"] == "oc_xxx"
        assert data["session_type"] == "group_chat"
        assert data["session_id"] == "group_123"
        assert data["session_name"] == "测试群聊"
        assert data["last_message_id"] == 100
        assert data["default_agent"] == "pm"
        assert data["single_chat_history"] == []

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "feishu_chat_id": "oc_xxx",
            "session_type": "single_chat",
            "session_id": "researcher",
            "session_name": "researcher",
            "single_chat_id": "sc_123",
            "last_message_id": 0,
            "last_sync_at": "2026-06-27T10:00:00",
            "created_at": "2026-06-27T10:00:00",
            "default_agent": "",
            "single_chat_history": [
                {"session_id": "sc_123", "agent_name": "researcher", "first_message": "你好", "created_at": "2026-06-27T10:00:00"}
            ],
        }

        state = FeishuSessionState.from_dict(data)
        assert state.feishu_chat_id == "oc_xxx"
        assert state.session_type == "single_chat"
        assert state.session_id == "researcher"
        assert state.single_chat_id == "sc_123"
        assert len(state.single_chat_history) == 1
        assert state.single_chat_history[0]["agent_name"] == "researcher"

    def test_from_dict_missing_optional_fields(self):
        """测试从字典创建（缺少可选字段）"""
        data = {
            "feishu_chat_id": "oc_xxx",
            "session_type": "idle",
            "session_id": "",
        }

        state = FeishuSessionState.from_dict(data)
        assert state.session_name == ""
        assert state.single_chat_id == ""
        assert state.last_message_id == 0
        assert state.single_chat_history == []


class TestFeishuSessionManagerWithRealMethods:
    """测试 FeishuSessionManager 真实方法（不复制实现逻辑）"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """创建独立的 manager 实例（绕过单例）"""
        FeishuSessionManager._instance = None
        mgr = FeishuSessionManager(temp_dir)
        yield mgr
        FeishuSessionManager._instance = None

    def test_get_or_create_state_creates_new(self, manager):
        """测试 get_or_create_state 创建新状态"""
        state = manager.get_or_create_state("oc_xxx")

        assert state.feishu_chat_id == "oc_xxx"
        assert state.session_type == "idle"
        assert state.session_id == ""
        assert state.session_name == ""

    def test_get_or_create_state_returns_existing(self, manager):
        """测试 get_or_create_state 返回已存在状态"""
        state1 = manager.get_or_create_state("oc_xxx")
        state1.session_type = "assistant"

        state2 = manager.get_or_create_state("oc_xxx")
        assert state2.session_type == "assistant"
        assert state1 is state2

    def test_switch_to_idle(self, manager):
        """测试 switch_to_idle"""
        manager.switch_to_group_chat("oc_xxx", "group_123", "测试群聊")
        manager.switch_to_idle("oc_xxx")

        state = manager.get_or_create_state("oc_xxx")
        assert state.session_type == "idle"
        assert state.session_id == ""
        assert state.session_name == ""

    def test_switch_to_idle_preserves_single_chat_id(self, manager):
        """测试 switch_to_idle 保留 single_chat_id"""
        manager.switch_to_single_chat("oc_xxx", "researcher", "sc_123")
        manager.switch_to_idle("oc_xxx")

        state = manager.get_or_create_state("oc_xxx")
        assert state.session_type == "idle"
        assert state.single_chat_id == "sc_123"  # 保留

    def test_switch_to_group_chat(self, manager):
        """测试 switch_to_group_chat"""
        manager.switch_to_group_chat("oc_xxx", "group_123", "测试群聊")

        state = manager.get_or_create_state("oc_xxx")
        assert state.session_type == "group_chat"
        assert state.session_id == "group_123"
        assert state.session_name == "测试群聊"
        assert state.single_chat_id == ""  # 清空单聊 ID

    def test_switch_to_single_chat(self, manager):
        """测试 switch_to_single_chat"""
        manager.switch_to_single_chat("oc_xxx", "researcher", "sc_123")

        state = manager.get_or_create_state("oc_xxx")
        assert state.session_type == "single_chat"
        assert state.session_id == "researcher"
        assert state.session_name == "researcher"
        assert state.single_chat_id == "sc_123"

    def test_switch_to_assistant(self, manager):
        """测试 switch_to_assistant"""
        manager.switch_to_assistant("oc_xxx")

        state = manager.get_or_create_state("oc_xxx")
        assert state.session_type == "assistant"

    def test_update_sync_state(self, manager):
        """测试 update_sync_state"""
        manager.update_sync_state("oc_xxx", 100)

        state = manager.get_or_create_state("oc_xxx")
        assert state.last_message_id == 100
        assert state.last_sync_at != ""

    def test_add_single_chat_history(self, manager):
        """测试 add_single_chat_history"""
        manager.add_single_chat_history("oc_xxx", "sc_123", "researcher", "你好世界")

        state = manager.get_or_create_state("oc_xxx")
        assert len(state.single_chat_history) == 1
        assert state.single_chat_history[0]["session_id"] == "sc_123"
        assert state.single_chat_history[0]["agent_name"] == "researcher"
        assert state.single_chat_history[0]["first_message"] == "你好世界"

    def test_add_single_chat_history_truncate(self, manager):
        """测试 add_single_chat_history 截断第一句话"""
        long_message = "abcdefghijklmnop"  # 16 chars
        manager.add_single_chat_history("oc_xxx", "sc_123", "researcher", long_message)

        state = manager.get_or_create_state("oc_xxx")
        assert state.single_chat_history[0]["first_message"] == "abcdefghij"  # 10 chars

    def test_add_single_chat_history_dedup(self, manager):
        """测试 add_single_chat_history 去重"""
        manager.add_single_chat_history("oc_xxx", "sc_123", "researcher", "你好")
        manager.add_single_chat_history("oc_xxx", "sc_123", "researcher", "世界")

        state = manager.get_or_create_state("oc_xxx")
        assert len(state.single_chat_history) == 1
        assert state.single_chat_history[0]["first_message"] == "你好"

    def test_add_single_chat_history_update_empty_first_message(self, manager):
        """测试 add_single_chat_history 更新空的第一句话"""
        manager.add_single_chat_history("oc_xxx", "sc_123", "researcher", "")
        manager.add_single_chat_history("oc_xxx", "sc_123", "researcher", "你好")

        state = manager.get_or_create_state("oc_xxx")
        assert len(state.single_chat_history) == 1
        assert state.single_chat_history[0]["first_message"] == "你好"

    def test_add_single_chat_history_limit(self, manager):
        """测试 add_single_chat_history 上限（50条）"""
        for i in range(55):
            manager.add_single_chat_history("oc_xxx", f"sc_{i}", "researcher", f"消息{i}")

        state = manager.get_or_create_state("oc_xxx")
        assert len(state.single_chat_history) == 50
        assert state.single_chat_history[0]["session_id"] == "sc_5"
        assert state.single_chat_history[-1]["session_id"] == "sc_54"


class TestFeishuSessionManagerPersistence:
    """测试 FeishuSessionManager 持久化"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_save_and_load(self, temp_dir):
        """测试持久化和加载"""
        FeishuSessionManager._instance = None
        manager1 = FeishuSessionManager(temp_dir)
        manager1.switch_to_group_chat("oc_xxx", "group_123", "测试群聊")
        manager1.update_sync_state("oc_xxx", 100)
        manager1.add_single_chat_history("oc_xxx", "sc_123", "researcher", "你好")
        manager1.save()

        FeishuSessionManager._instance = None
        manager2 = FeishuSessionManager(temp_dir)
        manager2.load()

        state = manager2.get_or_create_state("oc_xxx")
        assert state.session_type == "group_chat"
        assert state.session_id == "group_123"
        assert state.last_message_id == 100
        assert len(state.single_chat_history) == 1

        FeishuSessionManager._instance = None

    def test_load_nonexistent_file(self, temp_dir):
        """测试加载不存在的文件"""
        FeishuSessionManager._instance = None
        manager = FeishuSessionManager(temp_dir)
        manager.load()  # 不应抛出异常

        assert len(manager._states) == 0
        FeishuSessionManager._instance = None

    def test_migrate_old_format(self, temp_dir):
        """测试旧格式迁移"""
        old_data = [
            {
                "feishu_chat_id": "oc_xxx",
                "group_chat_id": "group_123",
                "group_chat_name": "测试群聊",
                "bound_at": "2026-06-26T10:00:00",
            }
        ]

        state_file = temp_dir / "channels" / "feishu"
        state_file.mkdir(parents=True, exist_ok=True)
        (state_file / "session_state.json").write_text(json.dumps(old_data, ensure_ascii=False))

        FeishuSessionManager._instance = None
        manager = FeishuSessionManager(temp_dir)
        manager.load()

        state = manager.get_or_create_state("oc_xxx")
        assert state.session_type == "group_chat"
        assert state.session_id == "group_123"
        assert state.session_name == "测试群聊"

        FeishuSessionManager._instance = None


class TestFeishuSessionManagerNoDeadlock:
    """测试 FeishuSessionManager 方法不会死锁"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def _create_manager(self, temp_dir):
        """创建独立的 manager 实例"""
        FeishuSessionManager._instance = None
        return FeishuSessionManager(temp_dir)

    def test_switch_to_idle_no_deadlock(self, temp_dir):
        """测试 switch_to_idle 不会死锁"""
        manager = self._create_manager(temp_dir)
        result = threading.Event()

        def run():
            manager.switch_to_idle("oc_xxx")
            result.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=2)
        assert result.is_set(), "switch_to_idle 死锁了"
        FeishuSessionManager._instance = None

    def test_switch_to_group_chat_no_deadlock(self, temp_dir):
        """测试 switch_to_group_chat 不会死锁"""
        manager = self._create_manager(temp_dir)
        result = threading.Event()

        def run():
            manager.switch_to_group_chat("oc_xxx", "group_1", "测试群聊")
            result.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=2)
        assert result.is_set(), "switch_to_group_chat 死锁了"
        FeishuSessionManager._instance = None

    def test_switch_to_single_chat_no_deadlock(self, temp_dir):
        """测试 switch_to_single_chat 不会死锁"""
        manager = self._create_manager(temp_dir)
        result = threading.Event()

        def run():
            manager.switch_to_single_chat("oc_xxx", "researcher", "sc_123")
            result.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=2)
        assert result.is_set(), "switch_to_single_chat 死锁了"
        FeishuSessionManager._instance = None

    def test_switch_to_assistant_no_deadlock(self, temp_dir):
        """测试 switch_to_assistant 不会死锁"""
        manager = self._create_manager(temp_dir)
        result = threading.Event()

        def run():
            manager.switch_to_assistant("oc_xxx")
            result.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=2)
        assert result.is_set(), "switch_to_assistant 死锁了"
        FeishuSessionManager._instance = None

    def test_update_sync_state_no_deadlock(self, temp_dir):
        """测试 update_sync_state 不会死锁"""
        manager = self._create_manager(temp_dir)
        result = threading.Event()

        def run():
            manager.update_sync_state("oc_xxx", 100)
            result.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=2)
        assert result.is_set(), "update_sync_state 死锁了"
        FeishuSessionManager._instance = None

    def test_add_single_chat_history_no_deadlock(self, temp_dir):
        """测试 add_single_chat_history 不会死锁"""
        manager = self._create_manager(temp_dir)
        result = threading.Event()

        def run():
            manager.add_single_chat_history("oc_xxx", "sc_123", "researcher", "你好")
            result.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=2)
        assert result.is_set(), "add_single_chat_history 死锁了"
        FeishuSessionManager._instance = None
