# Skills 管理模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现全局 Skill 资源管理系统，提供 skills 的增删查功能和 REST API

**Architecture:** 独立的 skills 模块（领域层）+ API 层（routes/services/schemas），通过扫描文件系统和解析 SKILL.md frontmatter 实现 skill 管理

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, PyYAML, pytest

---

## 文件结构

本实现将创建以下文件：

**Skills 模块（领域层）**：
- `agents_hub/skills/__init__.py` - 模块初始化
- `agents_hub/skills/models.py` - SkillInfo 数据模型
- `agents_hub/skills/exceptions.py` - Skill 异常类
- `agents_hub/skills/skill_manager.py` - SkillManager 核心逻辑

**API 层**：
- `agents_hub/api/schemas/skills.py` - Pydantic 数据模型
- `agents_hub/api/services/skill_service.py` - 应用服务层
- `agents_hub/api/routes/skills.py` - REST API 路由

**测试文件**：
- `tests/skills/test_skill_manager.py` - SkillManager 单元测试
- `tests/api/test_skills_api.py` - API 集成测试

---

### Task 1: Skills 模块基础结构

**Files:**
- Create: `agents_hub/skills/__init__.py`
- Create: `agents_hub/skills/models.py`
- Create: `agents_hub/skills/exceptions.py`

- [ ] **Step 1: 创建 skills 模块目录**

```bash
mkdir -p agents_hub/skills
```

- [ ] **Step 2: 创建 models.py（数据模型）**

```python
# agents_hub/skills/models.py
from dataclasses import dataclass


@dataclass
class SkillInfo:
    """Skill 信息（从 SKILL.md frontmatter 解析）"""

    name: str  # skill 名称
    description: str  # skill 描述
    path: str  # skill 目录的绝对路径（内部使用）
```

- [ ] **Step 3: 创建 exceptions.py（异常类）**

```python
# agents_hub/skills/exceptions.py
class SkillNotFoundError(Exception):
    """Skill 不存在"""

    pass


class InvalidSkillError(Exception):
    """无效的 Skill（SKILL.md 格式错误）"""

    pass
```

- [ ] **Step 4: 创建 __init__.py（模块导出）**

```python
# agents_hub/skills/__init__.py
from agents_hub.skills.models import SkillInfo
from agents_hub.skills.exceptions import SkillNotFoundError, InvalidSkillError

__all__ = ["SkillInfo", "SkillNotFoundError", "InvalidSkillError"]
```

- [ ] **Step 5: 提交基础结构**

```bash
git add agents_hub/skills/
git commit -m "feat(skills): add skills module basic structure

- Add SkillInfo data model
- Add SkillNotFoundError and InvalidSkillError exceptions
- Add module __init__.py"
```

### Task 2: SkillManager - frontmatter 解析功能

**Files:**
- Create: `agents_hub/skills/skill_manager.py`
- Create: `tests/skills/test_skill_manager.py`
- Create: `tests/skills/fixtures/` (测试数据)

- [ ] **Step 1: 创建测试数据目录和 fixture skill**

```bash
mkdir -p tests/skills/fixtures/valid-skill
```

```markdown
# tests/skills/fixtures/valid-skill/SKILL.md
---
name: test-skill
description: A test skill for unit testing
---

# Test Skill

This is a test skill.
```

- [ ] **Step 2: 编写 _parse_skill_md 的失败测试**

```python
# tests/skills/test_skill_manager.py
import pytest
from pathlib import Path
from agents_hub.skills.skill_manager import SkillManager
from agents_hub.skills.exceptions import InvalidSkillError


def test_parse_skill_md_missing_file():
    """测试：SKILL.md 文件不存在"""
    manager = SkillManager()
    invalid_path = Path("tests/skills/fixtures/nonexistent")
    
    with pytest.raises(InvalidSkillError, match="SKILL.md not found"):
        manager._parse_skill_md(invalid_path)
```

- [ ] **Step 3: 运行测试，验证失败**

Run: `pytest tests/skills/test_skill_manager.py::test_parse_skill_md_missing_file -v`
Expected: FAIL with "SkillManager has no attribute '_parse_skill_md'"

- [ ] **Step 4: 实现 SkillManager 基础结构和 _parse_skill_md**

```python
# agents_hub/skills/skill_manager.py
import yaml
from pathlib import Path
from agents_hub.config import config
from agents_hub.skills.models import SkillInfo
from agents_hub.skills.exceptions import SkillNotFoundError, InvalidSkillError


class SkillManager:
    """全局 Skill 管理器"""

    def __init__(self):
        self.skills_root = config.data_path / "skills"
        self.skills_root.mkdir(parents=True, exist_ok=True)

    def _parse_skill_md(self, skill_path: Path) -> SkillInfo:
        """解析 SKILL.md 的 frontmatter"""
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            raise InvalidSkillError(f"SKILL.md not found in {skill_path}")

        content = skill_md.read_text(encoding="utf-8")

        # 解析 frontmatter（格式：--- ... ---）
        if not content.startswith("---"):
            raise InvalidSkillError(f"Invalid SKILL.md format in {skill_path}")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise InvalidSkillError(f"Invalid SKILL.md format in {skill_path}")

        frontmatter = yaml.safe_load(parts[1])

        if "name" not in frontmatter or "description" not in frontmatter:
            raise InvalidSkillError(
                f"Missing name or description in {skill_path}/SKILL.md"
            )

        return SkillInfo(
            name=frontmatter["name"],
            description=frontmatter["description"],
            path=str(skill_path),
        )
```

- [ ] **Step 5: 运行测试，验证通过**

Run: `pytest tests/skills/test_skill_manager.py::test_parse_skill_md_missing_file -v`
Expected: PASS

- [ ] **Step 6: 添加更多 _parse_skill_md 测试用例**

```python
# tests/skills/test_skill_manager.py (追加)

def test_parse_skill_md_invalid_format():
    """测试：SKILL.md 格式错误（没有 frontmatter）"""
    manager = SkillManager()
    # 创建无效的 SKILL.md
    invalid_path = Path("tests/skills/fixtures/invalid-format")
    invalid_path.mkdir(parents=True, exist_ok=True)
    (invalid_path / "SKILL.md").write_text("No frontmatter here", encoding="utf-8")
    
    with pytest.raises(InvalidSkillError, match="Invalid SKILL.md format"):
        manager._parse_skill_md(invalid_path)


def test_parse_skill_md_missing_fields():
    """测试：SKILL.md 缺少必需字段"""
    manager = SkillManager()
    # 创建缺少字段的 SKILL.md
    missing_path = Path("tests/skills/fixtures/missing-fields")
    missing_path.mkdir(parents=True, exist_ok=True)
    (missing_path / "SKILL.md").write_text(
        "---\nname: test\n---\nContent", encoding="utf-8"
    )
    
    with pytest.raises(InvalidSkillError, match="Missing name or description"):
        manager._parse_skill_md(missing_path)


def test_parse_skill_md_success():
    """测试：成功解析 SKILL.md"""
    manager = SkillManager()
    valid_path = Path("tests/skills/fixtures/valid-skill")
    
    skill_info = manager._parse_skill_md(valid_path)
    
    assert skill_info.name == "test-skill"
    assert skill_info.description == "A test skill for unit testing"
    assert str(valid_path) in skill_info.path
```

- [ ] **Step 7: 运行所有测试，验证通过**

Run: `pytest tests/skills/test_skill_manager.py -v`
Expected: 4 tests PASS

- [ ] **Step 8: 提交 frontmatter 解析功能**

```bash
git add agents_hub/skills/skill_manager.py tests/skills/
git commit -m "feat(skills): add SKILL.md frontmatter parsing

- Implement SkillManager._parse_skill_md()
- Parse YAML frontmatter from SKILL.md
- Validate required fields (name, description)
- Add comprehensive unit tests"
```

### Task 3: SkillManager - list_skills 功能

**Files:**
- Modify: `agents_hub/skills/skill_manager.py`
- Modify: `tests/skills/test_skill_manager.py`

- [ ] **Step 1: 编写 list_skills 的失败测试**

```python
# tests/skills/test_skill_manager.py (追加)

def test_list_skills_empty():
    """测试：空的 skills 目录"""
    manager = SkillManager()
    # 临时修改 skills_root 为空目录
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        manager.skills_root = Path(tmpdir)
        skills = manager.list_skills()
        assert skills == []


def test_list_skills_with_valid_skills():
    """测试：列出有效的 skills"""
    manager = SkillManager()
    # 使用 fixtures 目录
    manager.skills_root = Path("tests/skills/fixtures")
    
    skills = manager.list_skills()
    
    # 应该只包含 valid-skill（跳过无效的）
    assert len(skills) >= 1
    skill_names = [s.name for s in skills]
    assert "test-skill" in skill_names
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `pytest tests/skills/test_skill_manager.py::test_list_skills_empty -v`
Expected: FAIL with "SkillManager has no attribute 'list_skills'"

- [ ] **Step 3: 实现 list_skills 方法**

```python
# agents_hub/skills/skill_manager.py (在 SkillManager 类中添加)

    def list_skills(self) -> list[SkillInfo]:
        """列出所有 skills"""
        skills = []
        for skill_dir in self.skills_root.iterdir():
            if skill_dir.is_dir():
                try:
                    skill_info = self._parse_skill_md(skill_dir)
                    skills.append(skill_info)
                except InvalidSkillError:
                    # 跳过无效的 skill 目录
                    continue
        return skills
```

- [ ] **Step 4: 运行测试，验证通过**

Run: `pytest tests/skills/test_skill_manager.py::test_list_skills_empty tests/skills/test_skill_manager.py::test_list_skills_with_valid_skills -v`
Expected: 2 tests PASS

- [ ] **Step 5: 提交 list_skills 功能**

```bash
git add agents_hub/skills/skill_manager.py tests/skills/test_skill_manager.py
git commit -m "feat(skills): add list_skills functionality

- Implement SkillManager.list_skills()
- Scan skills directory and parse all SKILL.md files
- Skip invalid skills gracefully
- Add unit tests"
```

### Task 4: SkillManager - get_skill 和 delete_skill 功能

**Files:**
- Modify: `agents_hub/skills/skill_manager.py`
- Modify: `tests/skills/test_skill_manager.py`

- [ ] **Step 1: 编写 get_skill 的失败测试**

```python
# tests/skills/test_skill_manager.py (追加)

def test_get_skill_not_found():
    """测试：获取不存在的 skill"""
    manager = SkillManager()
    
    with pytest.raises(SkillNotFoundError, match="Skill 'nonexistent' not found"):
        manager.get_skill("nonexistent")


def test_get_skill_success():
    """测试：成功获取 skill"""
    manager = SkillManager()
    manager.skills_root = Path("tests/skills/fixtures")
    
    skill = manager.get_skill("valid-skill")
    
    assert skill.name == "test-skill"
    assert skill.description == "A test skill for unit testing"
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `pytest tests/skills/test_skill_manager.py::test_get_skill_not_found -v`
Expected: FAIL with "SkillManager has no attribute 'get_skill'"

- [ ] **Step 3: 实现 get_skill 方法**

```python
# agents_hub/skills/skill_manager.py (在 SkillManager 类中添加)

    def get_skill(self, skill_name: str) -> SkillInfo:
        """获取单个 skill 信息"""
        skill_path = self.skills_root / skill_name
        if not skill_path.exists():
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        return self._parse_skill_md(skill_path)
```

- [ ] **Step 4: 运行测试，验证通过**

Run: `pytest tests/skills/test_skill_manager.py::test_get_skill_not_found tests/skills/test_skill_manager.py::test_get_skill_success -v`
Expected: 2 tests PASS

- [ ] **Step 5: 编写 delete_skill 的失败测试**

```python
# tests/skills/test_skill_manager.py (追加)

def test_delete_skill_not_found():
    """测试：删除不存在的 skill"""
    manager = SkillManager()
    
    with pytest.raises(SkillNotFoundError, match="Skill 'nonexistent' not found"):
        manager.delete_skill("nonexistent")


def test_delete_skill_success():
    """测试：成功删除 skill"""
    import tempfile
    import shutil
    
    manager = SkillManager()
    
    # 创建临时 skill 目录
    with tempfile.TemporaryDirectory() as tmpdir:
        manager.skills_root = Path(tmpdir)
        test_skill_path = manager.skills_root / "test-delete-skill"
        test_skill_path.mkdir()
        (test_skill_path / "SKILL.md").write_text(
            "---\nname: test\ndescription: test\n---\n", encoding="utf-8"
        )
        
        # 删除 skill
        manager.delete_skill("test-delete-skill")
        
        # 验证目录已删除
        assert not test_skill_path.exists()
```

- [ ] **Step 6: 运行测试，验证失败**

Run: `pytest tests/skills/test_skill_manager.py::test_delete_skill_not_found -v`
Expected: FAIL with "SkillManager has no attribute 'delete_skill'"

- [ ] **Step 7: 实现 delete_skill 方法**

```python
# agents_hub/skills/skill_manager.py (在 SkillManager 类中添加)
import shutil  # 添加到文件顶部的 import

    def delete_skill(self, skill_name: str) -> None:
        """删除 skill"""
        skill_path = self.skills_root / skill_name
        if not skill_path.exists():
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        shutil.rmtree(skill_path)
```

- [ ] **Step 8: 运行测试，验证通过**

Run: `pytest tests/skills/test_skill_manager.py::test_delete_skill_not_found tests/skills/test_skill_manager.py::test_delete_skill_success -v`
Expected: 2 tests PASS

- [ ] **Step 9: 提交 get_skill 和 delete_skill 功能**

```bash
git add agents_hub/skills/skill_manager.py tests/skills/test_skill_manager.py
git commit -m "feat(skills): add get_skill and delete_skill functionality

- Implement SkillManager.get_skill()
- Implement SkillManager.delete_skill()
- Add comprehensive unit tests"
```

### Task 5: SkillManager - add_skill_from_url 预留接口

**Files:**
- Modify: `agents_hub/skills/skill_manager.py`
- Modify: `tests/skills/test_skill_manager.py`

- [ ] **Step 1: 编写 add_skill_from_url 的失败测试**

```python
# tests/skills/test_skill_manager.py (追加)

def test_add_skill_from_url_not_implemented():
    """测试：add_skill_from_url 抛出 NotImplementedError"""
    manager = SkillManager()
    
    with pytest.raises(NotImplementedError, match="网络获取功能暂未实现"):
        manager.add_skill_from_url("https://example.com/skill.zip")
```

- [ ] **Step 2: 运行测试，验证失败**

Run: `pytest tests/skills/test_skill_manager.py::test_add_skill_from_url_not_implemented -v`
Expected: FAIL with "SkillManager has no attribute 'add_skill_from_url'"

- [ ] **Step 3: 实现 add_skill_from_url 方法（预留）**

```python
# agents_hub/skills/skill_manager.py (在 SkillManager 类中添加)

    def add_skill_from_url(self, url: str) -> SkillInfo:
        """从网络添加 skill（预留接口，暂不实现）"""
        raise NotImplementedError("网络获取功能暂未实现")
```

- [ ] **Step 4: 运行测试，验证通过**

Run: `pytest tests/skills/test_skill_manager.py::test_add_skill_from_url_not_implemented -v`
Expected: PASS

- [ ] **Step 5: 运行所有 SkillManager 测试**

Run: `pytest tests/skills/test_skill_manager.py -v`
Expected: All tests PASS

- [ ] **Step 6: 提交 add_skill_from_url 预留接口**

```bash
git add agents_hub/skills/skill_manager.py tests/skills/test_skill_manager.py
git commit -m "feat(skills): add add_skill_from_url placeholder

- Add add_skill_from_url() method that raises NotImplementedError
- Reserve interface for future network skill fetching
- Add unit test"
```

### Task 6: API Schemas - Pydantic 数据模型

**Files:**
- Create: `agents_hub/api/schemas/skills.py`

- [ ] **Step 1: 创建 API schemas 目录**

```bash
mkdir -p agents_hub/api/schemas
touch agents_hub/api/schemas/__init__.py
```

- [ ] **Step 2: 创建 skills.py（Pydantic 模型）**

```python
# agents_hub/api/schemas/skills.py
from pydantic import BaseModel
from agents_hub.skills.models import SkillInfo


class SkillResponse(BaseModel):
    """Skill 响应模型"""

    name: str
    description: str

    @classmethod
    def from_domain(cls, skill_info: SkillInfo) -> "SkillResponse":
        """从领域模型转换"""
        return cls(
            name=skill_info.name,
            description=skill_info.description,
        )


class SkillCreateRequest(BaseModel):
    """创建 Skill 请求（预留，暂不实现）"""

    url: str  # skill 的网络地址
```

- [ ] **Step 3: 提交 API schemas**

```bash
git add agents_hub/api/schemas/
git commit -m "feat(api): add skills API schemas

- Add SkillResponse for API responses
- Add SkillCreateRequest for future network fetching
- Add from_domain() converter"
```

### Task 7: API Service - 应用服务层

**Files:**
- Create: `agents_hub/api/services/skill_service.py`

- [ ] **Step 1: 创建 API services 目录**

```bash
mkdir -p agents_hub/api/services
touch agents_hub/api/services/__init__.py
```

- [ ] **Step 2: 创建 skill_service.py**

```python
# agents_hub/api/services/skill_service.py
from agents_hub.skills.skill_manager import SkillManager
from agents_hub.skills.models import SkillInfo


class SkillService:
    """Skills 应用服务层"""

    def __init__(self):
        self.skill_manager = SkillManager()

    def list_skills(self) -> list[SkillInfo]:
        """获取所有 skills"""
        return self.skill_manager.list_skills()

    def get_skill(self, skill_name: str) -> SkillInfo:
        """获取单个 skill"""
        return self.skill_manager.get_skill(skill_name)

    def delete_skill(self, skill_name: str) -> None:
        """删除 skill"""
        self.skill_manager.delete_skill(skill_name)

    def add_skill_from_url(self, url: str) -> SkillInfo:
        """从网络添加 skill（预留）"""
        return self.skill_manager.add_skill_from_url(url)
```

- [ ] **Step 3: 提交 API service**

```bash
git add agents_hub/api/services/
git commit -m "feat(api): add SkillService application layer

- Add SkillService to coordinate SkillManager
- Delegate all operations to SkillManager
- Prepare for future business logic (auth, audit, etc.)"
```

### Task 8: API Routes - REST API 端点

**Files:**
- Create: `agents_hub/api/routes/skills.py`

- [ ] **Step 1: 创建 API routes 目录**

```bash
mkdir -p agents_hub/api/routes
touch agents_hub/api/routes/__init__.py
```

- [ ] **Step 2: 创建 skills.py（REST API 路由）**

```python
# agents_hub/api/routes/skills.py
from fastapi import APIRouter, HTTPException
from agents_hub.api.services.skill_service import SkillService
from agents_hub.api.schemas.skills import SkillResponse, SkillCreateRequest
from agents_hub.skills.exceptions import SkillNotFoundError

router = APIRouter()


@router.get("/skills", response_model=list[SkillResponse])
async def list_skills():
    """获取所有 skills"""
    service = SkillService()
    skills = service.list_skills()
    return [SkillResponse.from_domain(s) for s in skills]


@router.get("/skills/{skill_name}", response_model=SkillResponse)
async def get_skill(skill_name: str):
    """获取单个 skill"""
    service = SkillService()
    try:
        skill = service.get_skill(skill_name)
        return SkillResponse.from_domain(skill)
    except SkillNotFoundError:
        raise HTTPException(status_code=404, detail="Skill not found")


@router.delete("/skills/{skill_name}")
async def delete_skill(skill_name: str):
    """删除 skill"""
    service = SkillService()
    try:
        service.delete_skill(skill_name)
        return {"message": "Skill deleted successfully"}
    except SkillNotFoundError:
        raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/skills", response_model=SkillResponse)
async def add_skill(request: SkillCreateRequest):
    """从网络添加 skill（预留接口）"""
    service = SkillService()
    try:
        skill = service.add_skill_from_url(request.url)
        return SkillResponse.from_domain(skill)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="功能暂未实现")
```

- [ ] **Step 3: 提交 API routes**

```bash
git add agents_hub/api/routes/
git commit -m "feat(api): add skills REST API routes

- Add GET /skills (list all skills)
- Add GET /skills/{skill_name} (get single skill)
- Add DELETE /skills/{skill_name} (delete skill)
- Add POST /skills (placeholder, returns 501)"
```

### Task 9: API 集成测试

**Files:**
- Create: `tests/api/test_skills_api.py`

- [ ] **Step 1: 创建 API 测试目录**

```bash
mkdir -p tests/api
touch tests/api/__init__.py
```

- [ ] **Step 2: 编写 API 集成测试**

```python
# tests/api/test_skills_api.py
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile


@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi import FastAPI
    from agents_hub.api.routes.skills import router
    
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


@pytest.fixture
def temp_skills_dir():
    """创建临时 skills 目录"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建测试 skill
        skill_path = Path(tmpdir) / "test-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Test skill\n---\n",
            encoding="utf-8"
        )
        yield tmpdir


def test_list_skills_empty(client, monkeypatch, temp_skills_dir):
    """测试：列出空的 skills"""
    from agents_hub.skills.skill_manager import SkillManager
    from agents_hub.config import config
    
    # Mock config.data_path
    monkeypatch.setattr(config, "data_path", Path(temp_skills_dir))
    
    response = client.get("/api/skills")
    assert response.status_code == 200
    # 应该返回 test-skill
    data = response.json()
    assert len(data) >= 1


def test_get_skill_success(client, monkeypatch, temp_skills_dir):
    """测试：获取单个 skill"""
    from agents_hub.config import config
    monkeypatch.setattr(config, "data_path", Path(temp_skills_dir))
    
    response = client.get("/api/skills/test-skill")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-skill"
    assert data["description"] == "Test skill"


def test_get_skill_not_found(client):
    """测试：获取不存在的 skill"""
    response = client.get("/api/skills/nonexistent")
    assert response.status_code == 404
    assert "Skill not found" in response.json()["detail"]


def test_delete_skill_success(client, monkeypatch, temp_skills_dir):
    """测试：删除 skill"""
    from agents_hub.config import config
    monkeypatch.setattr(config, "data_path", Path(temp_skills_dir))
    
    response = client.delete("/api/skills/test-skill")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]


def test_delete_skill_not_found(client):
    """测试：删除不存在的 skill"""
    response = client.delete("/api/skills/nonexistent")
    assert response.status_code == 404


def test_add_skill_not_implemented(client):
    """测试：添加 skill（未实现）"""
    response = client.post("/api/skills", json={"url": "https://example.com"})
    assert response.status_code == 501
    assert "暂未实现" in response.json()["detail"]
```

- [ ] **Step 3: 运行 API 集成测试**

Run: `pytest tests/api/test_skills_api.py -v`
Expected: All tests PASS

- [ ] **Step 4: 提交 API 集成测试**

```bash
git add tests/api/
git commit -m "test(api): add skills API integration tests

- Test all API endpoints (GET, DELETE, POST)
- Test success and error cases
- Use FastAPI TestClient"
```

### Task 10: 完整测试和文档更新

**Files:**
- Modify: `agents_hub/skills/__init__.py`
- Create/Modify: 相关文档

- [ ] **Step 1: 更新 skills 模块导出**

```python
# agents_hub/skills/__init__.py
from agents_hub.skills.models import SkillInfo
from agents_hub.skills.exceptions import SkillNotFoundError, InvalidSkillError
from agents_hub.skills.skill_manager import SkillManager

__all__ = [
    "SkillInfo",
    "SkillNotFoundError",
    "InvalidSkillError",
    "SkillManager",
]
```

- [ ] **Step 2: 运行完整测试套件**

Run: `pytest tests/skills/ tests/api/test_skills_api.py -v --cov=agents_hub/skills --cov=agents_hub/api`
Expected: All tests PASS with good coverage

- [ ] **Step 3: 运行代码质量检查**

Run: `ruff check agents_hub/skills/ agents_hub/api/`
Expected: No errors

Run: `ruff format agents_hub/skills/ agents_hub/api/`
Expected: All files formatted

Run: `mypy agents_hub/skills/ agents_hub/api/`
Expected: No type errors

- [ ] **Step 4: 提交最终更新**

```bash
git add agents_hub/skills/__init__.py
git commit -m "feat(skills): finalize skills module

- Update module exports
- All tests passing
- Code quality checks passed"
```

---

## 验证清单

完成所有任务后，验证以下功能：

- [ ] SkillManager 可以扫描和列出所有 skills
- [ ] SkillManager 可以解析 SKILL.md frontmatter
- [ ] SkillManager 可以获取单个 skill
- [ ] SkillManager 可以删除 skill
- [ ] API 端点 GET /api/skills 正常工作
- [ ] API 端点 GET /api/skills/{name} 正常工作
- [ ] API 端点 DELETE /api/skills/{name} 正常工作
- [ ] API 端点 POST /api/skills 返回 501
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 代码质量检查通过

---

## 自审结果

✅ **占位符检查**：无 TBD、TODO，所有代码和命令都是完整的
✅ **规格覆盖**：所有设计文档中的功能都已实现
  - SkillManager 的所有方法（list_skills, get_skill, delete_skill, add_skill_from_url）
  - API schemas（SkillResponse, SkillCreateRequest）
  - API service（SkillService）
  - API routes（4 个端点）
✅ **类型一致性**：所有方法签名、返回类型、字段名称在各任务中保持一致
✅ **测试覆盖**：每个功能都有对应的单元测试或集成测试

