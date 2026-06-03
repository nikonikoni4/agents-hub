# api/routes 规则

> 上级规则：[docs/coding-rules/backend-style.md](../../../docs/coding-rules/backend-style.md)

## 架构

```
route → service → manager
```

- route：HTTP 入口，只做参数接收和响应转换
- service：业务协调（`agents_hub/api/services/`）
- manager：领域逻辑（`agents_hub/skills/`、`agents_hub/roles/` 等）

## 路由层规则

### ✅ Router 必须声明 prefix 和 tags

每个 router 通过 `prefix` 声明统一前缀，通过 `tags` 声明文档分组。路由装饰器中不再重复前缀。

```python
# ❌ 错误 — 前缀写在每个路由上
router = APIRouter()

@router.get("/skills", response_model=list[SkillResponse])
@router.get("/skills/{skill_name}", response_model=SkillResponse)

# ✅ 正确 — 前缀统一在 router 声明
router = APIRouter(prefix="/skills", tags=["skills"])

@router.get("", response_model=list[SkillResponse])
@router.get("/{skill_name}", response_model=SkillResponse)
```

### ❌ 禁止路由路径与前缀重复

路由装饰器中的路径不能包含 `prefix` 已声明的前缀，避免出现 `/skills/skills` 这种重复路径。

```python
# ❌ 错误 — 最终路径变成 /skills/skills
router = APIRouter(prefix="/skills")

@router.get("/skills")

# ❌ 错误 — 最终路径变成 /skills/skills/{name}
@router.get("/skills/{skill_name}")

# ✅ 正确 — 最终路径是 /skills/{name}
@router.get("/{skill_name}")
```

### ❌ 禁止动态路径在静态路径之前定义

FastAPI 按注册顺序匹配路由。如果 `/{name}` 在 `/avatars` 之前定义，请求 `/avatars` 会被 `/{name}` 捕获，导致参数值为 `"avatars"` 而非命中静态路由。

```python
# ❌ 错误 — /avatars 永远不会被匹配到
@router.get("/{name}", response_model=RoleResponse)
def get_role(name: str): ...

@router.get("/avatars", response_model=list[str])
def list_avatars(): ...

# ✅ 正确 — 静态路径在前，动态路径在后
@router.get("/avatars", response_model=list[str])
def list_avatars(): ...

@router.get("/{name}", response_model=RoleResponse)
def get_role(name: str): ...
```

### ❌ 禁止在路由中写 try/except

全局异常处理器已在 `app.py` 注册，路由层不需要任何错误处理。

```python
# ❌ 错误
@router.get("/{skill_name}")
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    try:
        skill = service.get_skill(skill_name)
        return SkillResponse.from_domain(skill)
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict()) from e

# ✅ 正确
@router.get("/{skill_name}")
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    skill = service.get_skill(skill_name)
    return SkillResponse.from_domain(skill)
```

### ❌ 禁止在路由中导入异常类

路由不处理异常，不需要导入。

```python
# ❌ 错误
from agents_hub.skills.exceptions import SkillNotFoundError, InvalidSkillError

# ✅ 正确 — 无异常导入
from agents_hub.api.schemas.skills import SkillResponse
from agents_hub.api.services.skill_service import SkillService
```

### ❌ 禁止在路由中实例化 Service

使用 FastAPI 的 `Depends` 做依赖注入。

```python
# ❌ 错误
@router.get("")
def list_skills():
    service = SkillService()  # 直接实例化
    ...

# ✅ 正确
def get_skill_service() -> SkillService:
    return SkillService()

@router.get("")
def list_skills(service: SkillService = Depends(get_skill_service)):
    ...
```

### ❌ 禁止在路由中写业务逻辑

路由只做：接收参数 → 调用 service → 转换响应。

```python
# ❌ 错误 — 业务逻辑写在路由里
@router.delete("/{skill_name}")
def delete_skill(skill_name: str):
    skill_path = Path("skills") / skill_name
    if not skill_path.exists():
        raise HTTPException(404)
    shutil.rmtree(skill_path)

# ✅ 正确 — 委托给 service
@router.delete("/{skill_name}")
def delete_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    service.delete_skill(skill_name)
    return {"message": f"Skill '{skill_name}' 删除成功"}
```

### ❌ 禁止直接返回领域模型

使用 Pydantic schema 的 `from_domain` 方法转换。

```python
# ❌ 错误 — 返回领域模型
@router.get("/{skill_name}")
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    return service.get_skill(skill_name)  # 返回 SkillInfo

# ✅ 正确 — 转换为 response schema
@router.get("/{skill_name}", response_model=SkillResponse)
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    skill = service.get_skill(skill_name)
    return SkillResponse.from_domain(skill)
```

### ✅ 每个端点必须声明 response_model

```python
# ✅ 正确
@router.get("", response_model=list[SkillResponse])
@router.post("", response_model=SkillResponse)
@router.delete("/{skill_name}", response_model=dict[str, str])
```

## 文件组织

```
routes/
├── __init__.py    # 汇总所有 router
├── skills.py      # 一个领域一个文件
└── roles.py       # 未来新增
```

- `__init__.py` 中汇总所有 router：`from .skills import router`
- 每个文件一个 `router = APIRouter(prefix="/xxx", tags=["xxx"])`，对应一个领域
- 新增路由文件后，在 `__init__.py` 中汇总
