/**
 * findLatestAssistantChat 工具函数测试
 *
 * 测试覆盖：
 * 1. 筛选 Agents-Hub-Assistant 单聊
 * 2. 按 last_active_at 降序排序
 * 3. 无匹配时返回 null
 * 4. 空数组时返回 null
 */

import { describe, it, expect } from 'vitest';
import { findLatestAssistantChat } from './findLatestAssistantChat';
import type { SingleChatApiResponse } from '@/shared/types';

describe('findLatestAssistantChat', () => {
  const createMockChat = (
    overrides: Partial<SingleChatApiResponse> = {}
  ): SingleChatApiResponse => ({
    single_chat_id: 'test-id',
    single_chat_name: 'Test Chat',
    type: 'new',
    agent_name: 'Test-Agent',
    platform: 'claude',
    session_id: null,
    group_chat_id: null,
    cwd: '',
    created_at: '2026-01-01T00:00:00Z',
    last_active_at: '2026-01-01T00:00:00Z',
    ...overrides,
  });

  it('应该返回最近活跃的 Agents-Hub-Assistant 单聊', () => {
    const chats: SingleChatApiResponse[] = [
      createMockChat({
        single_chat_id: 'chat-1',
        agent_name: 'Agents-Hub-Assistant',
        last_active_at: '2026-01-01T00:00:00Z',
      }),
      createMockChat({
        single_chat_id: 'chat-2',
        agent_name: 'Agents-Hub-Assistant',
        last_active_at: '2026-01-02T00:00:00Z',
      }),
      createMockChat({
        single_chat_id: 'chat-3',
        agent_name: 'Other-Agent',
        last_active_at: '2026-01-03T00:00:00Z',
      }),
    ];

    const result = findLatestAssistantChat(chats);

    expect(result).not.toBeNull();
    expect(result!.single_chat_id).toBe('chat-2');
  });

  it('应该忽略非 Agents-Hub-Assistant 的单聊', () => {
    const chats: SingleChatApiResponse[] = [
      createMockChat({
        single_chat_id: 'chat-1',
        agent_name: 'Other-Agent',
        last_active_at: '2026-01-01T00:00:00Z',
      }),
    ];

    const result = findLatestAssistantChat(chats);

    expect(result).toBeNull();
  });

  it('应该在没有 Agents-Hub-Assistant 单聊时返回 null', () => {
    const chats: SingleChatApiResponse[] = [
      createMockChat({ agent_name: 'Agent-1' }),
      createMockChat({ agent_name: 'Agent-2' }),
    ];

    const result = findLatestAssistantChat(chats);

    expect(result).toBeNull();
  });

  it('应该在空数组时返回 null', () => {
    const result = findLatestAssistantChat([]);

    expect(result).toBeNull();
  });

  it('应该正确处理只有一个 Agents-Hub-Assistant 单聊的情况', () => {
    const chats: SingleChatApiResponse[] = [
      createMockChat({
        single_chat_id: 'chat-1',
        agent_name: 'Agents-Hub-Assistant',
        last_active_at: '2026-01-01T00:00:00Z',
      }),
    ];

    const result = findLatestAssistantChat(chats);

    expect(result).not.toBeNull();
    expect(result!.single_chat_id).toBe('chat-1');
  });

  it('应该按 last_active_at 降序排序，取最新的', () => {
    const chats: SingleChatApiResponse[] = [
      createMockChat({
        single_chat_id: 'chat-old',
        agent_name: 'Agents-Hub-Assistant',
        last_active_at: '2026-01-01T00:00:00Z',
      }),
      createMockChat({
        single_chat_id: 'chat-new',
        agent_name: 'Agents-Hub-Assistant',
        last_active_at: '2026-06-01T00:00:00Z',
      }),
      createMockChat({
        single_chat_id: 'chat-mid',
        agent_name: 'Agents-Hub-Assistant',
        last_active_at: '2026-03-01T00:00:00Z',
      }),
    ];

    const result = findLatestAssistantChat(chats);

    expect(result).not.toBeNull();
    expect(result!.single_chat_id).toBe('chat-new');
  });
});
