## 修复结果摘要

### 已修复

| # | 文件 | 问题 | 修复内容 |
|---|------|------|----------|
| 1 | `.gitignore` | 文件末尾缺少换行符（不符合 POSIX 标准） | 添加末尾换行符 |

### 待讨论

| # | 文件 | 问题 | 说明 |
|---|------|------|------|
| 1 | Spec vs 代码路径不一致 | Spec 已更新为 kebab-case (`/ws/group-chat/...`)，但代码仍是 snake_case (`/ws/group_chat/...`) | 需要决定：更新代码对齐 spec，还是回滚 spec |

**路径不一致涉及文件**：
- `agents_hub/api/websocket/endpoint.py:31` - WebSocket 端点路径
- `agents_hub/api/routes/websocket.py:16` - 广播 API 路径
- `frontend/src/core/websocket/WebSocketManager.ts:161` - 前端 WebSocket 连接

### 审查通过（无问题）

- `agents_hub/api/app.py` - 纯格式调整，logger 长行格式化正确
- `agents_hub/api/services/group_chat_service.py` - `toggle_use_docker` 方法逻辑正确，异常处理完整
- `agents_hub/core/context/group_chat_runtime.py` - `set_agent_use_docker` 和 `get_member_dicts` 实现正确
- `agents_hub/core/context/group_chat_session.py` - `AgentMemberInfo.use_docker` 字段定义正确
- `agents_hub/api/schemas/group_chats.py` - `GroupChatMember` schema 与代码对齐
- `CONTEXT.md` - `use_docker` 属性文档更新正确
- 所有 spec 文档更新 - 内容合理，格式规范

---

**需要用户决策**：WebSocket 路径的 kebab-case vs snake_case 问题，应更新代码还是回滚 spec？
