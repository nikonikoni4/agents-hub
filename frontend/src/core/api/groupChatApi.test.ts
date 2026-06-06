import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./client', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
  mockableRequest: vi.fn((_real, mock) => Promise.resolve(mock)),
}));

import apiClient from './client';
import {
  createGroupChat,
  getGroupChatInfo,
  listGroupChats,
  getMessages,
  getMembers,
  sendMessage,
  updateMemberDockerMode,
  deleteGroupChat,
} from './groupChatApi';

const mockedClient = vi.mocked(apiClient);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('groupChatApi', () => {
  it('createGroupChat 返回群聊信息', async () => {
    const result = await createGroupChat({
      group_chat_name: 'Test',
      project_path: '/tmp',
      team_members: [],
    });
    expect(result.group_chat_id).toBe('mock-chat-001');
    expect(result.group_chat_name).toBe('Test Chat');
  });

  it('getGroupChatInfo 返回群聊详情', async () => {
    const result = await getGroupChatInfo('chat-001');
    expect(result.group_chat_id).toBe('mock-chat-001');
  });

  it('listGroupChats 返回所有群聊', async () => {
    const result = await listGroupChats();
    expect(result).toHaveLength(2);
  });

  it('listGroupChats(true) 只返回活跃群聊', async () => {
    const result = await listGroupChats(true);
    expect(result).toHaveLength(1);
    expect(result[0]!.is_active).toBe(true);
  });

  it('getMessages 返回消息列表', async () => {
    const result = await getMessages('chat-001');
    expect(result).toHaveLength(2);
    expect(result[0]!.speaker).toBe('user');
  });

  it('getMembers 返回成员列表', async () => {
    const result = await getMembers('mock-chat-001');
    expect(result).toHaveLength(2);
    expect(result[0]!.name).toBe('Leader');
  });

  it('sendMessage 返回发送确认', async () => {
    const result = await sendMessage('chat-001', { content: 'Hello', members: ['Agent1'] });
    expect(result.message).toContain('sent successfully');
  });

  it('updateMemberDockerMode 返回更新后的成员', async () => {
    const result = await updateMemberDockerMode('chat-001', 'Agent1', true);
    expect(result.use_docker).toBe(true);
    expect(result.name).toBe('Agent1');
  });

  it('deleteGroupChat 返回删除确认', async () => {
    const result = await deleteGroupChat('chat-001');
    expect(result.message).toContain('deleted successfully');
  });

  describe('真实 API 调用路径', () => {
    it('listGroupChats 调用 GET /group-chats', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.get.mockResolvedValue([]);

      await listGroupChats();
      expect(mockedClient.get).toHaveBeenCalledWith('/group-chats', {
        params: { is_active_only: false },
      });
    });

    it('getMessages 带游标分页参数', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.get.mockResolvedValue([]);

      await getMessages('chat-001', 20, '2026-06-04T10:00:00');
      expect(mockedClient.get).toHaveBeenCalledWith('/group-chats/chat-001/messages', {
        params: { limit: 20, before: '2026-06-04T10:00:00' },
      });
    });

    it('getMessages 无游标时只传 limit', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.get.mockResolvedValue([]);

      await getMessages('chat-001', 30);
      expect(mockedClient.get).toHaveBeenCalledWith('/group-chats/chat-001/messages', {
        params: { limit: 30 },
      });
    });

    it('updateMemberDockerMode 调用 PUT', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.put.mockResolvedValue({});

      await updateMemberDockerMode('chat-001', 'Agent1', true);
      expect(mockedClient.put).toHaveBeenCalledWith('/group-chats/chat-001/Agent1/use-docker', {
        use_docker: true,
      });
    });

    it('deleteGroupChat 带 keepData 参数', async () => {
      const { mockableRequest } = await import('./client');
      vi.mocked(mockableRequest).mockImplementation(async (real) => real());
      mockedClient.delete.mockResolvedValue({});

      await deleteGroupChat('chat-001', true);
      expect(mockedClient.delete).toHaveBeenCalledWith('/group-chats/chat-001', {
        params: { keep_data: true },
      });
    });
  });
});
