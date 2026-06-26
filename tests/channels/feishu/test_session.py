"""飞书 Session 映射与同步状态测试"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from agents_hub.channels.feishu.session import (
    FeishuSessionManager,
    FeishuSessionMapping,
    FeishuSyncState,
)


class TestFeishuSessionMapping:
    """测试 FeishuSessionMapping 数据模型"""

    def test_create_mapping(self):
        """测试创建映射关系"""
        mapping = FeishuSessionMapping(
            feishu_chat_id="oc_xxx",
            group_chat_id="group_123",
            group_chat_name="测试群聊",
            bound_at="2026-06-26T10:00:00",
        )

        assert mapping.feishu_chat_id == "oc_xxx"
        assert mapping.group_chat_id == "group_123"
        assert mapping.group_chat_name == "测试群聊"
        assert mapping.bound_at == "2026-06-26T10:00:00"

    def test_mapping_to_dict(self):
        """测试映射关系转字典"""
        mapping = FeishuSessionMapping(
            feishu_chat_id="oc_xxx",
            group_chat_id="group_123",
            group_chat_name="测试群聊",
            bound_at="2026-06-26T10:00:00",
        )

        data = mapping.to_dict()
        assert data["feishu_chat_id"] == "oc_xxx"
        assert data["group_chat_id"] == "group_123"
        assert data["group_chat_name"] == "测试群聊"
        assert data["bound_at"] == "2026-06-26T10:00:00"

    def test_mapping_from_dict(self):
        """测试从字典创建映射关系"""
        data = {
            "feishu_chat_id": "oc_xxx",
            "group_chat_id": "group_123",
            "group_chat_name": "测试群聊",
            "bound_at": "2026-06-26T10:00:00",
        }

        mapping = FeishuSessionMapping.from_dict(data)
        assert mapping.feishu_chat_id == "oc_xxx"
        assert mapping.group_chat_id == "group_123"
        assert mapping.group_chat_name == "测试群聊"
        assert mapping.bound_at == "2026-06-26T10:00:00"


class TestFeishuSyncState:
    """测试 FeishuSyncState 数据模型"""

    def test_create_sync_state(self):
        """测试创建同步状态"""
        state = FeishuSyncState(
            feishu_chat_id="oc_xxx",
            last_message_id=100,
            last_sync_at="2026-06-26T10:00:00",
        )

        assert state.feishu_chat_id == "oc_xxx"
        assert state.last_message_id == 100
        assert state.last_sync_at == "2026-06-26T10:00:00"

    def test_sync_state_to_dict(self):
        """测试同步状态转字典"""
        state = FeishuSyncState(
            feishu_chat_id="oc_xxx",
            last_message_id=100,
            last_sync_at="2026-06-26T10:00:00",
        )

        data = state.to_dict()
        assert data["feishu_chat_id"] == "oc_xxx"
        assert data["last_message_id"] == 100
        assert data["last_sync_at"] == "2026-06-26T10:00:00"

    def test_sync_state_from_dict(self):
        """测试从字典创建同步状态"""
        data = {
            "feishu_chat_id": "oc_xxx",
            "last_message_id": 100,
            "last_sync_at": "2026-06-26T10:00:00",
        }

        state = FeishuSyncState.from_dict(data)
        assert state.feishu_chat_id == "oc_xxx"
        assert state.last_message_id == 100
        assert state.last_sync_at == "2026-06-26T10:00:00"


class TestFeishuSessionManager:
    """测试 FeishuSessionManager"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_dir):
        """创建测试 SessionManager"""
        return FeishuSessionManager(temp_dir)

    def test_bind(self, manager):
        """测试绑定飞书群"""
        manager.bind("oc_xxx", "group_123", "测试群聊")

        mapping = manager.get_mapping("oc_xxx")
        assert mapping is not None
        assert mapping.feishu_chat_id == "oc_xxx"
        assert mapping.group_chat_id == "group_123"
        assert mapping.group_chat_name == "测试群聊"

    def test_unbind(self, manager):
        """测试解绑飞书群"""
        manager.bind("oc_xxx", "group_123", "测试群聊")
        manager.unbind("oc_xxx")

        mapping = manager.get_mapping("oc_xxx")
        assert mapping is None

    def test_get_mapping_not_found(self, manager):
        """测试获取不存在的映射"""
        mapping = manager.get_mapping("oc_not_exist")
        assert mapping is None

    def test_get_sync_state_create_new(self, manager):
        """测试获取同步状态（不存在则创建）"""
        state = manager.get_sync_state("oc_xxx")

        assert state.feishu_chat_id == "oc_xxx"
        assert state.last_message_id == 0
        assert state.last_sync_at is not None

    def test_get_sync_state_existing(self, manager):
        """测试获取已存在的同步状态"""
        # 先更新同步状态
        manager.update_sync_state("oc_xxx", 100)

        # 再获取
        state = manager.get_sync_state("oc_xxx")
        assert state.last_message_id == 100

    def test_update_sync_state(self, manager):
        """测试更新同步状态"""
        manager.update_sync_state("oc_xxx", 100)

        state = manager.get_sync_state("oc_xxx")
        assert state.last_message_id == 100

        # 再次更新
        manager.update_sync_state("oc_xxx", 200)
        state = manager.get_sync_state("oc_xxx")
        assert state.last_message_id == 200

    def test_save_and_load(self, temp_dir):
        """测试持久化和加载"""
        # 创建 manager 并添加数据
        manager1 = FeishuSessionManager(temp_dir)
        manager1.bind("oc_xxx", "group_123", "测试群聊")
        manager1.update_sync_state("oc_xxx", 100)
        manager1.save()

        # 创建新的 manager 并加载
        manager2 = FeishuSessionManager(temp_dir)
        manager2.load()

        # 验证数据
        mapping = manager2.get_mapping("oc_xxx")
        assert mapping is not None
        assert mapping.group_chat_id == "group_123"

        state = manager2.get_sync_state("oc_xxx")
        assert state.last_message_id == 100

    def test_save_creates_directory(self, temp_dir):
        """测试保存时创建目录"""
        nested_dir = temp_dir / "nested" / "path"
        manager = FeishuSessionManager(nested_dir)

        manager.bind("oc_xxx", "group_123", "测试群聊")
        manager.save()

        # 验证文件创建
        assert (nested_dir / "channels" / "feishu" / "session_mapping.json").exists()
        assert (nested_dir / "channels" / "feishu" / "sync_state.json").exists()

    def test_load_nonexistent_files(self, temp_dir):
        """测试加载不存在的文件"""
        manager = FeishuSessionManager(temp_dir)
        manager.load()  # 应该不会抛出异常

        # 验证空数据
        assert manager.get_mapping("oc_xxx") is None

    def test_multiple_mappings(self, manager):
        """测试多个映射关系"""
        manager.bind("oc_aaa", "group_1", "群聊1")
        manager.bind("oc_bbb", "group_2", "群聊2")
        manager.bind("oc_ccc", "group_3", "群聊3")

        assert manager.get_mapping("oc_aaa").group_chat_id == "group_1"
        assert manager.get_mapping("oc_bbb").group_chat_id == "group_2"
        assert manager.get_mapping("oc_ccc").group_chat_id == "group_3"

    def test_bind_updates_existing(self, manager):
        """测试更新已存在的绑定"""
        manager.bind("oc_xxx", "group_123", "测试群聊")
        manager.bind("oc_xxx", "group_456", "新群聊")

        mapping = manager.get_mapping("oc_xxx")
        assert mapping.group_chat_id == "group_456"
        assert mapping.group_chat_name == "新群聊"

    def test_unbind_cleans_sync_state(self, manager):
        """测试解绑时清理同步状态"""
        manager.bind("oc_xxx", "group_123", "测试群聊")
        manager.update_sync_state("oc_xxx", 100)
        manager.unbind("oc_xxx")

        # 同步状态应该被清理
        state = manager.get_sync_state("oc_xxx")
        assert state.last_message_id == 0  # 重新创建的默认值

    def test_save_load_preserves_order(self, temp_dir):
        """测试保存和加载保持顺序"""
        manager1 = FeishuSessionManager(temp_dir)
        for i in range(10):
            manager1.bind(f"oc_{i}", f"group_{i}", f"群聊{i}")
            manager1.update_sync_state(f"oc_{i}", i * 10)
        manager1.save()

        manager2 = FeishuSessionManager(temp_dir)
        manager2.load()

        for i in range(10):
            mapping = manager2.get_mapping(f"oc_{i}")
            assert mapping.group_chat_id == f"group_{i}"

            state = manager2.get_sync_state(f"oc_{i}")
            assert state.last_message_id == i * 10
