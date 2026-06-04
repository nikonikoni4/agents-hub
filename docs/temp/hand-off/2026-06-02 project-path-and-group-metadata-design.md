# 交接文档：project_path 持久化和 group_metadata 设计

**日期**：2026-06-02  
**任务背景**：为 AgentSessionInfo 添加 cwd 参数，并设计群聊元数据持久化方案

---

## 1. 原始需求

用户想要：
1. 在 `AgentSessionInfo` 上添加 `cwd` 参数，表示每个 role 的 CLI 命令启动位置
2. `agents_bridge` 已经添加了 `cwd` 参数支持
3. 需要一个群聊级别的根目录配置，作为所有 agent 的默认 cwd

---

## 2. 方案演进过程

### 方案 1：使用 group_cwd（已废弃）
- 最初计划：在 `GroupChatSession` 中添加 `group_cwd` 字段
- 持久化到 `group_chat_session.jsonl` 的 `meta_data`
- **问题**：用户认为不需要单独的 `group_cwd`，直接使用 `project_path` 即可

### 方案 2：持久化 project_path（已废弃）
- 将 `project_path` 添加到 `GroupChatSession` 并持久化
- `project_path` 的双重用途：
  - 用途 1：计算群聊数据存储路径
  - 用途 2：作为 agent CLI 命令的默认工作目录
- **问题**：
  - `project_path` 当前没有持久化，每次都是构造参数传入
  - 发现 `GroupChatSession` 只在**有消息时才保存**，如果创建群聊但没有对话，则不会保存

### 方案 3：group_metadata.json（当前方案）✅
用户提出的最终方案：

#### 核心设计
1. **延迟创建消息历史 + 立即创建元数据索引**
   - 群聊数据（messages、agent_member）在**首次消息时**才创建
   - 使用 `group_metadata.json` 立即保存群聊配置信息

2. **文件结构**
```
teams/
  <project_path>/
    <group_chat_id>/
      group_metadata.json          # 新增：群聊元数据（GroupChat.start() 时立即创建）
      group_chat_session.jsonl     # 消息历史（首次消息时创建）
      agent_member.json     # Agent 状态（_generate_and_register_tokens() 时创建）
      compact_history.jsonl        # 压缩历史（首次压缩时创建）
```

3. **group_metadata.json 结构**
```json
{
  "group_chat_id": "abc-123",
  "group_chat_name": "我的开发团队",  // 默认使用 group_chat_id
  "project_path": "/workspace/project-a",
  "created_at": "2026-06-02T10:30:00",
  "group_type": "MANAGER_ORCHESTRATE"  // 可选
}
```

4. **CWD 优先级规则**
```
Agent 实际使用的 cwd = AgentSessionInfo.cwd (如果非空) 
                      OR project_path (从 group_metadata.json 读取)
                      OR None (使用当前工作目录)
```

---

## 3. 已完成的修改

### 3.1 数据模型修改
✅ `GroupChatSession` 添加了 `group_cwd` 字段（后来废弃，因为用户决定用 `group_metadata.json`）
✅ `AgentSessionInfo` 已有 `cwd` 字段（由 `agents_bridge` 已支持）

### 3.2 持久化层修改
✅ `GroupChatRepository`:
   - `load_group_chat_session()` 支持加载 `group_cwd`（后来废弃）
   - `save_group_chat_session()` 支持保存 `group_cwd`（后来废弃）

### 3.3 业务逻辑修改
✅ `GroupChat._generate_and_register_tokens()`:
   - 创建新 `AgentSessionInfo` 时，使用 `group_chat_session.group_cwd` 作为默认 `cwd`
   - 对已存在的 agent，如果 `cwd` 为空，则填充 `group_cwd`

**注意**：这部分代码需要调整，因为 `group_cwd` 废弃了，应该从 `group_metadata.json` 中读取 `project_path`

---

## 4. 待实现的功能

### 4.1 高优先级：group_metadata.json 支持

#### 新增数据模型
```python
# agents_hub/core/context/group_metadata.py
@dataclass
class GroupMetadata:
    group_chat_id: str
    group_chat_name: str  # 默认使用 group_chat_id
    project_path: str
    created_at: datetime
    group_type: str = "MANAGER_ORCHESTRATE"
```

#### GroupChatRepository 新增方法
```python
async def save_group_metadata(self, metadata: GroupMetadata):
    """保存群聊元数据到 group_metadata.json"""
    pass

async def load_group_metadata(self) -> GroupMetadata:
    """加载群聊元数据"""
    pass
```

#### GroupChat.start() 保存元数据
```python
async def start(self):
    await self.group_chat_context.load()
    
    # 立即保存元数据
    metadata = GroupMetadata(
        group_chat_id=self.group_chat_id,
        group_chat_name=self.group_chat_id,  # 默认值
        project_path=self.project_path,
        created_at=datetime.now(),
        group_type=self.group_type.value,
    )
    await self.group_chat_context.repository.save_group_metadata(metadata)
    
    # ... 后续逻辑
```

#### 调整 _generate_and_register_tokens()
将原来使用 `group_chat_session.group_cwd` 的地方改为从 `group_metadata.json` 读取 `project_path`：

```python
# 读取 project_path
metadata = await self.group_chat_context.repository.load_group_metadata()
default_cwd = metadata.project_path

# 创建 AgentSessionInfo 时使用
AgentSessionInfo(token=token, cwd=default_cwd)
```

### 4.2 中优先级：GroupChatManager 增强

#### 列出所有群聊
```python
def list_all_group_chats(self, base_path: str = "teams") -> list[dict]:
    """
    扫描 teams/*/*/group_metadata.json 获取所有群聊
    
    Returns:
        [
            {
                "group_chat_id": "abc-123",
                "group_chat_name": "我的开发团队",
                "project_path": "/workspace/project-a",
                "created_at": "2026-06-02T10:30:00",
                "is_active": True  // 是否在内存中活跃
            },
            ...
        ]
    """
    pass
```

#### 从磁盘加载群聊
```python
async def load_group_chat_from_disk(
    self, 
    group_chat_id: str, 
    project_path: str,
    team: Team
) -> GroupChat:
    """
    从磁盘加载一个群聊到内存
    
    1. 读取 group_metadata.json 验证信息
    2. 创建 GroupChat 实例
    3. 调用 GroupChat.load()
    4. 注册到 GroupChatManager
    """
    pass
```

#### 创建群聊（用户提问但未确认）
用户问："GroupChatManager 有创建群聊的方法吗？"

**当前情况**：没有。外部需要手动创建 `GroupChat` 并调用 `register()`。

**建议**（未确认是否实施）：
```python
async def create_group_chat(
    self,
    team: Team,
    group_type: GroupChatType,
    project_path: str,
    group_chat_name: str | None = None,
    group_chat_id: str | None = None,
) -> GroupChat:
    """
    创建并启动一个新群聊
    
    1. 创建 GroupChat 实例
    2. 调用 start() 启动
    3. 保存 group_metadata.json
    4. 自动注册到 GroupChatManager
    """
    pass
```

---

## 5. 关键发现

### 5.1 GroupChatSession 的保存时机
- **只在有消息时保存**：`add_message()` → `save_group_chat_session()`
- **创建群聊但没有对话**：不会保存 `group_chat_session.jsonl`
- **这是合理的**：避免创建空文件浪费空间

### 5.2 project_path 的生命周期
- **不持久化**：每次创建 `GroupChat` 时作为构造参数传入
- **用于计算路径**：`GroupChatRepository` 用它计算文件存储位置
- **现在也作为默认 cwd**：通过 `group_metadata.json` 持久化

### 5.3 GroupChatManager 的职责
- 当前只是**内存注册表**，管理活跃的 `GroupChat` 实例
- 没有创建、列表、持久化等管理功能
- 建议增强为完整的生命周期管理器

---

## 6. 需要回答的问题

1. **是否需要在 GroupChatManager 添加 create_group_chat() 方法？**
   - 当前外部需要手动创建 + 注册，比较繁琐
   - 统一管理可以简化使用

2. **group_metadata.json 是否需要版本号字段？**
   - 方便未来升级和兼容性处理

3. **如何处理旧群聊的迁移？**
   - 旧群聊没有 `group_metadata.json`
   - 需要降级处理或迁移脚本

---

## 7. 下一步行动

### 立即实施：
1. **回滚已废弃的 group_cwd 修改**
   - 移除 `GroupChatSession.group_cwd`
   - 移除持久化层的 `group_cwd` 支持

2. **实现 group_metadata.json 支持**
   - 创建 `GroupMetadata` 数据模型
   - `GroupChatRepository` 添加保存/加载方法
   - `GroupChat.start()` 立即保存元数据
   - 调整 `_generate_and_register_tokens()` 使用 `project_path`

### 后续优化：
3. **GroupChatManager 增强**
   - 添加 `list_all_group_chats()` 方法
   - 添加 `load_group_chat_from_disk()` 方法
   - （可选）添加 `create_group_chat()` 方法

4. **文档更新**
   - 更新 `CONTEXT.md` 说明 `group_metadata.json`
   - 说明 `project_path` 的双重用途

---

## 8. 代码位置参考

- `agents_hub/core/context/group_chat_session.py` - AgentSessionInfo, GroupChatSession
- `agents_hub/core/context/group_chat_repository.py` - 持久化层
- `agents_hub/core/context/group_chat_context.py` - 业务逻辑
- `agents_hub/core/orchestration/group_chat.py` - GroupChat 主逻辑
- `agents_hub/core/orchestration/group_chat_manager.py` - GroupChatManager

---

**交接完成**，建议下一位 Agent 先回滚废弃的修改，再实施 `group_metadata.json` 方案。
