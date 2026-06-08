# 单聊功能增强：显示位置切换 + 历史消息问题

**时间**：2026-06-08
**分支**：test_branch
**状态**：🚧 进行中

---

## 一、任务目标

增强单聊功能：1) 支持单聊在右侧栏和主界面之间切换显示；2) 排查并解决单聊历史消息为空的问题。

---

## 二、已完成的工作

### 单聊聚合显示到左侧栏
- [x] `SessionItem` 接口增加 `type`（group_chat/single_chat）、`agentName`、`platform` 字段
- [x] `groupSessionsByProject` 函数支持单聊按 cwd 分组合并到对应项目
- [x] `useSessionList` hook 并行加载群聊和单聊，为单聊设置 agent 头像
- [x] `SessionItem` 组件根据 `type` 区分显示（单聊头像 + "单聊"标签）
- [x] 点击单聊调用 `singleChatStore.openSingleChat` 打开单聊面板
- [x] 新增 3 个单聊聚合测试用例，全部 112 个测试通过

### 群聊显示增强（已完成并提交）
- [x] 后端 AgentMemberInfo 增加 status 字段（idle/busy）
- [x] RightSidebar 成员列表显示 cwd 路径和忙碌状态
- [x] ChatArea 顶部显示群聊项目路径
- [x] SessionItem 时间显示改为使用 last_view_at
- [x] 已提交：commit `ce8fc9c`

---

## 三、阻塞问题

### 问题 1：单聊历史消息为空

**现象**：选择单聊后，控制台显示返回的 messages 为空数组。
**调用链**：
```
useSingleChatMessages (hook)
  → getSingleChatMessages(id) (API)
    → GET /single-chats/{id}/messages (后端路由)
      → single_chat_service.get_messages()
        → if not index.session_path: return []  ← 关键行
```
**根本原因**：新创建的单聊（`new`/`fork` 类型）在用户发送第一条消息前，`session_path` 为 `None`，后端直接返回空列表。这是**设计上的预期行为**，因为此时还没有与 agent 建立会话，没有 session 文件可读。

**session_path 设置时机**：用户发送第一条消息后，`send_message_stream` 流结束时调用 `_resolve_session_path` 设置 `session_path`。

**如果发送消息后仍为空**：检查 `_resolve_session_path`（`single_chat_service.py:88-113`）中：
- `role_config.work_root` 是否配置
- session JSONL 文件是否存在于 `{work_root}/projects/`（Claude）或 `{work_root}/sessions/`（Codex）目录

**相关文件**：
| 文件 | 说明 |
|------|------|
| `agents_hub/api/services/single_chat_service.py:357` | `if not index.session_path: return []` 关键判断 |
| `agents_hub/api/services/single_chat_service.py:88-113` | `_resolve_session_path` 文件搜索逻辑 |
| `agents_hub/api/services/single_chat_service.py:279-336` | `send_message_stream` 中设置 session_path 的逻辑 |
| `frontend/src/features/single-chat/hooks/useSingleChatMessages.ts` | 前端消息加载 hook |
| `frontend/src/core/api/singleChatApi.ts:124` | `getSingleChatMessages` API 函数 |

---

## 四、未完成的任务

### 优先级 1：单聊显示位置切换
- [ ] `singleChatStore` 增加 `displayMode: 'sidebar' | 'main'` 状态和 `toggleDisplayMode` action
- [ ] `SingleChatPanel` 头部增加切换按钮（侧栏/主界面图标）
- [ ] `MainLayout` 根据 `displayMode` 决定渲染位置：
  - `sidebar`：保持现有逻辑，SingleChatPanel 在 RightSidebar 中
  - `main`：在 ChatArea 位置渲染 SingleChatPanel
- [ ] 主界面版本的 SingleChatPanel 适配更宽布局（当前设计是窄侧栏宽度）
- [ ] 切换时保持消息状态不丢失

### 优先级 2：单聊历史消息问题确认
- [ ] 确认用户是否已发送过消息（发送过才会有 session_path）
- [ ] 如果发送后仍为空，检查 `work_root` 配置和 session 文件是否存在
- [ ] 可在 `single_chat_service.py:357` 添加日志记录 `session_path` 值

---

## 五、下一步行动

1. **实现单聊显示位置切换**：在 singleChatStore 增加 displayMode，修改 MainLayout 和 SingleChatPanel
2. **确认历史消息问题**：让用户发送一条消息后再次检查是否为空
3. **如果消息仍为空**：检查后端 `work_root` 配置和 session 文件路径

---

## 六、相关文件

| 文件 | 修改状态 | 说明 |
|------|----------|------|
| `frontend/src/shared/adapters/sessionAdapter.ts` | ✅ 已修改 | SessionItem 增加 type/agentName/platform，groupSessionsByProject 支持单聊 |
| `frontend/src/shared/adapters/sessionAdapter.test.ts` | ✅ 已修改 | 新增 3 个单聊聚合测试 |
| `frontend/src/features/session/hooks/useSessionList.ts` | ✅ 已修改 | 并行加载群聊和单聊，设置单聊头像 |
| `frontend/src/features/session/components/SessionItem.tsx` | ✅ 已修改 | 根据 type 区分显示和点击行为 |
| `frontend/src/features/session/components/SessionItem.css` | ✅ 已修改 | 新增单聊头像和标签样式 |
| `frontend/src/features/session/components/SessionList.tsx` | ✅ 已修改 | 接受 onSelectSingleChat 回调 |
| `frontend/src/features/session/components/ProjectGroup.tsx` | ✅ 已修改 | 传递 onSelectSingleChat 回调 |
| `frontend/src/layouts/LeftSidebar/LeftSidebar.tsx` | ✅ 已修改 | 提供 handleSelectSingleChat 回调 |
| `frontend/src/features/single-chat/store/singleChatStore.ts` | 未修改 | 需增加 displayMode 状态 |
| `frontend/src/features/single-chat/components/SingleChatPanel.tsx` | 未修改 | 需增加切换按钮 |
| `frontend/src/layouts/MainLayout/MainLayout.tsx` | 未修改 | 需根据 displayMode 条件渲染 |
| `frontend/src/layouts/RightSidebar/RightSidebar.tsx` | 未修改 | 可能需要调整 SingleChatPanel 渲染逻辑 |
| `agents_hub/api/services/single_chat_service.py` | 未修改 | session_path 解析逻辑，可能需要调试 |

---

## 七、决策记录

### 决策 1：单聊聚合显示方案
- **背景**：左侧栏只显示群聊，需要同时显示单聊
- **决策**：采用混合显示方案（单聊和群聊在同一个列表中，按 lastUpdateAt 统一排序）
- **原因**：符合 feature 隔离原则，不增加新的分级层级，通过视觉样式区分类型

### 决策 2：单聊点击行为
- **背景**：点击单聊后应该在哪里显示
- **决策**：当前点击单聊调用 `singleChatStore.openSingleChat`，在右侧栏的 SingleChatPanel 中显示
- **原因**：保持与现有单聊功能的一致性，后续可通过 displayMode 切换到主界面

---

## 八、注意事项

1. **Feature 隔离**：session feature 不能直接 import single-chat feature 的 store。单聊点击回调通过 props 从 LeftSidebar 传递到 SessionItem。
2. **头像加载**：单聊的 agent 头像通过 `buildRoleAvatarMap` 在 `useSessionList` 中加载，存入 `memberAvatars[0]`。
3. **session_path 为 None 是预期行为**：新创建的单聊在发送第一条消息前没有历史记录，这不是 bug。
4. **布局适配**：SingleChatPanel 当前设计为窄侧栏宽度，切换到主界面时需要适配更宽的布局。
5. **未提交的修改**：单聊聚合显示的代码修改尚未提交（上一次提交 `ce8fc9c` 只包含群聊显示增强）。

---

## 九、参考文档

- `docs/specs/2026-06-08-single-chat.md` — 单聊通道模块规格
- `docs/specs/2026-06-06-frontend-features.md` — 前端功能层规格
- `docs/specs/2026-06-06-frontend-core.md` — 前端核心层规格
- `frontend/src/features/single-chat/` — 单聊 feature 目录
- `frontend/src/features/session/` — session feature 目录
