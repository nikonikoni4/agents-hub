# Frontend CLAUDE.md

## 架构约束（全局）

1. **模块隔离**：features 之间禁止直接依赖，必须通过 core 或 shared 通信
2. **单向依赖**：`components → hooks → store → core`，禁止反向依赖
3. **职责分离**：组件禁止包含业务逻辑，必须通过 hooks 调用

---

## 目录结构

```
frontend/src/
├── core/        # 业务无关的基础能力（WebSocket、API、Storage）
├── features/    # 按业务领域划分（chat、session、preview、diff、tasks）
├── shared/      # 跨 feature 复用（components、hooks、utils、types）
├── layouts/     # 页面级布局
└── App.tsx
```

**局部规则**：
- `core/` 规则 → 查看 [`src/core/CLAUDE.md`](src/core/CLAUDE.md)
- `features/` 规则 → 查看 [`src/features/CLAUDE.md`](src/features/CLAUDE.md)
- `shared/` 规则 → 查看 [`src/shared/CLAUDE.md`](src/shared/CLAUDE.md)

---

## 代码放置决策流程

```
写代码前问自己：
1. 是否包含业务逻辑？
   → 是：放 features/（查看 features/CLAUDE.md）
   → 否：继续判断

2. 是否多个 feature 复用？
   → 是：放 shared/（查看 shared/CLAUDE.md）
   → 否：放当前 feature 内

3. 是否与后端通信相关？
   → 是：放 core/（查看 core/CLAUDE.md）
   → 否：放 shared/
```

---

## 全局禁止项

1. ❌ **禁止 feature 之间直接依赖**
   ```typescript
   // ❌ 错误
   import { SessionList } from '@/features/session/components/SessionList';
   ```

2. ❌ **禁止在 components 中直接调用 API**
   ```typescript
   // ❌ 错误
   function ChatWindow() {
     wsManager.send(...);  // 必须通过 hooks
   }
   ```

3. ❌ **禁止在 store 中包含副作用**
   ```typescript
   // ❌ 错误
   const useStore = create((set) => ({
     sendMessage: (text) => {
       wsManager.send(text);  // 副作用必须在 hooks 中
     },
   }));
   ```

4. ❌ **禁止反向依赖**
   ```typescript
   // ❌ 错误：core 依赖 features
   // core/websocket/WebSocketManager.ts
   import { useChatStore } from '@/features/chat/store';
   ```

---

## Feature 间通信规则

**允许的方式**：
1. 通过 core 层（WebSocket 消息分发）
2. 通过 store 订阅（一个 feature 订阅另一个 store）
3. 通过 props（在 layout 中传递数据）

**禁止**：
- ❌ feature A 直接 import feature B

---

## 状态管理约束

1. **每个 feature 独立 store**（禁止全局大 store）
2. **跨模块共享**：通过订阅其他 store，禁止提升到全局
3. **持久化**：使用 `persist` 中间件，只持久化必要数据
4. **临时 UI 状态**：放组件内 `useState`，禁止放 store

---

## 快速决策表

### 何时创建新 feature？

| 场景 | 决策 |
|------|------|
| 单聊功能 | 复用 `features/chat/`（通过 props 区分） |
| 消息搜索 | 创建 `features/search/`（独立功能） |
| 预览功能 | 创建 `features/preview/`（独立功能） |

### 组件放哪里？

| 场景 | 决策 |
|------|------|
| `ChatMessageItem` | `features/chat/components/`（只在聊天用） |
| `Button` | `shared/components/`（多处复用） |

---

## 测试文件放置规则

测试文件**必须共置**在源码旁边，禁止集中放在独立的 `tests/` 目录。

```
features/skills/
  SkillCard.tsx
  SkillCard.test.tsx       ← 紧挨源码
  useSkillList.ts
  useSkillList.test.ts

core/api/
  roleApi.ts
  roleApi.test.ts

tests/
  setup.ts                 ← 只放全局 setup 和跨模块集成测试
```

**禁止**：
- ❌ 把单元测试放在 `frontend/tests/` 或 `frontend/src/tests/`
- ❌ 把单元测试放在 `__tests__/` 子目录（Jest 风格，本项目不用）
- ❌ 用 `test-xxx.ts` 命名（必须用 `xxx.test.ts`）

**命名规范**：
- `xxx.test.ts` / `xxx.test.tsx`

| 测试类型 | 放哪里 |
|---------|--------|
| 组件测试 | 与组件同目录：`SkillCard.test.tsx` |
| hook 测试 | 与 hook 同目录：`useSkillList.test.ts` |
| API/service 测试 | 与源码同目录：`roleApi.test.ts` |
| 全局 setup | `src/tests/setup.ts`（vitest.config 引用） |
| 跨模块集成测试 | `src/tests/integration.test.ts` |

---

## 参考

- 完整架构：[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
- MVP 设计：[`../docs/superpowers/specs/2026-06-01-frontend-mvp-design.md`](../docs/superpowers/specs/2026-06-01-frontend-mvp-design.md)
