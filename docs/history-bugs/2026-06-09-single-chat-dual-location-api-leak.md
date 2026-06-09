# 单聊双位置显示：API 调用未完全区分单聊/群聊

- 发现时间：2026-06-09
- 影响范围：点击单聊时，控制台报错 "GroupChat 'xxx' 不存在"
- 状态：已修复（2026-06-09，通过 Tab 分区重构彻底解决）

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

~~修复后仍有以下问题未完全解决：~~ 已通过重构彻底解决。

## 根因分析

1. **架构问题**：`ChatArea` 组件同时服务于群聊和单聊，但内部调用了多个群聊专属的 hook（`usePinnedMessages`, `useMembers`, `useTasks` 等），这些 hook 没有根据 `activeSessionType` 做区分

2. **状态管理复杂度**：需要同时管理 `SessionStore.activeSessionType` 和 `SingleChatStore.displayLocation` 两个状态，它们之间的协调逻辑分散在多个组件中，容易出现时序问题

3. **测试覆盖不足**：没有端到端测试覆盖单聊切换场景，仅靠单元测试无法发现这类多组件状态协调问题

## 最终修复（2026-06-09 Tab 分区重构）

**修复思路**：不再试图在同一个组件中区分单聊/群聊，而是彻底分离为两个独立 feature。

**具体措施**：

1. **Store 解耦**：`sessionStore` 只管群聊（移除 `activeSessionType`），`singleChatStore` 只管单聊，两个 store 零耦合

2. **组件分离**：`ChatArea` 只负责群聊，移除所有单聊相关代码；`SingleChatPanel` 作为自包含组件，不管渲染在右侧栏还是主界面，内部逻辑不变

3. **布局层切换**：`MainLayout` 根据 `displayLocation` 状态决定渲染 `ChatArea` 还是 `SingleChatPanel`（组件替换，不是数据替换）

4. **Tab 导航**：`SessionList` 增加"群聊"/"单聊" Tab，两个列表完全独立，各自调用各自的 API

5. **点击行为**：点击单聊不再改变主界面状态（移除 `sessionStore.clearActive()`），主界面保持显示当前群聊

**效果**：
- 点击单聊不再触发群聊 API 调用（根因消除）
- 单聊始终在右侧栏显示，可通过"移到主界面"按钮切换到主界面
- 群聊和单聊的状态完全隔离，不存在竞争条件
