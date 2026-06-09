# Session 列表 Tab 分区重构设计

## 背景

当前左侧栏的 session 列表将群聊和单聊混合显示，导致：
1. 点击单聊时错误调用群聊 API（404 错误）
2. 单聊和群聊的状态管理混乱，显示位置错误
3. 用户难以区分群聊和单聊

根本原因：群聊和单聊共享状态、混合获取数据、UI 组件耦合。

## 设计目标

通过 Tab 导航将群聊和单聊列表完全分离，实现两个 feature 的彻底解耦。

## 核心原则

- **完全解耦**：群聊和单聊是两个独立 feature，各自有 store、hooks、components，互不引用
- **组件替换而非数据替换**：单聊"移到主界面"时，是 SingleChatPanel 组件整体替换 ChatArea，不是把单聊数据塞进 ChatArea
- **按需加载**：只加载当前 Tab 对应的数据

## 详细设计

### 1. 状态管理（Store 层）

#### sessionStore — 只管群聊

状态：
- `projectGroups: ProjectGroup[]` — 群聊项目分组
- `activeSessionId: string | null` — 当前激活的群聊 ID
- `lastSelectedAt: number` — 最近选择时间戳

操作：
- `setProjectGroups(groups)` — 设置项目分组
- `selectGroupChat(id)` — 选择群聊，设置 activeSessionId
- `updateSession(id, updates)` — 更新某个 session 的数据
- `clearActive()` — 清空激活状态（单聊被激活时调用）

**移除**：`activeSessionType` 字段（不再需要区分类型）

#### singleChatStore — 只管单聊

状态：
- `singleChats: SingleChatApiResponse[]` — 单聊列表
- `activeSingleChatId: string | null` — 当前激活的单聊 ID
- `displayLocation: 'sidebar' | 'main'` — 单聊显示位置

操作：
- `setSingleChats(chats)` — 设置单聊列表
- `openSingleChat(id)` — 打开单聊，设置 activeSingleChatId，重置 displayLocation 为 sidebar
- `closeSingleChat()` — 关闭单聊
- `toggleLocation()` — 切换显示位置（sidebar ↔ main）
- `clearActive()` — 清空激活状态（群聊被激活时调用）

**关键**：两个 store 之间零引用。

### 2. 数据获取（Hook 层）

#### useGroupChatList — 群聊数据获取

职责：
- 调用 `listGroupChatInfos()` 获取群聊列表
- 调用 `storage.getLastViewRecords()` 获取本地 lastView 记录
- 调用 `groupSessionsByProject()` 按项目分组
- 加载成员头像
- 结果写入 `sessionStore.projectGroups`
- 监听 WebSocket refresh 信号自动刷新

#### useSingleChatList — 单聊数据获取

职责：
- 调用 `listSingleChats()` 获取单聊列表
- 按 cwd 分组（复用 `extractProjectName` 逻辑）
- 加载 agent 头像
- 结果写入 `singleChatStore.singleChats`
- 监听 WebSocket refresh 信号自动刷新

**关键**：两个 hook 完全独立，各自调用 API，写入各自 store。

### 3. UI 组件层

#### SessionList — 左侧栏 session 列表

- 顶部 Tab 导航："群聊" | "单聊"，默认"群聊"
- Tab 状态：组件内 `useState`，不持久化，每次刷新重置为群聊
- 群聊 Tab：调用 `useGroupChatList`，按项目分组渲染
- 单聊 Tab：调用 `useSingleChatList`，按 cwd 分组渲染
- 切换 Tab 时不影响当前激活的 session

#### SessionItem — 单个 session 项

移除：
- 头像（CompositeAvatar、AvatarImage）

增加：
- 类型标签（"群聊" / "单聊"），显示在最前面

保留：
- session 名称
- 预览内容
- 上次浏览时间（formatRelativeTime）
- 未读标记（isUnread）

点击逻辑：
- 群聊 → `sessionStore.selectGroupChat(id)` + `singleChatStore.clearActive()`
- 单聊 → `singleChatStore.openSingleChat(id)` + `sessionStore.clearActive()`

视图切换：
- SessionItem 不需要知道 LeftSidebar 的存在
- LeftSidebar 订阅 `sessionStore.activeSessionId` 和 `singleChatStore.activeSingleChatId`
- 检测到任一变化时，自动切换 viewMode 为 'chat'

#### ProjectGroup — 项目分组

保持不变，群聊和单聊列表都复用此组件。

### 4. 布局层

#### MainLayout — 决定主界面渲染什么

```
if (displayLocation === 'main' && activeSingleChatId) {
  渲染 <SingleChatPanel />  // 组件替换
} else {
  渲染 <ChatArea />          // 群聊主界面
}
```

#### RightSidebar — 决定右侧栏渲染什么

```
if (activeSingleChatId && displayLocation === 'sidebar') {
  渲染 <SingleChatPanel />  // 单聊面板
} else {
  渲染 群聊侧边栏内容（成员列表、置顶消息等）
}
```

#### SingleChatPanel — 自包含组件

- 自己管理消息获取、发送、滚动
- 自带"移到主界面" / "返回右侧" 按钮
- 不管渲染在哪里，内部逻辑完全一样

#### ChatArea — 群聊专用

- 不再有任何单聊相关的代码
- 只负责群聊消息显示和发送

### 5. 边界情况

#### 激活状态隔离

- 群聊激活：`sessionStore.activeSessionId` 有值，`singleChatStore.activeSingleChatId` 为 null
- 单聊激活：`singleChatStore.activeSingleChatId` 有值，`sessionStore.activeSessionId` 为 null
- 点击群聊时，调用 `singleChatStore.clearActive()`
- 点击单聊时，调用 `sessionStore.clearActive()`

#### Tab 切换与激活 session

- 切换 Tab 不改变当前激活的 session
- 比如：正在看群聊 A，切到单聊 Tab 浏览列表，再切回群聊 Tab，群聊 A 仍然激活

#### 错误处理

- 获取群聊列表失败：显示错误提示，不影响单聊 Tab
- 获取单聊列表失败：显示错误提示，不影响群聊 Tab
- 发送消息失败：在各自面板内处理，互不影响

### 6. 需要创建/修改的文件

#### 新建文件（features/session/）

- `features/session/store/sessionStore.ts` — 群聊 store
- `features/session/hooks/useGroupChatList.ts` — 群聊数据获取
- `features/session/hooks/useSessionActions.ts` — 群聊操作（选择、更新）
- `features/session/hooks/useCreateGroupChat.ts` — 创建群聊
- `features/session/hooks/useDeleteGroupChat.ts` — 删除群聊
- `features/session/components/SessionList.tsx` — session 列表（含 Tab）
- `features/session/components/SessionItem.tsx` — session 项
- `features/session/components/ProjectGroup.tsx` — 项目分组
- `features/session/components/CreateGroupChatDialog.tsx` — 创建对话弹窗
- `features/session/index.ts` — barrel export

#### 新建文件（features/single-chat/）

- `features/single-chat/store/singleChatStore.ts` — 单聊 store
- `features/single-chat/hooks/useSingleChatList.ts` — 单聊数据获取
- `features/single-chat/hooks/useSingleChatMessages.ts` — 单聊消息管理
- `features/single-chat/hooks/useSingleChatMembers.ts` — 单聊成员
- `features/single-chat/hooks/useNavigationHandler.ts` — 导航处理
- `features/single-chat/hooks/useCreateSingleChat.ts` — 创建单聊
- `features/single-chat/components/SingleChatPanel.tsx` — 单聊面板
- `features/single-chat/components/ToolCallCard.tsx` — 工具调用卡片
- `features/single-chat/index.ts` — barrel export

#### 修改文件

- `shared/adapters/sessionAdapter.ts` — 拆分群聊/单聊适配逻辑
- `layouts/LeftSidebar/LeftSidebar.tsx` — 移除 onSelectSingleChat 回调，改为订阅 store 变化自动切换视图
- `layouts/MainLayout/MainLayout.tsx` — 根据 displayLocation 切换渲染
- `layouts/RightSidebar/RightSidebar.tsx` — 简化 displayLocation 判断
- `layouts/ChatArea/ChatArea.tsx` — 移除单聊相关代码

### 7. 重构优先级

#### 第一阶段：核心状态分离
1. 创建 sessionStore（只管群聊）
2. 创建 singleChatStore（只管单聊）
3. 创建 useGroupChatList 和 useSingleChatList

#### 第二阶段：UI 组件重构
1. 创建 SessionList（含 Tab 导航）
2. 创建 SessionItem（移除头像，增加标签）
3. 创建 SingleChatPanel（自包含组件）

#### 第三阶段：布局层简化
1. 修改 MainLayout（组件替换逻辑）
2. 修改 RightSidebar（简化判断）
3. 修改 ChatArea（移除单聊代码）
4. 简化 LeftSidebar 回调
