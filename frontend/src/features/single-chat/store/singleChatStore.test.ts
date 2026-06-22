/**
 * singleChatStore 测试
 *
 * 测试覆盖：
 * 1. 状态管理
 * 2. 方法实现
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useSingleChatStore } from './singleChatStore';

describe('singleChatStore', () => {
  beforeEach(() => {
    // 重置 store 状态
    useSingleChatStore.setState({
      singleChats: [],
      activeSingleChatId: null,
      draftChat: null,
      displayLocation: 'sidebar',
    });
  });

  describe('状态管理', () => {
    it('应该有正确的初始状态', () => {
      const state = useSingleChatStore.getState();
      expect(state.singleChats).toEqual([]);
      expect(state.activeSingleChatId).toBeNull();
      expect(state.draftChat).toBeNull();
      expect(state.displayLocation).toBe('sidebar');
    });

    it('应该在 setSingleChats 时更新 singleChats', () => {
      const mockChats = [
        {
          single_chat_id: 'chat-1',
          single_chat_name: 'Test Chat',
          type: 'new' as const,
          agent_name: 'Test-Agent',
          platform: 'claude' as const,
          session_id: null,
          group_chat_id: null,
          cwd: '',
          created_at: '',
          last_active_at: '',
        },
      ];

      const { setSingleChats } = useSingleChatStore.getState();
      setSingleChats(mockChats);

      const state = useSingleChatStore.getState();
      expect(state.singleChats).toEqual(mockChats);
    });

    it('应该在 openSingleChat 时设置 activeSingleChatId', () => {
      const { openSingleChat } = useSingleChatStore.getState();
      openSingleChat('chat-1');

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBe('chat-1');
      expect(state.draftChat).toBeNull();
    });

    it('应该在 openDraftChat 时设置 draftChat', () => {
      const draft = {
        agent_name: 'Test-Agent',
        single_chat_name: 'Test Draft',
        type: 'new' as const,
      };

      const { openDraftChat } = useSingleChatStore.getState();
      openDraftChat(draft);

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBeNull();
      expect(state.draftChat).toEqual(draft);
    });

    it('应该在 closeSingleChat 时清除状态', () => {
      useSingleChatStore.setState({
        activeSingleChatId: 'chat-1',
        draftChat: null,
      });

      const { closeSingleChat } = useSingleChatStore.getState();
      closeSingleChat();

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBeNull();
      expect(state.draftChat).toBeNull();
    });

    it('应该在 clearActive 时清除状态', () => {
      useSingleChatStore.setState({
        activeSingleChatId: 'chat-1',
        draftChat: { agent_name: 'Test', single_chat_name: 'Test', type: 'new' },
      });

      const { clearActive } = useSingleChatStore.getState();
      clearActive();

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBeNull();
      expect(state.draftChat).toBeNull();
    });
  });
});
