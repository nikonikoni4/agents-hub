# GroupChatService 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 GroupChatService 作为业务编排层，提供群聊生命周期管理和查询接口

**Architecture:** 轻量服务层设计，Service 负责业务编排，依赖注入全局单例 GroupChatManager，使用统一异常处理，提供资源型 API 接口

**Tech Stack:** FastAPI, Pydantic, agents_hub.core.orchestration (GroupChatManager, Team), agents_hub.roles (RoleManager)

---

## 文件结构规划

### 新建文件
- `agents_hub/api/schemas/group_chats.py` - Pydantic 数据模型（请求/响应）
- `agents_hub/api/services/group_chat_service.py` - 业务编排服务层
- `agents_hub/api/routers/group_chats.py` - FastAPI 路由层（后续任务）
- `tests/api/services/test_group_chat_service.py` - Service 单元测试
- `tests/api/schemas/test_group_chats.py` - Schema 验证测试

### 修改文件
- `agents_hub/api/app.py` - 添加 GroupChatManager 单例初始化
- `agents_hub/core/orchestration/__init__.py` - 导出 GroupChatManager（如果尚未导出）

---

## Task 1: 创建 Pydantic Schema 定义

**Files:**
- Create: `agents_hub/api/schemas/group_chats.py`
- Create: `tests/api/schemas/test_group_chats.py`

- [ ] **Step 1: 编写 Schema 验证测试**

```python
# tests/api/schemas/test_group_chats.py
import pytest
from datetime import datetime
from pydantic import ValidationError
from agents_hub.api.schemas.group_chats import (
    GroupChatCreate,
    GroupChatInfo,
    GroupChatSummary,
    GroupChatMember,
)


def test_group_chat_create_valid():
    """测试有效的创建请求"""
    data = {
        "team_members": ["Leader", "Worker1"],
        "project_path": "/path/to/project",
        "group_chat_name": "My Team",
    }
    schema = GroupChatCreate(**data)
    assert schema.team_members == ["Leader", "Worker1"]
    assert schema.project_path == "/path/to/project"
    assert schema.group_chat_name == "My Team"


def test_group_chat_create_without_name():
    """测试创建请求可以不提供群聊名"""
    data = {
        "team_members": ["Leader"],
        "project_path": "/path/to/project",
    }
    schema = GroupChatCreate(**data)
    assert schema.group_chat_name is None


def test_group_chat_create_empty_members_fails():
    """测试空成员列表应该失败"""
    data = {
        "team_members": [],
        "project_path": "/path/to/project",
    }
    with pytest.raises(ValidationError) as exc_info:
        GroupChatCreate(**data)
    assert "at least 1 item" in str(exc_info.value).lower()


def test_group_chat_info_valid():
    """测试群聊详细信息响应"""
    data = {
        "group_chat_id": "gc_123",
        "group_chat_name": "Test Group",
        "project_path": "/path/to/project",
        "created_at": datetime(2026, 6, 3, 10, 0, 0),
        "group_type": "MANAGER_ORCHESTRATE",
        "is_active": True,
    }
    schema = GroupChatInfo(**data)
    assert schema.group_chat_id == "gc_123"
    assert schema.is_active is True


def test_group_chat_summary_valid():
    """测试群聊摘要响应"""
    data = {
        "group_chat_id": "gc_123",
        "group_chat_name": "Test Group",
        "project_path": "/path/to/project",
        "is_active": False,
        "created_at": datetime(2026, 6, 3, 10, 0, 0),
    }
    schema = GroupChatSummary(**data)
    assert schema.project_path == "/path/to/project"


def test_group_chat_member_valid():
    """测试群聊成员响应"""
    data = {
        "name": "Leader",
        "main_session": "session_123",
        "btw_session": ["btw_1", "btw_2"],
        "cwd": "/path/to/project",
        "use_docker": False,
    }
    schema = GroupChatMember(**data)
    assert schema.name == "Leader"
    assert len(schema.btw_session) == 2


def test_group_chat_member_optional_fields():
    """测试成员可选字段"""
    data = {
        "name": "Worker1",
        "main_session": None,
        "btw_session": [],
        "cwd": None,
    }
    schema = GroupChatMember(**data)
    assert schema.use_docker is False  # 默认值
    assert schema.main_session is None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/schemas/test_group_chats.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agents_hub.api.schemas.group_chats'"

- [ ] **Step 3: 实现 Schema 定义**

```python
# agents_hub/api/schemas/group_chats.py
"""
群聊相关的 Pydantic Schema 定义

用于 API 请求验证和响应序列化
"""

from datetime import datetime
from pydantic import BaseModel, Field


class GroupChatCreate(BaseModel):
    """创建群聊请求"""

    team_members: list[str] = Field(..., min_length=1, description="团队成员角色名列表")
    project_path: str = Field(..., description="项目路径")
    group_chat_name: str | None = Field(None, description="群聊名称，不提供则使用 group_chat_id")


class GroupChatInfo(BaseModel):
    """群聊详细信息"""

    group_chat_id: str
    group_chat_name: str
    project_path: str
    created_at: datetime
    group_type: str
    is_active: bool


class GroupChatSummary(BaseModel):
    """群聊摘要（列表展示）"""

    group_chat_id: str
    group_chat_name: str
    project_path: str
    is_active: bool
    created_at: datetime


class GroupChatMember(BaseModel):
    """群聊成员（运行时信息）"""

    name: str
    main_session: str | None
    btw_session: list[str]
    cwd: str | None
    use_docker: bool = False
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/schemas/test_group_chats.py -v`
Expected: 所有测试通过

- [ ] **Step 5: 提交 Schema 定义**

```bash
git add agents_hub/api/schemas/group_chats.py tests/api/schemas/test_group_chats.py
git commit -m "feat(api): 添加群聊 Pydantic Schema 定义

- GroupChatCreate: 创建请求验证
- GroupChatInfo: 详细信息响应
- GroupChatSummary: 列表摘要响应
- GroupChatMember: 成员信息响应
- 包含完整的单元测试覆盖"
```

---

## Task 2: 初始化 GroupChatManager 全局单例

**Files:**
- Modify: `agents_hub/api/app.py`
- Create: `tests/api/test_app_singleton.py`

- [ ] **Step 1: 编写单例测试**

```python
# tests/api/test_app_singleton.py
"""测试 GroupChatManager 单例初始化"""

from agents_hub.api.app import get_group_chat_manager
from agents_hub.core.orchestration import GroupChatManager


def test_get_group_chat_manager_returns_instance():
    """测试 get_group_chat_manager 返回 GroupChatManager 实例"""
    manager = get_group_chat_manager()
    assert isinstance(manager, GroupChatManager)


def test_get_group_chat_manager_returns_same_instance():
    """测试多次调用返回同一个实例（单例）"""
    manager1 = get_group_chat_manager()
    manager2 = get_group_chat_manager()
    assert manager1 is manager2
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/test_app_singleton.py -v`
Expected: FAIL with "ImportError: cannot import name 'get_group_chat_manager'"

- [ ] **Step 3: 在 app.py 中添加单例初始化**

首先检查 `agents_hub/api/app.py` 的当前内容：

Run: `head -50 agents_hub/api/app.py`

然后在文件顶部（import 区域后）添加：

```python
# agents_hub/api/app.py
# ... 现有 imports ...
from agents_hub.core.orchestration import GroupChatManager

# 全局单例（模块级变量）
_group_chat_manager_singleton = GroupChatManager()


def get_group_chat_manager() -> GroupChatManager:
    """获取全局 GroupChatManager 单例
    
    Returns:
        GroupChatManager: 全局唯一的 GroupChatManager 实例
    """
    return _group_chat_manager_singleton


# ... 现有的 app = FastAPI() 等代码 ...
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/test_app_singleton.py -v`
Expected: 所有测试通过

- [ ] **Step 5: 提交单例初始化**

```bash
git add agents_hub/api/app.py tests/api/test_app_singleton.py
git commit -m "feat(api): 添加 GroupChatManager 全局单例

- 在 app.py 中初始化全局单例
- 提供 get_group_chat_manager() 依赖注入函数
- 保证 MCP Server 和 API Server 共享同一实例"
```

---

## Task 3: 实现 create_group_chat 方法

**Files:**
- Create: `agents_hub/api/services/group_chat_service.py`
- Create: `tests/api/services/test_group_chat_service.py`

- [ ] **Step 1: 编写 create_group_chat 测试**

```python
# tests/api/services/test_group_chat_service.py
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.api.schemas.group_chats import GroupChatInfo
from agents_hub.exceptions import ValidationError, ResourceNotFoundError, StateError, ExternalServiceError
from agents_hub.core.orchestration import Team


@pytest.fixture
def mock_group_chat_manager():
    """Mock GroupChatManager"""
    manager = Mock()
    manager.register = Mock()
    manager.get_group_chat = Mock()
    return manager


@pytest.fixture
def service(mock_group_chat_manager):
    """创建 GroupChatService 实例"""
    return GroupChatService(mock_group_chat_manager)


def test_create_group_chat_success(service, mock_group_chat_manager):
    """测试成功创建群聊"""
    # Arrange
    team_members = ["Leader", "Worker1"]
    project_path = "/path/to/project"
    group_chat_name = "Test Group"
    
    mock_group_chat = Mock()
    mock_group_chat.group_chat_id = "gc_test_123"
    mock_group_chat.start = MagicMock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(
            group_chat_id="gc_test_123",
            group_chat_name="Test Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        )
    )
    
    with patch("agents_hub.api.services.group_chat_service.Team") as MockTeam, \
         patch("agents_hub.api.services.group_chat_service.GroupChat") as MockGroupChat, \
         patch("agents_hub.api.services.group_chat_service.generate_group_chat_id", return_value="gc_test_123"):
        
        MockTeam.return_value = Mock()
        MockGroupChat.return_value = mock_group_chat
        
        # Act
        result = service.create_group_chat(team_members, project_path, group_chat_name)
    
    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == "gc_test_123"
    assert result.group_chat_name == "Test Group"
    mock_group_chat.start.assert_called_once()
    mock_group_chat_manager.register.assert_called_once_with("gc_test_123", mock_group_chat)


def test_create_group_chat_empty_members_raises_validation_error(service):
    """测试空成员列表抛出 ValidationError"""
    with pytest.raises(ValidationError) as exc_info:
        service.create_group_chat([], "/path/to/project")
    assert "team_members 不能为空" in str(exc_info.value)


def test_create_group_chat_invalid_role_raises_resource_not_found(service):
    """测试无效角色抛出 ResourceNotFoundError"""
    with patch("agents_hub.api.services.group_chat_service.Team") as MockTeam:
        MockTeam.side_effect = ValueError("错误的role_name InvalidRole")
        
        with pytest.raises(ResourceNotFoundError) as exc_info:
            service.create_group_chat(["InvalidRole"], "/path/to/project")
        assert "InvalidRole" in str(exc_info.value)


def test_create_group_chat_start_fails_raises_state_error(service, mock_group_chat_manager):
    """测试启动失败抛出 StateError"""
    mock_group_chat = Mock()
    mock_group_chat.start = MagicMock(side_effect=Exception("启动失败"))
    
    with patch("agents_hub.api.services.group_chat_service.Team"), \
         patch("agents_hub.api.services.group_chat_service.GroupChat", return_value=mock_group_chat), \
         patch("agents_hub.api.services.group_chat_service.generate_group_chat_id", return_value="gc_test"):
        
        with pytest.raises(StateError) as exc_info:
            service.create_group_chat(["Leader"], "/path/to/project")
        assert "群聊启动失败" in str(exc_info.value)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/services/test_group_chat_service.py::test_create_group_chat_success -v`
Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: 实现 create_group_chat 方法**

```python
# agents_hub/api/services/group_chat_service.py
"""
GroupChatService 业务编排层

协调 GroupChatManager、Team、RoleManager，提供群聊生命周期管理和查询接口
"""

from datetime import datetime

from agents_hub.api.schemas.group_chats import (
    GroupChatInfo,
    GroupChatSummary,
    GroupChatMember,
)
from agents_hub.core.orchestration import GroupChatManager, Team, GroupChat
from agents_hub.core.utils.id_generator import generate_group_chat_id
from agents_hub.roles import RoleManager
from agents_hub.exceptions import ValidationError, ResourceNotFoundError, StateError, ExternalServiceError


class GroupChatService:
    """群聊应用服务层
    
    轻量业务编排层，不持有状态，所有状态在 GroupChatManager 中
    """

    def __init__(self, group_chat_manager: GroupChatManager):
        """
        Args:
            group_chat_manager: 全局单例 GroupChatManager（依赖注入）
        """
        self.group_chat_manager = group_chat_manager
        self.role_manager = RoleManager()

    async def create_group_chat(
        self,
        team_members: list[str],
        project_path: str,
        group_chat_name: str | None = None,
    ) -> GroupChatInfo:
        """创建并启动新群聊
        
        Args:
            team_members: 团队成员角色名列表
            project_path: 项目路径
            group_chat_name: 群聊名称，不提供则使用 group_chat_id
            
        Returns:
            GroupChatInfo: 群聊详细信息
            
        Raises:
            ValidationError: team_members 为空
            ResourceNotFoundError: role 不存在或 project_path 不存在
            StateError: 启动失败
        """
        # 1. 验证 team_members 非空
        if not team_members:
            raise ValidationError(
                "team_members 不能为空",
                details={"team_members": team_members},
            )

        # 2. 创建 Team 对象（验证 roles 存在）
        try:
            team = Team(team_members_name=team_members, team_name="default_team")
        except ValueError as e:
            raise ResourceNotFoundError(
                str(e),
                details={"team_members": team_members},
            ) from e

        # 3. 生成 group_chat_id
        group_chat_id = generate_group_chat_id()

        # 4. 创建 GroupChat 实例
        group_chat = GroupChat(
            group_chat_id=group_chat_id,
            team=team,
            project_path=project_path,
            group_chat_name=group_chat_name or group_chat_id,
        )

        # 5. 调用 GroupChat.start()
        try:
            await group_chat.start()
        except Exception as e:
            raise StateError(
                f"群聊启动失败: {e}",
                details={
                    "group_chat_id": group_chat_id,
                    "project_path": project_path,
                },
            ) from e

        # 6. 注册到 GroupChatManager
        self.group_chat_manager.register(group_chat_id, group_chat)

        # 7. 返回 GroupChatInfo
        return await self._build_group_chat_info_from_instance(group_chat)

    async def _build_group_chat_info_from_instance(
        self, group_chat: GroupChat
    ) -> GroupChatInfo:
        """从内存中的 GroupChat 实例构建 GroupChatInfo"""
        metadata = await group_chat.group_chat_context.repository.load_group_metadata()
        return GroupChatInfo(
            group_chat_id=metadata.group_chat_id,
            group_chat_name=metadata.group_chat_name,
            project_path=metadata.project_path,
            created_at=metadata.created_at,
            group_type=metadata.group_type,
            is_active=True,
        )
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/services/test_group_chat_service.py -k create_group_chat -v`
Expected: 所有 create_group_chat 相关测试通过

- [ ] **Step 5: 提交 create_group_chat 实现**

```bash
git add agents_hub/api/services/group_chat_service.py tests/api/services/test_group_chat_service.py
git commit -m "feat(service): 实现 create_group_chat 方法

- 验证 team_members 非空
- 创建 Team 对象并验证 roles
- 生成 group_chat_id 并创建 GroupChat 实例
- 启动群聊并注册到 GroupChatManager
- 包含完整的错误处理和单元测试"
```

---

## Task 4: 实现 load_group_chat 方法

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py`
- Modify: `tests/api/services/test_group_chat_service.py`

- [ ] **Step 1: 编写 load_group_chat 测试**

```python
# tests/api/services/test_group_chat_service.py
# ... 在现有测试文件末尾添加 ...

def test_load_group_chat_already_in_memory(service, mock_group_chat_manager):
    """测试加载已在内存中的群聊（幂等性）"""
    # Arrange
    group_chat_id = "gc_existing"
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Existing Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        )
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat
    
    # Act
    result = service.load_group_chat(group_chat_id)
    
    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.get_group_chat.assert_called_once_with(group_chat_id)


def test_load_group_chat_from_disk(service, mock_group_chat_manager):
    """测试从磁盘加载群聊"""
    # Arrange
    group_chat_id = "gc_from_disk"
    mock_group_chat_manager.get_group_chat.return_value = None  # 不在内存
    
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Loaded Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        )
    )
    mock_group_chat_manager.load_group_chat_from_disk.return_value = mock_group_chat
    
    # Act
    result = service.load_group_chat(group_chat_id)
    
    # Assert
    assert isinstance(result, GroupChatInfo)
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.load_group_chat_from_disk.assert_called_once_with(group_chat_id)


def test_load_group_chat_not_found_raises_error(service, mock_group_chat_manager):
    """测试加载不存在的群聊抛出异常"""
    # Arrange
    mock_group_chat_manager.get_group_chat.return_value = None
    mock_group_chat_manager.load_group_chat_from_disk.side_effect = FileNotFoundError("群聊不存在")
    
    # Act & Assert
    with pytest.raises(ResourceNotFoundError) as exc_info:
        service.load_group_chat("gc_nonexistent")
    assert "群聊不存在" in str(exc_info.value)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/services/test_group_chat_service.py::test_load_group_chat_already_in_memory -v`
Expected: FAIL with "AttributeError: 'GroupChatService' object has no attribute 'load_group_chat'"

- [ ] **Step 3: 实现 load_group_chat 方法**

在 `agents_hub/api/services/group_chat_service.py` 的 `GroupChatService` 类中添加：

```python
    async def load_group_chat(self, group_chat_id: str) -> GroupChatInfo:
        """加载群聊（从内存或磁盘）
        
        Args:
            group_chat_id: 群聊 ID
            
        Returns:
            GroupChatInfo: 群聊详细信息
            
        Raises:
            ResourceNotFoundError: 群聊不存在或 role 已被删除
            StateError: 加载失败
        """
        # 1. 检查是否已在内存中
        group_chat = self.group_chat_manager.get_group_chat(group_chat_id)
        if group_chat:
            # 已在内存，直接返回（幂等性）
            return await self._build_group_chat_info_from_instance(group_chat)

        # 2. 从磁盘加载
        try:
            group_chat = await self.group_chat_manager.load_group_chat_from_disk(
                group_chat_id
            )
        except FileNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e
        except ValueError as e:
            # Team 验证失败（role 已被删除）
            raise ResourceNotFoundError(
                f"群聊加载失败，role 不存在: {e}",
                details={"group_chat_id": group_chat_id},
            ) from e
        except Exception as e:
            raise StateError(
                f"群聊加载失败: {e}",
                details={"group_chat_id": group_chat_id},
            ) from e

        # 3. 返回 GroupChatInfo
        return await self._build_group_chat_info_from_instance(group_chat)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/services/test_group_chat_service.py -k load_group_chat -v`
Expected: 所有 load_group_chat 相关测试通过

- [ ] **Step 5: 提交 load_group_chat 实现**

```bash
git add agents_hub/api/services/group_chat_service.py tests/api/services/test_group_chat_service.py
git commit -m "feat(service): 实现 load_group_chat 方法

- 支持幂等性：已在内存则直接返回
- 从磁盘加载并注册到 GroupChatManager
- 转换底层异常为业务异常
- 包含完整的单元测试覆盖"
```

---

## Task 5: 实现 delete_group_chat 方法

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py`
- Modify: `tests/api/services/test_group_chat_service.py`

- [ ] **Step 1: 编写 delete_group_chat 测试**

```python
# tests/api/services/test_group_chat_service.py
# ... 在现有测试文件末尾添加 ...

from pathlib import Path


async def test_delete_group_chat_keep_data(service, mock_group_chat_manager):
    """测试删除群聊但保留数据"""
    # Arrange
    group_chat_id = "gc_to_delete"
    mock_group_chat_manager.unregister = Mock()
    
    # Act
    await service.delete_group_chat(group_chat_id, keep_data=True)
    
    # Assert
    mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)


async def test_delete_group_chat_with_data(service, mock_group_chat_manager):
    """测试完全删除群聊（内存+磁盘）"""
    # Arrange
    group_chat_id = "gc_to_delete_full"
    project_path = "/path/to/project"
    
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(project_path=project_path)
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat
    mock_group_chat_manager.unregister = Mock()
    
    with patch("agents_hub.api.services.group_chat_service.get_group_chat_dir") as mock_get_dir, \
         patch("shutil.rmtree") as mock_rmtree:
        mock_get_dir.return_value = Path("/path/to/group_chats/gc_to_delete_full")
        
        # Act
        await service.delete_group_chat(group_chat_id, keep_data=False)
        
        # Assert
        mock_group_chat_manager.get_group_chat.assert_called_once()
        mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)
        mock_get_dir.assert_called_once_with(project_path, group_chat_id)
        mock_rmtree.assert_called_once_with(Path("/path/to/group_chats/gc_to_delete_full"))


async def test_delete_group_chat_from_disk_when_not_in_memory(service, mock_group_chat_manager):
    """测试删除不在内存中的群聊（从磁盘读取 metadata）"""
    # Arrange
    group_chat_id = "gc_disk_delete"
    project_path = "/path/to/project"
    
    mock_group_chat_manager.get_group_chat.return_value = None  # 不在内存
    
    with patch("agents_hub.api.services.group_chat_service.get_group_chat_dir") as mock_get_dir, \
         patch("agents_hub.api.services.group_chat_service.Path") as MockPath, \
         patch("shutil.rmtree") as mock_rmtree, \
         patch("json.load") as mock_json_load:
        
        # Mock 文件系统
        mock_metadata_file = Mock()
        mock_metadata_file.exists.return_value = True
        mock_metadata_file.open = MagicMock()
        MockPath.return_value = mock_metadata_file
        
        mock_json_load.return_value = {"project_path": project_path}
        mock_get_dir.return_value = Path("/path/to/group_chats/gc_disk_delete")
        
        # Act
        await service.delete_group_chat(group_chat_id, keep_data=False)
        
        # Assert
        mock_group_chat_manager.unregister.assert_called_once_with(group_chat_id)
        mock_rmtree.assert_called_once()


async def test_delete_group_chat_idempotent(service, mock_group_chat_manager):
    """测试删除不存在的群聊是幂等的（不抛异常）"""
    # Arrange
    mock_group_chat_manager.get_group_chat.return_value = None
    
    with patch("agents_hub.api.services.group_chat_service.Path") as MockPath:
        mock_file = Mock()
        mock_file.exists.return_value = False
        MockPath.return_value = mock_file
        
        # Act & Assert - 不应抛异常
        await service.delete_group_chat("gc_nonexistent", keep_data=False)
        mock_group_chat_manager.unregister.assert_called_once()


async def test_delete_group_chat_file_deletion_fails(service, mock_group_chat_manager):
    """测试文件删除失败抛出 ExternalServiceError"""
    # Arrange
    group_chat_id = "gc_delete_fail"
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(project_path="/path")
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat
    
    with patch("agents_hub.api.services.group_chat_service.get_group_chat_dir"), \
         patch("shutil.rmtree", side_effect=PermissionError("权限不足")):
        
        # Act & Assert
        with pytest.raises(ExternalServiceError) as exc_info:
            await service.delete_group_chat(group_chat_id, keep_data=False)
        assert "文件删除失败" in str(exc_info.value)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/services/test_group_chat_service.py::test_delete_group_chat_keep_data -v`
Expected: FAIL with "AttributeError: 'GroupChatService' object has no attribute 'delete_group_chat'"

- [ ] **Step 3: 实现 delete_group_chat 方法**

在 `agents_hub/api/services/group_chat_service.py` 顶部添加导入：

```python
import shutil
import json
from pathlib import Path
from agents_hub.core.context.group_chat_paths import get_group_chat_dir
from agents_hub.exceptions import ValidationError, ResourceNotFoundError, StateError, ExternalServiceError, ExternalServiceError
```

在 `GroupChatService` 类中添加：

```python
    async def delete_group_chat(
        self, group_chat_id: str, keep_data: bool = False
    ) -> None:
        """删除群聊
        
        Args:
            group_chat_id: 群聊 ID
            keep_data: True=仅从内存移除，False=完全删除（内存+磁盘）
            
        Raises:
            ResourceNotFoundError: 群聊不存在（仅当 keep_data=False 且磁盘也不存在时）
            ExternalServiceError: 文件删除失败
        """
        project_path = None

        # 1. 如果 keep_data=False，先读取 metadata（在 unregister 之前）
        if not keep_data:
            # 尝试从内存中的 GroupChat 实例读取
            group_chat = self.group_chat_manager.get_group_chat(group_chat_id)
            if group_chat:
                metadata = group_chat.group_chat_context.repository.load_group_metadata()
                project_path = metadata.project_path
            else:
                # 从磁盘读取
                metadata_file = Path(
                    get_group_chat_dir(None, group_chat_id)
                ) / "group_metadata.json"
                if metadata_file.exists():
                    with metadata_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        project_path = data.get("project_path")

        # 2. 从内存中移除
        await self.group_chat_manager.unregister(group_chat_id)

        # 3. 如果 keep_data=False，删除磁盘数据
        if not keep_data and project_path:
            try:
                group_chat_dir = get_group_chat_dir(project_path, group_chat_id)
                if group_chat_dir.exists():
                    shutil.rmtree(group_chat_dir)
            except (PermissionError, OSError) as e:
                raise ExternalServiceError(
                    f"文件删除失败: {e}",
                    details={
                        "group_chat_id": group_chat_id,
                        "group_chat_dir": str(group_chat_dir),
                    },
                ) from e
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/services/test_group_chat_service.py -k delete_group_chat -v`
Expected: 所有 delete_group_chat 相关测试通过

- [ ] **Step 5: 提交 delete_group_chat 实现**

```bash
git add agents_hub/api/services/group_chat_service.py tests/api/services/test_group_chat_service.py
git commit -m "feat(service): 实现 delete_group_chat 方法

- 支持 keep_data 参数：保留或删除磁盘数据
- 竞态安全：先读取 metadata 再 unregister
- 幂等性：不存在的群聊静默返回
- 完整的错误处理和单元测试"
```

---

## Task 6: 实现 list_group_chats 方法

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py`
- Modify: `tests/api/services/test_group_chat_service.py`

- [ ] **Step 1: 编写 list_group_chats 测试**

```python
# tests/api/services/test_group_chat_service.py
# ... 在现有测试文件末尾添加 ...

from agents_hub.core.context.group_metadata import GroupMetadata


async def test_list_group_chats_returns_all(service, mock_group_chat_manager):
    """测试列出所有群聊"""
    # Arrange
    mock_metadata_list = [
        GroupMetadata(
            group_chat_id="gc_1",
            group_chat_name="Group 1",
            project_path="/path/1",
            created_at=datetime(2026, 6, 1, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        ),
        GroupMetadata(
            group_chat_id="gc_2",
            group_chat_name="Group 2",
            project_path="/path/2",
            created_at=datetime(2026, 6, 2, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        ),
    ]
    mock_group_chat_manager.list_all_group_chats.return_value = mock_metadata_list
    mock_group_chat_manager.get_group_chat.side_effect = [Mock(), None]  # gc_1 活跃，gc_2 非活跃
    
    # Act
    result = await service.list_group_chats(is_active_only=False)
    
    # Assert
    assert len(result) == 2
    assert result[0].group_chat_id == "gc_1"
    assert result[0].is_active is True
    assert result[1].group_chat_id == "gc_2"
    assert result[1].is_active is False


async def test_list_group_chats_active_only(service, mock_group_chat_manager):
    """测试只列出活跃群聊"""
    # Arrange
    mock_metadata_list = [
        GroupMetadata(
            group_chat_id="gc_active",
            group_chat_name="Active Group",
            project_path="/path/active",
            created_at=datetime(2026, 6, 1, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        ),
        GroupMetadata(
            group_chat_id="gc_inactive",
            group_chat_name="Inactive Group",
            project_path="/path/inactive",
            created_at=datetime(2026, 6, 2, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        ),
    ]
    mock_group_chat_manager.list_all_group_chats.return_value = mock_metadata_list
    mock_group_chat_manager.get_group_chat.side_effect = [Mock(), None]
    
    # Act
    result = await service.list_group_chats(is_active_only=True)
    
    # Assert
    assert len(result) == 1
    assert result[0].group_chat_id == "gc_active"
    assert result[0].is_active is True


async def test_list_group_chats_empty(service, mock_group_chat_manager):
    """测试没有群聊时返回空列表"""
    # Arrange
    mock_group_chat_manager.list_all_group_chats.return_value = []
    
    # Act
    result = await service.list_group_chats()
    
    # Assert
    assert result == []
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/services/test_group_chat_service.py::test_list_group_chats_returns_all -v`
Expected: FAIL with "AttributeError: 'GroupChatService' object has no attribute 'list_group_chats'"

- [ ] **Step 3: 实现 list_group_chats 方法**

在 `GroupChatService` 类中添加：

```python
    async def list_group_chats(self, is_active_only: bool = False) -> list[GroupChatSummary]:
        """列出所有群聊
        
        Args:
            is_active_only: True=只返回活跃群聊，False=返回所有群聊
            
        Returns:
            list[GroupChatSummary]: 群聊摘要列表
        """
        # 1. 调用 GroupChatManager.list_all_group_chats()
        all_metadata = self.group_chat_manager.list_all_group_chats()

        # 2. 转换为 GroupChatSummary 列表
        summaries = []
        for metadata in all_metadata:
            # 检查是否在内存中（活跃状态）
            is_active = self.group_chat_manager.get_group_chat(metadata.group_chat_id) is not None
            
            # 3. 如果 is_active_only=True，过滤出活跃的
            if is_active_only and not is_active:
                continue
            
            summaries.append(
                GroupChatSummary(
                    group_chat_id=metadata.group_chat_id,
                    group_chat_name=metadata.group_chat_name,
                    project_path=metadata.project_path,
                    is_active=is_active,
                    created_at=metadata.created_at,
                )
            )

        return summaries
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/services/test_group_chat_service.py -k list_group_chats -v`
Expected: 所有 list_group_chats 相关测试通过

- [ ] **Step 5: 提交 list_group_chats 实现**

```bash
git add agents_hub/api/services/group_chat_service.py tests/api/services/test_group_chat_service.py
git commit -m "feat(service): 实现 list_group_chats 方法

- 支持 is_active_only 参数过滤活跃群聊
- 基于内存状态判断 is_active
- 返回 GroupChatSummary 列表
- 包含完整的单元测试覆盖"
```

---

## Task 7: 实现 get_group_chat_info 方法

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py`
- Modify: `tests/api/services/test_group_chat_service.py`

- [ ] **Step 1: 编写 get_group_chat_info 测试**

```python
# tests/api/services/test_group_chat_service.py
# ... 在现有测试文件末尾添加 ...

def test_get_group_chat_info_from_memory(service, mock_group_chat_manager):
    """测试从内存获取群聊信息"""
    # Arrange
    group_chat_id = "gc_memory"
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Memory Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        )
    )
    mock_group_chat_manager.get_group_chat.return_value = mock_group_chat
    
    # Act
    result = service.get_group_chat_info(group_chat_id)
    
    # Assert
    assert result.group_chat_id == group_chat_id
    assert result.is_active is True
    mock_group_chat_manager.get_group_chat.assert_called_once_with(group_chat_id)


def test_get_group_chat_info_from_disk(service, mock_group_chat_manager):
    """测试从磁盘获取群聊信息"""
    # Arrange
    group_chat_id = "gc_disk"
    mock_group_chat_manager.get_group_chat.return_value = None  # 不在内存
    
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(
            group_chat_id=group_chat_id,
            group_chat_name="Disk Group",
            project_path="/path/to/project",
            created_at=datetime(2026, 6, 3, 10, 0, 0),
            group_type="MANAGER_ORCHESTRATE",
        )
    )
    mock_group_chat_manager.load_group_chat_from_disk.return_value = mock_group_chat
    
    # Act
    result = service.get_group_chat_info(group_chat_id)
    
    # Assert
    assert result.group_chat_id == group_chat_id
    assert result.is_active is False  # 从磁盘加载，非活跃
    mock_group_chat_manager.load_group_chat_from_disk.assert_called_once_with(group_chat_id)


def test_get_group_chat_info_not_found(service, mock_group_chat_manager):
    """测试获取不存在的群聊信息"""
    # Arrange
    mock_group_chat_manager.get_group_chat.return_value = None
    mock_group_chat_manager.load_group_chat_from_disk.side_effect = FileNotFoundError("不存在")
    
    # Act & Assert
    with pytest.raises(ResourceNotFoundError):
        service.get_group_chat_info("gc_nonexistent")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/services/test_group_chat_service.py::test_get_group_chat_info_from_memory -v`
Expected: FAIL with "AttributeError: 'GroupChatService' object has no attribute 'get_group_chat_info'"

- [ ] **Step 3: 实现 get_group_chat_info 方法**

在 `GroupChatService` 类中添加：

```python
    async def get_group_chat_info(self, group_chat_id: str) -> GroupChatInfo:
        """获取群聊详细信息
        
        Args:
            group_chat_id: 群聊 ID
            
        Returns:
            GroupChatInfo: 群聊详细信息
            
        Raises:
            ResourceNotFoundError: 群聊不存在
        """
        # 1. 尝试从内存获取
        group_chat = self.group_chat_manager.get_group_chat(group_chat_id)
        if group_chat:
            # 内存中存在，is_active=True
            info = await self._build_group_chat_info_from_instance(group_chat)
            return info

        # 2. 从磁盘读取
        try:
            group_chat = await self.group_chat_manager.load_group_chat_from_disk(
                group_chat_id
            )
            # 从磁盘加载，is_active=False
            metadata = await group_chat.group_chat_context.repository.load_group_metadata()
            return GroupChatInfo(
                group_chat_id=metadata.group_chat_id,
                group_chat_name=metadata.group_chat_name,
                project_path=metadata.project_path,
                created_at=metadata.created_at,
                group_type=metadata.group_type,
                is_active=False,
            )
        except FileNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/services/test_group_chat_service.py -k get_group_chat_info -v`
Expected: 所有 get_group_chat_info 相关测试通过

- [ ] **Step 5: 提交 get_group_chat_info 实现**

```bash
git add agents_hub/api/services/group_chat_service.py tests/api/services/test_group_chat_service.py
git commit -m "feat(service): 实现 get_group_chat_info 方法

- 优先从内存读取（is_active=True）
- 内存不存在则从磁盘加载（is_active=False）
- 完整的错误处理和单元测试"
```

---

## Task 8: 实现 get_group_chat_members 方法

**Files:**
- Modify: `agents_hub/api/services/group_chat_service.py`
- Modify: `tests/api/services/test_group_chat_service.py`

- [ ] **Step 1: 编写 get_group_chat_members 测试**

```python
# tests/api/services/test_group_chat_service.py
# ... 在现有测试文件末尾添加 ...

def test_get_group_chat_members_success(service, mock_group_chat_manager):
    """测试成功获取群聊成员"""
    # Arrange
    group_chat_id = "gc_members"
    project_path = "/path/to/project"
    
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(project_path=project_path)
    )
    mock_group_chat_manager.load_group_chat_from_disk.return_value = mock_group_chat
    
    session_state_data = {
        "Leader": {
            "main_session": "session_123",
            "btw_session": ["btw_1", "btw_2"],
            "cwd": "/path/to/project",
            "use_docker": False,
        },
        "Worker1": {
            "main_session": None,
            "btw_session": [],
            "cwd": "/path/to/project",
        },
    }
    
    with patch("agents_hub.api.services.group_chat_service.Path") as MockPath, \
         patch("builtins.open", create=True) as mock_open, \
         patch("json.load", return_value=session_state_data):
        
        mock_file = Mock()
        mock_file.exists.return_value = True
        MockPath.return_value = mock_file
        
        # Act
        result = service.get_group_chat_members(group_chat_id)
    
    # Assert
    assert len(result) == 2
    assert result[0].name == "Leader"
    assert result[0].main_session == "session_123"
    assert len(result[0].btw_session) == 2
    assert result[0].use_docker is False
    assert result[1].name == "Worker1"
    assert result[1].main_session is None


def test_get_group_chat_members_file_not_found(service, mock_group_chat_manager):
    """测试 session_state 文件不存在"""
    # Arrange
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(project_path="/path")
    )
    mock_group_chat_manager.load_group_chat_from_disk.return_value = mock_group_chat
    
    with patch("agents_hub.api.services.group_chat_service.Path") as MockPath:
        mock_file = Mock()
        mock_file.exists.return_value = False
        MockPath.return_value = mock_file
        
        # Act & Assert
        with pytest.raises(ResourceNotFoundError) as exc_info:
            service.get_group_chat_members("gc_no_file")
        assert "session_state 文件不存在" in str(exc_info.value)


def test_get_group_chat_members_json_decode_error(service, mock_group_chat_manager):
    """测试 JSON 格式错误转换为 StateError"""
    # Arrange
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(project_path="/path")
    )
    mock_group_chat_manager.load_group_chat_from_disk.return_value = mock_group_chat
    
    with patch("agents_hub.api.services.group_chat_service.Path") as MockPath, \
         patch("builtins.open", create=True), \
         patch("json.load", side_effect=json.JSONDecodeError("Invalid JSON", "", 0)):
        
        mock_file = Mock()
        mock_file.exists.return_value = True
        MockPath.return_value = mock_file
        
        # Act & Assert
        with pytest.raises(StateError) as exc_info:
            service.get_group_chat_members("gc_bad_json")
        assert "JSON 格式错误" in str(exc_info.value)


def test_get_group_chat_members_missing_fields_use_defaults(service, mock_group_chat_manager):
    """测试缺失字段使用默认值"""
    # Arrange
    mock_group_chat = Mock()
    mock_group_chat.group_chat_context.repository.load_group_metadata = MagicMock(
        return_value=Mock(project_path="/path")
    )
    mock_group_chat_manager.load_group_chat_from_disk.return_value = mock_group_chat
    
    # 缺少某些字段
    session_state_data = {
        "Leader": {
            "main_session": "session_123",
            # 缺少 btw_session, cwd, use_docker
        },
    }
    
    with patch("agents_hub.api.services.group_chat_service.Path") as MockPath, \
         patch("builtins.open", create=True), \
         patch("json.load", return_value=session_state_data):
        
        mock_file = Mock()
        mock_file.exists.return_value = True
        MockPath.return_value = mock_file
        
        # Act
        result = service.get_group_chat_members("gc_partial")
    
    # Assert
    assert len(result) == 1
    assert result[0].name == "Leader"
    assert result[0].btw_session == []  # 默认空列表
    assert result[0].cwd is None
    assert result[0].use_docker is False  # 默认 False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/api/services/test_group_chat_service.py::test_get_group_chat_members_success -v`
Expected: FAIL with "AttributeError: 'GroupChatService' object has no attribute 'get_group_chat_members'"

- [ ] **Step 3: 实现 get_group_chat_members 方法**

在 `GroupChatService` 类中添加：

```python
    async def get_group_chat_members(
        self, group_chat_id: str
    ) -> list[GroupChatMember]:
        """获取群聊成员列表
        
        Args:
            group_chat_id: 群聊 ID
            
        Returns:
            list[GroupChatMember]: 成员列表
            
        Raises:
            ResourceNotFoundError: 群聊不存在或 session_state 文件不存在
            StateError: JSON 格式错误或数据损坏
        """
        # 1. 读取 metadata 获取 project_path
        try:
            group_chat = await self.group_chat_manager.load_group_chat_from_disk(
                group_chat_id
            )
            metadata = await group_chat.group_chat_context.repository.load_group_metadata()
            project_path = metadata.project_path
        except FileNotFoundError as e:
            raise ResourceNotFoundError(
                f"群聊不存在: {group_chat_id}",
                details={"group_chat_id": group_chat_id},
            ) from e

        # 2. 构建 agent_session_state.json 文件路径
        group_chat_dir = get_group_chat_dir(project_path, group_chat_id)
        session_state_file = group_chat_dir / "agent_session_state.json"

        # 3. 验证文件存在性
        if not session_state_file.exists():
            raise ResourceNotFoundError(
                f"session_state 文件不存在: {session_state_file}",
                details={
                    "group_chat_id": group_chat_id,
                    "session_state_file": str(session_state_file),
                },
            )

        # 4. 读取并解析 JSON（带异常捕获）
        try:
            with session_state_file.open("r", encoding="utf-8") as f:
                session_data = json.load(f)
        except json.JSONDecodeError as e:
            raise StateError(
                f"session_state JSON 格式错误: {e}",
                details={
                    "group_chat_id": group_chat_id,
                    "session_state_file": str(session_state_file),
                },
            ) from e

        # 5. 使用 Pydantic 模型验证并转换
        members = []
        for agent_name, agent_data in session_data.items():
            member = GroupChatMember(
                name=agent_name,
                main_session=agent_data.get("main_session"),
                btw_session=agent_data.get("btw_session", []),
                cwd=agent_data.get("cwd"),
                use_docker=agent_data.get("use_docker", False),
            )
            members.append(member)

        return members
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/api/services/test_group_chat_service.py -k get_group_chat_members -v`
Expected: 所有 get_group_chat_members 相关测试通过

- [ ] **Step 5: 提交 get_group_chat_members 实现**

```bash
git add agents_hub/api/services/group_chat_service.py tests/api/services/test_group_chat_service.py
git commit -m "feat(service): 实现 get_group_chat_members 方法

- 从 agent_session_state.json 读取成员信息
- 完整的容错处理（文件不存在、JSON 格式错误）
- 使用 dict.get() 提供默认值
- Pydantic 自动验证字段类型
- 包含完整的单元测试覆盖"
```

---

## Task 9: 集成测试与文档

**Files:**
- Create: `tests/api/services/test_group_chat_service_integration.py`
- Modify: `docs/superpowers/specs/2026-06-03-group-chat-service-design.md`

- [ ] **Step 1: 编写集成测试**

```python
# tests/api/services/test_group_chat_service_integration.py
"""
GroupChatService 集成测试

测试 Service 与真实 GroupChatManager 的集成
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from agents_hub.api.services.group_chat_service import GroupChatService
from agents_hub.core.orchestration import GroupChatManager
from agents_hub.exceptions import ValidationError, ResourceNotFoundError


@pytest.fixture
def temp_project_dir():
    """创建临时项目目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def real_service():
    """使用真实的 GroupChatManager"""
    manager = GroupChatManager()
    return GroupChatService(manager)


@pytest.fixture
def ensure_leader_role():
    """确保测试环境中存在 Leader role"""
    from agents_hub.roles import RoleManager
    role_manager = RoleManager()
    roles = role_manager.list_role_names()
    if "Leader" not in roles:
        pytest.skip("测试环境缺少 Leader role，跳过集成测试")


async def test_full_lifecycle(real_service, temp_project_dir, ensure_leader_role):
    """测试完整的群聊生命周期：创建 → 加载 → 列表 → 删除"""
    # 1. 创建群聊
    info = await real_service.create_group_chat(
        team_members=["Leader"],
        project_path=str(temp_project_dir),
        group_chat_name="Integration Test Group",
    )
    assert info.group_chat_name == "Integration Test Group"
    assert info.is_active is True
    group_chat_id = info.group_chat_id

    # 2. 列出群聊（应该包含刚创建的）
    summaries = await real_service.list_group_chats()
    assert any(s.group_chat_id == group_chat_id for s in summaries)

    # 3. 获取详细信息
    detail = await real_service.get_group_chat_info(group_chat_id)
    assert detail.group_chat_id == group_chat_id
    assert detail.is_active is True

    # 4. 删除群聊（保留数据）
    await real_service.delete_group_chat(group_chat_id, keep_data=True)
    
    # 5. 验证不在内存中
    summaries_after = await real_service.list_group_chats(is_active_only=True)
    assert not any(s.group_chat_id == group_chat_id for s in summaries_after)

    # 6. 从磁盘加载
    loaded_info = await real_service.load_group_chat(group_chat_id)
    assert loaded_info.group_chat_id == group_chat_id
    assert loaded_info.is_active is True  # 重新加载后变为活跃

    # 7. 完全删除
    await real_service.delete_group_chat(group_chat_id, keep_data=False)
    
    # 8. 验证彻底不存在
    with pytest.raises(ResourceNotFoundError):
        await real_service.get_group_chat_info(group_chat_id)


async def test_idempotent_operations(real_service, temp_project_dir, ensure_leader_role):
    """测试幂等性操作"""
    # 创建群聊
    info = await real_service.create_group_chat(
        team_members=["Leader"],
        project_path=str(temp_project_dir),
    )
    group_chat_id = info.group_chat_id

    # 多次加载应该返回相同结果
    info1 = await real_service.load_group_chat(group_chat_id)
    info2 = await real_service.load_group_chat(group_chat_id)
    assert info1.group_chat_id == info2.group_chat_id

    # 删除不存在的群聊不抛异常
    await real_service.delete_group_chat("gc_nonexistent", keep_data=True)

    # 清理
    await real_service.delete_group_chat(group_chat_id, keep_data=False)
```

- [ ] **Step 2: 运行集成测试**

Run: `pytest tests/api/services/test_group_chat_service_integration.py -v`
Expected: 所有集成测试通过

- [ ] **Step 3: 更新设计文档状态**

在 `docs/superpowers/specs/2026-06-03-group-chat-service-design.md` 的元信息部分修改：

```markdown
| 字段 | 值 |
|------|-----|
| 创建日期 | 2026-06-03 |
| 作者 | Claude & Nico |
| 状态 | ✅ 已实现 |
| 相关模块 | agents_hub/api/services/, agents_hub/api/schemas/ |
| 最后审查 | 2026-06-03（Subagent 架构审查） |
| 实现完成 | 2026-06-03 |
```

- [ ] **Step 4: 验证所有测试通过**

Run: `pytest tests/api/services/test_group_chat_service*.py -v`
Expected: 所有单元测试和集成测试通过

- [ ] **Step 5: 最终提交**

```bash
git add tests/api/services/test_group_chat_service_integration.py docs/superpowers/specs/2026-06-03-group-chat-service-design.md
git commit -m "test(service): 添加 GroupChatService 集成测试

- 测试完整生命周期（创建→加载→列表→删除）
- 测试幂等性操作
- 更新设计文档状态为已实现"
```

---

## 执行后验证清单

完成所有 Task 后，执行以下验证：

- [ ] 所有单元测试通过：`pytest tests/api/services/test_group_chat_service.py -v`
- [ ] 所有集成测试通过：`pytest tests/api/services/test_group_chat_service_integration.py -v`
- [ ] Schema 验证测试通过：`pytest tests/api/schemas/test_group_chats.py -v`
- [ ] 代码符合 DRY、YAGNI、SRP 原则
- [ ] 所有方法都有完整的异常处理
- [ ] 设计文档状态已更新
- [ ] 所有变更已提交到 git

---

## 下一步

完成本计划后，下一步工作：

1. **创建 FastAPI 路由层** (`agents_hub/api/routers/group_chats.py`)
   - 定义 REST API 端点
   - 依赖注入 GroupChatService
   - OpenAPI 文档

2. **注册路由到 FastAPI 应用**
   - 在 `agents_hub/api/app.py` 中注册路由

3. **端到端测试**
   - 测试 API 端点与前端集成
   - 测试全局异常处理器

---

**计划创建完成！**