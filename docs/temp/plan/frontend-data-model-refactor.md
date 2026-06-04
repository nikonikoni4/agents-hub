# 前端数据模型重构计划（调整版）

## 文档信息

- **创建时间**: 2026-06-04
- **状态**: 待审核
- **负责人**: Nico
- **预计工期**: 2 天

---

## 一、现状分析

### 当前架构问题

1. **前后端耦合严重**
   - 前端类型名称直接使用后端模型名称（`Role`、`GroupChat`、`Message`）
   - 后端改名，前端必须同步修改
   - 无法体现前端特有的业务语义

2. **类型职责不清**
   - `models.ts` 混杂了 API 响应类型和前端业务类型
   - 无法清晰识别哪些类型来自后端 API
   - 类型定义分散，维护困难

3. **缺少适配/聚合层**
   - 组件直接使用 API 响应类型
   - 无法处理数据转换（如 `created_at: string` → `createdAt: Date`）
   - 多 API 聚合场景无统一处理机制

4. **存在冗余定义**
   - `Agent` 类型是 `Role` 的别名（完全重复）
   - 部分内联类型定义（已在前面修复）

---

## 二、目标架构

### 核心设计理念

**务实渐进，按需扩展**：
1. ✅ 阶段 1：规范 API Schemas，删除冗余
2. ✅ 阶段 2：建立 Adapters 框架（不实现具体聚合）
3. ⏸️ Domain 类型：页面设计时按需创建

### 两层架构（初期）

```
┌─────────────────────────────────────────────────────────┐
│                    Features / Layouts                    │
│              (直接使用 API Schemas 类型)                  │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│         Adapters (框架层，提供基础转换能力)              │
│  • 基础 1:1 转换函数（类型安全）                          │
│  • 预留聚合函数接口（按需实现）                           │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  API Layer (core/api)                    │
│              (返回 API Schemas 类型)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
                 Backend API
```

### 未来扩展为三层（按需）

当页面设计时需要不同于 API 的数据结构，引入 Domain 层：

```
Features/Layouts (使用 Domain 类型)
        ↓
Adapters (API → Domain 转换 + 聚合)
        ↓
API Layer (返回 API Schemas 类型)
        ↓
Backend API
```

---

## 三、类型定义规范

### 1. API Schemas 类型（`api-schemas.ts`）

**命名规则**：`{资源名}ApiResponse` / `{资源名}ApiItem`

**职责**：
- 严格对应后端 Pydantic schemas
- 使用后端字段名（如 `created_at`、`group_chat_id`）
- 保持后端数据类型（如日期用 `string`）
- 添加 JSDoc 注释标注对应的后端 schema

**示例**：
```typescript
/**
 * 角色信息
 * 对应后端: RoleResponse schema
 */
export interface RoleApiResponse {
  name: string;
  platform: 'claude' | 'codex';
  avatar: string | null;
  abilities: string[];
  type: 'leader' | 'team_member' | null;
  scope: string[] | null;
  description: string | null;
}

/**
 * 群聊详细信息
 * 对应后端: GroupChatInfo schema
 */
export interface GroupChatApiResponse {
  group_chat_id: string;
  group_chat_name: string;
  project_path: string;
  created_at: string;  // ISO 8601 字符串
  group_type: 'sequence_execute' | 'manager_orchestrate';
  is_active: boolean;
}

/**
 * 消息信息
 * 对应后端: MessageInfo schema
 */
export interface MessageApiItem {
  speaker: string;
  content: string;
  timestamp: string;  // ISO 8601 字符串
  platform: string;
}
```

---

### 2. Domain 类型（`domain.ts`）

**命名规则**：符合前端业务语义的名称

**职责**：
- 前端组件直接使用的业务模型
- 使用 camelCase 字段名
- 使用前端友好的数据类型（如 `Date`、枚举）
- 体现前端业务语义

**示例**：
```typescript
/**
 * 团队成员（前端业务模型）
 */
export interface TeamMember {
  id: string;                    // API 的 name 字段
  displayName: string;            // API 的 name 字段
  avatarUrl: string | null;       // API 的 avatar 字段
  skills: string[];               // API 的 abilities 字段
  isLeader: boolean;              // 从 type 字段派生
  platform: AgentPlatform;
  scope: string[] | null;
  description: string | null;
}

/**
 * 会话（前端业务模型）
 */
export interface Conversation {
  id: string;                     // API 的 group_chat_id
  title: string;                  // API 的 group_chat_name
  projectPath: string;
  createdAt: Date;                // API 的 created_at (转换为 Date)
  isActive: boolean;
  type: ConversationType;         // API 的 group_type
}

/**
 * 聊天消息（前端业务模型）
 */
export interface ChatMessage {
  id: string;                     // 前端生成（timestamp + speaker）
  sender: MessageSender;          // 解析后的发送者信息
  content: string;
  timestamp: Date;                // API 的 timestamp (转换为 Date)
  platform: string;
}

/**
 * 消息发送者信息（前端派生）
 */
export interface MessageSender {
  type: 'user' | 'agent';
  name: string;
  avatarUrl?: string;
}

/**
 * 会话类型（前端枚举）
 */
export enum ConversationType {
  Sequential = 'sequential',      // API 的 sequence_execute
  Managed = 'managed',            // API 的 manager_orchestrate
}

/**
 * Agent 平台（前端枚举）
 */
export enum AgentPlatform {
  Claude = 'claude',
  Codex = 'codex',
}
```

---

### 3. API Requests 类型（`api-requests.ts`）

**命名规则**：`{操作}{资源名}Request`

**职责**：
- API 请求参数类型
- 保持与当前 `api.ts` 一致

**示例**：
```typescript
/**
 * 创建角色请求
 * 对应后端: RoleCreateRequest
 */
export interface CreateRoleRequest {
  name: string;
  platform: AgentPlatform;
  avatar?: string | null;
  abilities?: string[];
  type?: RoleType | null;
  scope?: string[] | null;
  description?: string | null;
}

/**
 * 创建群聊请求
 * 对应后端: GroupChatCreate
 */
export interface CreateConversationRequest {
  team_members: string[];
  project_path: string;
  group_chat_name?: string;
}

/**
 * 发送消息请求
 * 对应后端: MessageCreate
 */
export interface SendMessageRequest {
  content: string;
  send_to: string;
}
```

---

### 4. Adapters 实现规范

**命名规则**：`adapt{资源名}` / `aggregate{场景}`

**职责**：
- API 类型 → Domain 类型转换
- 多 API 响应聚合
- 数据格式适配

**示例**：
```typescript
// adapters/roleAdapter.ts

import type { RoleApiResponse, RoleSkillApiItem } from '@/shared/types/api-schemas';
import type { TeamMember } from '@/shared/types/domain';
import { getRoleInfo, getRoleSkills } from '@/core/api/roleApi';

/**
 * 将 API 角色响应转换为前端团队成员模型
 */
export function adaptRole(apiRole: RoleApiResponse): TeamMember {
  return {
    id: apiRole.name,
    displayName: apiRole.name,
    avatarUrl: apiRole.avatar,
    skills: apiRole.abilities,
    isLeader: apiRole.type === 'leader',
    platform: apiRole.platform,
    scope: apiRole.scope,
    description: apiRole.description,
  };
}

/**
 * 聚合：获取角色及其关联的 Skills 详情
 */
export async function aggregateRoleWithSkills(roleName: string) {
  const [roleData, skillsData] = await Promise.all([
    getRoleInfo(roleName),
    getRoleSkills(roleName),
  ]);
  
  return {
    ...adaptRole(roleData),
    skillDetails: skillsData.map(adaptSkill),
  };
}

/**
 * 将多个 API 角色响应转换为团队成员列表
 */
export function adaptRoleList(apiRoles: RoleApiResponse[]): TeamMember[] {
  return apiRoles.map(adaptRole);
}
```

```typescript
// adapters/chatAdapter.ts

import type { GroupChatApiResponse, MessageApiItem } from '@/shared/types/api-schemas';
import type { Conversation, ChatMessage, MessageSender } from '@/shared/types/domain';

/**
 * 将 API 群聊响应转换为前端会话模型
 */
export function adaptGroupChat(apiChat: GroupChatApiResponse): Conversation {
  return {
    id: apiChat.group_chat_id,
    title: apiChat.group_chat_name,
    projectPath: apiChat.project_path,
    createdAt: new Date(apiChat.created_at),
    isActive: apiChat.is_active,
    type: apiChat.group_type === 'sequence_execute' 
      ? ConversationType.Sequential 
      : ConversationType.Managed,
  };
}

/**
 * 将 API 消息响应转换为前端聊天消息模型
 */
export function adaptMessage(apiMessage: MessageApiItem): ChatMessage {
  return {
    id: `${apiMessage.timestamp}-${apiMessage.speaker}`,
    sender: parseSender(apiMessage.speaker, apiMessage.platform),
    content: apiMessage.content,
    timestamp: new Date(apiMessage.timestamp),
    platform: apiMessage.platform,
  };
}

/**
 * 解析发送者信息
 */
function parseSender(speaker: string, platform: string): MessageSender {
  if (speaker === 'user') {
    return { type: 'user', name: 'You' };
  }
  return {
    type: 'agent',
    name: speaker,
    // avatarUrl 可以从其他地方获取
  };
}

/**
 * 聚合：获取会话及其消息历史
 */
export async function aggregateConversationWithMessages(chatId: string) {
  const [chatData, messagesData] = await Promise.all([
    getGroupChatInfo(chatId),
    getMessages(chatId),
  ]);
  
  return {
    conversation: adaptGroupChat(chatData),
    messages: messagesData.map(adaptMessage),
  };
}
```

---

## 四、实施计划

### 阶段 1：规范现有数据模型（1 天）

**目标**：基于 API schemas 重新组织类型定义，删除冗余

#### 核心原则
- ✅ 保留：严格对应后端 API schemas 的类型
- ✅ 规范：统一命名为 `{资源名}ApiResponse` 格式
- ❌ 删除：前端自创的、与后端不对应的业务类型
- ⏸️ 暂不创建：Domain 类型（留待页面设计时按需创建）

#### 任务清单

- [ ] **任务 1.1**：重新组织类型文件结构
  - [ ] 重命名 `models.ts` → `api-schemas.ts`
  - [ ] 重命名 `api.ts` → `api-requests.ts`
  - [ ] 保持 `websocket.ts` 不变
  - [ ] 更新 `types/index.ts` 导出

- [ ] **任务 1.2**：规范 API Schemas 类型命名
  - [ ] `Role` → `RoleApiResponse`
  - [ ] `GroupChat` → `GroupChatApiResponse`
  - [ ] `GroupChatSummary` → `GroupChatSummaryApiItem`
  - [ ] `GroupChatMember` → `GroupChatMemberApiItem`
  - [ ] `Message` → `MessageApiItem`
  - [ ] `AgentMessage` → `AgentMessageApiItem`
  - [ ] `Skill` → `SkillApiItem`
  - [ ] `RoleSkill` → `RoleSkillApiItem`
  - [ ] `AgentContextState` → `AgentContextStateApiResponse`
  - [ ] `AgentSessionInfo` → `AgentSessionInfoApiResponse`
  - [ ] `SystemConfig` → `SystemConfigApiResponse`

- [ ] **任务 1.3**：删除冗余类型
  - [ ] 删除 `Agent` 类型别名（与 `Role` 重复）
  - [ ] 检查是否有其他冗余定义

- [ ] **任务 1.4**：为每个类型添加 JSDoc
  - [ ] 标注对应的后端 schema 名称
  - [ ] 添加字段说明（特别是枚举值含义）

- [ ] **任务 1.5**：更新 API 层类型引用
  - [ ] 更新 `roleApi.ts` 的返回类型
  - [ ] 更新 `groupChatApi.ts` 的返回类型
  - [ ] 更新 `skillApi.ts` 的返回类型
  - [ ] 确保所有 API 函数返回 `*ApiResponse` 类型

- [ ] **任务 1.6**：更新 Mock 数据类型
  - [ ] 修改所有 `MOCK_*` 常量的类型注解
  - [ ] 确保 Mock 数据与新类型一致

- [ ] **任务 1.7**：全局搜索替换类型引用
  - [ ] 查找所有导入 `Role` 的地方，替换为 `RoleApiResponse`
  - [ ] 查找所有导入 `GroupChat` 的地方，替换为 `GroupChatApiResponse`
  - [ ] 查找所有导入 `Message` 的地方，替换为 `MessageApiItem`
  - [ ] 其他类型同理

- [ ] **任务 1.8**：运行测试验证
  - [ ] 运行 `npm run type-check` 确保无类型错误
  - [ ] 运行测试套件确保功能正常
  - [ ] 修复因类型重命名导致的问题

- [ ] **任务 1.9**：更新文档
  - [ ] 在 `api-schemas.ts` 文件头添加说明注释
  - [ ] 更新 `frontend/src/shared/CLAUDE.md`
  - [ ] 添加类型命名规范说明

---

### 阶段 2：建立聚合层框架（0.5 天）

**目标**：创建 Adapters 层框架，但不实现具体聚合逻辑

#### 核心原则
- ✅ 创建目录结构和模板文件
- ✅ 提供基础的转换函数（1:1 映射）
- ❌ 不实现复杂聚合逻辑（等待页面设计时按需添加）
- ✅ 编写使用指南和示例

#### 任务清单

- [ ] **任务 2.1**：创建 Adapters 目录结构
  - [ ] 创建 `frontend/src/shared/adapters/` 目录
  - [ ] 创建 `adapters/index.ts`
  - [ ] 创建 `adapters/README.md` 使用指南
  - [ ] 创建 `adapters/types.ts` 定义 Adapter 通用类型

- [ ] **任务 2.2**：创建 Adapter 模板文件（无实现）
  - [ ] 创建 `adapters/roleAdapter.ts`（仅框架）
  - [ ] 创建 `adapters/chatAdapter.ts`（仅框架）
  - [ ] 创建 `adapters/skillAdapter.ts`（仅框架）
  - [ ] 创建 `adapters/messageAdapter.ts`（仅框架）
  - [ ] 每个文件包含：
    - 基础 `adapt*()` 函数（1:1 映射，类型转换）
    - 预留 `aggregate*()` 函数签名（注释说明用途）
    - JSDoc 示例

- [ ] **任务 2.3**：编写 Adapter 使用指南
  - [ ] 在 `adapters/README.md` 中说明：
    - 何时使用 Adapter
    - 如何添加新的聚合函数
    - 命名规范
    - 示例代码
  - [ ] 提供 2-3 个实际使用场景示例

- [ ] **任务 2.4**：更新编码规范文档
  - [ ] 创建 `docs/coding-rules/frontend-data-model.md`
  - [ ] 定义三层架构规范：
    - API Schemas 层：何时定义，如何命名
    - Adapters 层：何时使用，如何扩展
    - Domain 层：何时创建（页面设计时按需）
  - [ ] 添加决策流程图

- [ ] **任务 2.5**：提供一个完整示例（可选）
  - [ ] 选择一个简单场景（如 Role 列表展示）
  - [ ] 实现完整的流程：
    - API 返回 `RoleApiResponse[]`
    - Adapter 转换为前端友好格式
    - 组件使用转换后的数据
  - [ ] 作为后续开发的参考模板

---

### 阶段 3：验证和完善（0.5 天）

**目标**：确保重构完成，文档齐全

#### 任务清单

- [ ] **任务 3.1**：代码审查
  - [ ] 检查所有 API 函数返回类型是否为 `*ApiResponse`
  - [ ] 检查是否还有遗留的旧类型名称
  - [ ] 检查 Adapter 框架是否完整

- [ ] **任务 3.2**：文档完善
  - [ ] 更新 `docs/ARCHITECTURE.md` 架构文档
  - [ ] 在 `frontend/src/shared/CLAUDE.md` 中添加 Adapter 使用规范
  - [ ] 确保所有关键决策都有文档记录

- [ ] **任务 3.3**：测试验证
  - [ ] 运行完整测试套件
  - [ ] 手动测试主要功能
  - [ ] 确认类型检查无错误
  - [ ] 确认 Mock 模式工作正常

- [ ] **任务 3.4**：编写迁移总结
  - [ ] 记录重构前后对比
  - [ ] 记录遇到的问题和解决方案
  - [ ] 为后续开发提供最佳实践指南

---

## 五、风险评估

### 高风险项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 类型重命名导致大量编译错误 | 高 | 使用 IDE 的全局搜索替换功能，逐个类型修改 |
| 遗漏部分类型引用未更新 | 中 | 使用 TypeScript 严格模式，编译时检查 |

### 中风险项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| Mock 数据类型不匹配 | 中 | 同步更新所有 Mock 数据的类型注解 |
| 现有测试用例失败 | 中 | 及时修复测试用例中的类型引用 |

---

## 六、验收标准

### 功能验收

- [ ] 所有现有功能正常工作
- [ ] TypeScript 编译无错误
- [ ] 所有测试用例通过
- [ ] Mock 模式下所有功能可用

### 代码质量验收

- [ ] 所有 API 函数返回 `*ApiResponse` 类型
- [ ] 删除了冗余的类型定义（如 `Agent`）
- [ ] 所有类型都有 JSDoc 注释标注对应的后端 schema
- [ ] Adapters 框架搭建完成，包含使用指南

### 文档验收

- [ ] 创建 `docs/coding-rules/frontend-data-model.md` 规范文档
- [ ] 创建 `frontend/src/shared/adapters/README.md` 使用指南
- [ ] 更新 `frontend/src/shared/CLAUDE.md`
- [ ] 提供至少一个完整的使用示例

---

## 七、后续优化

### Domain 类型的按需创建策略

**原则**：Domain 类型不在重构阶段批量创建，而是在实际页面设计时按需定义

#### 何时创建 Domain 类型？

1. **组件需要不同于 API 的数据结构**
   - API 返回 `created_at: string`，组件需要 `Date` 对象
   - API 返回扁平结构，组件需要嵌套结构
   - API 字段名不符合前端语义（如 `abilities` → `skills`）

2. **需要聚合多个 API 响应**
   - 显示角色详情页：需要 Role + Skills
   - 显示会话列表：需要 GroupChat + Members + 最后一条消息

3. **需要派生/计算属性**
   - `isExpired`、`canEdit`、`displayName` 等

#### 创建流程

```typescript
// 1. 设计页面时，先使用 API 类型
function RoleList() {
  const [roles, setRoles] = useState<RoleApiResponse[]>([]);
  // ...
}

// 2. 发现 API 类型不满足需求时，创建 Domain 类型
// 在 shared/types/domain.ts 中添加：
export interface TeamMember {
  id: string;
  displayName: string;
  skills: string[];
  isLeader: boolean;
  // ... 其他前端需要的字段
}

// 3. 在 Adapter 中实现转换
// 在 shared/adapters/roleAdapter.ts 中添加：
export function adaptRole(apiRole: RoleApiResponse): TeamMember {
  return {
    id: apiRole.name,
    displayName: apiRole.name,
    skills: apiRole.abilities,
    isLeader: apiRole.type === 'leader',
  };
}

// 4. 组件使用 Domain 类型
function RoleList() {
  const [roles, setRoles] = useState<TeamMember[]>([]);
  
  useEffect(() => {
    listRoles().then(apiRoles => {
      setRoles(apiRoles.map(adaptRole));
    });
  }, []);
}
```

#### Domain 类型创建规范

- **文件位置**：`frontend/src/shared/types/domain.ts`
- **命名规范**：使用前端业务语义（`TeamMember` 而非 `Role`）
- **字段命名**：使用 camelCase
- **添加注释**：说明与 API 类型的区别和转换逻辑
- **同步更新**：在对应的 Adapter 中添加转换函数

---

## 八、参考资料

### 设计模式

- **适配器模式（Adapter Pattern）**：用于转换 API 类型到 Domain 类型
- **仓储模式（Repository Pattern）**：Adapter 可视为前端的"仓储层"
- **领域驱动设计（DDD）**：Domain 类型体现前端领域模型

### 相关文档

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) - 架构文档
- [`frontend/CLAUDE.md`](../../frontend/CLAUDE.md) - 前端编码规范
- [`frontend/src/core/CLAUDE.md`](../../frontend/src/core/CLAUDE.md) - Core 层规范
- [`frontend/src/shared/CLAUDE.md`](../../frontend/src/shared/CLAUDE.md) - Shared 层规范

---

## 九、决策记录

### 核心决策

1. **为什么采用渐进式架构？**
   - ❌ 避免：一次性创建三层架构，大量 Domain 类型和 Adapter 实现闲置
   - ✅ 采用：先规范 API Schemas，建立 Adapters 框架，Domain 类型按需创建
   - **理由**：务实高效，避免过度设计

2. **为什么 Domain 类型按需创建？**
   - 页面设计前无法准确预测前端需要什么数据结构
   - 提前创建的 Domain 类型可能与实际需求不符，导致重复修改
   - 按需创建可以确保每个 Domain 类型都有明确的使用场景

3. **为什么阶段 2 只建立框架不实现聚合？**
   - 聚合逻辑依赖具体的页面需求（哪些数据需要一起展示）
   - 提前实现的聚合函数可能不符合实际使用场景
   - 框架提供了扩展点，后续添加聚合函数成本很低

4. **字段命名风格选择**
   - API Schemas：保持后端 snake_case（便于对照后端 schema）
   - Domain（未来）：使用前端 camelCase（符合 JS/TS 惯例）
   - Adapter 负责命名风格转换

5. **为什么删除 `Agent` 类型别名？**
   - `Agent` 完全等同于 `Role`，违反 DRY 原则
   - 造成语义混淆：开发者不知道该用哪个
   - 统一使用 `RoleApiResponse` 更清晰

---

**待审核问题**：
1. ~~是否需要为 Adapter 添加缓存机制？~~ → 阶段 2 不实现
2. ~~是否需要支持 Adapter 的逆向转换（Domain → API）？~~ → 按需添加
3. ~~是否需要引入运行时类型校验库（如 Zod）？~~ → 后续优化项

---

## 附录：类型对照表

### 阶段 1 类型重命名对照

| 旧类型名 | 新类型名 | 说明 |
|---------|---------|------|
| `Role` | `RoleApiResponse` | 角色信息 |
| `Agent` | **删除**（使用 `RoleApiResponse`） | 与 Role 重复 |
| `GroupChat` | `GroupChatApiResponse` | 群聊详细信息 |
| `GroupChatSummary` | `GroupChatSummaryApiItem` | 群聊列表项 |
| `GroupChatMember` | `GroupChatMemberApiItem` | 群聊成员信息 |
| `Message` | `MessageApiItem` | 消息信息 |
| `AgentMessage` | `AgentMessageApiItem` | Agent 内部消息 |
| `Skill` | `SkillApiItem` | 全局 Skill 信息 |
| `RoleSkill` | `RoleSkillApiItem` | 角色关联的 Skill |
| `AgentContextState` | `AgentContextStateApiResponse` | Agent 上下文状态 |
| `AgentSessionInfo` | `AgentSessionInfoApiResponse` | Agent 会话信息 |
| `SystemConfig` | `SystemConfigApiResponse` | 系统配置信息 |

### 文件重命名对照

| 旧文件名 | 新文件名 |
|---------|---------|
| `shared/types/models.ts` | `shared/types/api-schemas.ts` |
| `shared/types/api.ts` | `shared/types/api-requests.ts` |
