"""Role 模块 E2E API 测试

测试 Role 模块的完整 CRUD 流程以及技能关联功能。
假设服务器已启动在 localhost:8000。

运行方式：
    pytest tests/e2e/api/test_role_e2e.py -v
"""



# ── 测试数据常量 ──────────────────────────────────────────────────────────

LEADER = {
    "name": "e2e_leader",
    "platform": "claude",
    "type": "leader",
    "abilities": ["code_review", "task_assignment"],
}

WORKER_A = {
    "name": "e2e_worker_a",
    "platform": "claude",
    "type": "team_member",
    "abilities": ["coding"],
}

WORKER_B = {
    "name": "e2e_worker_b",
    "platform": "codex",
    "type": "team_member",
    "abilities": ["testing"],
}

# 需要在 teardown 中清理的角色名称
_ALL_TEST_ROLES = [LEADER["name"], WORKER_A["name"], WORKER_B["name"]]


# ── 辅助函数 ──────────────────────────────────────────────────────────────

def _cleanup_roles(api):
    """尽力清理所有测试创建的角色，忽略不存在的情况"""
    for name in _ALL_TEST_ROLES:
        api.delete(f"/roles/{name}")


# ── 测试类 ────────────────────────────────────────────────────────────────

class TestRoleE2E:
    """按顺序测试 Role 模块的核心流程

    使用 test_XX_ 前缀控制执行顺序，确保依赖关系正确。
    """

    # ── 创建角色 ──────────────────────────────────────────────────────────

    def test_01_create_leader(self, api):
        """创建 e2e_leader 角色 -> 201，验证返回 name"""
        resp = api.post("/roles", json=LEADER)
        assert resp.status_code == 201, f"创建失败: {resp.text}"
        data = resp.json()
        assert data["name"] == "e2e_leader"

    def test_02_create_worker_a(self, api):
        """创建 e2e_worker_a 角色 -> 201"""
        resp = api.post("/roles", json=WORKER_A)
        assert resp.status_code == 201, f"创建失败: {resp.text}"

    def test_03_create_worker_b(self, api):
        """创建 e2e_worker_b 角色 -> 201"""
        resp = api.post("/roles", json=WORKER_B)
        assert resp.status_code == 201, f"创建失败: {resp.text}"

    # ── 查询角色 ──────────────────────────────────────────────────────────

    def test_04_list_roles_contains_leader(self, api):
        """GET /roles -> 200，列表中包含 e2e_leader"""
        resp = api.get("/roles")
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()]
        assert "e2e_leader" in names, f"列表中未找到 e2e_leader, 实际: {names}"

    def test_05_get_role_by_name(self, api):
        """GET /roles/e2e_leader -> 200，返回正确的 name"""
        resp = api.get("/roles/e2e_leader")
        assert resp.status_code == 200
        assert resp.json()["name"] == "e2e_leader"

    def test_06_get_nonexistent_role(self, api):
        """GET /roles/not_exist -> 404"""
        resp = api.get("/roles/not_exist")
        assert resp.status_code == 404

    # ── 更新角色 ──────────────────────────────────────────────────────────

    def test_07_patch_leader_description(self, api):
        """PATCH /roles/e2e_leader 更新 description -> 200"""
        resp = api.patch("/roles/e2e_leader", json={"description": "updated by e2e"})
        assert resp.status_code == 200, f"更新失败: {resp.text}"

    # ── 头像列表 ──────────────────────────────────────────────────────────

    def test_08_list_avatars(self, api):
        """GET /roles/avatars -> 200"""
        resp = api.get("/roles/avatars")
        assert resp.status_code == 200

    # ── 技能关联 ──────────────────────────────────────────────────────────

    def test_09_add_skill_to_leader(self, api):
        """POST /roles/e2e_leader/skills 添加 deep-answer -> 201"""
        resp = api.post("/roles/e2e_leader/skills", json={"skill_id": "deep-answer"})
        assert resp.status_code == 201, f"添加技能失败: {resp.text}"

    def test_10_get_leader_skills(self, api):
        """GET /roles/e2e_leader -> 200，验证 skills 字段存在"""
        resp = api.get("/roles/e2e_leader")
        assert resp.status_code == 200
        data = resp.json()
        assert "skills" in data

    def test_11_remove_skill_from_leader(self, api):
        """DELETE /roles/e2e_leader/skills/deep-answer -> 200"""
        resp = api.delete("/roles/e2e_leader/skills/deep-answer")
        assert resp.status_code == 200, f"删除技能失败: {resp.text}"

    # ── 删除角色 ──────────────────────────────────────────────────────────

    def test_12_delete_worker_b(self, api):
        """DELETE /roles/e2e_worker_b -> 200"""
        resp = api.delete("/roles/e2e_worker_b")
        assert resp.status_code == 200, f"删除失败: {resp.text}"

    def test_13_verify_worker_b_deleted(self, api):
        """GET /roles/e2e_worker_b -> 404，确认已删除"""
        resp = api.get("/roles/e2e_worker_b")
        assert resp.status_code == 404

    # ── teardown：清理剩余测试数据 ────────────────────────────────────────

    def test_99_cleanup(self, api):
        """清理剩余的测试角色（e2e_leader, e2e_worker_a）"""
        for name in [LEADER["name"], WORKER_A["name"]]:
            resp = api.delete(f"/roles/{name}")
            # 忽略已不存在的情况
            assert resp.status_code in (200, 404), f"清理 {name} 失败: {resp.text}"
