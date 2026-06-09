# 单聊双位置显示功能

## 任务背景

当前单聊只能显示在右侧栏，用户需要能够在右侧栏（快速对话）和中间主界面（深度对话）之间灵活切换。

## 任务目标

实现单聊可以在右侧栏和中间主界面之间切换显示，默认显示在右侧栏，通过切换按钮可以移到中间主界面获得更大空间。

## 检查清单

### Phase 1：状态管理基础
- [x] sessionStore 添加 `activeSessionType: 'group_chat' | 'single_chat' | null` 字段 — commit c3bd195
- [x] sessionStore 的 `selectSession` 方法支持传入 `type` 参数 — commit c3bd195
- [x] singleChatStore 添加 `displayLocation: 'sidebar' | 'main'` 字段 — commit 8e76f3b
- [x] singleChatStore 移除 `isPanelOpen` 字段（改用 displayLocation 判断） — commit 0244ac7
- [x] singleChatStore 添加 `toggleLocation()` 和 `setLocation()` 方法 — commit 8e76f3b
- [x] SessionList 点击单聊时调用 `selectSession(id, 'single_chat')` 和 `setLocation('sidebar')` — commit b73f25e
- [x] SessionList 点击群聊时调用 `selectSession(id, 'group_chat')` 和 `setLocation('sidebar')`（单聊自动回到默认位置） — commit b73f25e

### Phase 2：消息加载
- [x] 创建 `adaptSingleChatMessages` 适配器，将 `SingleChatMessageApiItem[]` 转为 `MessageApiItem[]` — commit d45c182, 07e9781, 01b7c23
- [x] useChatMessages 读取 `activeSessionType` 状态 — commit 13fb3e6
- [x] useChatMessages 根据 `activeSessionType` 调用不同 API（`getSingleChatMessages` vs `getMessages`） — commit 13fb3e6
- [x] useChatMessages 单聊消息通过适配器统一格式 — commit 13fb3e6
- [x] 单聊消息发送支持 SSE 流式（区别于群聊 WebSocket） — 已有实现（无需修改）

### Phase 3：UI 切换
- [x] ChatArea 读取 `activeSessionType` 和 `displayLocation` 状态 — commit 2d36d2f
- [x] ChatArea 当 `activeSessionType === 'single_chat' && displayLocation === 'main'` 时显示单聊 — commit 2d36d2f
- [x] ChatArea 当显示单聊时，复用现有消息列表组件（通过 useChatMessages） — commit 2d36d2f
- [x] SingleChatPanel 标题栏添加位置切换按钮 — commit 1395880
- [x] 切换按钮根据 `displayLocation` 显示不同文案和图标（"📍 移到主界面" / "📌 返回右侧"） — commit 1395880
- [x] RightSidebar 的 single-chat Tab 检测 `displayLocation === 'main'` 时显示占位提示 — commit a957472
- [x] 占位提示包含"返回右侧"按钮，点击调用 `setLocation('sidebar')` — commit a957472

### Phase 4：边界处理
- [x] 删除单聊时，如果是当前激活的单聊，清空 sessionStore 和 singleChatStore 状态 — 已有实现（无需修改）
- [x] 单聊消息加载失败时，显示错误提示并清空消息列表 — commit 13fb3e6
- [x] 单聊没有历史消息时，显示空状态提示 — 已有实现（无需修改）
- [x] 单聊和群聊切换时，消息正确加载，不会混乱 — commit 13fb3e6

### 测试验证
- [x] 点击左侧单聊 → 右侧显示单聊面板 — 实现完成，需手动验证
- [x] 点击"移到主界面" → 中间显示单聊，右侧显示提示 — 实现完成，需手动验证
- [x] 点击"返回右侧" → 单聊回到右侧 — 实现完成，需手动验证
- [x] 单聊在中间时，点击群聊 → 单聊自动回到右侧，中间显示群聊 — 实现完成，需手动验证
- [x] 单聊消息正常加载和显示 — 实现完成，需手动验证
- [x] 单聊消息发送（SSE 流式）正常工作 — 已有实现，需手动验证
- [x] 删除当前激活的单聊 → 状态正确清理 — 已有实现，需手动验证
