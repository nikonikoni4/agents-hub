import { describe, it, expect } from 'vitest';
import {
  adaptGroupChat,
  adaptGroupChatSummary,
  adaptGroupChatSummaryList,
  adaptGroupChatMember,
  adaptGroupChatMemberList,
  aggregateConversationWithMessages,
  aggregateConversationWithMembers,
} from './chatAdapter';
import type { GroupChatApiResponse, GroupChatMemberApiItem } from '@/shared/types/api-schemas';

const mockChat: GroupChatApiResponse = {
  group_chat_id: 'chat-001',
  group_chat_name: 'Test Chat',
  project_path: '/tmp',
  created_at: '2026-06-03T10:00:00Z',
  group_type: 'sequence_execute',
  is_active: true,
};

const mockSummary: GroupChatApiResponse = {
  group_chat_id: 'chat-001',
  group_chat_name: 'Test Chat',
  project_path: '/tmp',
  created_at: '2026-06-03T10:00:00Z',
  group_type: 'manager_orchestrate',
  is_active: true,
};

const mockMember: GroupChatMemberApiItem = {
  name: 'Agent1',
  main_session: 'session-001',
  btw_session: [],
  cwd: '/tmp',
  use_docker: false,
  status: 'idle',
  context_usage: null,
};

describe('chatAdapter', () => {
  describe('adaptGroupChat', () => {
    it('转换群聊数据', () => {
      const result = adaptGroupChat(mockChat);
      expect(result.group_chat_id).toBe('chat-001');
      expect(result.is_active).toBe(true);
    });
  });

  describe('adaptGroupChatSummary', () => {
    it('转换群聊摘要', () => {
      const result = adaptGroupChatSummary(mockSummary);
      expect(result.group_chat_id).toBe('chat-001');
    });
  });

  describe('adaptGroupChatSummaryList', () => {
    it('转换摘要列表', () => {
      const result = adaptGroupChatSummaryList([
        mockSummary,
        { ...mockSummary, group_chat_id: 'chat-002' },
      ]);
      expect(result).toHaveLength(2);
    });

    it('空列表返回空数组', () => {
      expect(adaptGroupChatSummaryList([])).toEqual([]);
    });
  });

  describe('adaptGroupChatMember', () => {
    it('转换成员数据', () => {
      const result = adaptGroupChatMember(mockMember);
      expect(result.name).toBe('Agent1');
      expect(result.use_docker).toBe(false);
    });
  });

  describe('adaptGroupChatMemberList', () => {
    it('转换成员列表', () => {
      const result = adaptGroupChatMemberList([mockMember]);
      expect(result).toHaveLength(1);
    });
  });

  describe('聚合函数', () => {
    it('aggregateConversationWithMessages 未实现', async () => {
      await expect(aggregateConversationWithMessages('chat-001')).rejects.toThrow(
        'not implemented'
      );
    });

    it('aggregateConversationWithMembers 未实现', async () => {
      await expect(aggregateConversationWithMembers('chat-001')).rejects.toThrow('not implemented');
    });
  });
});
