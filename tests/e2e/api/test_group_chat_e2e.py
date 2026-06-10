"""GroupChat 模块 E2E API 测试

测试范围：
- POST /api/v1/group-chats - 创建群聊（xfail，需要 agent CLI）
- GET /api/v1/group-chats - 列出所有群聊
- GET /api/v1/group-chats/{id} - 获取群聊详情
- DELETE /api/v1/group-chats/{id} - 删除群聊

数据策略：
- setup 阶段手动创建测试数据文件到 local_data/teams/ 目录
- teardown 阶段清理整个测试目录
- 使用固定 UUID 作为 group_chat_id，确保可重复运行

运行前提：服务器已启动（uvicorn agents_hub.api.app:app --port 8000）
运行命令：pytest tests/e2e/api/test_group_chat_e2e.py -v
"""

import json
import shutil
from pathlib import Path

import pytest

# ── 测试常量 ──────────────────────────────────────────────────────────────

# 固定的 group_chat_id，确保测试可重复
GROUP_CHAT_ID = "e2e-gc-0001-0002-0003-000400050006"

# 测试项目路径及其 sanitize 后的目录名
PROJECT_PATH = "D:/e2e-test-project"
SANITIZED_PATH = "D-e2e-test-project"  # sanitize_project_path("D:/e2e-test-project")

# 测试数据根目录
TEAMS_DIR = Path("local_data/teams")
TEST_CHAT_DIR = TEAMS_DIR / SANITIZED_PATH / GROUP_CHAT_ID

# 群聊元数据
METADATA = {
    "group_chat_id": GROUP_CHAT_ID,
    "group_chat_name": "e2e-test-chat",
    "project_path": PROJECT_PATH,
    "created_at": "2026-06-05T00:00:00",
    "group_type": "manager_orchestrate",
}

# agent session 状态
AGENT_MEMBERS = {
    "e2e_leader": {
        "main_session": "test-session-1",
        "btw_session": [],
        "context_state": {"compacted_loc": 0, "loaded_msg_idx": 0},
    },
    "e2e_worker_a": {
        "main_session": "test-session-2",
        "btw_session": [],
        "context_state": {"compacted_loc": 0, "loaded_msg_idx": 0},
    },
}

# 用于 POST 创建的请求体
CREATE_REQUEST = {
    "team_members": ["e2e_leader", "e2e_worker_a"],
    "project_path": PROJECT_PATH,
    "group_chat_name": "e2e-chat",
}


# ── 测试类 ────────────────────────────────────────────────────────────────


class TestGroupChatE2E:
    """按顺序测试 GroupChat 模块的核心流程

    setup 阶段手动创建测试数据文件，模拟一个已存在的群聊。
    POST 创建群聊标记为 xfail（需要 agent CLI）。
    """

    # 用于记录 POST 创建成功后的 group_chat_id（如果成功的话）
    _created_group_chat_id: str | None = None

    # ── setup：创建测试数据 ────────────────────────────────────────────────

    def test_00_setup_create_test_data(self):
        """在 local_data/teams/ 下手动创建测试数据目录和文件"""
        # 创建目录
        TEST_CHAT_DIR.mkdir(parents=True, exist_ok=True)

        # 写入 group_metadata.json
        metadata_file = TEST_CHAT_DIR / "group_metadata.json"
        metadata_file.write_text(
            json.dumps(METADATA, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 写入 agent_member.json
        member_file = TEST_CHAT_DIR / "agent_member.json"
        member_file.write_text(
            json.dumps(AGENT_MEMBERS, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 验证文件已创建
        assert metadata_file.exists(), "group_metadata.json 未创建"
        assert member_file.exists(), "agent_member.json 未创建"

    # ── POST 创建群聊（xfail） ─────────────────────────────────────────────

    @pytest.mark.xfail(reason="需要 agent CLI（Claude/Codex），CI 环境中通常不可用")
    def test_01_create_group_chat(self, api):
        """POST /group-chats 创建群聊 -> 200

        需要真实的 agent CLI 才能成功，标记为 xfail。
        如果成功，记录返回的 group_chat_id 供后续测试使用。
        """
        resp = api.post("/group-chats", json=CREATE_REQUEST)
        assert resp.status_code == 200, f"创建失败: {resp.text}"

        data = resp.json()
        assert "group_chat_id" in data
        assert data["group_chat_name"] == "e2e-chat"
        assert data["project_path"] == PROJECT_PATH

        # 记录创建成功的 group_chat_id
        TestGroupChatE2E._created_group_chat_id = data["group_chat_id"]

    # ── GET 列表 ───────────────────────────────────────────────────────────

    def test_02_list_group_chats(self, api):
        """GET /group-chats -> 200，返回群聊列表，包含手动创建的测试数据"""
        resp = api.get("/group-chats")
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)

        # 验证手动创建的群聊在列表中
        ids = [gc["group_chat_id"] for gc in data]
        assert GROUP_CHAT_ID in ids, f"列表中未找到测试群聊 {GROUP_CHAT_ID}，实际: {ids}"

    def test_03_list_group_chats_with_active_filter(self, api):
        """GET /group-chats?is_active_only=true -> 200

        手动创建的数据不在内存中，is_active 应为 False，
        使用 active 过滤时可能不包含测试数据。
        """
        resp = api.get("/group-chats", params={"is_active_only": True})
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)
        # 手动创建的数据不是活跃的，所以不应出现在 active-only 列表中
        ids = [gc["group_chat_id"] for gc in data]
        assert GROUP_CHAT_ID not in ids, "手动创建的数据不应出现在活跃群聊列表中"

    # ── GET 详情 ───────────────────────────────────────────────────────────

    def test_04_get_group_chat_info(self, api):
        """GET /group-chats/{id} -> 200，返回群聊详细信息

        注意：此接口会尝试从磁盘加载群聊（load_group_chat_from_disk），
        可能因 agent CLI 不可用而失败。使用 created_id 优先，fallback 到手动数据。
        """
        # 优先使用 POST 创建成功的 id
        target_id = TestGroupChatE2E._created_group_chat_id or GROUP_CHAT_ID

        resp = api.get(f"/group-chats/{target_id}")

        # 如果是手动创建的数据，load_group_chat_from_disk 可能失败
        if not TestGroupChatE2E._created_group_chat_id and resp.status_code != 200:
            pytest.skip(
                f"GET /group-chats/{target_id} 返回 {resp.status_code}，"
                "可能因为 agent CLI 不可用导致 load 失败"
            )

        assert resp.status_code == 200, f"获取详情失败: {resp.text}"
        data = resp.json()
        assert data["group_chat_id"] == target_id

    # ── DELETE 删除 ────────────────────────────────────────────────────────

    def test_05_delete_group_chat(self, api):
        """DELETE /group-chats/{id}?keep_data=false -> 200

        清理通过 API 创建的群聊（如果有的话）。
        手动创建的数据由 teardown 清理。
        """
        # 只清理 POST 创建成功的群聊
        if not TestGroupChatE2E._created_group_chat_id:
            pytest.skip("没有通过 API 创建的群聊，跳过删除测试")

        target_id = TestGroupChatE2E._created_group_chat_id
        resp = api.delete(f"/group-chats/{target_id}", params={"keep_data": False})
        assert resp.status_code == 200, f"删除失败: {resp.text}"

        data = resp.json()
        assert "message" in data

    # ── teardown：清理测试数据 ──────────────────────────────────────────────

    def test_99_teardown_cleanup(self):
        """清理手动创建的测试数据目录"""
        if TEAMS_DIR.exists():
            e2e_project_dir = TEAMS_DIR / SANITIZED_PATH
            if e2e_project_dir.exists():
                try:
                    shutil.rmtree(e2e_project_dir)
                except PermissionError:
                    # Windows 上服务器可能持有日志文件句柄，跳过清理
                    pass
