# 实施总结：project_path 持久化和 group_metadata.json

**日期**：2026-06-02  
**任务**：为 AgentMemberInfo 添加 cwd 参数，并设计群聊元数据持久化方案

---

## 一、任务完成情况

### ✅ 已完成的修改

1. **创建 GroupMetadata 数据模型** (`agents_hub/core/context/group_metadata.py`)
   - 定义了 `GroupMetadata` 数据类
   - 包含 `group_chat_id`、`group_chat_name`、`project_path`、`created_at`、`group_type` 字段
   - 实现 `to_dict()` 和 `from_dict()` 序列化方法

2. **添加路径工具函数** (`agents_hub/core/foundation/paths.py`)
   - 在 `GroupChatPaths` 中添加 `metadata_file()` 方法
   - 返回 `group_metadata.json` 的路径

3. **移除 group_cwd 字段** (`agents_hub/core/context/group_chat_session.py`)
   - 从 `GroupChatSession` 中删除废弃的 `group_cwd` 字段

4. **Repository 添加 metadata 支持** (`agents_hub/core/context/group_chat_repository.py`)
   - `__init__` 中保存 `project_path` 属性
   - 添加 `metadata_file` 路径和 `_metadata_lock` 锁
   - 实现 `save_group_metadata()` 方法
   - 实现 `load_group_metadata()` 方法
   - 移除 `group_cwd` 的持久化逻辑

5. **GroupChat.start() 立即保存 metadata** (`agents_hub/core/orchestration/group_chat.py`)
   - 在加载上下文后立即创建并保存 `GroupMetadata`
   - metadata 在首次消息之前就已创建

6. **调整 token 生成逻辑** (`agents_hub/core/orchestration/group_chat.py`)
   - `_generate_and_register_tokens()` 从 metadata 读取 `project_path` 作为 `default_cwd`
   - 替换原来使用 `group_chat_session.group_cwd` 的逻辑

7. **导出新模型** (`agents_hub/core/context/__init__.py`)
   - 添加 `GroupMetadata` 到导出列表

---

## 二、文件结构变化

### 修改前
```
teams/<project_path>/<group_chat_id>/
├── group_chat_session.jsonl      # 消息历史（首次消息时创建，包含 group_cwd）
├── agent_member.json       # Agent 状态
└── compact_history.jsonl          # 压缩历史
```

### 修改后
```
teams/<project_path>/<group_chat_id>/
├── group_metadata.json            # ✅ 新增：群聊元数据（GroupChat.start() 时立即创建）
├── group_chat_session.jsonl       # 消息历史（首次消息时创建，不再包含 group_cwd）
├── agent_member.json       # Agent 状态
└── compact_history.jsonl          # 压缩历史
```

---

## 三、核心设计原则

1. **SSOT（单一数据源）**：`project_path` 只存储在 `group_metadata.json` 中
2. **延迟创建 vs 立即创建**：
   - `group_metadata.json` 在 `GroupChat.start()` 时立即创建
   - `group_chat_session.jsonl` 在首次消息时才创建（延迟创建）
3. **职责分离**：
   - `GroupMetadata` 只关注配置信息
   - `GroupChatSession` 只关注消息历史
4. **CWD 优先级规则**：
   ```
   Agent 实际使用的 cwd = AgentMemberInfo.cwd (如果非空) 
                         OR project_path (从 group_metadata.json 读取)
                         OR None (使用当前工作目录)
   ```

---

## 四、测试覆盖

### 创建的测试文件

1. **`tests/core/context/test_group_metadata.py`** (5 个测试)
   - 测试 metadata 的保存和加载
   - 测试加载不存在的 metadata
   - 测试 metadata 文件路径
   - 测试默认 group_type
   - 测试序列化和反序列化

2. **`tests/core/orchestration/test_group_chat_metadata.py`** (4 个测试)
   - 测试 metadata 和 agent cwd 的完整工作流程
   - 测试 agent cwd 为空时的回退逻辑
   - 测试 metadata 在重启后的持久化
   - 测试 metadata 独立于消息历史创建

### 测试结果

✅ 所有 15 个 context 层测试通过
- `test_agent_session_cwd.py`: 4 个测试通过
- `test_group_chat_context.py`: 6 个测试通过
- `test_group_metadata.py`: 5 个测试通过

✅ 所有 4 个集成测试通过
- `test_group_chat_metadata.py`: 4 个测试通过

---

## 五、向后兼容性

### 旧群聊处理

1. **没有 group_metadata.json 的旧群聊**：
   - `load_group_metadata()` 返回 `None`
   - `_generate_and_register_tokens()` 中 `default_cwd` 为空字符串
   - Agent 的 cwd 保持原有值或为空

2. **没有 cwd 字段的旧 agent_member.json**：
   - `load_agent_member()` 会将 `cwd` 设置为默认值 `""`
   - 向后兼容测试已通过

---

## 六、关键代码位置

| 文件 | 修改内容 |
|------|---------|
| `agents_hub/core/context/group_metadata.py` | 新增：GroupMetadata 数据模型 |
| `agents_hub/core/foundation/paths.py` | 新增：metadata_file() 方法 |
| `agents_hub/core/context/group_chat_session.py` | 删除：group_cwd 字段 |
| `agents_hub/core/context/group_chat_repository.py` | 新增：save/load_group_metadata()<br>删除：group_cwd 持久化逻辑 |
| `agents_hub/core/orchestration/group_chat.py` | 新增：start() 中保存 metadata<br>修改：_generate_and_register_tokens() 使用 metadata |
| `agents_hub/core/context/__init__.py` | 新增：导出 GroupMetadata |

---

## 七、后续可选增强

以下功能不在当前任务范围内，可作为后续优化：

1. **GroupChatManager 增强**：
   - `list_all_group_chats()` - 扫描所有 `group_metadata.json`
   - `load_group_chat_from_disk()` - 从磁盘加载群聊
   - `create_group_chat()` - 统一创建入口

2. **版本管理**：
   - 在 metadata 中添加 `version` 字段
   - 方便未来升级和迁移

3. **群聊名称管理**：
   - 提供修改 `group_chat_name` 的接口
   - 当前默认使用 `group_chat_id`

---

## 八、验证清单

- [x] GroupMetadata 数据模型创建
- [x] metadata_file() 路径工具函数添加
- [x] GroupChatSession.group_cwd 字段移除
- [x] Repository 添加 metadata 保存/加载方法
- [x] Repository 移除 group_cwd 持久化逻辑
- [x] GroupChat.start() 立即保存 metadata
- [x] _generate_and_register_tokens() 使用 metadata
- [x] 所有单元测试通过
- [x] 所有集成测试通过
- [x] 向后兼容性验证

---

**实施完成时间**：2026-06-02  
**所有测试状态**：✅ PASSED (19/19)
