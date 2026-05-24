# Role Config 模块实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现角色配置模块，支持角色的 CRUD、Skill 管理、权限配置和 RoleConfig 构造

**Architecture:** 在 `agents_hub/agents/` 下创建 RoleManager 和 Role 类，RoleManager 负责角色生命周期管理，Role 负责单个角色的配置管理和 RoleConfig 构造。数据存储在 `local_data/agents/` 目录下。

**Tech Stack:** Python 3.11+, dataclasses, pathlib, pytest

---

## 文件结构

```
agents_hub/
├── agent_bridge/
│   └── config.py          # 修改: 移除 RoleConfig 的 system_prompt 和 skills
└── agents/
    ├── __init__.py
    ├── models.py          # 数据结构定义 (RoleInfo, SkillInfo)
    ├── exceptions.py      # 自定义异常类
    ├── role.py            # Role 类
    └── role_manager.py    # RoleManager 类

tests/
└── unit/
    └── agents/
        ├── __init__.py
        ├── test_role.py
        └── test_role_manager.py
```

---

### Task 0: 修改现有 RoleConfig 定义

**Files:**
- Modify: `agents_hub/agent_bridge/config.py`

- [ ] **Step 1: 读取现有 config.py**

```python
# 当前内容 (agents_hub/agent_bridge/config.py):
"""配置数据类和平台枚举"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List
from enum import Enum

# CLI 命令路径
CODEX_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
CLAUDE_COMMAND = str(Path.home() / ".local" / "bin" / "claude")


class AgentPlatform(Enum):
    """Agent 平台枚举"""
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass
class RoleConfig:
    """角色配置"""
    platform: AgentPlatform    # 平台类型
    system_prompt: str         # system prompt 内容
    skills: List[str]          # skill 列表

    # Codex 专用字段
    codex_home: Optional[str] = None  # CODEX_HOME 路径

    # Claude 专用字段
    claude_config_dir: Optional[str] = None  # CLAUDE_CONFIG_DIR 路径
```

- [ ] **Step 2: 修改 RoleConfig，移除 system_prompt 和 skills**

```python
"""配置数据类和平台枚举"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from enum import Enum

# CLI 命令路径
CODEX_COMMAND = str(Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd")
CLAUDE_COMMAND = str(Path.home() / ".local" / "bin" / "claude")


class AgentPlatform(Enum):
    """Agent 平台枚举"""
    CLAUDE = "claude"
    CODEX = "codex"


@dataclass
class RoleConfig:
    """角色配置 - 给 agent_bridge 使用的运行时配置

    注意: system_prompt 和 skills 由 CLI 从目录自动加载，不在此配置中
    """
    platform: AgentPlatform    # 平台类型

    # Codex 专用字段
    codex_home: Optional[str] = None  # CODEX_HOME 路径

    # Claude 专用字段
    claude_config_dir: Optional[str] = None  # CLAUDE_CONFIG_DIR 路径
```

- [ ] **Step 3: 检查并更新引用 RoleConfig 的代码**

Run: `grep -r "system_prompt\|skills" agents_hub/ --include="*.py" | grep -i "roleconfig"`

需要更新的文件:
- `agents_hub/agent_bridge/bridge.py` - 如果有使用 system_prompt 或 skills

- [ ] **Step 4: 运行现有测试确保不破坏**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 5: 提交**

```bash
git add agents_hub/agent_bridge/config.py
git commit -m "refactor(config): remove system_prompt and skills from RoleConfig per CONTEXT.md"
```

---

### Task 1: 创建数据结构和异常定义

**Files:**
- Create: `agents_hub/agents/__init__.py`
- Create: `agents_hub/agents/models.py`
- Create: `agents_hub/agents/exceptions.py`

- [ ] **Step 1: 创建 agents 模块目录和 __init__.py**

```python
"""角色配置模块"""

from agents_hub.agents.role import Role
from agents_hub.agents.role_manager import RoleManager
from agents_hub.agents.models import RoleInfo, SkillInfo
from agents_hub.agents.exceptions import RoleNotFoundError, RoleAlreadyExistsError, PlatformConfigNotFoundError

__all__ = [
    "Role",
    "RoleManager",
    "RoleInfo",
    "SkillInfo",
    "RoleNotFoundError",
    "RoleAlreadyExistsError",
    "PlatformConfigNotFoundError",
]
```

- [ ] **Step 2: 创建 exceptions.py 定义自定义异常**

```python
"""角色配置模块的自定义异常"""


class RoleError(Exception):
    """角色配置异常基类"""
    pass


class RoleNotFoundError(RoleError):
    """角色不存在"""
    pass


class RoleAlreadyExistsError(RoleError):
    """角色已存在"""
    pass


class PlatformConfigNotFoundError(RoleError):
    """平台配置目录不存在 (如 ~/.claude 或 ~/.codex)"""
    pass


class SkillNotFoundError(RoleError):
    """Skill 不存在"""
    pass


class SkillAlreadyExistsError(RoleError):
    """Skill 已存在于角色中"""
    pass
```

- [ ] **Step 3: 创建 models.py 定义数据结构**

```python
"""角色配置模块的数据结构定义"""

from dataclasses import dataclass
from typing import Optional, List, Literal
from agents_hub.agent_bridge.config import AgentPlatform


@dataclass
class RoleInfo:
    """角色摘要信息"""
    name: str
    platform: AgentPlatform
    avatar: Optional[str]
    abilities: List[str]
    type: Optional[str] = None  # "leader" | "team_member" | None
    scope: Optional[List[str]] = None  # 所属群聊列表


@dataclass
class SkillInfo:
    """Skill 摘要信息"""
    id: str           # skill 标识
    name: str         # skill 名称
    description: str  # skill 描述
```

- [ ] **Step 4: 验证模块可导入**

Run: `python -c "from agents_hub.agents.models import RoleInfo, SkillInfo, PermissionsConfig; from agents_hub.agents.exceptions import RoleNotFoundError; print('Import OK')"`
Expected: `Import OK`

- [ ] **Step 5: 提交**

```bash
git add agents_hub/agents/__init__.py agents_hub/agents/models.py agents_hub/agents/exceptions.py
git commit -m "feat(agents): add data structures, exceptions, and public API exports"
```

---

### Task 2: 创建 Role 类

**Files:**
- Create: `agents_hub/agents/role.py`
- Create: `tests/unit/agents/__init__.py`
- Create: `tests/unit/agents/test_role.py`

- [ ] **Step 1: 创建测试目录和 __init__.py**

```python
# tests/unit/agents/__init__.py
```

- [ ] **Step 2: 编写 Role 类的测试**

```python
"""Role 类的单元测试"""

import json
import pytest
from pathlib import Path
from agents_hub.agents.role import Role
from agents_hub.agents.models import RoleInfo, SkillInfo
from agents_hub.agents.exceptions import SkillNotFoundError, SkillAlreadyExistsError
from agents_hub.agent_bridge.config import AgentPlatform


@pytest.fixture
def role_dir(tmp_path):
    """创建测试用的角色目录"""
    role_dir = tmp_path / "local_data" / "agents" / "test_role"
    role_dir.mkdir(parents=True)
    work_root = role_dir / "work_root"
    work_root.mkdir()
    (work_root / "skills").mkdir()
    return role_dir


@pytest.fixture
def claude_role(role_dir):
    """创建 Claude 平台的测试角色"""
    role_json = {
        "name": "test_role",
        "platform": "claude",
        "avatar": None,
        "abilities": ["coding", "review"],
        "type": None,
        "scope": None,
        "skills": []
    }
    (role_dir / "role.json").write_text(json.dumps(role_json, ensure_ascii=False), encoding="utf-8")
    (role_dir / "work_root" / "CLAUDE.md").write_text("# Test Role", encoding="utf-8")
    return Role(role_dir)


def test_get_info(claude_role):
    """测试获取角色摘要信息"""
    info = claude_role.get_info()
    assert isinstance(info, RoleInfo)
    assert info.name == "test_role"
    assert info.platform == AgentPlatform.CLAUDE
    assert info.avatar is None
    assert info.abilities == ["coding", "review"]
    assert info.type is None
    assert info.scope is None


def test_update_abilities(claude_role):
    """测试更新能力标签"""
    claude_role.update_abilities(["coding", "testing", "documentation"])
    info = claude_role.get_info()
    assert info.abilities == ["coding", "testing", "documentation"]

    # 验证 role.json 已更新
    role_json = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert role_json["abilities"] == ["coding", "testing", "documentation"]


def test_update_avatar(claude_role):
    """测试更新头像"""
    avatar_dir = claude_role.role_dir / "avatar"
    avatar_dir.mkdir(exist_ok=True)
    (avatar_dir / "test_avatar.png").write_bytes(b"fake image")

    claude_role.update_avatar("test_avatar.png")
    info = claude_role.get_info()
    assert info.avatar == "test_avatar.png"


def test_list_skills_empty(claude_role):
    """测试列出空的 skills"""
    skills = claude_role.list_skills()
    assert skills == []


def test_add_skill(claude_role):
    """测试添加 skill"""
    # 创建全局 skill 库
    global_skills_dir = claude_role.role_dir.parent.parent / "skills" / "test_skill"
    global_skills_dir.mkdir(parents=True)
    (global_skills_dir / "skill.json").write_text(json.dumps({
        "id": "test_skill",
        "name": "Test Skill",
        "description": "A test skill"
    }), encoding="utf-8")

    claude_role.add_skill("test_skill")
    skills = claude_role.list_skills()
    assert len(skills) == 1
    assert skills[0].id == "test_skill"


def test_add_skill_already_exists(claude_role):
    """测试添加已存在的 skill"""
    # 先创建一个 skill
    skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    skill_dir.mkdir(parents=True)

    with pytest.raises(SkillAlreadyExistsError):
        claude_role.add_skill("test_skill")


def test_remove_skill(claude_role):
    """测试移除 skill"""
    # 先添加一个 skill
    skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "skill.json").write_text(json.dumps({
        "id": "test_skill",
        "name": "Test Skill",
        "description": "A test skill"
    }), encoding="utf-8")

    # 更新 role.json 中的 skills
    role_json = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    role_json["skills"] = ["test_skill"]
    (claude_role.role_dir / "role.json").write_text(json.dumps(role_json), encoding="utf-8")

    claude_role.remove_skill("test_skill")
    skills = claude_role.list_skills()
    assert len(skills) == 0


def test_remove_skill_not_found(claude_role):
    """测试移除不存在的 skill"""
    with pytest.raises(SkillNotFoundError):
        claude_role.remove_skill("nonexistent_skill")


def test_get_role_config(claude_role):
    """测试构造 RoleConfig"""
    config = claude_role.get_role_config()
    assert config.platform == AgentPlatform.CLAUDE
    assert config.claude_config_dir == str(claude_role.role_dir / "work_root")
    assert config.codex_home is None


def test_get_permissions_config(claude_role):
    """测试获取权限配置"""
    # 创建 settings.json
    settings = {
        "permissions": {
            "allow": ["Read"],
            "deny": ["Bash"],
            "ask": ["Write"]
        }
    }
    (claude_role.role_dir / "work_root" / "settings.json").write_text(
        json.dumps(settings), encoding="utf-8"
    )

    config = claude_role.get_permissions_config()
    assert "permissions" in config
    assert config["permissions"]["allow"] == ["Read"]


def test_update_permissions_config(claude_role):
    """测试更新权限配置"""
    # 创建初始 settings.json
    settings = {"permissions": {"allow": ["Read"]}}
    (claude_role.role_dir / "work_root" / "settings.json").write_text(
        json.dumps(settings), encoding="utf-8"
    )

    # 更新配置
    new_config = {"permissions": {"allow": ["Read", "Write"], "deny": ["Bash"]}}
    claude_role.update_permissions_config(new_config)

    # 验证更新
    updated = json.loads((claude_role.role_dir / "work_root" / "settings.json").read_text(encoding="utf-8"))
    assert updated["permissions"]["allow"] == ["Read", "Write"]
    assert updated["permissions"]["deny"] == ["Bash"]
```

- [ ] **Step 3: 运行测试验证失败**

Run: `pytest tests/unit/agents/test_role.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agents_hub.agents.role'"

- [ ] **Step 4: 实现 Role 类**

```python
"""Role 类 - 单个角色的配置管理"""

import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any

from agents_hub.agent_bridge.config import AgentPlatform, RoleConfig
from agents_hub.agents.models import RoleInfo, SkillInfo
from agents_hub.agents.exceptions import SkillNotFoundError, SkillAlreadyExistsError


class Role:
    """单个角色的配置管理"""

    def __init__(self, role_dir: Path):
        """
        Args:
            role_dir: 角色目录路径 (local_data/agents/<role_name>)
        """
        self.role_dir = role_dir
        self._role_json_path = role_dir / "role.json"
        self._work_root = role_dir / "work_root"

    def _read_role_json(self) -> Dict[str, Any]:
        """读取 role.json"""
        return json.loads(self._role_json_path.read_text(encoding="utf-8"))

    def _write_role_json(self, data: Dict[str, Any]) -> None:
        """写入 role.json"""
        self._role_json_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_info(self) -> RoleInfo:
        """返回角色摘要信息"""
        data = self._read_role_json()
        return RoleInfo(
            name=data["name"],
            platform=AgentPlatform(data["platform"]),
            avatar=data.get("avatar"),
            abilities=data.get("abilities", []),
            type=data.get("type"),
            scope=data.get("scope"),
        )

    def update_name(self, new_name: str) -> None:
        """更新角色名称，同步修改目录名和 role.json"""
        data = self._read_role_json()
        data["name"] = new_name
        self._write_role_json(data)

        # 重命名目录
        new_dir = self.role_dir.parent / new_name
        self.role_dir.rename(new_dir)
        self.role_dir = new_dir

    def update_avatar(self, avatar_path: str) -> None:
        """更新头像，将旧头像移入 history"""
        data = self._read_role_json()

        # 如果有旧头像，移入 history
        if data.get("avatar"):
            avatar_dir = self.role_dir / "avatar"
            history_files = list(avatar_dir.glob("history_*.png"))
            next_num = len(history_files) + 1
            old_avatar = avatar_dir / data["avatar"]
            if old_avatar.exists():
                old_avatar.rename(avatar_dir / f"history_{next_num:02d}.png")

        data["avatar"] = avatar_path
        self._write_role_json(data)

    def update_abilities(self, abilities: List[str]) -> None:
        """更新能力标签列表"""
        data = self._read_role_json()
        data["abilities"] = abilities
        self._write_role_json(data)

    def list_skills(self) -> List[SkillInfo]:
        """列出角色已启用的 skills"""
        skills_dir = self._work_root / "skills"
        if not skills_dir.exists():
            return []

        skills = []
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_json = skill_dir / "skill.json"
                if skill_json.exists():
                    data = json.loads(skill_json.read_text(encoding="utf-8"))
                    skills.append(SkillInfo(
                        id=data["id"],
                        name=data["name"],
                        description=data["description"]
                    ))
        return skills

    def add_skill(self, skill_id: str, global_skills_dir: Optional[Path] = None) -> None:
        """添加 skill，从全局 skill 库复制到 work_root/skills/

        Args:
            skill_id: skill 标识
            global_skills_dir: 全局 skill 库路径，默认为 local_data/skills
        """
        if global_skills_dir is None:
            global_skills_dir = self.role_dir.parent.parent / "skills"

        global_skill_dir = global_skills_dir / skill_id
        if not global_skill_dir.exists():
            raise SkillNotFoundError(f"Skill '{skill_id}' not found in global skill library")

        target_dir = self._work_root / "skills" / skill_id
        if target_dir.exists():
            raise SkillAlreadyExistsError(f"Skill '{skill_id}' already exists in role")

        shutil.copytree(global_skill_dir, target_dir)

        # 更新 role.json
        data = self._read_role_json()
        if "skills" not in data:
            data["skills"] = []
        data["skills"].append(skill_id)
        self._write_role_json(data)

    def remove_skill(self, skill_id: str) -> None:
        """移除 skill，从 work_root/skills/ 删除"""
        skill_dir = self._work_root / "skills" / skill_id
        if not skill_dir.exists():
            raise SkillNotFoundError(f"Skill '{skill_id}' not found in role")

        shutil.rmtree(skill_dir)

        # 更新 role.json
        data = self._read_role_json()
        if "skills" in data and skill_id in data["skills"]:
            data["skills"].remove(skill_id)
            self._write_role_json(data)

    def get_permissions_config(self) -> Dict[str, Any]:
        """读取平台特定的权限配置，返回原始字典"""
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])

        if platform == AgentPlatform.CLAUDE:
            settings_path = self._work_root / "settings.json"
        else:
            settings_path = self._work_root / "config.toml"

        if not settings_path.exists():
            return {}

        if platform == AgentPlatform.CLAUDE:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            # Codex 使用 TOML，这里简化处理
            return {}

    def update_permissions_config(self, config: Dict[str, Any]) -> None:
        """更新平台特定的权限配置"""
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])

        if platform == AgentPlatform.CLAUDE:
            settings_path = self._work_root / "settings.json"
            settings_path.write_text(
                json.dumps(config, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        else:
            # Codex 使用 TOML，这里简化处理
            pass

    def get_role_config(self) -> RoleConfig:
        """构造给 agent_bridge 使用的 RoleConfig"""
        data = self._read_role_json()
        platform = AgentPlatform(data["platform"])

        return RoleConfig(
            platform=platform,
            codex_home=str(self._work_root) if platform == AgentPlatform.CODEX else None,
            claude_config_dir=str(self._work_root) if platform == AgentPlatform.CLAUDE else None
        )
```

- [ ] **Step 5: 运行测试验证通过**

Run: `pytest tests/unit/agents/test_role.py -v`
Expected: All tests PASS

- [ ] **Step 6: 提交**

```bash
git add agents_hub/agents/role.py tests/unit/agents/__init__.py tests/unit/agents/test_role.py
git commit -m "feat(agents): implement Role class with config management"
```

---

### Task 3: 创建 RoleManager 类

**Files:**
- Create: `agents_hub/agents/role_manager.py`
- Create: `tests/unit/agents/test_role_manager.py`

- [ ] **Step 1: 编写 RoleManager 类的测试**

```python
"""RoleManager 类的单元测试"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch
from agents_hub.agents.role_manager import RoleManager
from agents_hub.agents.models import RoleInfo
from agents_hub.agents.exceptions import RoleNotFoundError, RoleAlreadyExistsError, PlatformConfigNotFoundError
from agents_hub.agent_bridge.config import AgentPlatform


@pytest.fixture
def agents_dir(tmp_path):
    """创建测试用的 agents 目录"""
    agents_dir = tmp_path / "local_data" / "agents"
    agents_dir.mkdir(parents=True)
    return agents_dir


@pytest.fixture
def role_manager(agents_dir):
    """创建 RoleManager 实例"""
    return RoleManager(agents_dir)


def test_list_roles_empty(role_manager):
    """测试列出空的角色列表"""
    roles = role_manager.list_roles()
    assert roles == []


def test_create_claude_role(role_manager, agents_dir, tmp_path):
    """测试创建 Claude 平台角色"""
    # 创建模拟的 ~/.claude 目录
    mock_home = tmp_path / "home"
    mock_home.mkdir()
    mock_claude = mock_home / ".claude"
    mock_claude.mkdir()
    (mock_claude / "settings.json").write_text('{"permissions": {}}', encoding="utf-8")

    with patch("agents_hub.agents.role_manager.Path.home", return_value=mock_home):
        role = role_manager.create_role("test_claude", AgentPlatform.CLAUDE)

    # 验证目录结构
    role_dir = agents_dir / "test_claude"
    assert role_dir.exists()
    assert (role_dir / "role.json").exists()
    assert (role_dir / "avatar").exists()
    assert (role_dir / "work_root").exists()
    assert (role_dir / "work_root" / "skills").exists()
    assert (role_dir / "work_root" / "CLAUDE.md").exists()
    assert (role_dir / "work_root" / "settings.json").exists()

    # 验证 role.json 内容
    role_json = json.loads((role_dir / "role.json").read_text(encoding="utf-8"))
    assert role_json["name"] == "test_claude"
    assert role_json["platform"] == "claude"
    assert "scope" in role_json
    assert "type" in role_json


def test_create_codex_role(role_manager, agents_dir, tmp_path):
    """测试创建 Codex 平台角色"""
    # 创建模拟的 ~/.codex 目录
    mock_home = tmp_path / "home"
    mock_home.mkdir()
    mock_codex = mock_home / ".codex"
    mock_codex.mkdir()
    (mock_codex / "auth.json").write_text('{}', encoding="utf-8")
    (mock_codex / "config.toml").write_text('', encoding="utf-8")
    (mock_codex / "rules").mkdir()

    with patch("agents_hub.agents.role_manager.Path.home", return_value=mock_home):
        role = role_manager.create_role("test_codex", AgentPlatform.CODEX)

    # 验证目录结构
    role_dir = agents_dir / "test_codex"
    assert role_dir.exists()
    assert (role_dir / "work_root" / "auth.json").exists()
    assert (role_dir / "work_root" / "config.toml").exists()
    assert (role_dir / "work_root" / "rules").exists()
    assert (role_dir / "work_root" / "AGENTS.md").exists()


def test_create_role_already_exists(role_manager, agents_dir):
    """测试创建已存在的角色"""
    # 创建第一个角色
    (agents_dir / "existing_role").mkdir()

    with pytest.raises(RoleAlreadyExistsError):
        role_manager.create_role("existing_role", AgentPlatform.CLAUDE)


def test_create_role_platform_config_not_found(role_manager, tmp_path):
    """测试平台配置目录不存在"""
    mock_home = tmp_path / "empty_home"
    mock_home.mkdir()

    with patch("agents_hub.agents.role_manager.Path.home", return_value=mock_home):
        with pytest.raises(PlatformConfigNotFoundError):
            role_manager.create_role("test_role", AgentPlatform.CLAUDE)


def test_get_role(role_manager, agents_dir):
    """测试获取角色"""
    # 创建测试角色
    role_dir = agents_dir / "test_role"
    role_dir.mkdir()
    role_json = {
        "name": "test_role",
        "platform": "claude",
        "avatar": None,
        "abilities": []
    }
    (role_dir / "role.json").write_text(json.dumps(role_json), encoding="utf-8")

    role = role_manager.get_role("test_role")
    assert role is not None
    assert role.get_info().name == "test_role"


def test_get_role_not_found(role_manager):
    """测试获取不存在的角色"""
    with pytest.raises(RoleNotFoundError):
        role_manager.get_role("nonexistent_role")


def test_list_roles(role_manager, agents_dir):
    """测试列出多个角色"""
    # 创建两个测试角色
    for name in ["role1", "role2"]:
        role_dir = agents_dir / name
        role_dir.mkdir()
        role_json = {
            "name": name,
            "platform": "claude",
            "avatar": None,
            "abilities": []
        }
        (role_dir / "role.json").write_text(json.dumps(role_json), encoding="utf-8")

    roles = role_manager.list_roles()
    assert len(roles) == 2
    role_names = [r.name for r in roles]
    assert "role1" in role_names
    assert "role2" in role_names


def test_delete_role(role_manager, agents_dir):
    """测试删除角色"""
    # 创建测试角色
    role_dir = agents_dir / "test_role"
    role_dir.mkdir()

    role_manager.delete_role("test_role")
    assert not role_dir.exists()


def test_delete_role_not_found(role_manager):
    """测试删除不存在的角色"""
    with pytest.raises(RoleNotFoundError):
        role_manager.delete_role("nonexistent_role")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/agents/test_role_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agents_hub.agents.role_manager'"

- [ ] **Step 3: 实现 RoleManager 类**

```python
"""RoleManager 类 - 角色生命周期管理"""

import json
import shutil
from pathlib import Path
from typing import List, Optional

from agents_hub.agent_bridge.config import AgentPlatform
from agents_hub.agents.models import RoleInfo
from agents_hub.agents.role import Role
from agents_hub.agents.exceptions import RoleNotFoundError, RoleAlreadyExistsError, PlatformConfigNotFoundError


class RoleManager:
    """角色生命周期管理"""

    def __init__(self, agents_dir: Path):
        """
        Args:
            agents_dir: agents 目录路径 (local_data/agents)
        """
        self.agents_dir = agents_dir

    def list_roles(self) -> List[RoleInfo]:
        """扫描 local_data/agents/*/role.json，返回所有角色摘要列表"""
        roles = []
        if not self.agents_dir.exists():
            return roles

        for role_dir in self.agents_dir.iterdir():
            if role_dir.is_dir():
                role_json = role_dir / "role.json"
                if role_json.exists():
                    data = json.loads(role_json.read_text(encoding="utf-8"))
                    roles.append(RoleInfo(
                        name=data["name"],
                        platform=AgentPlatform(data["platform"]),
                        avatar=data.get("avatar"),
                        abilities=data.get("abilities", []),
                        type=data.get("type"),
                        scope=data.get("scope"),
                    ))
        return roles

    def get_role(self, name: str) -> Role:
        """按名称加载单个角色，返回 Role 实例"""
        role_dir = self.agents_dir / name
        if not role_dir.exists():
            raise RoleNotFoundError(f"Role '{name}' not found")

        role_json = role_dir / "role.json"
        if not role_json.exists():
            raise RoleNotFoundError(f"Role '{name}' not found (missing role.json)")

        return Role(role_dir)

    def create_role(
        self,
        name: str,
        platform: AgentPlatform,
        avatar: Optional[str] = None,
        abilities: Optional[List[str]] = None,
        type: Optional[str] = None,
        scope: Optional[List[str]] = None,
    ) -> Role:
        """创建新角色，初始化目录结构和 role.json"""
        role_dir = self.agents_dir / name
        if role_dir.exists():
            raise RoleAlreadyExistsError(f"Role '{name}' already exists")

        # 创建目录结构
        role_dir.mkdir(parents=True)
        avatar_dir = role_dir / "avatar"
        avatar_dir.mkdir()
        work_root = role_dir / "work_root"
        work_root.mkdir()
        (work_root / "skills").mkdir()

        # 根据 platform 复制配置
        if platform == AgentPlatform.CLAUDE:
            self._init_claude_config(work_root)
        else:
            self._init_codex_config(work_root)

        # 写入 role.json
        role_json = {
            "name": name,
            "platform": platform.value,
            "avatar": avatar,
            "abilities": abilities or [],
            "type": type,
            "scope": scope,
            "skills": [],
        }
        (role_dir / "role.json").write_text(
            json.dumps(role_json, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        return Role(role_dir)

    def delete_role(self, name: str) -> None:
        """删除角色及其目录"""
        role_dir = self.agents_dir / name
        if not role_dir.exists():
            raise RoleNotFoundError(f"Role '{name}' not found")

        shutil.rmtree(role_dir)

    def _init_claude_config(self, work_root: Path) -> None:
        """初始化 Claude 平台配置"""
        home_claude = Path.home() / ".claude"
        if not home_claude.exists():
            raise PlatformConfigNotFoundError(f"Claude config directory not found: {home_claude}")

        # 复制 settings.json
        settings_src = home_claude / "settings.json"
        if settings_src.exists():
            shutil.copy2(settings_src, work_root / "settings.json")

        # 创建空白 CLAUDE.md
        (work_root / "CLAUDE.md").write_text("", encoding="utf-8")

    def _init_codex_config(self, work_root: Path) -> None:
        """初始化 Codex 平台配置"""
        home_codex = Path.home() / ".codex"
        if not home_codex.exists():
            raise PlatformConfigNotFoundError(f"Codex config directory not found: {home_codex}")

        # 复制配置文件
        for file_name in ["auth.json", "config.toml"]:
            src = home_codex / file_name
            if src.exists():
                shutil.copy2(src, work_root / file_name)

        # 复制 rules 目录
        rules_src = home_codex / "rules"
        if rules_src.exists():
            shutil.copytree(rules_src, work_root / "rules")

        # 创建空白 AGENTS.md
        (work_root / "AGENTS.md").write_text("", encoding="utf-8")
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/agents/test_role_manager.py -v`
Expected: All tests PASS

- [ ] **Step 5: 提交**

```bash
git add agents_hub/agents/role_manager.py tests/unit/agents/test_role_manager.py
git commit -m "feat(agents): implement RoleManager with CRUD operations"
```

---

### Task 4: 运行完整测试套件

**Files:**
- Test: `tests/unit/agents/`

- [ ] **Step 1: 运行所有 agents 模块测试**

Run: `pytest tests/unit/agents/ -v`
Expected: All tests PASS

- [ ] **Step 2: 运行所有项目测试确保无回归**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 3: 检查测试覆盖率**

Run: `pytest tests/unit/agents/ --cov=agents_hub.agents --cov-report=term-missing`
Expected: Coverage report showing which lines are not covered

- [ ] **Step 4: 提交最终版本**

```bash
git add -A
git commit -m "feat(agents): complete role config module implementation"
```

---

## 验收标准检查

1. ✅ 能创建角色，目录结构和 role.json 正确生成
2. ✅ 能列出所有角色
3. ✅ 能按名称加载角色并构造 RoleConfig
4. ✅ 能添加/移除 skill，同步到目录
5. ✅ 能读取和更新权限配置（抽象接口，返回原始 dict）
6. ✅ 能更新角色基本信息（名称、头像、能力标签）

## 审查问题修复清单

| # | 问题 | 修复方式 |
|---|------|----------|
| 1 | RoleConfig 包含 system_prompt/skills | Task 0: 修改 config.py 移除 |
| 2 | 现有 config.py 与 spec 不一致 | Task 0: 修改 config.py |
| 3 | 自定义异常类未定义 | Task 1: 创建 exceptions.py |
| 4 | role.json 缺少 scope 字段 | Task 1/2/3: 添加 scope 字段 |
| 5 | type 字段无校验/RoleInfo 缺少 | Task 1: 添加到 RoleInfo |
| 6 | 测试 Path.home() 未 mock | Task 3: 使用 unittest.mock.patch |
