/**
 * 群聊相关 API 接口
 *
 * 提供群聊的 CRUD 操作和消息管理
 */

import apiClient, { mockableRequest } from './client';
import type {
  GroupChatApiResponse,
  GroupChatSummaryApiItem,
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

const MOCK_GROUP_CHATS: GroupChatSummaryApiItem[] = [
  {
    group_chat_id: 'mock-chat-001',
    group_chat_name: 'Frontend Development Team',
    project_path: '/home/user/projects/frontend-app',
    is_active: true,
    created_at: '2026-06-03T10:00:00Z',
  },
  {
    group_chat_id: 'mock-chat-002',
    group_chat_name: 'Backend API Team',
    project_path: '/home/user/projects/backend-api',
    is_active: true,
    created_at: '2026-06-02T15:30:00Z',
  },
  {
    group_chat_id: 'mock-chat-003',
    group_chat_name: 'Code Review Session',
    project_path: '/home/user/projects/legacy-system',
    is_active: false,
    created_at: '2026-06-01T09:15:00Z',
  },
  {
    group_chat_id: 'mock-chat-004',
    group_chat_name: 'Database Migration',
    project_path: '/home/user/projects/db-migration',
    is_active: true,
    created_at: '2026-05-31T14:20:00Z',
  },
  {
    group_chat_id: 'mock-chat-005',
    group_chat_name: 'Testing & QA',
    project_path: '/home/user/projects/test-automation',
    is_active: false,
    created_at: '2026-05-30T08:45:00Z',
  },
];

const MOCK_MESSAGES: MessageApiItem[] = [
  {
    speaker: 'user',
    content: "Hello team! Let's start the code review for the authentication module.",
    timestamp: '2026-06-03T10:00:00Z',
    platform: 'user',
  },
  {
    speaker: 'Agent1',
    content:
      '你好！我是 Agent1，我已经查看了认证模块的代码。整体结构清晰，但有几个安全性问题需要注意。',
    timestamp: '2026-06-03T10:00:05Z',
    platform: 'claude',
  },
  {
    speaker: 'Agent2',
    content:
      'I noticed the password validation is too weak. We should enforce stronger requirements.',
    timestamp: '2026-06-03T10:00:12Z',
    platform: 'codex',
  },
  {
    speaker: 'Agent1',
    content: '同意。另外，我发现 JWT token 的过期时间设置得太长了，建议调整为 15 分钟。',
    timestamp: '2026-06-03T10:00:20Z',
    platform: 'claude',
  },
  {
    speaker: 'user',
    content: 'Good points. What about the refresh token mechanism?',
    timestamp: '2026-06-03T10:00:35Z',
    platform: 'user',
  },
  {
    speaker: 'Agent2',
    content:
      'The refresh token is stored in localStorage, which is vulnerable to XSS attacks. I recommend using httpOnly cookies instead.',
    timestamp: '2026-06-03T10:00:42Z',
    platform: 'codex',
  },
  {
    speaker: 'Agent1',
    content: '正确。我还建议添加 CSRF 保护和 rate limiting 来防止暴力破解攻击。',
    timestamp: '2026-06-03T10:00:55Z',
    platform: 'claude',
  },
  {
    speaker: 'user',
    content: 'Excellent suggestions. Can you create a task list for these improvements?',
    timestamp: '2026-06-03T10:01:10Z',
    platform: 'user',
  },
  {
    speaker: 'Agent2',
    content:
      'Sure! Here are the tasks:\n1. Strengthen password requirements\n2. Reduce JWT expiration to 15 minutes\n3. Move refresh token to httpOnly cookie\n4. Add CSRF protection\n5. Implement rate limiting',
    timestamp: '2026-06-03T10:01:18Z',
    platform: 'codex',
  },
  {
    speaker: 'Agent1',
    content: '我可以帮忙实现第 1、2、4 项。Agent2 可以处理第 3、5 项吗？',
    timestamp: '2026-06-03T10:01:30Z',
    platform: 'claude',
  },
];

const MOCK_MEMBERS: GroupChatMemberApiItem[] = [
  {
    name: 'Agent1',
    main_session: 'session-001',
    btw_session: [],
    cwd: '/home/user/project',
    use_docker: false,
  },
  {
    name: 'Agent2',
    main_session: 'session-002',
    btw_session: ['session-003'],
    cwd: '/home/user/project',
    use_docker: true,
  },
];

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
): Promise<GroupChatSummaryApiItem[]> {
  return mockableRequest(
    () =>
      apiClient.get<GroupChatSummaryApiItem[]>('/group-chats', {
        params: { is_active_only: isActiveOnly },
      }),
    isActiveOnly ? MOCK_GROUP_CHATS.filter((c) => c.is_active) : MOCK_GROUP_CHATS
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
    MOCK_MESSAGES
  );
}

/**
 * 获取群聊成员列表
 */
export async function getMembers(chatId: string): Promise<GroupChatMemberApiItem[]> {
  return mockableRequest(
    () => apiClient.get<GroupChatMemberApiItem[]>(`/group-chats/${chatId}/members`),
    MOCK_MEMBERS
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
