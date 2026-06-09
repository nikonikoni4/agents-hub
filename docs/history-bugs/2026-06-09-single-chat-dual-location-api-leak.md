# 单聊双位置显示：API 调用未完全区分单聊/群聊

- 发现时间：2026-06-09
- 影响范围：点击单聊时，控制台报错 "GroupChat 'xxx' 不存在"
- 状态：未修复（已缓解部分问题，仍需后续处理）

## 问题描述

实现单聊双位置显示功能后，点击左侧列表中的单聊项时，控制台输出错误：

```
Failed to load pinned messages: ApiError: GroupChat '71117145-8cda-4e4b-98c2-5203d5808bc5' 不存在
    at ApiError.fromResponse (client.ts:54:14)
    at client.ts:118:31
    at async usePinnedMessages.ts:36:20
```

此外，点击单聊后右侧栏会从群聊 tab 切换到单聊 tab，但单聊消息仍然显示在中间主界面，而不是右侧栏。

## 已缓解的修复

### 修复 1：ChatArea 的 usePinnedMessages 条件调用

`frontend/src/layouts/ChatArea/ChatArea.tsx`

```typescript
// 修复前：无论单聊还是群聊都调用 usePinnedMessages
const { pin, unpin, isPinned } = usePinnedMessages(activeSessionId);

// 修复后：只有群聊才调用
const { pin, unpin, isPinned } = usePinnedMessages(
  activeSessionType === 'group_chat' ? activeSessionId : null
);
```

### 修复 2：SessionItem 状态更新顺序

`frontend/src/features/session/components/SessionItem.tsx`

```typescript
// 修复前：先 selectSession 再 setLocation（存在状态竞争）
selectSession(session.id, 'single_chat');
setActiveSingleChat(session.id);
setLocation('sidebar');

// 修复后：先 setLocation 再 selectSession
setLocation('sidebar');
setActiveSingleChat(session.id);
selectSession(session.id, 'single_chat');
```

## 残留问题

修复后仍有以下问题未完全解决：

1. **控制台报错**：点击单聊时仍会输出 "群聊不存在" 错误，说明还有其他 hook 或组件在单聊时调用了群聊 API（如 `useMembers`, `useTasks`, `useAgentCalls` 等）

2. **显示位置错误**：点击单聊后，右侧栏切换到 single-chat tab，但单聊消息仍显示在中间主界面而非右侧栏。可能原因：
   - `displayLocation` 状态更新时序问题
   - ChatArea 的条件渲染逻辑（`showingSingleChat = activeSessionType === 'single_chat' && displayLocation === 'main'`）在某些场景下判断不准确
   - 多个 store 的状态更新存在竞争

## 根因分析

1. **架构问题**：`ChatArea` 组件同时服务于群聊和单聊，但内部调用了多个群聊专属的 hook（`usePinnedMessages`, `useMembers`, `useTasks` 等），这些 hook 没有根据 `activeSessionType` 做区分

2. **状态管理复杂度**：需要同时管理 `SessionStore.activeSessionType` 和 `SingleChatStore.displayLocation` 两个状态，它们之间的协调逻辑分散在多个组件中，容易出现时序问题

3. **测试覆盖不足**：没有端到端测试覆盖单聊切换场景，仅靠单元测试无法发现这类多组件状态协调问题

## 修复方向（后续）

1. **彻底隔离 API 调用**：在 ChatArea 中，当 `activeSessionType === 'single_chat'` 时，禁用所有群聊专属 hook 的 API 调用
2. **简化状态管理**：考虑合并或统一管理 `activeSessionType` 和 `displayLocation`，减少状态竞争的可能性
3. **添加集成测试**：编写覆盖单聊切换场景的端到端测试
