"""Skill 模块 E2E API 测试

测试范围：
- GET /api/v1/skills - 获取 skill 列表
- GET /api/v1/skills/{skill_name} - 获取单个 skill
- GET /api/v1/skills/not_exist - 404 场景

运行前提：服务器已启动（uvicorn agents_hub.api.app:app --port 8000）
运行命令：pytest tests/e2e/api/test_skill_e2e.py -v
"""

EXPECTED_SKILLS = ["deep-answer", "grill-with-docs", "hand-off", "knowledge-research"]


class TestSkillE2E:
    """Skill API 端到端测试"""

    def test_list_skills(self, api):
        """GET /skills -> 200, 返回包含所有预置 skill 的列表"""
        resp = api.get("/skills")
        assert resp.status_code == 200

        data = resp.json()
        assert isinstance(data, list)

        names = [s["name"] for s in data]
        for skill in EXPECTED_SKILLS:
            assert skill in names, f"缺少 skill: {skill}"

    def test_get_skill_by_name(self, api):
        """GET /skills/deep-answer -> 200, 返回正确的 skill 信息"""
        resp = api.get("/skills/deep-answer")
        assert resp.status_code == 200

        data = resp.json()
        assert data["name"] == "deep-answer"

    def test_get_skill_not_found(self, api):
        """GET /skills/not_exist -> 404"""
        resp = api.get("/skills/not_exist")
        assert resp.status_code == 404
