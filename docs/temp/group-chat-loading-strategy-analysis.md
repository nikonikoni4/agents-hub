# 群聊加载策略分析与建议

## 问题背景

当前系统需要决定群聊加载策略：
- **方案 A**：按活跃文件夹加载
- **方案 B**：按前 N 个活跃群聊加载
- **待解决**：不活跃群聊如何获取？是否需要搜索/筛选/分页机制？

## 当前实现分析

### 后端现状

**数据存储结构**：
```
local_data/teams/
  └── <项目路径哈希>/
      └── <group_chat_id>/
          ├── group_metadata.json
          ├── agent_member.json
          └── <group_chat_id>.jsonl
```

**API 端点**：
```python
GET /api/v1/group-chats?is_active_only=false
```

**实现方式** (`GroupChatManager.list_all_group_chats()`):
- 全量扫描 `local_data/teams/*/*/group_metadata.json`
- 读取所有群聊的 metadata
- 返回完整列表（包含 is_active 标记）
- **无分页机制**
- **无排序机制**
- **无筛选机制**（只有 is_active_only 二元过滤）

### 前端现状

**数据获取** (`useGroupChatList.ts`):
```typescript
const chats = await listGroupChatInfos();  // 获取全部群聊
const groups = groupSessionsByProject(chats, lastViewRecords, []);
```

**展示方式**：
- 按项目路径分组
- 在每个项目组内显示所有群聊
- **全量加载所有群聊**
- **无懒加载**
- **无虚拟滚动**

### 性能瓶颈分析

当前架构的潜在问题：

| 群聊数量 | 问题 | 影响 |
|---------|------|------|
| < 50 | 无明显问题 | 可接受 |
| 50-200 | 前端渲染压力 | 列表滚动卡顿 |
| 200-1000 | 扫描磁盘耗时 | 首屏加载慢 |
| > 1000 | 内存占用过高 | 前后端都卡 |

---

## 方案对比

### 方案 A：按活跃文件夹加载

**定义**：优先加载最近使用的项目文件夹下的群聊。

**实现思路**：
```
1. 记录每个项目文件夹的最后访问时间
2. 按访问时间排序文件夹
3. 优先加载前 N 个文件夹的群聊
4. 懒加载其他文件夹
```

**优点**：
- ✅ 符合用户工作习惯（通常集中在少数项目）
- ✅ 减少扫描范围（只扫描活跃文件夹）
- ✅ 项目切换时自然分组

**缺点**：
- ❌ 需要额外维护文件夹访问时间
- ❌ 跨项目搜索群聊困难
- ❌ 单个项目下群聊很多时仍有问题

**适用场景**：
- 用户同时维护多个项目（10+ 个）
- 每个项目下群聊数量适中（< 50 个）

---

### 方案 B：按前 N 个活跃群聊加载

**定义**：全局排序所有群聊，优先加载最近使用的 N 个。

**实现思路**：
```
1. 维护每个群聊的 last_update_at 字段
2. 按 last_update_at 降序排序
3. 首次加载前 N 个（如 50 个）
4. 滚动到底部时加载更多
```

**优点**：
- ✅ 最符合直觉（最近用过的就在前面）
- ✅ 实现简单（单字段排序）
- ✅ 支持跨项目统一视图

**缺点**：
- ❌ 仍需全量扫描获取排序依据
- ❌ 项目分组视图下不够自然

**适用场景**：
- 用户主要在少数几个群聊中工作
- 需要快速访问最近使用的群聊

---

### 方案 C（推荐）：混合策略 + 分页

**定义**：结合 A 和 B 的优点，分层加载。

**实现思路**：
```
第一层：内存中活跃群聊（is_active=true）
  └─ 立即显示，无延迟

第二层：最近访问的 N 个项目文件夹
  └─ 扫描这些文件夹，按 last_update_at 排序，取前 50 个

第三层：其他群聊（懒加载）
  └─ 用户滚动到底部或主动搜索时加载
```

**分页机制**：
```
GET /api/v1/group-chats?limit=50&offset=0&sort_by=last_update_at&order=desc
```

**搜索机制**：
```
GET /api/v1/group-chats?search=<关键词>&project_path=<可选>
```

---

## 推荐方案详细设计

### 后端改动

#### 1. 增强 GroupMetadata

```python
# agents_hub/core/context/group_metadata.py

@dataclass
class GroupMetadata:
    group_chat_id: str
    group_chat_name: str
    project_path: str
    created_at: datetime
    group_type: GroupChatType
    last_update_at: datetime  # 新增：最后消息时间
    last_speaker: str | None  # 新增：最后发言者
    last_message: str | None  # 新增：最后消息摘要（前 100 字符）
```

#### 2. 修改 list_all_group_chats()

```python
# agents_hub/core/orchestration/group_chat_manager.py

def list_all_group_chats(
    self,
    limit: int | None = None,
    offset: int = 0,
    sort_by: str = "last_update_at",
    order: str = "desc",
    project_path: str | None = None,
) -> tuple[list[dict], int]:
    """
    列出群聊，支持分页和排序
    
    Returns:
        (群聊列表, 总数)
    """
    # 1. 扫描所有群聊
    all_chats = self._scan_all_group_chats()
    
    # 2. 过滤项目路径
    if project_path:
        all_chats = [c for c in all_chats if c["project_path"] == project_path]
    
    total = len(all_chats)
    
    # 3. 排序
    reverse = (order == "desc")
    all_chats.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
    
    # 4. 分页
    if limit:
        all_chats = all_chats[offset : offset + limit]
    
    return all_chats, total
```

#### 3. 更新 API 端点

```python
# agents_hub/api/routes/group_chat.py

@router.get("", response_model=GroupChatListResponse)
async def list_group_chats(
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    sort_by: str = Query("last_update_at", description="排序字段"),
    order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    project_path: str | None = Query(None, description="过滤项目路径"),
    is_active_only: bool = Query(False, description="只返回活跃群聊"),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """列出群聊（分页）"""
    chats, total = await service.list_group_chats(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        project_path=project_path,
        is_active_only=is_active_only,
    )
    return GroupChatListResponse(items=chats, total=total, limit=limit, offset=offset)
```

### 前端改动

#### 1. 修改 API 调用

```typescript
// frontend/src/core/api/groupChatApi.ts

export async function listGroupChats(params: {
  limit?: number;
  offset?: number;
  sortBy?: 'last_update_at' | 'created_at';
  order?: 'asc' | 'desc';
  projectPath?: string;
  isActiveOnly?: boolean;
}): Promise<GroupChatListResponse> {
  return apiClient.get<GroupChatListResponse>('/group-chats', { params });
}
```

#### 2. 实现懒加载

```typescript
// frontend/src/features/session/hooks/useGroupChatList.ts

export function useGroupChatList() {
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  
  const loadMore = useCallback(async () => {
    if (!hasMore || isLoading) return;
    
    setIsLoading(true);
    try {
      const response = await listGroupChats({
        limit: 50,
        offset: projectGroups.flatMap(g => g.sessions).length,
        sortBy: 'last_update_at',
        order: 'desc',
      });
      
      // 合并新数据
      const newGroups = groupSessionsByProject(response.items, ...);
      setProjectGroups([...projectGroups, ...newGroups]);
      
      setHasMore(response.items.length === response.limit);
    } finally {
      setIsLoading(false);
    }
  }, [projectGroups, hasMore, isLoading]);
  
  return { projectGroups, loadMore, hasMore, isLoading };
}
```

#### 3. UI 优化

```typescript
// frontend/src/features/session/components/SessionList.tsx

export function SessionList() {
  const { projectGroups, loadMore, hasMore, isLoading } = useGroupChatList();
  const observerRef = useRef<IntersectionObserver>();
  
  // 滚动到底部时加载更多
  const lastElementRef = useCallback((node: HTMLElement | null) => {
    if (isLoading) return;
    if (observerRef.current) observerRef.current.disconnect();
    
    observerRef.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        loadMore();
      }
    });
    
    if (node) observerRef.current.observe(node);
  }, [isLoading, hasMore, loadMore]);
  
  return (
    <div>
      {projectGroups.map((group, idx) => (
        <ProjectGroup
          key={group.projectPath}
          {...group}
          ref={idx === projectGroups.length - 1 ? lastElementRef : undefined}
        />
      ))}
      {isLoading && <LoadingSpinner />}
    </div>
  );
}
```

---

## 搜索/筛选功能

### 后端实现

```python
# agents_hub/api/routes/group_chat.py

@router.get("/search", response_model=GroupChatListResponse)
async def search_group_chats(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(50, ge=1, le=200),
    service: GroupChatService = Depends(get_group_chat_service),
):
    """搜索群聊（按名称或项目路径）"""
    return await service.search_group_chats(query, limit)
```

### 前端实现

```typescript
// 搜索框组件
export function SearchGroupChat() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);
  
  const { data, isLoading } = useQuery(
    ['searchGroupChats', debouncedQuery],
    () => searchGroupChats(debouncedQuery),
    { enabled: debouncedQuery.length > 0 }
  );
  
  return (
    <input
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      placeholder="搜索群聊..."
    />
  );
}
```

---

## 性能优化建议

### 1. 缓存机制

```python
# 缓存扫描结果 5 分钟
from functools import lru_cache
import time

@lru_cache(maxsize=1)
def _cached_scan_group_chats():
    cache_key = time.time() // 300  # 5 分钟失效
    return (cache_key, _scan_all_group_chats())

def list_all_group_chats(...):
    _, all_chats = _cached_scan_group_chats()
    # 继续处理...
```

### 2. 索引文件

创建索引文件避免每次全量扫描：

```
local_data/teams/index.json
{
  "version": 1,
  "last_update": "2026-06-14T10:00:00Z",
  "groups": [
    {
      "group_chat_id": "xxx",
      "project_path": "/path/to/project",
      "last_update_at": "2026-06-14T09:30:00Z",
      "metadata_file": "teams/<hash>/<id>/group_metadata.json"
    }
  ]
}
```

每次创建/删除群聊时更新索引，查询时直接读索引。

### 3. 数据库迁移（长期）

如果群聊数量超过 1000，考虑引入 SQLite：

```sql
CREATE TABLE group_chats (
  group_chat_id TEXT PRIMARY KEY,
  group_chat_name TEXT,
  project_path TEXT,
  created_at TIMESTAMP,
  last_update_at TIMESTAMP,
  is_active BOOLEAN,
  metadata_path TEXT
);

CREATE INDEX idx_last_update ON group_chats(last_update_at DESC);
CREATE INDEX idx_project_path ON group_chats(project_path);
```

---

## 实施建议

### 第一阶段（立即）：最小改动
1. 保持现有 API 不变
2. 前端实现虚拟滚动（`@tanstack/react-virtual`）
3. 前端本地分组和排序

**工作量**：2-4 小时

### 第二阶段（短期）：分页支持
1. 后端增加 `limit`/`offset` 参数
2. 前端实现懒加载
3. 添加 `last_update_at` 字段

**工作量**：1-2 天

### 第三阶段（中期）：完整搜索
1. 后端实现全文搜索
2. 前端添加搜索框
3. 实现索引文件

**工作量**：2-3 天

### 第四阶段（长期）：数据库迁移
1. 引入 SQLite
2. 迁移历史数据
3. 优化查询性能

**工作量**：1 周

---

## 总结

**推荐方案**：混合策略（方案 C）

**核心思路**：
- 活跃群聊（内存中）→ 立即显示
- 最近使用的群聊 → 首次加载 50 个
- 其他群聊 → 懒加载 + 搜索

**优先级**：
1. **P0**：前端虚拟滚动（立即实施）
2. **P1**：后端分页支持（短期）
3. **P2**：搜索功能（中期）
4. **P3**：数据库迁移（长期，取决于规模）

**决策依据**：
- 当前群聊数量 < 100：只需前端优化
- 100-500：增加分页
- 500-1000：增加搜索
- \> 1000：考虑数据库

---

## 问题回答

### Q1：方案 A 还是 B？
**A**：推荐方案 C（混合），结合两者优点。

### Q2：不活跃的群聊如何获取？
**A**：懒加载 + 搜索。首屏显示活跃群聊，滚动到底部加载更多，或通过搜索框查找。

### Q3：是否需要分页机制？
**A**：需要，但优先级取决于当前群聊数量：
- < 100：可选（前端虚拟滚动即可）
- \> 100：必需（后端分页）

### Q4：是否需要搜索/筛选？
**A**：需要，但作为第二阶段功能。先实现分页，再实现搜索。
