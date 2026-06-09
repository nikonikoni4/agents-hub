# Session 列表重构：增加 Tab 分区

## 任务背景

当前左侧栏的 session 列表将群聊和单聊混合显示，导致以下问题：
1. 点击单聊时错误调用群聊 API（404 错误）
2. 单聊和群聊的状态管理混乱，出现显示位置错误
3. 用户难以区分群聊和单聊

重构目标：通过增加 Tab 导航，将群聊和单聊列表完全分离，避免混合显示带来的各种 bug。

## 任务目标

在左侧栏增加 Tab 导航，将群聊和单聊列表分区显示，点击对应 Tab 只显示对应类型的 session，同时简化 UI（移除头像，增加类型标签）。

## 相关代码架构分析

### 当前架构问题

1. **Session Store 混合管理**：`sessionStore` 同时管理群聊（projectGroups）和单聊数据，导致状态混乱
2. **SingleChat Store 状态重叠**：`singleChatStore` 与 `sessionStore` 有状态重叠（activeSessionId vs activeSingleChatId）
3. **数据获取混合**：`useSessionList` hook 同时获取群聊和单聊数据，混合存储
4. **UI 组件混合处理**：`SessionItem` 组件同时处理群聊和单聊的点击逻辑
5. **显示位置复杂**：`displayLocation` 状态导致单聊显示位置判断复杂

### 需要重构的文件清单

#### 1. 核心状态管理（最重要）

**Session Store** (`features/session/store/sessionStore.ts`)
- 当前职责：存储 projectGroups、activeSessionId、activeSessionType
- 重构方向：
  - 只管理群聊相关状态（projectGroups）
  - 移除 activeSessionType（或简化为只处理群聊）
  - 保留 selectSession、updateSession 等操作

**SingleChat Store** (`features/single-chat/store/singleChatStore.ts`)
- 当前职责：存储 singleChats、activeSingleChatId、displayLocation
- 重构方向：
  - 只管理单聊相关状态（singleChats）
  - 简化 displayLocation 逻辑（或移除，因为单聊只在右侧栏显示）
  - 保留 openSingleChat、closeSingleChat 等操作

#### 2. 数据获取层

**useSessionList Hook** (`features/session/hooks/useSessionList.ts`)
- 当前职责：同时获取群聊和单聊数据，混合存储到 projectGroups
- 重构方向：
  - 拆分为两个独立的 hook：
    - `useGroupChatList`：只获取群聊数据，存储到 sessionStore.projectGroups
    - `useSingleChatList`：只获取单聊数据，存储到 singleChatStore.singleChats
  - 或者在现有 hook 中分离数据流，根据 Tab 选择性获取

#### 3. UI 组件层

**SessionList 组件** (`features/session/components/SessionList.tsx`)
- 当前职责：渲染 session 列表（群聊和单聊混合）
- 重构方向：
  - 增加 Tab 导航栏（"群聊"、"单聊"）
  - 根据选中的 Tab 渲染对应类型的列表
  - 群聊列表按项目分组显示
  - 单聊列表按单聊文件夹分组显示

**SessionItem 组件** (`features/session/components/SessionItem.tsx`)
- 当前职责：显示单个 session 信息，处理点击，显示头像
- 重构方向：
  - 移除头像显示（CompositeAvatar、AvatarImage）
  - 增加类型标签（"群聊" 或 "单聊"）
  - 简化点击逻辑（根据类型调用不同的 store 操作）
  - 保留：标题、预览、时间、未读标记

**ProjectGroup 组件** (`features/session/components/ProjectGroup.tsx`)
- 当前职责：按项目分组显示 session 列表
- 重构方向：保持不变，继续用于群聊列表的分组显示

#### 4. 布局层

**LeftSidebar** (`layouts/LeftSidebar/LeftSidebar.tsx`)
- 当前职责：包含 SessionList，传递 onSelectSingleChat 回调
- 重构方向：
  - 简化回调逻辑（因为 Tab 分离后，点击逻辑更清晰）
  - 可能移除 onSelectSingleChat 回调（由 SessionList 内部处理）

**ChatArea** (`layouts/ChatArea/ChatArea.tsx`)
- 当前职责：根据 activeSessionType 和 displayLocation 切换显示群聊/单聊
- 重构方向：
  - 简化显示逻辑：只显示群聊内容
  - 移除单聊相关的条件判断（因为单聊只在右侧栏显示）
  - 移除 showingSingleChat 判断和相关代码

**RightSidebar** (`layouts/RightSidebar/RightSidebar.tsx`)
- 当前职责：显示单聊面板（SingleChatPanel）、成员列表、置顶消息等
- 重构方向：
  - 保留单聊面板显示逻辑
  - 简化 displayLocation 判断（单聊始终在右侧栏）
  - 保留群聊相关的功能（成员列表、置顶消息等）

#### 5. Hooks 层

**useSessionActions** (`features/session/hooks/useSessionActions.ts`)
- 当前职责：处理 session 选择、切换等操作
- 重构方向：
  - 简化为只处理群聊 session 的操作
  - 移除单聊相关的逻辑

**useSingleChatMessages** (`features/single-chat/hooks/useSingleChatMessages.ts`)
- 当前职责：管理单聊消息的获取和发送
- 重构方向：保持不变，继续用于单聊面板

**useSingleChatMembers** (`features/single-chat/hooks/useSingleChatMembers.ts`)
- 当前职责：获取单聊关联的群聊成员信息
- 重构方向：保持不变，用于获取 Agent 头像

**useNavigationHandler** (`features/single-chat/hooks/useNavigationHandler.ts`)
- 当前职责：处理单聊中的导航操作
- 重构方向：保持不变

#### 6. 适配器层

**sessionAdapter** (`shared/adapters/sessionAdapter.ts`)
- 当前职责：适配 session 数据格式，聚合群聊和单聊
- 重构方向：
  - 拆分适配逻辑：分别适配群聊和单聊数据
  - 或者简化为只处理群聊数据（单聊数据由 singleChatStore 管理）

**singleChatMessageAdapter** (`shared/adapters/singleChatMessageAdapter.ts`)
- 当前职责：适配单聊消息格式
- 重构方向：保持不变

#### 7. 类型定义

**api-schemas.ts** (`shared/types/api-schemas.ts`)
- 当前职责：定义 API 响应类型
- 重构方向：
  - 确保 SingleChatApiResponse 和 GroupChatApiResponse 类型清晰分离
  - 可能需要增加 sessionType 字段用于区分

**SessionItem 类型** (`shared/adapters/sessionAdapter.ts`)
- 当前职责：定义 SessionItem 接口（包含 type 字段）
- 重构方向：
  - 考虑拆分为 GroupChatSessionItem 和 SingleChatSessionItem
  - 或者保留统一类型，但通过 type 字段区分

## 重构优先级建议

### 第一阶段：核心状态分离（最重要）
1. 重构 sessionStore：只管理群聊状态
2. 重构 singleChatStore：只管理单聊状态
3. 拆分 useSessionList：分别获取群聊和单聊数据

### 第二阶段：UI 组件重构
1. 重构 SessionList：增加 Tab 导航
2. 重构 SessionItem：移除头像，增加标签
3. 简化 LeftSidebar 回调逻辑

### 第三阶段：布局层简化
1. 简化 ChatArea：移除单聊显示逻辑
2. 简化 RightSidebar：移除 displayLocation 判断
3. 清理相关 hooks 和适配器

## 检查清单

### 1. Session 列表 Tab 导航

- [ ] 在 SessionList 组件顶部增加 Tab 导航栏，包含"群聊"和"单聊"两个 Tab 按钮
- [ ] 默认选中"群聊" Tab
- [ ] 点击"群聊" Tab 只显示群聊 session 列表
- [ ] 点击"单聊" Tab 只显示单聊 session 列表
- [ ] Tab 切换时更新激活状态，高亮当前选中的 Tab

### 2. Session 列表数据分离

- [ ] 从 sessionStore 获取 projectGroups 数据
- [ ] 从 singleChatStore 获取 singleChats 数据
- [ ] 根据当前选中的 Tab，过滤显示对应类型的 session 列表
- [ ] 群聊列表按项目分组显示（projectGroups 结构）
- [ ] 单聊列表按单聊文件夹分组显示

### 3. SessionItem UI 简化

- [ ] 移除 SessionItem 中的头像显示（CompositeAvatar 和 AvatarImage）
- [ ] 在 SessionItem 最前面增加类型标签（"群聊" 或 "单聊"）
- [ ] 保留 session 名称显示
- [ ] 保留上次浏览时间显示（formatRelativeTime）
- [ ] 保留未读标记显示（isUnread）
- [ ] 保留预览内容显示（preview）

### 4. SessionItem 点击行为

- [ ] 点击群聊 session 时：
  - 调用 selectSession(sessionId, 'group_chat')
  - 调用 handleSelectSession(sessionId, 'group_chat')
  - 设置 activeSessionType 为 'group_chat'
- [ ] 点击单聊 session 时：
  - 调用 openSingleChat(sessionId) 设置 activeSingleChatId 和 displayLocation
  - 调用 selectSession(sessionId, 'single_chat')
  - 标记单聊为已读（storage.setLastView + updateSession）
  - 通知父组件（onSelectSingleChat 回调）

### 5. 状态管理

- [ ] sessionStore 维护 projectGroups、activeSessionId、activeSessionType
- [ ] singleChatStore 维护 singleChats、activeSingleChatId、displayLocation
- [ ] Tab 选中状态使用组件内部 useState 管理（sessionListTab: 'group' | 'single'）
- [ ] 切换 Tab 时不影响当前激活的 session

### 6. 数据获取

- [ ] useSessionList hook 获取群聊列表（调用 listGroupChats API）
- [ ] useSessionList hook 获取单聊列表（调用 listSingleChats API）
- [ ] 将获取的数据适配为统一的 SessionItem 类型
- [ ] 适配时保留 session 的所有必要字段：id、title、type、preview、lastUpdateAt、lastViewAt、isUnread、memberAvatars、agentName、projectPath

### 7. 项目分组显示

- [ ] 群聊列表按 projectPath 分组显示（与现有逻辑一致）
- [ ] 单聊列表按单聊文件夹分组显示（或扁平显示，视需求而定）
- [ ] 每个分组显示项目名称标题

### 8. 其他 UI 保持不变

- [ ] SessionItem 的 hover 和 active 状态样式保持不变
- [ ] SessionItem 的删除功能保持不变（仅群聊显示删除按钮）
- [ ] SessionItem 的右键菜单保持不变
- [ ] 左侧栏的整体布局和样式保持不变

### 9. 错误处理

- [ ] 获取群聊列表失败时显示错误提示
- [ ] 获取单聊列表失败时显示错误提示
- [ ] 点击 session 时的错误处理（删除失败等）

## 关键约束

1. **不混合显示**：群聊和单聊必须通过 Tab 完全分离，不能混合在同一个列表中
2. **UI 简化**：移除头像，增加类型标签，其他 UI 保持不变
3. **状态隔离**：群聊和单聊的状态管理必须隔离，避免 API 调用混乱
4. **按需加载**：只加载当前 Tab 对应的数据，不加载另一种类型的数据
