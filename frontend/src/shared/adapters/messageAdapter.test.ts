import { describe, it, expect } from 'vitest';
import {
  adaptMessage,
  adaptMessageList,
  adaptAgentMessage,
  adaptAgentMessageList,
  parseSender,
  aggregateMessagesWithSenders,
} from './messageAdapter';
import type { MessageApiItem, AgentMessageApiItem } from '@/shared/types/api-schemas';

const mockMessage: MessageApiItem = {
  speaker: 'user',
  content: 'Hello',
  timestamp: '2026-06-03T10:00:00Z',
  platform: 'user',
};

const mockAgentMessage: AgentMessageApiItem = {
  call_id: 'call-001',
  content: '你好',
  send_from: 'Agent1',
  send_to: 'user',
  session_type: 'main',
  message_type: 'task',
  timestamp: '2026-06-03T10:00:05Z',
};

describe('messageAdapter', () => {
  describe('adaptMessage', () => {
    it('转换单条消息', () => {
      const result = adaptMessage(mockMessage);
      expect(result.speaker).toBe('user');
      expect(result.content).toBe('Hello');
    });
  });

  describe('adaptMessageList', () => {
    it('转换消息列表', () => {
      const result = adaptMessageList([mockMessage, { ...mockMessage, speaker: 'Agent1' }]);
      expect(result).toHaveLength(2);
    });

    it('空列表返回空数组', () => {
      expect(adaptMessageList([])).toEqual([]);
    });
  });

  describe('adaptAgentMessage', () => {
    it('转换 Agent 消息', () => {
      const result = adaptAgentMessage(mockAgentMessage);
      expect(result.send_from).toBe('Agent1');
      expect(result.call_id).toBe('call-001');
    });
  });

  describe('adaptAgentMessageList', () => {
    it('转换 Agent 消息列表', () => {
      const result = adaptAgentMessageList([mockAgentMessage]);
      expect(result).toHaveLength(1);
    });
  });

  describe('parseSender', () => {
    it('返回 speaker 和 platform', () => {
      const result = parseSender('user', 'user');
      expect(result).toEqual({ speaker: 'user', platform: 'user' });
    });
  });

  describe('aggregateMessagesWithSenders', () => {
    it('未实现时抛出错误', async () => {
      await expect(aggregateMessagesWithSenders('chat-001')).rejects.toThrow('not implemented');
    });
  });
});
