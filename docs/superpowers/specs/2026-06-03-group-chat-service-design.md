# GroupChatService 设计文档

## 元信息

| 字段 | 值 |
|------|-----|
| 创建日期 | 2026-06-03 |
| 作者 | Claude & Nico |
| 状态 | 设计完成，待实现 |
| 相关模块 | agents_hub/api/services/, agents_hub/api/schemas/ |
| 最后审查 | 2026-06-03（Subagent 架构审查） |

## 修订记录

| 日期 | 版本 | 修改内容 |
|------|------|---------|
| 2026-06-03 | 1.0 | 初始设计完成 |
| 2026-06-03 | 1.1 | 架构审查后修复严重问题和部分中等问题 |

**v1.1 主要修改**：
- 修复 delete_group_chat 的竞态条件（先读 metadata 再 unregister）
- 为 get_group_chat_members 添加容错处理说明（JSONDecodeError 转换）
- 澄清 load_group_chat 职责（依赖 GroupChatManager，不重复实现）
- 移除 create_group_chat 中的 project_path 验证（由 GroupChat 负责）
- 为 list_group_chats 添加 is_active_only 参数
- 为 GroupChatSummary 添加 project_path 字段
- 补充 use_docker 字段的数据来源说明
- 明确 get_group_chat_info 的 is_active 判断逻辑
- 添加完整的异常转换映射表
- 补充单例初始化时机和跨进程共享说明
- 添加前端性能优化建议

## 概述

GroupChatService 是群聊应用服务层，作为 API 路由层和 Core 层之间的业务编排层。负责协调 GroupChatManager、Team、RoleManager，提供群聊生命周期管理和查询接口。

### 设计定位

**方案选择：轻量服务层（业务编排层）**

```
API 路由层
    ↓
GroupChatService (业务编排)
    ↓
GroupChatManager (全局注册表) + Team (验证) + RoleManager (验证)
    ↓
GroupChat (单个群聊生命周期)
```

**职责边界**：
- **Service**: 业务流程编排、参数验证、异常转换
- **GroupChatManager**: 全局注册表、token 管理、实例管理
- **GroupChat**: 单个群聊的启动/加载/停止/清理

**不做什么**：
- 不持有状态（所有状态在 GroupChatManager）
- 不直接操作文件
- 不管理 token

## 架构设计

### 全局单例共享

GroupChatManager 必须是全局单例，因为需要在多个入口之间共享状态：

```
┌─────────────────────────────────────────────────┐
│      全局 GroupChatManager（唯一实例）            │
│  • _group_chats: dict[str, GroupChat]          │
│  • _tokens: dict[str, tuple[agent, group_id]]  │
└─────────────┬───────────────────────────────────┘
              │
    ┌─────────┴──────────┐
    ↓                    ↓
┌─────────────┐   ┌──────────────┐
│  MCP Server │   │  API Server  │
│  (Agent调用) │   │  (前端调用)   │
└─────────────┘   └──────────────┘
      │                  │
      ↓                  ↓
  call_agent        GroupChatService
```

**实现方式：依赖注入**

```python
# agents_hub/api/app.py
_group_chat_manager_singleton = GroupChatManager()

def get_group_chat_manager() -> GroupChatManager:
    return _group_chat_manager_singleton

# 使用
service = GroupChatService(get_group_chat_manager())
```

**初始化时机**：

在 `agents_hub/api/app.py` 中，FastAPI 应用启动时初始化：

```python
# agents_hub/api/app.py
from fastapi import FastAPI
from agents_hub.core.orchestration import GroupChatManager

# 全局单例（模块级变量）
_group_chat_manager_singleton = GroupChatManager()

def get_group_chat_manager() -> GroupChatManager:
    """获取全局 GroupChatManager 单例"""
    return _group_chat_manager_singleton

# FastAPI 应用
app = FastAPI()

@app.on_event("startup")
async def startup():
    # 可以在这里执行额外的初始化逻辑
    logger.info("GroupChatManager 单例已初始化")
```

**跨进程共享说明**：

- **同一进程**：如果 MCP Server 和 API Server 在同一进程中运行（共享内存），单例有效
- **不同进程**：如果在不同进程中，需要通过以下方式同步状态：
  1. 共享数据库（如 SQLite 的 WAL 模式）
  2. Redis 等外部缓存
  3. **文件系统作为 SSOT**（当前设计）

**当前设计的状态同步机制**：
- 通过 `list_all_group_chats()` 扫描磁盘上的 `group_metadata.json` 文件
- 通过文件系统作为单一数据源（SSOT）保证一致性
- 内存中的状态（`_group_chats`）是磁盘状态的缓存
- 适用于单机部署或共享文件系统的分布式部署

### 接口设计策略

**选择：资源型 API（而非业务型聚合 API）**

后端提供原子接口，前端自己聚合：

```
GET /api/group_chats                    # 群聊列表
GET /api/group_chats/{id}               # 群聊信息
GET /api/group_chats/{id}/members       # 成员列表
GET /api/roles/{role_name}              # 角色详情（RoleService）
```

**优点**：
- 职责清晰，Service 不侵入跨领域聚合
- 易于测试和扩展
- 符合 RESTful 风格

## 数据模型

### 请求模型

```python
class GroupChatCreate(BaseModel):
    """创建群聊请求"""
    team_members: list[str] = Field(..., min_length=1)
    project_path: str
    group_chat_name: str | None = None
```

### 响应模型

```python
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
    project_path: str  # 用于区分同名群聊或显示所属项目
    is_active: bool
    created_at: datetime


class GroupChatMember(BaseModel):
    """群聊成员（运行时信息）"""
    name: str
    main_session: str | None
    btw_session: list[str]
    cwd: str | None
    use_docker: bool = False  # 占位，当前默认 False
                              # 数据来源：agent_session_state.json 的 "use_docker" 字段
                              # Docker 分支实现后需要从配置读取
```

### 数据来源映射

```
磁盘文件                    中间数据结构              响应 Schema
─────────────────────────────────────────────────────────────
group_metadata.json  →  GroupMetadata        →  GroupChatSummary
                        (dataclass)              GroupChatInfo

agent_session_state  →  dict[str, dict]      →  GroupChatMember
.json                   (直接解析JSON)
```

**说明**：
- `GroupMetadataSchema` 和 `AgentSessionStateSchema` 在设计阶段提及，但实现时可以直接使用 `GroupMetadata` dataclass 和原始 dict
- 不需要额外的转换层，简化实现

## Service 接口

### 生命周期管理

#### 1. create_group_chat

```python
async def create_group_chat(
    self,
    team_members: list[str],
    project_path: str,
    group_chat_name: str | None = None,
) -> GroupChatInfo
```

**流程**：
1. 验证 team_members 非空
2. 创建 Team 对象（验证 roles 存在，会自动验证 project_path）
3. 生成 group_chat_id
4. 创建 GroupChat 实例
5. 调用 GroupChat.start()
6. 注册到 GroupChatManager
7. 返回 GroupChatInfo

**异常**：
- `ValidationError`: team_members 为空
- `ResourceNotFoundError`: role 不存在或 project_path 不存在（由 Team 或 GroupChat 验证并转换）
- `StateError`: 启动失败

**说明**：
- Service 层不重复验证 project_path，由 GroupChat.start() 负责
- 每次调用生成新的 group_chat_id，不检查重复

#### 2. load_group_chat

```python
async def load_group_chat(self, group_chat_id: str) -> GroupChatInfo
```

**流程**：
1. 检查是否已在内存中
   - 如果存在，直接返回 GroupChatInfo（幂等性）
2. 调用 GroupChatManager.load_group_chat_from_disk(group_chat_id)
   - Manager 内部会读取 metadata 和 team_members
   - Manager 内部会创建 Team 对象并验证 roles
   - Manager 内部会创建 GroupChat 实例并调用 load()
   - Manager 内部会注册到自身
3. 从返回的 GroupChat 实例构建 GroupChatInfo
4. 返回 GroupChatInfo

**异常**：
- `ResourceNotFoundError`: 群聊不存在或 role 已被删除（Manager 抛出并转换）
- `StateError`: 加载失败

**说明**：
- Service 层不重复实现加载逻辑，依赖 GroupChatManager 完成
- Service 层只负责异常转换和响应构建
- **幂等性**: 多次调用返回相同的 GroupChatInfo

#### 3. delete_group_chat

```python
async def delete_group_chat(
    self, 
    group_chat_id: str, 
    keep_data: bool = False
) -> None
```

**流程**：
1. 如果 keep_data=False，先读取 metadata（在 unregister 之前）
   - 尝试从内存中的 GroupChat 实例读取
   - 如果不在内存，从磁盘读取
2. 从内存中移除（调用 GroupChatManager.unregister）
3. 如果 keep_data=False：
   - 使用步骤 1 获取的 project_path
   - 获取群聊目录路径
   - 删除整个目录

**异常**：
- `ResourceNotFoundError`: 群聊不存在（磁盘和内存都不存在时）
- `ExternalServiceError`: 文件删除失败

**说明**：
- `keep_data=True`: 只从内存移除，保留磁盘数据
- `keep_data=False`: 完全删除（内存+磁盘）
- **幂等性**: 如果群聊不存在，静默返回（不抛出异常）
- **竞态安全**: 先读取 metadata，再 unregister，避免数据丢失

### 查询接口

#### 4. list_group_chats

```python
async def list_group_chats(self, is_active_only: bool = False) -> list[GroupChatSummary]
```

**流程**：
1. 调用 GroupChatManager.list_all_group_chats()
2. 如果 is_active_only=True，过滤出活跃的群聊
3. 转换为 GroupChatSummary 列表

**异常**：无（返回空列表如果没有群聊）

**说明**：
- `is_active_only=False`: 返回所有群聊（活跃+非活跃）
- `is_active_only=True`: 只返回内存中运行的群聊
- 支持前端按需加载，避免列表过长

#### 5. get_group_chat_info

```python
async def get_group_chat_info(self, group_chat_id: str) -> GroupChatInfo
```

**流程**：
1. 尝试从内存获取
   - 调用 GroupChatManager.get_group_chat()
   - 读取实例的 metadata
   - 返回 GroupChatInfo（is_active=True）
2. 如果不在内存，从磁盘读取 metadata
   - 调用 GroupChatManager.load_group_chat_from_disk()
   - 返回 GroupChatInfo（is_active=False）

**异常**：
- `ResourceNotFoundError`: 群聊不存在

**说明**：
- `is_active` 字段根据来源确定：内存=True，磁盘=False
- 数据一致性：优先从内存读取，保证最新状态

#### 6. get_group_chat_members

```python
async def get_group_chat_members(self, group_chat_id: str) -> list[GroupChatMember]
```

**流程**：
1. 读取 metadata 获取 project_path
   - 调用 `GroupChatManager.load_group_chat_from_disk()`
2. 构建 agent_session_state.json 文件路径
3. 验证文件存在性
4. 读取并解析 JSON（带异常捕获）
5. 使用 Pydantic 模型验证并转换为 GroupChatMember 列表
   - 使用 `dict.get()` 提供默认值，避免 KeyError
   - Pydantic 自动验证字段类型

**异常**：
- `ResourceNotFoundError`: 群聊不存在或 session_state 文件不存在
- `StateError`: JSON 格式错误或数据损坏

**说明**：
- 返回所有成员（Leader + Workers）
- 不包含头像、描述（由前端调用 RoleService 获取）
- **容错处理**: 缺失字段使用默认值，JSON 解析错误转换为 StateError

### 辅助方法（私有）

```python
async def _build_group_chat_info_from_instance(
    self, 
    group_chat: GroupChat
) -> GroupChatInfo:
    """从内存中的 GroupChat 实例构建 GroupChatInfo"""
    metadata = await group_chat.group_chat_context.repository.load_group_metadata()
    return GroupChatInfo(...)
```

## 异常处理

### 异常体系

使用 `agents_hub/exceptions.py` 的统一异常：

| 异常类型 | 使用场景 |
|---------|---------|
| `ValidationError` | 输入参数不符合要求 |
| `ResourceNotFoundError` | 资源不存在（群聊、role、project_path） |
| `StateError` | 操作在错误状态下执行（启动/加载失败） |
| `ExternalServiceError` | 外部服务调用失败（文件系统错误） |

### 异常转换

Service 层将底层异常转换为业务语义：

```python
# Team 的 ValueError → ResourceNotFoundError
try:
    team = Team(team_members_name=team_members, team_name="default_team")
except ValueError as e:
    raise ResourceNotFoundError(str(e), details={...}) from e

# GroupChat 启动失败 → StateError
try:
    await group_chat.start()
except Exception as e:
    raise StateError(f"群聊启动失败: {e}", details={...}) from e
```

### 全局异常处理器

由于项目已有全局异常处理器，Service 层直接抛出异常，不需要在每个方法中 try-except。

### 完整异常转换映射

| 底层异常 | Service 层异常 | 场景 |
|---------|---------------|------|
| Team 的 ValueError | ResourceNotFoundError | role 不存在 |
| GroupChat.start() 失败 | StateError | 启动失败 |
| FileNotFoundError | ResourceNotFoundError | 群聊不存在或文件不存在 |
| JSONDecodeError | StateError | agent_session_state.json 格式错误 |
| PermissionError | ExternalServiceError | 文件权限不足 |
| OSError (磁盘满等) | ExternalServiceError | 系统级文件操作错误 |
| GroupChatNotFoundError | ResourceNotFoundError | 群聊不在内存中 |

## 前端集成

### 使用流程示例

**右侧栏成员列表**：

```javascript
// 1. 获取成员列表（运行时信息）
const members = await api.getGroupChatMembers(groupChatId)
// [{ name: "Leader", main_session: "xxx", cwd: "/path", use_docker: false }, ...]

// 2. 并行获取角色详情
const roleDetails = await Promise.all(
  members.map(m => api.getRoleDetail(m.name))
)

// 3. 聚合显示
const displayMembers = members.map((m, i) => ({
  ...m,  // name, main_session, btw_session, cwd, use_docker
  avatar: roleDetails[i].avatar,
  description: roleDetails[i].description,
  abilities: roleDetails[i].abilities
}))
```

**性能优化建议**：
- 前端应该缓存已获取的 RoleDetail，避免重复请求同一个 role
- 如果 members 列表很长（10+ 成员），考虑：
  - 使用请求去重（多个成员可能引用同一个 role）
  - 分批请求或使用虚拟滚动
  - 延迟加载非关键信息

## 依赖关系

### 模块依赖

```
GroupChatService
├── GroupChatManager（全局单例，依赖注入）
├── RoleManager（实例化）
├── Team（验证用）
├── GroupChat（创建实例）
├── group_chat_paths（路径工具）
└── exceptions（异常类）
```

### 数据流

```
前端请求
    ↓
API 路由层
    ↓
GroupChatService（业务编排）
    ├→ GroupChatManager（全局状态）
    ├→ Team（验证）
    ├→ RoleManager（验证）
    └→ GroupChat（生命周期管理）
```

## 设计决策

### 决策 1：为什么选择轻量服务层而非富领域服务？

**理由**：
- 符合现有 SkillService 风格
- 职责清晰：Service 做编排，Manager 做管理，GroupChat 做执行
- 易于测试和维护

### 决策 2：为什么选择资源型 API 而非业务型聚合 API？

**理由**：
- 职责单一：GroupChatService 管理群聊，不跨域聚合 role 信息
- 易于扩展：新增信息只需新增接口
- 性能可控：前端可以并行请求、按需加载

### 决策 3：为什么 GroupChatManager 必须是单例？

**理由**：
- 持有全局运行时状态（_group_chats, _tokens）
- 需要在 MCP Server 和 API Server 之间共享
- 保证状态一致性

### 决策 4：为什么移除 stop_group_chat 方法？

**理由**：
- 群聊的停止应该由 GroupChatManager 根据空闲时间自动管理
- 用户不应该手动"停止"群聊，只有"删除"的概念
- 类似数据库连接池的自动回收机制

### 决策 5：为什么不在 metadata 中存储 team_members？

**理由**：
- agent_session_state.json 是运行时真实状态的 SSOT
- metadata 是配置快照，应保持轻量
- Service 层负责数据聚合和转换

## 待实现事项

### 当前设计中的占位

1. **use_docker 字段**：
   - 当前默认 False
   - Docker 分支实现后需要从配置读取

2. **权限字段**：
   - role.json 中的 permissions 字段未实现
   - 需要在 RoleService 中添加

### 后续优化

1. **Team 冗余设计**：
   - 当前创建 GroupChat 需要传入 Team 对象
   - 后续会简化为直接传入 team_members 列表

2. **自动清理机制**：
   - GroupChatManager 根据空闲时间自动 unregister
   - 需要定义清理策略（多久未活动视为空闲）

## 总结

GroupChatService 作为轻量业务编排层，提供了清晰的群聊生命周期管理和查询接口。通过资源型 API 设计，保持了模块间的低耦合和高内聚，便于测试和扩展。

核心设计要点：
- ✅ 全局单例共享（MCP + API）
- ✅ 业务编排层定位
- ✅ 资源型 API 设计
- ✅ 统一异常处理
- ✅ 前端友好的数据模型
