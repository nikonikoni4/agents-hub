# Frontend 前端基础设施

agents-hub 前端的核心基础设施，包括类型定义、API 客户端和 WebSocket 管理器。

## 📁 目录结构

```
frontend/src/
├── shared/types/              # 类型定义
│   ├── models.ts             # 核心数据模型（15+ 类型）
│   ├── api.ts                # API 请求/响应类型
│   ├── websocket.ts          # WebSocket 事件类型
│   └── index.ts              # 统一导出
│
├── core/                      # 核心基础设施
│   ├── api/                  # REST API 客户端
│   │   ├── client.ts         # Axios 封装 + ApiError + Mock 支持
│   │   ├── groupChatApi.ts   # 群聊 API（6 个接口）
│   │   ├── roleApi.ts        # 角色管理 API（9 个接口）
│   │   └── index.ts          # 统一导出
│   │
│   ├── websocket/            # WebSocket 管理
│   │   └── WebSocketManager.ts  # 单例 WebSocket 管理器
│   │
│   └── index.ts              # Core 统一导出
│
└── tests/                     # 测试文件
    └── integration.test.ts   # 集成测试示例
```

## 🚀 快速开始

### 1. 环境配置

创建 `.env.development` 文件（已创建）：

```env
# API 配置
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/api/v1

# Mock 开关
VITE_USE_MOCK=false

# 调试模式
VITE_DEBUG=true
```

### 2. Mock 模式切换

```bash
# 开启 Mock 模式（前端独立开发，不依赖后端）
VITE_USE_MOCK=true npm run dev

# 连接真实后端
VITE_USE_MOCK=false npm run dev
```

## 📖 使用示例

### 类型定义

```typescript
import type { Role, GroupChat, Message } from '@/shared/types';

const role: Role = {
  name: 'Developer',
  platform: 'claude',
  avatar: null,
  abilities: ['代码编写'],
  type: 'team_member',
  scope: null,
  description: '开发工程师',
};
```

### API 调用

```typescript
import {
  createGroupChat,
  listGroupChats,
  getMessages,
  listRoles,
} from '@/core/api';

// 创建群聊
const chat = await createGroupChat({
  team_members: ['Agent1', 'Agent2'],
  project_path: '/home/user/project',
  group_chat_name: 'My Chat',
});

// 获取消息历史
const messages = await getMessages(chat.group_chat_id, 50, 0);

// 获取角色列表
const roles = await listRoles();
```

### WebSocket 连接

```typescript
import { wsManager } from '@/core/websocket/WebSocketManager';

// 订阅事件
wsManager.on('connected', () => {
  console.log('连接成功');
});

wsManager.on('message', (data) => {
  console.log('收到消息:', data);
});

wsManager.on('refresh', (signal) => {
  console.log('收到刷新信号:', signal);
  // 重新拉取消息
});

// 连接到群聊
wsManager.connect('chat-id-123');

// 发送消息
wsManager.send({
  content: 'Hello',
  send_to: 'Agent1',
});

// 断开连接
wsManager.disconnect();
```

### 错误处理

```typescript
import { ApiError } from '@/core/api';

try {
  const chat = await createGroupChat(data);
} catch (error) {
  if (error instanceof ApiError) {
    console.error('API 错误:', error.code, error.message);
    console.error('状态码:', error.status);
  }
}
```

## 🔧 API 接口清单

### 群聊 API

| 函数 | 功能 | 参数 |
|------|------|------|
| `createGroupChat` | 创建群聊 | `CreateGroupChatRequest` |
| `getGroupChatInfo` | 获取群聊详情 | `chatId` |
| `listGroupChats` | 列出所有群聊 | `isActiveOnly?` |
| `getMessages` | 获取消息历史 | `chatId, limit?, offset?` |
| `getMembers` | 获取成员列表 | `chatId` |
| `sendMessage` | 发送消息 | `chatId, SendMessageRequest` |
| `updateMemberDockerMode` | 切换 Docker | `chatId, memberName, useDocker` |
| `deleteGroupChat` | 删除群聊 | `chatId, keepData?` |

### 角色管理 API

| 函数 | 功能 | 参数 |
|------|------|------|
| `createRole` | 创建角色 | `CreateRoleRequest` |
| `getRoleInfo` | 获取角色详情 | `name` |
| `listRoles` | 列出所有角色 | - |
| `updateRole` | 更新角色 | `name, UpdateRoleRequest` |
| `deleteRole` | 删除角色 | `name` |
| `getRoleSkills` | 获取角色 Skills | `name` |
| `addSkillToRole` | 添加 Skill | `name, skillId` |
| `removeSkillFromRole` | 移除 Skill | `name, skillId` |
| `listAvatars` | 列出可用头像 | - |

## ✅ 集成测试

运行集成测试验证功能：

```typescript
import { runAllTests } from '@/tests/integration.test';

// 在浏览器控制台运行
runAllTests();
```

**测试场景**：
1. API 调用流程（创建群聊、获取消息、列出角色）
2. WebSocket 连接与断开
3. WebSocket 自动重连（可选）

## 🎯 特性

### API Client
- ✅ 统一的错误处理（ApiError）
- ✅ 请求/响应拦截器
- ✅ 完整的 Mock 支持（环境变量切换）
- ✅ 自动 token 管理
- ✅ 开发模式日志

### WebSocket Manager
- ✅ 单例模式
- ✅ 自动重连（指数退避：1s, 2s, 4s, 8s, 16s）
- ✅ 消息队列（离线时缓存，最多 100 条）
- ✅ 事件订阅系统（on/off）
- ✅ 连接状态管理
- ✅ 最大重试 5 次

### 类型安全
- ✅ 所有类型与后端 Pydantic schemas 一致
- ✅ 完整的 TypeScript 类型推导
- ✅ 枚举类型（平台、角色类型、群聊类型等）

## 📝 开发规范

遵循 `frontend/CLAUDE.md` 的架构约束：
- **分层架构**：core（基础） → features（业务） → shared（复用）
- **单向依赖**：components → hooks → store → core
- **模块隔离**：features 之间禁止直接依赖

## 🔍 故障排查

### API 调用失败
1. 检查后端是否启动（`http://localhost:8000/health`）
2. 检查 `.env.development` 配置
3. 开启 `VITE_DEBUG=true` 查看详细日志
4. 尝试开启 Mock 模式验证前端逻辑

### WebSocket 连接失败
1. 检查后端 WebSocket 端点（`ws://localhost:8000/api/v1/ws/group_chat/{id}`）
2. 查看浏览器控制台 WebSocket 连接日志
3. 确认 `group_chat_id` 存在且活跃

### TypeScript 类型错误
1. 确保导入路径使用 `@/` 别名
2. 检查 `tsconfig.json` 配置
3. 重启 TypeScript 服务（VS Code: Cmd/Ctrl + Shift + P → Restart TS Server）

## 🚧 后续工作

完成基础设施后，可以开始：
1. **UI 开发**：`features/chat`（聊天窗口）
2. **状态管理**：`features/chat/store`（Zustand）
3. **布局组件**：`layouts/MainLayout.tsx`

## 📚 参考文档

- [后端 API 文档](../../docs/ARCHITECTURE.md)
- [前端架构规范](../CLAUDE.md)
- [设计系统](../../docs/DESIGN.md)
- [实施计划](../../docs/temp/frontend-implementation-plan.md)
