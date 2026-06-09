/**
 * 单聊相关 API 接口
 *
 * 提供单聊的 CRUD 操作和消息管理
 */

import apiClient, { mockableRequest } from './client';
import type { SingleChatApiResponse, SingleChatMessageApiItem } from '@/shared/types';

// ==================== Mock 数据 ====================

const MOCK_SINGLE_CHATS: SingleChatApiResponse[] = [
  {
    single_chat_id: 'mock-sc-001',
    single_chat_name: '开发助手对话',
    type: 'new',
    agent_name: 'Developer',
    platform: 'claude',
    session_id: 'sess-001',
    group_chat_id: null,
    cwd: '/home/user/project',
    created_at: '2026-06-08T10:00:00Z',
    last_active_at: '2026-06-08T10:00:00Z',
  },
  {
    single_chat_id: 'mock-sc-002',
    single_chat_name: 'Designer 对话',
    type: 'fork',
    agent_name: 'Designer',
    platform: 'claude',
    session_id: 'sess-002',
    group_chat_id: 'mock-chat-001',
    cwd: '/home/user/project',
    created_at: '2026-06-08T09:00:00Z',
    last_active_at: '2026-06-08T09:30:00Z',
  },
];

const MOCK_MESSAGES: SingleChatMessageApiItem[] = [
  {
    id: 'msg-001',
    role: 'user',
    content: '帮我分析一下这段代码的性能问题',
    timestamp: '2026-06-08T10:01:00Z',
    model: null,
  },
  {
    id: 'msg-002',
    role: 'assistant',
    content:
      '好的，让我来看看这段代码。\n\n主要的性能瓶颈在以下几个方面：\n\n1. **循环嵌套过深** — 时间复杂度 O(n²)\n2. **重复计算** — 缺少缓存机制\n3. **内存分配** — 频繁创建临时对象',
    timestamp: '2026-06-08T10:01:05Z',
    model: 'claude-sonnet-4-20250514',
  },
];

// ==================== API 函数 ====================

/**
 * 获取单聊列表
 *
 * 后端返回 { single_chats: [...] }，此处提取数组
 */
export async function listSingleChats(): Promise<SingleChatApiResponse[]> {
  const mock = { single_chats: MOCK_SINGLE_CHATS };
  const res = await mockableRequest(
    () => apiClient.get<{ single_chats: SingleChatApiResponse[] }>('/single-chats'),
    mock
  );
  return res.single_chats;
}

const MOCK_SINGLE_CHAT_DETAIL: SingleChatApiResponse = {
  single_chat_id: 'mock-sc-001',
  single_chat_name: '开发助手对话',
  type: 'new',
  agent_name: 'Developer',
  platform: 'claude',
  session_id: 'sess-001',
  group_chat_id: null,
  cwd: '/home/user/project',
  created_at: '2026-06-08T10:00:00Z',
  last_active_at: '2026-06-08T10:00:00Z',
};

/**
 * 获取单聊详情
 */
export async function getSingleChat(id: string): Promise<SingleChatApiResponse> {
  return mockableRequest(() => apiClient.get<SingleChatApiResponse>(`/single-chats/${id}`), {
    ...MOCK_SINGLE_CHAT_DETAIL,
    single_chat_id: id,
  });
}

/**
 * 获取单聊消息历史
 *
 * 后端返回 { messages: [...] }，此处提取 messages 数组
 */
export async function getSingleChatMessages(id: string): Promise<SingleChatMessageApiItem[]> {
  const mock = { messages: MOCK_MESSAGES };
  const res = await mockableRequest(
    () => apiClient.get<{ messages: SingleChatMessageApiItem[] }>(`/single-chats/${id}/messages`),
    mock
  );
  return res.messages;
}
