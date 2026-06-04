/**
 * 群聊相关 API 接口
 *
 * 提供群聊的 CRUD 操作和消息管理
 */

import apiClient, { mockableRequest } from './client';
import type {
  GroupChatApiResponse,
  GroupChatInfoApiResponse,
  GroupChatMemberApiItem,
  MessageApiItem,
  CreateGroupChatRequest,
  SendMessageRequest,
  UpdateDockerModeRequest,
  SuccessResponse,
} from '@/shared/types';

// ==================== Mock 数据 ====================

const MOCK_GROUP_CHAT: GroupChatApiResponse = {
  group_chat_id: 'mock-chat-001',
  group_chat_name: 'Test Chat',
  project_path: '/home/user/project',
  created_at: '2026-06-03T10:00:00Z',
  group_type: 'sequence_execute',
  is_active: true,
};

const MOCK_GROUP_CHATS: GroupChatApiResponse[] = [
  {
    group_chat_id: 'mock-chat-001',
    group_chat_name: 'Frontend Development Team',
    project_path: '/home/user/projects/frontend-app',
    created_at: '2026-06-03T10:00:00Z',
    group_type: 'manager_orchestrate',
    is_active: true,
  },
  {
    group_chat_id: 'mock-chat-002',
    group_chat_name: 'Backend API Team',
    project_path: '/home/user/projects/backend-api',
    created_at: '2026-06-02T15:30:00Z',
    group_type: 'sequence_execute',
    is_active: true,
  },
  {
    group_chat_id: 'mock-chat-003',
    group_chat_name: 'Code Review Session',
    project_path: '/home/user/projects/legacy-system',
    created_at: '2026-06-01T09:15:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
  },
  {
    group_chat_id: 'mock-chat-004',
    group_chat_name: 'Database Migration',
    project_path: '/home/user/projects/db-migration',
    created_at: '2026-05-31T14:20:00Z',
    group_type: 'sequence_execute',
    is_active: true,
  },
  {
    group_chat_id: 'mock-chat-005',
    group_chat_name: 'Testing & QA',
    project_path: '/home/user/projects/test-automation',
    created_at: '2026-05-30T08:45:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
  },
];

const MOCK_GROUP_CHAT_INFOS: GroupChatInfoApiResponse[] = [
  {
    group_chat_id: 'mock-chat-001',
    group_chat_name: 'Frontend Development Team',
    project_path: '/home/user/projects/frontend-app',
    created_at: '2026-06-03T10:00:00Z',
    group_type: 'manager_orchestrate',
    is_active: true,
    last_speaker: 'Agent1',
    last_message: '前端组件已完成开发，准备提交代码审查',
    last_update_at: '2026-06-03T11:30:00Z',
  },
  {
    group_chat_id: 'mock-chat-002',
    group_chat_name: 'Backend API Team',
    project_path: '/home/user/projects/backend-api',
    created_at: '2026-06-02T15:30:00Z',
    group_type: 'sequence_execute',
    is_active: true,
    last_speaker: 'Agent2',
    last_message: 'API 接口文档已更新，包含新的认证端点',
    last_update_at: '2026-06-02T16:45:00Z',
  },
  {
    group_chat_id: 'mock-chat-003',
    group_chat_name: 'Code Review Session',
    project_path: '/home/user/projects/legacy-system',
    created_at: '2026-06-01T09:15:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
    last_speaker: 'user',
    last_message: '请检查认证模块的安全性问题',
    last_update_at: '2026-06-01T10:00:00Z',
  },
  {
    group_chat_id: 'mock-chat-004',
    group_chat_name: 'Database Migration',
    project_path: '/home/user/projects/db-migration',
    created_at: '2026-05-31T14:20:00Z',
    group_type: 'sequence_execute',
    is_active: true,
    last_speaker: 'Agent1',
    last_message: '迁移脚本已准备就绪，建议在低峰期执行',
    last_update_at: '2026-05-31T15:30:00Z',
  },
  {
    group_chat_id: 'mock-chat-005',
    group_chat_name: 'Testing & QA',
    project_path: '/home/user/projects/test-automation',
    created_at: '2026-05-30T08:45:00Z',
    group_type: 'manager_orchestrate',
    is_active: false,
    last_speaker: 'Agent2',
    last_message: '单元测试覆盖率已达到 85%',
    last_update_at: '2026-05-30T09:15:00Z',
  },
];

// 按 chatId 分组的 mock 消息数据
const MOCK_MESSAGES_BY_CHAT: Record<string, MessageApiItem[]> = {
  'mock-chat-001': [
    {
      speaker: 'user',
      content: '我们需要开发一个新的用户仪表板页面，包含数据可视化组件。',
      timestamp: '2026-06-03T10:00:00Z',
      platform: 'user',
    },
    {
      speaker: 'Agent1',
      content: '好的，我来负责前端组件开发。建议使用 Recharts 库来实现图表功能。',
      timestamp: '2026-06-03T10:00:05Z',
      platform: 'claude',
    },
    {
      speaker: 'Agent2',
      content: '我可以处理后端 API 接口，提供用户统计数据。',
      timestamp: '2026-06-03T10:00:12Z',
      platform: 'codex',
    },
  ],
  'mock-chat-002': [
    {
      speaker: 'user',
      content: '请帮我设计用户认证系统的 API 接口。',
      timestamp: '2026-06-02T15:30:00Z',
      platform: 'user',
    },
    {
      speaker: 'Agent1',
      content: '我建议采用 JWT + Refresh Token 的方案，access token 设置 15 分钟过期。',
      timestamp: '2026-06-02T15:30:05Z',
      platform: 'claude',
    },
    {
      speaker: 'user',
      content: '好的，请输出完整的 API 文档。',
      timestamp: '2026-06-02T15:31:00Z',
      platform: 'user',
    },
    {
      speaker: 'Agent1',
      content: 'API 文档已更新，包含登录、注册、刷新 token、登出四个端点。',
      timestamp: '2026-06-02T16:45:00Z',
      platform: 'claude',
    },
  ],
  'mock-chat-003': [
    {
      speaker: 'user',
      content: '请检查认证模块的安全性问题。',
      timestamp: '2026-06-01T09:15:00Z',
      platform: 'user',
    },
    {
      speaker: 'Agent1',
      content:
        '已发现几个安全问题：1. 密码验证过于简单 2. JWT token 过期时间过长 3. refresh token 存储在 localStorage',
      timestamp: '2026-06-01T09:15:10Z',
      platform: 'claude',
    },
    {
      speaker: 'Agent2',
      content: '建议使用 httpOnly cookie 存储 refresh token，并添加 CSRF 保护。',
      timestamp: '2026-06-01T09:15:20Z',
      platform: 'codex',
    },
  ],
};

// 默认 mock 消息（用于未匹配的 chatId）
const MOCK_MESSAGES_DEFAULT: MessageApiItem[] = [
  {
    speaker: 'user',
    content: '开始新会话。',
    timestamp: '2026-06-03T10:00:00Z',
    platform: 'user',
  },
  {
    speaker: 'Agent1',
    content: '收到，准备就绪。',
    timestamp: '2026-06-03T10:00:05Z',
    platform: 'claude',
  },
];

const MOCK_MEMBERS: Record<string, GroupChatMemberApiItem[]> = {
  'mock-chat-001': [
    {
      name: 'Leader',
      main_session: 'session-leader-001',
      btw_session: [],
      cwd: '/home/user/projects/frontend-app',
      use_docker: false,
    },
    {
      name: 'Developer',
      main_session: 'session-dev-001',
      btw_session: [],
      cwd: '/home/user/projects/frontend-app',
      use_docker: true,
    },
  ],
  'mock-chat-002': [
    {
      name: 'Leader',
      main_session: 'session-leader-002',
      btw_session: [],
      cwd: '/home/user/projects/backend-api',
      use_docker: false,
    },
    {
      name: 'Developer',
      main_session: 'session-dev-002',
      btw_session: ['session-dev-002-btw'],
      cwd: '/home/user/projects/backend-api',
      use_docker: true,
    },
    {
      name: 'Tester',
      main_session: 'session-tester-001',
      btw_session: [],
      cwd: '/home/user/projects/backend-api',
      use_docker: false,
    },
  ],
  'mock-chat-003': [
    {
      name: 'Leader',
      main_session: 'session-leader-003',
      btw_session: [],
      cwd: '/home/user/projects/legacy-system',
      use_docker: false,
    },
    {
      name: 'Designer',
      main_session: 'session-designer-001',
      btw_session: [],
      cwd: '/home/user/projects/legacy-system',
      use_docker: false,
    },
  ],
};

// ==================== API 接口 ====================

/**
 * 创建并启动新群聊
 */
export async function createGroupChat(data: CreateGroupChatRequest): Promise<GroupChatApiResponse> {
  return mockableRequest(
    () => apiClient.post<GroupChatApiResponse>('/group-chats', data),
    MOCK_GROUP_CHAT
  );
}

/**
 * 获取群聊详细信息
 */
export async function getGroupChatInfo(chatId: string): Promise<GroupChatApiResponse> {
  return mockableRequest(
    () => apiClient.get<GroupChatApiResponse>(`/group-chats/${chatId}`),
    MOCK_GROUP_CHAT
  );
}

/**
 * 列出所有群聊
 *
 * @param isActiveOnly - 是否只返回活跃群聊
 */
export async function listGroupChats(
  isActiveOnly: boolean = false
): Promise<GroupChatApiResponse[]> {
  return mockableRequest(
    () =>
      apiClient.get<GroupChatApiResponse[]>('/group-chats', {
        params: { is_active_only: isActiveOnly },
      }),
    isActiveOnly ? MOCK_GROUP_CHATS.filter((c) => c.is_active) : MOCK_GROUP_CHATS
  );
}

/**
 * 列出所有群聊（包含 Session 列表扩展信息）
 *
 * 返回包含 last_speaker、last_message、last_update_at 的完整信息
 * 用于 Session 列表展示
 *
 * @param isActiveOnly - 是否只返回活跃群聊
 */
export async function listGroupChatInfos(
  isActiveOnly: boolean = false
): Promise<GroupChatInfoApiResponse[]> {
  return mockableRequest(
    () =>
      apiClient.get<GroupChatInfoApiResponse[]>('/group-chats', {
        params: { is_active_only: isActiveOnly, include_info: true },
      }),
    isActiveOnly ? MOCK_GROUP_CHAT_INFOS.filter((c) => c.is_active) : MOCK_GROUP_CHAT_INFOS
  );
}

/**
 * 获取消息历史
 *
 * @param chatId - 群聊 ID
 * @param limit - 返回消息数量上限（1-200，默认 50）
 * @param offset - 跳过前 N 条消息（默认 0）
 */
export async function getMessages(
  chatId: string,
  limit: number = 50,
  offset: number = 0
): Promise<MessageApiItem[]> {
  return mockableRequest(
    () =>
      apiClient.get<MessageApiItem[]>(`/group-chats/${chatId}/messages`, {
        params: { limit, offset },
      }),
    MOCK_MESSAGES_BY_CHAT[chatId] ?? MOCK_MESSAGES_DEFAULT
  );
}

/**
 * 获取群聊成员列表
 */
export async function getMembers(chatId: string): Promise<GroupChatMemberApiItem[]> {
  return mockableRequest(
    () => apiClient.get<GroupChatMemberApiItem[]>(`/group-chats/${chatId}/members`),
    MOCK_MEMBERS[chatId] ?? []
  );
}

/**
 * 向群聊发送消息
 */
export async function sendMessage(
  chatId: string,
  data: SendMessageRequest
): Promise<SuccessResponse> {
  return mockableRequest(
    () => apiClient.post<SuccessResponse>(`/group-chats/${chatId}/messages`, data),
    { message: 'Message sent successfully' }
  );
}

/**
 * 切换成员 Docker 沙箱模式
 */
export async function updateMemberDockerMode(
  chatId: string,
  memberName: string,
  useDocker: boolean
): Promise<GroupChatMemberApiItem> {
  const data: UpdateDockerModeRequest = { use_docker: useDocker };
  return mockableRequest(
    () =>
      apiClient.put<GroupChatMemberApiItem>(
        `/group-chats/${chatId}/${memberName}/use-docker`,
        data
      ),
    {
      ...MOCK_MEMBERS[0],
      name: memberName,
      use_docker: useDocker,
      main_session: null,
      btw_session: [],
      cwd: null,
    }
  );
}

/**
 * 删除群聊
 *
 * @param chatId - 群聊 ID
 * @param keepData - true=仅从内存移除，false=完全删除（默认）
 */
export async function deleteGroupChat(
  chatId: string,
  keepData: boolean = false
): Promise<SuccessResponse> {
  return mockableRequest(
    () =>
      apiClient.delete<SuccessResponse>(`/group-chats/${chatId}`, {
        params: { keep_data: keepData },
      }),
    { message: `Group chat ${chatId} deleted successfully` }
  );
}
