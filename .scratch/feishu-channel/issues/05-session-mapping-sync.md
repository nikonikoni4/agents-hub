---
labels: [ready-for-agent]
---

# Issue 5：Session 映射与同步状态管理

## Parent

无

## What to build

实现飞书群到 agents-hub 群聊的映射关系，以及增量同步状态管理。

**实现内容**：
1. `agents_hub/channels/feishu/session.py`
   - `FeishuSessionMapping` - 绑定关系数据模型
   - `FeishuSyncState` - 同步状态数据模型
   - `FeishuSessionManager` - 管理映射和同步状态
   - 持久化到 JSON 文件

**数据模型**：
```python
@dataclass
class FeishuSessionMapping:
    """飞书群绑定关系（持久化）"""
    feishu_chat_id: str          # 飞书群 ID（oc_xxx，创建后不变）
    group_chat_id: str           # agents-hub 群聊 ID
    group_chat_name: str         # agents-hub 群聊名称（便于显示）
    bound_at: str                # 绑定时间

@dataclass
class FeishuSyncState:
    """同步状态（持久化）"""
    feishu_chat_id: str          # 飞书群 ID
    last_message_id: int         # 最后同步的消息 ID
    last_sync_at: str            # 最后同步时间
```

**核心功能**：
- `bind()` - 绑定飞书群到 agents-hub 群聊
- `unbind()` - 解绑飞书群
- `get_mapping()` - 获取绑定关系
- `get_sync_state()` - 获取同步状态（不存在则创建）
- `update_sync_state()` - 更新同步状态
- `save()` - 持久化映射关系和同步状态
- `load()` - 加载映射关系和同步状态

## Acceptance criteria

- [ ] `FeishuSessionMapping` 数据模型定义
- [ ] `FeishuSyncState` 数据模型定义
- [ ] `FeishuSessionManager` 类实现
- [ ] 映射关系能够持久化到 JSON 文件
- [ ] 同步状态能够持久化到 JSON 文件
- [ ] `load()` 启动时自动加载映射和同步状态
- [ ] `save()` 修改后自动保存
- [ ] 单元测试通过

## Blocked by

- Issue 2：飞书 Channel 基础框架

## 相关文件

- `agents_hub/channels/feishu/session.py`

## 参考文档

- [架构约束文件](../architecture.md)
- [Checklist](../checklist.md)
- `agents_hub/channels/wechat/commander.py` - 微信会话管理参考
