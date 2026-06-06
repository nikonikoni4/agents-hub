# 前后端职责划分重构 - 实施总结

## 已完成的工作

### 阶段 1：后端清理 ✅

**文件**：`agents_hub/api/services/group_chat_service.py`

**移除的 broadcast 调用**：
1. ✅ `create_group_chat()` - 第 166 行（前端创建群聊）
2. ✅ `send_message()` - 第 470 行（前端发送消息）
3. ✅ `pin_message()` - 第 700 行（前端 pin 消息）
4. ✅ `unpin_message()` - 第 720 行（前端 unpin 消息）
5. ✅ `add_group_chat_members()` - 第 758 行（前端添加成员）
6. ✅ 移除 `from agents_hub.realtime import broadcast_group_chat_refresh` 导入

**保留的 broadcast 调用**：
- ✅ `agents_hub/mcp/server.py` 第 462 行：`speak_in_group_chat()` - Agent 发言
- ✅ `agents_hub/mcp/server.py` 第 572 行：`finish_agent_call()` - Agent 完成任务

---

### 阶段 2：前端高优先级修复 ✅

#### 1. 修复创建群聊后列表不刷新 ✅

**文件**：`frontend/src/features/session/hooks/useCreateGroupChat.ts`

**改动**：
```typescript
// 导入 useSessionList
import { useSessionList } from './useSessionList';

export function useCreateGroupChat() {
  const { refreshSessions } = useSessionList();
  
  const createChat = useCallback(async (data: CreateGroupChatRequest) => {
    const result = await createGroupChat(data);
    // ✅ 创建成功后立即刷新群聊列表
    await refreshSessions();
    return result.group_chat_id;
  }, [refreshSessions]);
}
```

**效果**：创建群聊后，左侧列表立即显示新群聊，无需手动刷新或等待 WebSocket。

---

#### 2. 添加删除群聊功能 ✅

**文件**：`frontend/src/features/session/hooks/useDeleteGroupChat.ts`（新增）

**功能**：
- 提供 `deleteChat(chatId, keepData)` 方法
- 乐观更新：立即从列表移除
- 失败时回滚

**使用方式**：
```typescript
import { useDeleteGroupChat } from '@/features/session/hooks/useDeleteGroupChat';

function SessionItem() {
  const { deleteChat, deleting } = useDeleteGroupChat();
  
  const handleDelete = async () => {
    try {
      await deleteChat(chatId, false); // false = 完全删除
      // 删除成功，列表已自动更新
    } catch (error) {
      // 删除失败，已自动回滚
      toast.error('删除失败');
    }
  };
}
```

---

#### 3. 添加 Docker 开关功能 ✅

**文件**：`frontend/src/features/chat/hooks/useMembers.ts`

**新增方法**：
- `refresh()` - 手动刷新成员列表
- `toggleDockerMode(memberName)` - 切换成员的 Docker 状态

**改动**：
```typescript
export function useMembers() {
  // ... 原有代码
  
  const toggleDockerMode = useCallback(async (memberName: string) => {
    const currentMember = members.find(m => m.name === memberName);
    const newValue = !currentMember.use_docker;
    
    // ✅ 乐观更新
    setMembers(prev => prev.map(m => 
      m.name === memberName ? { ...m, use_docker: newValue } : m
    ));
    
    try {
      await updateMemberDockerMode(activeSessionId, memberName, { use_docker: newValue });
    } catch (error) {
      // ✅ 失败时回滚
      await fetchMembers();
      throw error;
    }
  }, [activeSessionId, members, fetchMembers]);
  
  return { members, loading, refresh: fetchMembers, toggleDockerMode };
}
```

**使用方式**：
```typescript
// 在 RightSidebar 或 MemberItem 组件中
import { useMembers } from '@/features/chat/hooks/useMembers';

function MemberItem({ member }: { member: MemberWithRole }) {
  const { toggleDockerMode } = useMembers();
  
  const handleToggle = async () => {
    try {
      await toggleDockerMode(member.name);
      // Docker 状态已切换，UI 已自动更新
    } catch (error) {
      toast.error('切换失败');
    }
  };
  
  return (
    <div>
      <span>{member.name}</span>
      {/* 显示 Docker 状态 */}
      <button onClick={handleToggle}>
        {member.use_docker ? '🐳 Docker' : '💻 本地'}
      </button>
    </div>
  );
}
```

---

## 待完成的工作（中优先级）

### 1. 添加 roles 订阅同步头像变更 🟡

**文件**：`frontend/src/features/session/hooks/useSessionList.ts`

**需要添加**：
```typescript
import { useRolesStore } from '@/features/roles/store/rolesStore';

export function useSessionList() {
  const { roles } = useRolesStore();
  
  useEffect(() => {
    // 当 roles 发生变化时，重新构建头像映射并刷新列表
    refreshSessions();
  }, [roles]);
}
```

---

### 2. 改进消息发送错误处理 🟡

**文件**：`frontend/src/layouts/ChatArea/ChatArea.tsx`

**需要改进**：
```typescript
const handleSendMessage = async (content: string) => {
  // 生成临时 ID
  const tempId = `temp-${Date.now()}`;
  
  // 乐观更新
  setLocalMessages(prev => [...prev, {
    id: tempId,
    speaker: 'user',
    content,
    timestamp: new Date().toISOString(),
    platform: 'web'
  }]);
  
  try {
    await sendMessage(chatId, { content, send_to });
  } catch (error) {
    // ✅ 失败时移除乐观消息
    setLocalMessages(prev => prev.filter(m => m.id !== tempId));
    toast.error('消息发送失败');
  }
};
```

---

### 3. 优化成员列表乐观更新 🟡

**文件**：`frontend/src/features/chat/hooks/useMembers.ts`

**需要添加**：
```typescript
const addMember = useCallback(async (memberName: string) => {
  // 乐观更新
  setMembers(prev => [...prev, {
    name: memberName,
    main_session: null,
    btw_session: [],
    cwd: null,
    use_docker: false,
    role: null,
    isOnline: false
  }]);
  
  try {
    await addGroupChatMembers(chatId, { member_names: [memberName] });
  } catch (error) {
    await fetchMembers(); // 失败时回滚
    throw error;
  }
}, [chatId, fetchMembers]);
```

---

## UI 集成指南

### 在 RightSidebar 中显示 Docker 状态

**文件**：`frontend/src/layouts/RightSidebar/RightSidebar.tsx`

**示例代码**：
```tsx
import { useMembers } from '@/features/chat/hooks/useMembers';

function RightSidebar() {
  const { members, toggleDockerMode } = useMembers();
  
  return (
    <div className="right-sidebar">
      <h3>成员列表</h3>
      {members.map(member => (
        <div key={member.name} className="member-item">
          <img src={member.role?.avatar} alt={member.name} />
          <span>{member.name}</span>
          
          {/* Docker 状态显示 */}
          <button
            onClick={() => toggleDockerMode(member.name)}
            className={member.use_docker ? 'docker-active' : 'docker-inactive'}
          >
            {member.use_docker ? '🐳' : '💻'}
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

### 添加删除群聊功能到 SessionList

**文件**：`frontend/src/features/session/components/SessionList.tsx` 或相关组件

**示例代码**：
```tsx
import { useDeleteGroupChat } from '@/features/session/hooks/useDeleteGroupChat';

function SessionItem({ session }) {
  const { deleteChat, deleting } = useDeleteGroupChat();
  const [showMenu, setShowMenu] = useState(false);
  
  const handleDelete = async () => {
    if (!confirm('确定要删除此群聊吗？')) return;
    
    try {
      await deleteChat(session.group_chat_id);
      toast.success('删除成功');
    } catch (error) {
      toast.error('删除失败');
    }
  };
  
  return (
    <div className="session-item">
      <span>{session.group_chat_name}</span>
      
      {/* 右键菜单或三点菜单 */}
      <button onClick={() => setShowMenu(!showMenu)}>⋮</button>
      
      {showMenu && (
        <div className="menu">
          <button onClick={handleDelete} disabled={deleting}>
            {deleting ? '删除中...' : '删除群聊'}
          </button>
        </div>
      )}
    </div>
  );
}
```

---

## 验证测试

### 手动测试清单

#### 1. 创建群聊测试 ✅
- [ ] 打开应用，点击"新建群聊"
- [ ] 填写信息并创建
- [ ] **预期**：群聊立即出现在左侧列表中，无需刷新

#### 2. 删除群聊测试（需要 UI 集成）
- [ ] 右键点击群聊，选择"删除"
- [ ] **预期**：群聊立即从列表中消失

#### 3. Docker 开关测试（需要 UI 集成）
- [ ] 在右侧成员列表中，点击成员的 Docker 图标切换
- [ ] **预期**：图标状态立即改变

#### 4. WebSocket 推送测试 ✅
- [ ] 等待 Agent 回复消息
- [ ] **预期**：收到 WebSocket refresh 信号，消息列表更新显示 Agent 回复

---

## 架构原则确认

### ✅ 职责划分正确

**后端 broadcast 边界**：
- ✅ **应该 broadcast**：Agent 产生内容（前端无法预知）
  - `speak_in_group_chat()` - Agent 发言
  - `finish_agent_call()` - Agent 完成任务
  
- ❌ **不应该 broadcast**：前端主动操作（前端已知结果）
  - `create_group_chat()` - 已移除
  - `send_message()` - 已移除
  - `pin_message()` - 已移除
  - `unpin_message()` - 已移除
  - `add_group_chat_members()` - 已移除

**前端状态管理原则**：
- ✅ 乐观更新：前端操作后立即更新本地状态
- ✅ API 响应驱动：根据 API 返回结果调整状态
- ✅ WebSocket 仅用于后端推送：监听 Agent 产生的内容

---

## 提交信息

### 第一次提交（已完成）

```
refactor: 重构前后端职责划分，移除不合理的 broadcast 调用

后端改动：
- 移除 group_chat_service.py 中 5 处前端操作相关的 broadcast_group_chat_refresh 调用
- 移除 broadcast_group_chat_refresh 导入
- 保留 MCP 工具中的 broadcast (speak_in_group_chat、finish_agent_call)

前端改动：
- 修复创建群聊后列表不刷新问题
- useCreateGroupChat 在创建成功后调用 refreshSessions()

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

### 第二次提交（当前待提交）

```
feat: 添加删除群聊和 Docker 开关状态管理

前端改动：
- 新增 useDeleteGroupChat hook，提供删除群聊功能和乐观更新
- useMembers 添加 toggleDockerMode 方法，支持 Docker 开关切换
- useMembers 添加 refresh 方法，支持手动刷新成员列表
- 所有操作均采用乐观更新策略，失败时自动回滚

使用示例见 IMPLEMENTATION_SUMMARY.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

---

## 后续建议

1. **UI 集成**：需要在 RightSidebar 和 SessionList 组件中集成新功能
2. **决策记录**：建议创建 `docs/design-decisions/0011-frontend-state-management-responsibility.md`
3. **测试覆盖**：为新增的 hooks 编写单元测试
4. **用户文档**：更新用户使用指南，说明 Docker 开关功能
