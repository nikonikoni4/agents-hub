/**
 * 群聊相关 API 接口
 *
 * 提供群聊的 CRUD 操作和消息管理
 */

import apiClient, { mockableRequest } from './client';
import type {
  GroupChat,
  GroupChatSummary,
  GroupChatMember,
  Message,
  CreateGroupChatRequest,
  SendMessageRequest,
  UpdateDockerModeRequest,
} from '@/shared/types';

// ==================== Mock 数据 ====================

const MOCK_GROUP_CHAT: GroupChat = {
  group_chat_id: 'mock-chat-001',
  group_chat_name: 'Test Chat',
  project_path: '/home/user/project',
  created_at: '2026-06-03T10:00:00Z',
  group_type: 'sequence_execute',
  is_active: true,
};

const MOCK_GROUP_CHATS: GroupChatSummary[] = [
  {
    group_chat_id: 'mock-chat-001',
    group_chat_name: 'Test Chat 1',
    project_path: '/home/user/project1',
    is_active: true,
    created_at: '2026-06-03T10:00:00Z',
  },
  {
    group_chat_id: 'mock-chat-002',
    group_chat_name: 'Test Chat 2',
    project_path: '/home/user/project2',
    is_active: false,
    created_at: '2026-06-02T15:30:00Z',
  },
];

const MOCK_MESSAGES: Message[] = [
  {
    speaker: 'user',
    content: 'Hello, Agent!',
    timestamp: '2026-06-03T10:00:00Z',
    platform: 'user',
  },
  {
    speaker: 'Agent1',
    content: '你好！我是 Agent1，有什么可以帮助你的吗？',
    timestamp: '2026-06-03T10:00:05Z',
    platform: 'claude',
  },
];

const MOCK_MEMBERS: GroupChatMember[] = [
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
export async function createGroupChat(data: CreateGroupChatRequest): Promise<GroupChat> {
  return mockableRequest(() => apiClient.post('/group-chats', data), MOCK_GROUP_CHAT);
}

/**
 * 获取群聊详细信息
 */
export async function getGroupChatInfo(chatId: string): Promise<GroupChat> {
  return mockableRequest(() => apiClient.get(`/group-chats/${chatId}`), MOCK_GROUP_CHAT);
}

/**
 * 列出所有群聊
 *
 * @param isActiveOnly - 是否只返回活跃群聊
 */
export async function listGroupChats(isActiveOnly: boolean = false): Promise<GroupChatSummary[]> {
  return mockableRequest(
    () => apiClient.get('/group-chats', { params: { is_active_only: isActiveOnly } }),
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
): Promise<Message[]> {
  return mockableRequest(
    () => apiClient.get(`/group-chats/${chatId}/messages`, { params: { limit, offset } }),
    MOCK_MESSAGES
  );
}

/**
 * 获取群聊成员列表
 */
export async function getMembers(chatId: string): Promise<GroupChatMember[]> {
  return mockableRequest(() => apiClient.get(`/group-chats/${chatId}/members`), MOCK_MEMBERS);
}

/**
 * 向群聊发送消息
 */
export async function sendMessage(
  chatId: string,
  data: SendMessageRequest
): Promise<{ message: string }> {
  return mockableRequest(() => apiClient.post(`/group-chats/${chatId}/messages`, data), {
    message: 'Message sent successfully',
  });
}

/**
 * 切换成员 Docker 沙箱模式
 */
export async function updateMemberDockerMode(
  chatId: string,
  memberName: string,
  useDocker: boolean
): Promise<GroupChatMember> {
  const data: UpdateDockerModeRequest = { use_docker: useDocker };
  return mockableRequest(
    () => apiClient.put(`/group-chats/${chatId}/${memberName}/use-docker`, data),
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
): Promise<{ message: string }> {
  return mockableRequest(
    () => apiClient.delete(`/group-chats/${chatId}`, { params: { keep_data: keepData } }),
    { message: `Group chat ${chatId} deleted successfully` }
  );
}
