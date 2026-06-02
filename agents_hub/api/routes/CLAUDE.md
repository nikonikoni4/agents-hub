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

### ❌ 禁止在路由中写 try/except

全局异常处理器已在 `app.py` 注册，路由层不需要任何错误处理。

```python
# ❌ 错误
@router.get("/skills/{skill_name}")
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    try:
        skill = service.get_skill(skill_name)
        return SkillResponse.from_domain(skill)
    except SkillNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.to_dict()) from e

# ✅ 正确
@router.get("/skills/{skill_name}")
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
@router.get("/skills")
def list_skills():
    service = SkillService()  # 直接实例化
    ...

# ✅ 正确
def get_skill_service() -> SkillService:
    return SkillService()

@router.get("/skills")
def list_skills(service: SkillService = Depends(get_skill_service)):
    ...
```

### ❌ 禁止在路由中写业务逻辑

路由只做：接收参数 → 调用 service → 转换响应。

```python
# ❌ 错误 — 业务逻辑写在路由里
@router.delete("/skills/{skill_name}")
def delete_skill(skill_name: str):
    skill_path = Path("skills") / skill_name
    if not skill_path.exists():
        raise HTTPException(404)
    shutil.rmtree(skill_path)

# ✅ 正确 — 委托给 service
@router.delete("/skills/{skill_name}")
def delete_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    service.delete_skill(skill_name)
    return {"message": f"Skill '{skill_name}' 删除成功"}
```

### ❌ 禁止直接返回领域模型

使用 Pydantic schema 的 `from_domain` 方法转换。

```python
# ❌ 错误 — 返回领域模型
@router.get("/skills/{skill_name}")
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    return service.get_skill(skill_name)  # 返回 SkillInfo

# ✅ 正确 — 转换为 response schema
@router.get("/skills/{skill_name}", response_model=SkillResponse)
def get_skill(skill_name: str, service: SkillService = Depends(get_skill_service)):
    skill = service.get_skill(skill_name)
    return SkillResponse.from_domain(skill)
```

### ✅ 每个端点必须声明 response_model

```python
# ✅ 正确
@router.get("/skills", response_model=list[SkillResponse])
@router.post("/skills", response_model=SkillResponse)
@router.delete("/skills/{skill_name}", response_model=dict[str, str])
```

## 文件组织

```
routes/
├── __init__.py    # 汇总所有 router
├── skills.py      # 一个领域一个文件
└── roles.py       # 未来新增
```

- `__init__.py` 中汇总所有 router：`from .skills import router`
- 每个文件一个 `router = APIRouter()`，对应一个领域
- 新增路由文件后，在 `__init__.py` 中汇总
