# Skills 管理模块设计

## 背景

agents-hub 需要一个全局的 Skill 资源管理系统，用于：
1. 管理全局 skills 库（作为所有 Role 添加 skill 的数据来源）
2. 提供 skills 的增删查功能
3. 为未来的"skill 广场"（从网络获取 skill）预留接口

核心需求：
- 全局 skills 库存储在 `config.data_path/skills/`
- 每个 skill 是一个目录，包含 `SKILL.md` 文件
- 从 SKILL.md 的 frontmatter 读取 `name` 和 `description`
- Role 通过符号链接引用全局 skills（本体只有一份）

## 系统概览

### 架构分层

```
┌─────────────────────────────────────────────────────────┐
│  前端 (React + Electron)                                 │
│  - Skills 列表页面                                       │
│  - Skill 详情页面                                        │
└─────────────────────────────────────────────────────────┘
                      ↓ HTTP REST API
┌─────────────────────────────────────────────────────────┐
│  API 层 (FastAPI)                                        │
│  - routes/skills.py: REST API 端点                       │
│  - services/skill_service.py: 应用服务层                 │
│  - schemas/skills.py: Pydantic 数据模型                  │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  Skills 模块 (领域层)                                     │
│  - skill_manager.py: SkillManager 类                     │
│  - models.py: SkillInfo 数据模型                         │
│  - exceptions.py: Skill 异常类                           │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  文件系统                                                 │
│  config.data_path/skills/                                │
│  ├── skill-creator/                                      │
│  │   └── SKILL.md                                        │
│  └── frontend-design/                                    │
│      └── SKILL.md                                        │
└─────────────────────────────────────────────────────────┘
```

### 核心目标

1. **全局 Skill 资源管理** — 统一管理所有可用的 skills
2. **简单的增删查接口** — 提供 REST API 供前端调用
3. **Frontmatter 解析** — 从 SKILL.md 读取 name 和 description
4. **预留扩展接口** — 为未来的网络获取功能预留 API

## 核心组件设计

### 1. 目录结构

```
agents_hub/
├── skills/                    # 新增模块
│   ├── __init__.py
│   ├── skill_manager.py       # SkillManager 类
│   ├── models.py              # SkillInfo 数据模型
│   └── exceptions.py          # Skill 异常类
│
├── api/
│   ├── routes/
│   │   └── skills.py          # Skills REST API
│   ├── services/
│   │   └── skill_service.py   # Skills 应用服务
│   └── schemas/
│       └── skills.py          # Pydantic 数据模型（API 层）
│
└── config.data_path/skills/   # 全局 skills 存储
    ├── skill-creator/
    │   └── SKILL.md
    └── frontend-design/
        └── SKILL.md
```

### 2. 数据模型

#### skills/models.py（领域层）

```python
from dataclasses import dataclass

@dataclass
class SkillInfo:
    """Skill 信息（从 SKILL.md frontmatter 解析）"""
    name: str           # skill 名称
    description: str    # skill 描述
    path: str          # skill 目录的绝对路径（内部使用）
```

#### api/schemas/skills.py（API 层）

```python
from pydantic import BaseModel

class SkillResponse(BaseModel):
    """Skill 响应模型"""
    name: str
    description: str
    
    @classmethod
    def from_domain(cls, skill_info: SkillInfo):
        return cls(
            name=skill_info.name,
            description=skill_info.description
        )

class SkillCreateRequest(BaseModel):
    """创建 Skill 请求（预留，暂不实现）"""
    url: str           # skill 的网络地址
    # 未来扩展：version, source 等
```

**设计说明**：
- `SkillInfo`：领域层数据模型，包含 path（内部使用）
- `SkillResponse`：API 响应模型，只返回 name 和 description（不暴露 path）
- `SkillCreateRequest`：预留接口，用于未来从网络添加 skill

### 3. SkillManager（核心逻辑）

#### skills/skill_manager.py

```python
import yaml
import shutil
from pathlib import Path
from agents_hub.config import config
from agents_hub.skills.models import SkillInfo
from agents_hub.skills.exceptions import SkillNotFoundError, InvalidSkillError

class SkillManager:
    """全局 Skill 管理器"""
    
    def __init__(self):
        self.skills_root = config.data_path / "skills"
        self.skills_root.mkdir(parents=True, exist_ok=True)
    
    def list_skills(self) -> list[SkillInfo]:
        """列出所有 skills
        
        扫描 skills_root 下的所有子目录，
        读取每个目录下的 SKILL.md frontmatter，
        返回 SkillInfo 列表。
        
        Returns:
            list[SkillInfo]: 所有 skills 的信息列表
        """
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
    
    def get_skill(self, skill_name: str) -> SkillInfo:
        """获取单个 skill 信息
        
        Args:
            skill_name: skill 名称
            
        Returns:
            SkillInfo: skill 信息
            
        Raises:
            SkillNotFoundError: skill 不存在
        """
        skill_path = self.skills_root / skill_name
        if not skill_path.exists():
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")
        
        return self._parse_skill_md(skill_path)
    
    def delete_skill(self, skill_name: str) -> None:
        """删除 skill
        
        Args:
            skill_name: skill 名称
            
        Raises:
            SkillNotFoundError: skill 不存在
            
        注意：
            暂不检查是否有 Role 正在使用该 skill。
            未来需要在删除前检查符号链接引用。
        """
        skill_path = self.skills_root / skill_name
        if not skill_path.exists():
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")
        
        shutil.rmtree(skill_path)
    
    def add_skill_from_url(self, url: str) -> SkillInfo:
        """从网络添加 skill（预留接口，暂不实现）
        
        Args:
            url: skill 的网络地址
            
        Returns:
            SkillInfo: 添加的 skill 信息
            
        Raises:
            NotImplementedError: 功能暂未实现
            
        未来实现：
            1. 下载 skill 压缩包
            2. 解压到临时目录
            3. 验证 SKILL.md 格式
            4. 移动到 skills_root
        """
        raise NotImplementedError("网络获取功能暂未实现")
    
    def _parse_skill_md(self, skill_path: Path) -> SkillInfo:
        """解析 SKILL.md 的 frontmatter
        
        Args:
            skill_path: skill 目录路径
            
        Returns:
            SkillInfo: 解析后的 skill 信息
            
        Raises:
            InvalidSkillError: SKILL.md 格式错误或缺少必需字段
        """
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
            path=str(skill_path)
        )
```

**关键设计**：
- `list_skills()`：扫描目录 + 解析 frontmatter，跳过无效的 skill
- `get_skill()`：获取单个 skill，不存在时抛出异常
- `delete_skill()`：直接删除目录（暂不检查 Role 使用情况）
- `add_skill_from_url()`：预留接口，抛出 NotImplementedError
- `_parse_skill_md()`：解析 SKILL.md 的 frontmatter，验证必需字段

### 4. 应用服务层

#### api/services/skill_service.py

```python
from agents_hub.skills.skill_manager import SkillManager
from agents_hub.skills.models import SkillInfo

class SkillService:
    """Skills 应用服务层
    
    协调 SkillManager，提供业务逻辑封装。
    当前阶段逻辑简单，主要是转发调用。
    未来可以在这里添加权限验证、审计日志等。
    """
    
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

### 5. API 路由

#### api/routes/skills.py

```python
from fastapi import APIRouter, HTTPException
from api.services.skill_service import SkillService
from api.schemas.skills import SkillResponse, SkillCreateRequest
from agents_hub.skills.exceptions import SkillNotFoundError

router = APIRouter()

@router.get("/skills", response_model=list[SkillResponse])
async def list_skills():
    """获取所有 skills
    
    Returns:
        list[SkillResponse]: skills 列表
    """
    service = SkillService()
    skills = service.list_skills()
    return [SkillResponse.from_domain(s) for s in skills]

@router.get("/skills/{skill_name}", response_model=SkillResponse)
async def get_skill(skill_name: str):
    """获取单个 skill
    
    Args:
        skill_name: skill 名称
        
    Returns:
        SkillResponse: skill 信息
        
    Raises:
        HTTPException: 404 - skill 不存在
    """
    service = SkillService()
    try:
        skill = service.get_skill(skill_name)
        return SkillResponse.from_domain(skill)
    except SkillNotFoundError:
        raise HTTPException(status_code=404, detail="Skill not found")

@router.delete("/skills/{skill_name}")
async def delete_skill(skill_name: str):
    """删除 skill
    
    Args:
        skill_name: skill 名称
        
    Returns:
        dict: 成功消息
        
    Raises:
        HTTPException: 404 - skill 不存在
    """
    service = SkillService()
    try:
        service.delete_skill(skill_name)
        return {"message": "Skill deleted successfully"}
    except SkillNotFoundError:
        raise HTTPException(status_code=404, detail="Skill not found")

@router.post("/skills", response_model=SkillResponse)
async def add_skill(request: SkillCreateRequest):
    """从网络添加 skill（预留接口）
    
    Args:
        request: 包含 skill URL 的请求
        
    Returns:
        SkillResponse: 添加的 skill 信息
        
    Raises:
        HTTPException: 501 - 功能暂未实现
    """
    service = SkillService()
    try:
        skill = service.add_skill_from_url(request.url)
        return SkillResponse.from_domain(skill)
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="功能暂未实现")
```

**API 端点**：
- `GET /api/skills` - 列出所有 skills
- `GET /api/skills/{skill_name}` - 获取单个 skill
- `DELETE /api/skills/{skill_name}` - 删除 skill
- `POST /api/skills` - 添加 skill（预留，返回 501）

### 6. 异常处理

#### skills/exceptions.py

```python
from agents_hub.exceptions import ResourceNotFoundError, ValidationError

class SkillNotFoundError(ResourceNotFoundError):
    """Skill 不存在"""
    pass

class InvalidSkillError(ValidationError):
    """无效的 Skill（SKILL.md 格式错误）"""
    pass
```

**异常体系**：
- `SkillNotFoundError`：继承自 `ResourceNotFoundError`，用于 skill 不存在的情况
- `InvalidSkillError`：继承自 `ValidationError`，用于 SKILL.md 格式错误

## 与 Role 模块的集成（预留说明）

### Role 添加 Skill 的流程（未来实现）

当用户给某个 Role 添加 skill 时，流程如下：

```
1. 前端调用 POST /api/roles/{role_name}/skills
   {
     "skill_name": "skill-creator"
   }

2. RoleService 调用 SkillManager.get_skill() 验证 skill 存在

3. RoleService 创建符号链接：
   local_data/agents/{role_name}/work_root/skills/{skill_name}
   ↓ (符号链接)
   config.data_path/skills/{skill_name}

4. 更新 role.json 记录已安装的 skills（可选）
```

**符号链接说明**：
- Windows 需要管理员权限或开发者模式才能创建符号链接
- 使用 `os.symlink(target, link_name)` 创建
- 本体只有一份，所有 Role 共享同一份 skill 文件
- 更新 skill 时，所有使用该 skill 的 Role 自动生效

### 删除 Skill 的安全检查（未来实现）

```python
def delete_skill(self, skill_name: str) -> None:
    """删除 skill"""
    # 1. 检查是否有 Role 正在使用
    # 需要扫描所有 Role 的 work_root/skills/ 目录
    # 如果有符号链接指向该 skill，抛出异常或提示用户
    
    # 2. 删除 skill 目录
    skill_path = self.skills_root / skill_name
    if not skill_path.exists():
        raise SkillNotFoundError(f"Skill '{skill_name}' not found")
    
    shutil.rmtree(skill_path)
```

**说明**：
- 这部分逻辑属于 **roles 模块**，不在本次设计范围内
- 本次只实现 skills 模块的基础功能
- 符号链接的创建和管理留到设计 Role 管理功能时实现

## 数据流

### 1. 列出所有 Skills

```
前端
  → GET /api/skills
    → SkillService.list_skills()
      → SkillManager.list_skills()
        → 扫描 config.data_path/skills/
        → 解析每个 SKILL.md 的 frontmatter
        → 返回 list[SkillInfo]
      → 转换为 list[SkillResponse]
    → 返回 JSON
```

### 2. 删除 Skill

```
前端
  → DELETE /api/skills/{skill_name}
    → SkillService.delete_skill()
      → SkillManager.delete_skill()
        → 检查 skill 是否存在
        → 删除 config.data_path/skills/{skill_name} 目录
      → 返回成功消息
    → 返回 JSON
```

### 3. 从网络添加 Skill（预留）

```
前端
  → POST /api/skills
    → SkillService.add_skill_from_url()
      → SkillManager.add_skill_from_url()
        → 抛出 NotImplementedError
      → 捕获异常
    → 返回 501 Not Implemented
```

## 未来扩展

### 1. 网络获取 Skill

**实现方式**：
- 定义 Skill 仓库的索引格式（JSON 文件）
- 从 GitHub/GitLab 下载 skill 压缩包
- 解压、验证、保存到 skills_root

**索引格式示例**：
```json
{
  "skills": [
    {
      "name": "skill-creator",
      "description": "Create and improve skills",
      "version": "1.0.0",
      "download_url": "https://github.com/.../skill-creator.zip"
    }
  ]
}
```

### 2. Skill 版本管理

**扩展字段**：
- `version`：skill 版本号
- `author`：作者
- `created_at`：创建时间
- `updated_at`：更新时间

### 3. Skill 分类和标签

**扩展字段**：
- `category`：分类（代码生成、文档编写等）
- `tags`：标签列表

### 4. Skill 使用统计

**功能**：
- 统计每个 skill 被多少个 Role 使用
- 在删除 skill 前提示用户

## 测试计划

### 单元测试

- `SkillManager.list_skills()` - 测试扫描和解析
- `SkillManager.get_skill()` - 测试获取单个 skill
- `SkillManager.delete_skill()` - 测试删除
- `SkillManager._parse_skill_md()` - 测试 frontmatter 解析

### 集成测试

- API 端点测试（使用 FastAPI TestClient）
- 异常处理测试（skill 不存在、格式错误等）

## 总结

本设计实现了一个简单的全局 Skill 资源管理系统，包括：

1. **独立的 skills 模块**：职责清晰，易于扩展
2. **完整的 API 接口**：支持增删查操作
3. **Frontmatter 解析**：从 SKILL.md 读取元数据
4. **预留扩展接口**：为网络获取功能预留 API

**不在本次范围内**：
- Skill 与 Role 的绑定关系（属于 roles 模块）
- 符号链接的创建和管理（属于 roles 模块）
- 网络获取 skill 的具体实现（未来迭代）
