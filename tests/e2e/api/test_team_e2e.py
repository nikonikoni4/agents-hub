"""Team 模块 E2E API 测试

测试 Team 模块的完整 CRUD 流程以及校验逻辑。
假设服务器已启动在 localhost:8000，且 Role 模块的 E2E 测试
已创建 e2e_leader 和 e2e_worker_a 角色。

运行方式：
    pytest tests/e2e/api/test_team_e2e.py -v
"""

import pytest


# ── 测试数据常量 ──────────────────────────────────────────────────────────

TEAM_NAME = "e2e-team-alpha"
TEAM_MEMBERS = ["e2e_leader", "e2e_worker_a"]

# Team 测试需要的前置角色
_PREREQUISITE_ROLES = [
    {"name": "e2e_leader", "platform": "claude", "type": "leader", "abilities": ["code_review"]},
    {"name": "e2e_worker_a", "platform": "claude", "type": "team_member", "abilities": ["coding"]},
]


# ── 测试类 ────────────────────────────────────────────────────────────────

class TestTeamE2E:
    """按顺序测试 Team 模块的核心流程

    test_00 创建前置角色，test_99 清理所有测试数据。
    """

    # ── setup：创建前置角色 ────────────────────────────────────────────────

    def test_00_setup_create_roles(self, api):
        """创建 Team 测试所需的前置角色（e2e_leader, e2e_worker_a）"""
        for role in _PREREQUISITE_ROLES:
            resp = api.post("/roles", json=role)
            # 201=新建成功, 409=已存在（上次测试残留）都可接受
            assert resp.status_code in (201, 409), f"创建角色 {role['name']} 失败: {resp.text}"

    # ── 创建团队 ──────────────────────────────────────────────────────────

    def test_01_create_team(self, api):
        """POST 创建团队 e2e-team-alpha -> 201，验证返回 name 和 members"""
        resp = api.post("/teams", json={"name": TEAM_NAME, "members": TEAM_MEMBERS})
        assert resp.status_code == 201, f"创建失败: {resp.text}"
        data = resp.json()
        assert data["name"] == TEAM_NAME
        assert data["members"] == TEAM_MEMBERS

    def test_02_create_team_empty_members(self, api):
        """POST 创建成员为空的团队 -> 400 (EMPTY_TEAM_MEMBERS)"""
        resp = api.post("/teams", json={"name": "empty-team", "members": []})
        assert resp.status_code == 400, f"期望 400，实际: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data["error_code"] == "EMPTY_TEAM_MEMBERS"

    def test_03_create_team_invalid_members(self, api):
        """POST 创建含不存在角色的团队 -> 400 (INVALID_TEAM_MEMBERS)"""
        resp = api.post("/teams", json={"name": "ghost-team", "members": ["ghost"]})
        assert resp.status_code == 400, f"期望 400，实际: {resp.status_code} {resp.text}"
        data = resp.json()
        assert data["error_code"] == "INVALID_TEAM_MEMBERS"

    # ── 查询团队 ──────────────────────────────────────────────────────────

    def test_04_list_teams(self, api):
        """GET /teams -> 200，列表中包含 e2e-team-alpha"""
        resp = api.get("/teams")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert TEAM_NAME in names, f"列表中未找到 {TEAM_NAME}, 实际: {names}"

    def test_05_get_team_by_name(self, api):
        """GET /teams/e2e-team-alpha -> 200，返回正确的 name 和 members"""
        resp = api.get(f"/teams/{TEAM_NAME}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == TEAM_NAME
        assert data["members"] == TEAM_MEMBERS

    def test_06_get_nonexistent_team(self, api):
        """GET /teams/not_exist -> 404"""
        resp = api.get("/teams/not_exist")
        assert resp.status_code == 404

    # ── 更新团队 ──────────────────────────────────────────────────────────

    def test_07_patch_team_members(self, api):
        """PATCH /teams/e2e-team-alpha 更新 members -> 200"""
        resp = api.patch(f"/teams/{TEAM_NAME}", json={"members": ["e2e_leader"]})
        assert resp.status_code == 200, f"更新失败: {resp.text}"
        data = resp.json()
        assert data["members"] == ["e2e_leader"]

    # ── 删除团队 ──────────────────────────────────────────────────────────

    def test_08_delete_team(self, api):
        """DELETE /teams/e2e-team-alpha -> 200"""
        resp = api.delete(f"/teams/{TEAM_NAME}")
        assert resp.status_code == 200, f"删除失败: {resp.text}"

    def test_09_verify_team_deleted(self, api):
        """GET /teams/e2e-team-alpha -> 404，确认已删除"""
        resp = api.get(f"/teams/{TEAM_NAME}")
        assert resp.status_code == 404

    # ── teardown：清理剩余测试数据 ────────────────────────────────────────

    def test_99_cleanup(self, api):
        """清理测试团队和前置角色"""
        # 清理团队
        resp = api.delete(f"/teams/{TEAM_NAME}")
        assert resp.status_code in (200, 404), f"清理 {TEAM_NAME} 失败: {resp.text}"
        # 清理前置角色
        for role in _PREREQUISITE_ROLES:
            resp = api.delete(f"/roles/{role['name']}")
            assert resp.status_code in (200, 404), f"清理角色 {role['name']} 失败: {resp.text}"
