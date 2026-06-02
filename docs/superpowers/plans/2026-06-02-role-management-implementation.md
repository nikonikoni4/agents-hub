# Role Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `roles` so `role.json` only stores role metadata, Skill enablement is driven by `work_root/skills`, and role creation automatically initializes the fixed agents-hub MCP for the role's platform config root.

**Architecture:** Keep changes inside the existing `agents_hub.roles` boundary. `RoleManager` remains responsible for role lifecycle and platform config initialization; `Role` remains responsible for single-role metadata and Skill directory operations. Do not introduce permission fields, raw platform config editing, or user-facing MCP management.

**Tech Stack:** Python dataclasses, pathlib/shutil/json, subprocess via `subprocess.run`, pytest, unittest.mock.

---

## 版本

| 版本 | 更新内容 |
| ---- | -------- |
| 1.0 | 创建 plan 初稿 |

## File Structure

- Modify `agents_hub/roles/role_manager.py`: remove `skills` from new `role.json`, add fixed agents-hub MCP initialization after platform root setup, inject `CLAUDE_CONFIG_DIR` or `CODEX_HOME` when running platform CLI, and keep create rollback behavior.
- Modify `agents_hub/roles/role.py`: stop writing `role.json.skills`, add symlink-first Skill enablement with copy fallback, remove Skill entries by deleting the role skill path only, and keep `list_skills()` directory-driven.
- Modify `tests/utils/roles/test_role_manager.py`: assert new metadata-only `role.json`, assert platform/type are immutable by absence of mutators, mock subprocess calls for Claude/Codex MCP initialization, and assert MCP failure rolls back.
- Modify `tests/utils/roles/test_role.py`: assert Skill operations do not read/write `role.json.skills`, assert symlink behavior, assert copy fallback behavior, assert removal never touches the global Skill.
- Optional docs follow-up after implementation: update `docs/specs/2026-05-24-agents-role.md` from unstable implementation facts if the code lands cleanly. Do not do this inside the first implementation pass unless tests are green.

## Task 1: Metadata-only role.json

**Files:**
- Modify: `tests/utils/roles/test_role_manager.py`
- Modify: `agents_hub/roles/role_manager.py`

- [ ] **Step 1: Write the failing test for new role.json shape**

In `tests/utils/roles/test_role_manager.py`, update `test_create_claude_role` and `test_create_codex_role` to patch MCP initialization and assert `skills` is absent:

```python
def test_create_claude_role(role_manager, agents_dir):
    """测试创建 Claude 平台角色"""
    mock_home = Path(tempfile.mkdtemp())
    mock_claude = mock_home / ".claude"
    mock_claude.mkdir()
    (mock_claude / "settings.json").write_text('{"permissions": {}}', encoding="utf-8")

    with (
        patch("agents_hub.roles.role_manager.Path.home", return_value=mock_home),
        patch.object(role_manager, "_init_agents_hub_mcp") as init_mcp,
    ):
        role = role_manager.create_role("test_claude", AgentPlatform.CLAUDE)

    role_dir = agents_dir / "test_claude"
    assert role.role_dir == role_dir
    assert role_dir.exists()
    assert (role_dir / "role.json").exists()
    assert (role_dir / "work_root").exists()
    assert (role_dir / "work_root" / "skills").exists()
    assert (role_dir / "work_root" / "CLAUDE.md").exists()
    assert (role_dir / "work_root" / "settings.json").exists()
    init_mcp.assert_called_once_with(AgentPlatform.CLAUDE, role_dir / "work_root")

    role_json = json.loads((role_dir / "role.json").read_text(encoding="utf-8"))
    assert role_json == {
        "name": "test_claude",
        "platform": "claude",
        "description": None,
        "avatar": None,
        "abilities": [],
        "type": None,
        "scope": None,
    }
    assert "skills" not in role_json
```

Also update `test_create_codex_role`:

```python
def test_create_codex_role(role_manager, agents_dir):
    """测试创建 Codex 平台角色"""
    mock_home = Path(tempfile.mkdtemp())
    mock_codex = mock_home / ".codex"
    mock_codex.mkdir()
    (mock_codex / "auth.json").write_text("{}", encoding="utf-8")
    (mock_codex / "config.toml").write_text("", encoding="utf-8")
    (mock_codex / "rules").mkdir()

    with (
        patch("agents_hub.roles.role_manager.Path.home", return_value=mock_home),
        patch.object(role_manager, "_init_agents_hub_mcp") as init_mcp,
    ):
        role = role_manager.create_role("test_codex", AgentPlatform.CODEX)

    role_dir = agents_dir / "test_codex"
    assert role.role_dir == role_dir
    assert role_dir.exists()
    assert (role_dir / "work_root" / "auth.json").exists()
    assert (role_dir / "work_root" / "config.toml").exists()
    assert (role_dir / "work_root" / "rules").exists()
    assert (role_dir / "work_root" / "AGENTS.md").exists()
    init_mcp.assert_called_once_with(AgentPlatform.CODEX, role_dir / "work_root")

    role_json = json.loads((role_dir / "role.json").read_text(encoding="utf-8"))
    assert role_json["name"] == "test_codex"
    assert role_json["platform"] == "codex"
    assert "skills" not in role_json
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/utils/roles/test_role_manager.py::test_create_claude_role tests/utils/roles/test_role_manager.py::test_create_codex_role -v
```

Expected: FAIL because `_init_agents_hub_mcp` does not exist and `role.json` still includes `skills`.

- [ ] **Step 3: Remove `skills` from role creation and call MCP initializer**

In `agents_hub/roles/role_manager.py`, add `subprocess` and `os` imports for the next task, and update `create_role` so the `try` block includes MCP initialization and `role_json` omits `skills`:

```python
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
```

Replace the platform-init try block and `role_json` section with:

```python
        try:
            if platform == AgentPlatform.CLAUDE:
                self._init_claude_config(work_root)
            else:
                self._init_codex_config(work_root)
            self._init_agents_hub_mcp(platform, work_root)
        except Exception:
            shutil.rmtree(role_dir, ignore_errors=True)
            raise

        role_json = {
            "name": name,
            "platform": platform.value,
            "description": description,
            "avatar": avatar,
            "abilities": abilities or [],
            "type": type.value if isinstance(type, RoleType) else type,
            "scope": scope,
        }
```

Add a stub below `_init_codex_config` for now:

```python
    def _init_agents_hub_mcp(self, platform: AgentPlatform, work_root: Path) -> None:
        """Initialize the fixed agents-hub MCP for this role's platform config root."""
        return None
```

- [ ] **Step 4: Run tests to verify Task 1 passes**

Run:

```bash
python -m pytest tests/utils/roles/test_role_manager.py::test_create_claude_role tests/utils/roles/test_role_manager.py::test_create_codex_role -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add agents_hub/roles/role_manager.py tests/utils/roles/test_role_manager.py
git commit -m "refactor(roles): keep role json metadata only"
```

If unrelated files are staged, run `git diff --cached --name-only` and unstage unrelated files with `git restore --staged <path>` before committing.

## Task 2: Fixed agents-hub MCP initialization

**Files:**
- Modify: `tests/utils/roles/test_role_manager.py`
- Modify: `agents_hub/roles/role_manager.py`

- [ ] **Step 1: Write failing tests for Claude and Codex MCP CLI calls**

Add imports to `tests/utils/roles/test_role_manager.py`:

```python
import subprocess
```

Add these tests near the create-role tests:

```python
def test_init_agents_hub_mcp_claude_sets_config_root(role_manager, agents_dir):
    """创建 Claude 角色时，MCP 添加命令写入角色 CLAUDE_CONFIG_DIR"""
    work_root = agents_dir / "test_claude" / "work_root"
    work_root.mkdir(parents=True)

    with patch("agents_hub.roles.role_manager.subprocess.run") as run:
        role_manager._init_agents_hub_mcp(AgentPlatform.CLAUDE, work_root)

    run.assert_called_once()
    args, kwargs = run.call_args
    assert args[0] == [
        "claude",
        "mcp",
        "add",
        "--transport",
        "http",
        "agents-hub",
        "--",
        "http://localhost:8001/mcp",
    ]
    assert kwargs["check"] is True
    assert kwargs["env"]["CLAUDE_CONFIG_DIR"] == str(work_root)


def test_init_agents_hub_mcp_codex_sets_config_root(role_manager, agents_dir):
    """创建 Codex 角色时，MCP 添加命令写入角色 CODEX_HOME"""
    work_root = agents_dir / "test_codex" / "work_root"
    work_root.mkdir(parents=True)

    with patch("agents_hub.roles.role_manager.subprocess.run") as run:
        role_manager._init_agents_hub_mcp(AgentPlatform.CODEX, work_root)

    run.assert_called_once()
    args, kwargs = run.call_args
    assert args[0] == [
        "codex",
        "mcp",
        "add",
        "agents-hub",
        "--url",
        "http://localhost:8001/mcp",
    ]
    assert kwargs["check"] is True
    assert kwargs["env"]["CODEX_HOME"] == str(work_root)
```

- [ ] **Step 2: Write failing rollback test for MCP failure**

Add:

```python
def test_create_role_cleanup_on_mcp_failure(role_manager, agents_dir):
    """MCP 自动添加失败时，创建角色回滚整个角色目录"""
    mock_home = Path(tempfile.mkdtemp())
    mock_claude = mock_home / ".claude"
    mock_claude.mkdir()
    (mock_claude / "settings.json").write_text("{}", encoding="utf-8")

    with (
        patch("agents_hub.roles.role_manager.Path.home", return_value=mock_home),
        patch.object(
            role_manager,
            "_init_agents_hub_mcp",
            side_effect=subprocess.CalledProcessError(1, ["claude", "mcp", "add"]),
        ),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            role_manager.create_role("test_role", AgentPlatform.CLAUDE)

    assert not (agents_dir / "test_role").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/utils/roles/test_role_manager.py::test_init_agents_hub_mcp_claude_sets_config_root tests/utils/roles/test_role_manager.py::test_init_agents_hub_mcp_codex_sets_config_root tests/utils/roles/test_role_manager.py::test_create_role_cleanup_on_mcp_failure -v
```

Expected: first two FAIL because `_init_agents_hub_mcp` stub does not call subprocess; rollback test should PASS after Task 1 because `create_role` already wraps MCP in rollback.

- [ ] **Step 4: Implement `_init_agents_hub_mcp`**

Replace the stub in `agents_hub/roles/role_manager.py`:

```python
    def _init_agents_hub_mcp(self, platform: AgentPlatform, work_root: Path) -> None:
        """Initialize the fixed agents-hub MCP for this role's platform config root."""
        env = os.environ.copy()
        if platform == AgentPlatform.CLAUDE:
            env["CLAUDE_CONFIG_DIR"] = str(work_root)
            cmd = [
                "claude",
                "mcp",
                "add",
                "--transport",
                "http",
                "agents-hub",
                "--",
                "http://localhost:8001/mcp",
            ]
        else:
            env["CODEX_HOME"] = str(work_root)
            cmd = [
                "codex",
                "mcp",
                "add",
                "agents-hub",
                "--url",
                "http://localhost:8001/mcp",
            ]
        subprocess.run(cmd, check=True, env=env)
```

- [ ] **Step 5: Run tests to verify Task 2 passes**

Run:

```bash
python -m pytest tests/utils/roles/test_role_manager.py::test_init_agents_hub_mcp_claude_sets_config_root tests/utils/roles/test_role_manager.py::test_init_agents_hub_mcp_codex_sets_config_root tests/utils/roles/test_role_manager.py::test_create_role_cleanup_on_mcp_failure -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add agents_hub/roles/role_manager.py tests/utils/roles/test_role_manager.py
git commit -m "feat(roles): initialize agents hub mcp for new roles"
```

## Task 3: Skill symlink-first enablement

**Files:**
- Modify: `tests/utils/roles/test_role.py`
- Modify: `agents_hub/roles/role.py`

- [ ] **Step 1: Update the role fixture to remove `skills` from role.json**

In `tests/utils/roles/test_role.py`, change `claude_role` fixture to:

```python
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
    }
    (role_dir / "role.json").write_text(json.dumps(role_json, ensure_ascii=False), encoding="utf-8")
    (role_dir / "work_root" / "CLAUDE.md").write_text("# Test Role", encoding="utf-8")
    return Role(role_dir)
```

- [ ] **Step 2: Write failing test for symlink add without role.json mutation**

Replace `test_add_skill` with:

```python
def test_add_skill_creates_symlink_without_role_json_mutation(claude_role):
    """添加 skill 默认创建指向全局 skill 的目录链接，不写 role.json"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "test_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "test_skill",
                "name": "Test Skill",
                "description": "A test skill",
            }
        ),
        encoding="utf-8",
    )

    before = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))

    claude_role.add_skill("test_skill")

    skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    assert skill_dir.exists()
    assert skill_dir.is_symlink()
    assert (skill_dir / "skill.json").read_text(encoding="utf-8") == (
        global_skill_dir / "skill.json"
    ).read_text(encoding="utf-8")
    assert claude_role.list_skills()[0].id == "test_skill"
    after = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert after == before
    assert "skills" not in after
```

- [ ] **Step 3: Write failing test for copy fallback**

Add:

```python
def test_add_skill_falls_back_to_copy_when_symlink_fails(claude_role):
    """目录链接失败时，添加 skill 降级复制目录"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "copy_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "copy_skill",
                "name": "Copy Skill",
                "description": "Copied when symlink fails",
            }
        ),
        encoding="utf-8",
    )

    with patch("pathlib.Path.symlink_to", side_effect=OSError("symlink disabled")):
        claude_role.add_skill("copy_skill")

    skill_dir = claude_role.role_dir / "work_root" / "skills" / "copy_skill"
    assert skill_dir.exists()
    assert not skill_dir.is_symlink()
    assert json.loads((skill_dir / "skill.json").read_text(encoding="utf-8"))["id"] == "copy_skill"
    role_json = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert "skills" not in role_json
```

Add `patch` to imports:

```python
from unittest.mock import patch
```

- [ ] **Step 4: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/utils/roles/test_role.py::test_add_skill_creates_symlink_without_role_json_mutation tests/utils/roles/test_role.py::test_add_skill_falls_back_to_copy_when_symlink_fails -v
```

Expected: FAIL because `add_skill` currently copies and writes `role.json.skills`.

- [ ] **Step 5: Implement symlink-first add**

In `agents_hub/roles/role.py`, replace `add_skill` body with:

```python
        target_dir = self._work_root / "skills" / skill_id
        if target_dir.exists() or target_dir.is_symlink():
            role_name = self._read_role_json()["name"]
            raise SkillAlreadyExistsError(skill_id=skill_id, role_name=role_name)

        if global_skills_dir is None:
            global_skills_dir = self.role_dir.parent.parent / "skills"

        global_skill_dir = global_skills_dir / skill_id
        if not global_skill_dir.exists():
            raise SkillNotFoundError(skill_id=skill_id)

        try:
            target_dir.symlink_to(global_skill_dir, target_is_directory=True)
        except OSError:
            shutil.copytree(global_skill_dir, target_dir)
```

- [ ] **Step 6: Run tests to verify Task 3 passes**

Run:

```bash
python -m pytest tests/utils/roles/test_role.py::test_add_skill_creates_symlink_without_role_json_mutation tests/utils/roles/test_role.py::test_add_skill_falls_back_to_copy_when_symlink_fails tests/utils/roles/test_role.py::test_add_skill_already_exists -v
```

Expected: PASS.

- [ ] **Step 7: Commit Task 3**

```bash
git add agents_hub/roles/role.py tests/utils/roles/test_role.py
git commit -m "feat(roles): enable skills with symlink fallback"
```

## Task 4: Skill removal is directory-only

**Files:**
- Modify: `tests/utils/roles/test_role.py`
- Modify: `agents_hub/roles/role.py`

- [ ] **Step 1: Replace removal test to assert global Skill survives**

Replace `test_remove_skill` with:

```python
def test_remove_skill_deletes_role_entry_without_touching_global_skill(claude_role):
    """移除 skill 只删除角色入口，不修改 role.json，不影响全局 skill"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "test_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "test_skill",
                "name": "Test Skill",
                "description": "A test skill",
            }
        ),
        encoding="utf-8",
    )
    claude_role.add_skill("test_skill")
    before = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))

    claude_role.remove_skill("test_skill")

    role_skill_dir = claude_role.role_dir / "work_root" / "skills" / "test_skill"
    assert not role_skill_dir.exists()
    assert global_skill_dir.exists()
    assert (global_skill_dir / "skill.json").exists()
    after = json.loads((claude_role.role_dir / "role.json").read_text(encoding="utf-8"))
    assert after == before
```

- [ ] **Step 2: Add test for copied fallback removal**

Add:

```python
def test_remove_skill_deletes_copied_fallback_without_touching_global_skill(claude_role):
    """移除复制 fallback 的 skill 时，也不能影响全局 skill"""
    global_skill_dir = claude_role.role_dir.parent.parent / "skills" / "copy_skill"
    global_skill_dir.mkdir(parents=True)
    (global_skill_dir / "skill.json").write_text(
        json.dumps(
            {
                "id": "copy_skill",
                "name": "Copy Skill",
                "description": "Copied when symlink fails",
            }
        ),
        encoding="utf-8",
    )
    with patch("pathlib.Path.symlink_to", side_effect=OSError("symlink disabled")):
        claude_role.add_skill("copy_skill")

    claude_role.remove_skill("copy_skill")

    assert not (claude_role.role_dir / "work_root" / "skills" / "copy_skill").exists()
    assert global_skill_dir.exists()
    assert (global_skill_dir / "skill.json").exists()
```

- [ ] **Step 3: Run tests to verify current removal behavior fails**

Run:

```bash
python -m pytest tests/utils/roles/test_role.py::test_remove_skill_deletes_role_entry_without_touching_global_skill tests/utils/roles/test_role.py::test_remove_skill_deletes_copied_fallback_without_touching_global_skill -v
```

Expected: first test may fail on symlink removal because `shutil.rmtree()` follows directory assumptions poorly for symlinks on some platforms; it also currently mutates `role.json.skills` if the field exists.

- [ ] **Step 4: Implement directory-only removal**

In `agents_hub/roles/role.py`, replace `remove_skill` body with:

```python
        skill_dir = self._work_root / "skills" / skill_id
        if not skill_dir.exists() and not skill_dir.is_symlink():
            raise SkillNotFoundError(skill_id=skill_id)

        if skill_dir.is_symlink():
            skill_dir.unlink()
        else:
            shutil.rmtree(skill_dir)
```

- [ ] **Step 5: Run tests to verify Task 4 passes**

Run:

```bash
python -m pytest tests/utils/roles/test_role.py::test_remove_skill_deletes_role_entry_without_touching_global_skill tests/utils/roles/test_role.py::test_remove_skill_deletes_copied_fallback_without_touching_global_skill tests/utils/roles/test_role.py::test_remove_skill_not_found -v
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add agents_hub/roles/role.py tests/utils/roles/test_role.py
git commit -m "refactor(roles): remove skills by role directory state"
```

## Task 5: Remove permission config behavior from Role

**Files:**
- Modify: `tests/utils/roles/test_role.py`
- Modify: `agents_hub/roles/role.py`
- Modify: `docs/specs/2026-05-24-agents-role.md` only after code tests are green

- [ ] **Step 1: Delete obsolete permission tests**

Remove these two tests from `tests/utils/roles/test_role.py`:

```python
def test_get_permissions_config(claude_role):
    ...

def test_update_permissions_config(claude_role):
    ...
```

- [ ] **Step 2: Delete permission config methods**

Remove `get_permissions_config()` and `update_permissions_config()` from `agents_hub/roles/role.py`.

Also remove the unused `Any` import only if `_read_role_json()` no longer needs it. In the current file `_read_role_json()` uses `dict[str, Any]`, so keep:

```python
from typing import Any
```

- [ ] **Step 3: Run role tests**

Run:

```bash
python -m pytest tests/utils/roles/test_role.py -v
```

Expected: PASS.

- [ ] **Step 4: Run role manager tests**

Run:

```bash
python -m pytest tests/utils/roles/test_role_manager.py -v
```

Expected: PASS with subprocess calls mocked where create-role tests patch `_init_agents_hub_mcp`.

- [ ] **Step 5: Commit Task 5**

```bash
git add agents_hub/roles/role.py tests/utils/roles/test_role.py
git commit -m "refactor(roles): remove platform permission config editing"
```

## Task 6: Update formal roles spec after implementation

**Files:**
- Modify: `docs/specs/2026-05-24-agents-role.md`
- Modify: `docs/specs/index.md`

- [ ] **Step 1: Update the formal roles spec version table**

In `docs/specs/2026-05-24-agents-role.md`, increment metadata:

```yaml
version: 1.4
updated_at: 2026-06-02
last_updated: 收窄 role.json 为角色元信息，Skill 改为 work_root/skills 目录状态，角色创建自动初始化固定 agents-hub MCP，权限和原生配置编辑暂不落地
```

Add version row:

```md
| 1.4 | role.json 不再保存 skills；Skill 以 work_root/skills 为启用状态；创建角色自动初始化固定 agents-hub MCP；权限和原生配置编辑暂不落地 |
```

- [ ] **Step 2: Update stable behavior sections**

Adjust these sections in `docs/specs/2026-05-24-agents-role.md`:

```md
模块定位：
- **负责**：角色 CRUD、配置持久化、Skill 管理、头像引用管理、创建角色时初始化固定 agents-hub MCP、构造给 agent_bridge 的 RoleConfig
- **不负责**：用户自定义 MCP 管理、权限策略落地、原生平台配置编辑、消息传递、prompt 构造、多 agent 协调、群聊管理、任务调度
```

Replace the Skill section with:

```md
### Skill 管理机制

Skill 采用**引用优先模式**：全局 `local_data/skills/` 是 Skill 内容的 SSOT，角色的 `work_root/skills/<skill_id>` 是平台可见的启用入口。

行为规则：
- 添加 skill 时，优先在角色 `work_root/skills/` 下创建指向全局 skill 目录的 symlink
- 如果 symlink 创建失败，降级复制整个 skill 目录
- `role.json` 不保存 skills 字段
- 列出 skill 时扫描 `work_root/skills/`
- 移除 skill 时只删除角色下的入口，不影响全局 skill
```

Replace permissions scope references with:

```md
- 权限配置语义化操作暂不落地，等待 Docker / 外部沙箱方案明确
- 不提供 settings.json / config.toml 原生编辑接口
```

- [ ] **Step 3: Update specs index summary**

In `docs/specs/index.md`, update the `roles` entry summary to mention:

```md
 - 内容摘要：roles 角色配置模块的正式规格，定义角色生命周期管理、配置数据结构（RoleConfig/RoleInfo）、头像引用机制、Skill 引用优先管理、创建角色时固定 agents-hub MCP 初始化，以及权限/原生配置编辑暂不落地边界
```

- [ ] **Step 4: Run docs diff check**

Run:

```bash
git diff -- docs/specs/2026-05-24-agents-role.md docs/specs/index.md
```

Expected: diff only changes roles spec and specs index.

- [ ] **Step 5: Commit Task 6**

```bash
git add docs/specs/2026-05-24-agents-role.md docs/specs/index.md
git commit -m "docs(roles): update role management spec"
```

## Task 7: Full verification

**Files:**
- No source modifications expected.

- [ ] **Step 1: Run focused tests**

Run:

```bash
python -m pytest tests/utils/roles/test_role.py tests/utils/roles/test_role_manager.py -v
```

Expected: PASS.

- [ ] **Step 2: Run lint for touched package**

Run:

```bash
ruff check agents_hub/roles tests/utils/roles
```

Expected: PASS.

- [ ] **Step 3: Run format check for touched package**

Run:

```bash
ruff format --check agents_hub/roles tests/utils/roles
```

Expected: PASS.

- [ ] **Step 4: Run mypy if current branch baseline allows it**

Run:

```bash
mypy agents_hub/roles
```

Expected: PASS for `agents_hub/roles`. If repo-level mypy still fails in unrelated `agents_hub/core/orchestration/group_chat.py`, record that as pre-existing and do not fix it in this task.

- [ ] **Step 5: Inspect staged and unstaged changes**

Run:

```bash
git status --short
git diff --stat
```

Expected: only intentional role implementation, role tests, and roles docs changes are present.

## Self-Review

- Spec coverage: metadata-only `role.json` is covered by Task 1; fixed MCP initialization and rollback by Task 2; symlink-first Skill behavior by Tasks 3 and 4; permission removal by Task 5; formal docs sync by Task 6; verification by Task 7.
- Red-flag scan: no task uses unresolved filler text. Commands, files, snippets, and expected outcomes are explicit.
- Type consistency: plan uses existing `AgentPlatform`, `RoleType`, `SkillAlreadyExistsError`, `SkillNotFoundError`, `Role`, and `RoleManager`. New helper `_init_agents_hub_mcp` is introduced before later tests depend on its behavior.
