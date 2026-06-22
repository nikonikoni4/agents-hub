/**
 * useAssistantChat hook 测试
 *
 * 测试覆盖：
 * 1. initAssistantChat - 会话查找逻辑
 * 2. startNewChat - 开始新对话功能
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useAssistantChat } from './useAssistantChat';
import { useSingleChatStore } from '../store/singleChatStore';

describe('useAssistantChat', () => {
  beforeEach(() => {
    // 重置 store 状态
    useSingleChatStore.setState({
      singleChats: [],
      activeSingleChatId: null,
      draftChat: null,
    });
  });

  describe('initAssistantChat', () => {
    it('应该在无活跃会话时创建新的 draft 单聊', () => {
      const { result } = renderHook(() => useAssistantChat());

      act(() => {
        result.current.initAssistantChat();
      });

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBeNull();
      expect(state.draftChat).toEqual({
        type: 'new',
        single_chat_name: 'Agents Hub 助手',
        agent_name: 'Agents-Hub-Assistant',
      });
    });

    it('应该在有历史会话时打开最近的会话', () => {
      const mockChats = [
        {
          single_chat_id: 'chat-old',
          single_chat_name: 'Old Chat',
          type: 'new' as const,
          agent_name: 'Agents-Hub-Assistant',
          platform: 'claude' as const,
          session_id: null,
          group_chat_id: null,
          cwd: '',
          created_at: '2026-01-01T00:00:00Z',
          last_active_at: '2026-01-01T00:00:00Z',
        },
        {
          single_chat_id: 'chat-new',
          single_chat_name: 'New Chat',
          type: 'new' as const,
          agent_name: 'Agents-Hub-Assistant',
          platform: 'claude' as const,
          session_id: null,
          group_chat_id: null,
          cwd: '',
          created_at: '2026-06-01T00:00:00Z',
          last_active_at: '2026-06-01T00:00:00Z',
        },
      ];

      useSingleChatStore.setState({ singleChats: mockChats });

      const { result } = renderHook(() => useAssistantChat());

      act(() => {
        result.current.initAssistantChat();
      });

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBe('chat-new');
      expect(state.draftChat).toBeNull();
    });

    it('应该在已有活跃会话时不执行任何操作', () => {
      useSingleChatStore.setState({
        activeSingleChatId: 'existing-chat',
        draftChat: null,
      });

      const { result } = renderHook(() => useAssistantChat());

      act(() => {
        result.current.initAssistantChat();
      });

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBe('existing-chat');
    });

    it('应该在已有 draft 会话时不执行任何操作', () => {
      const existingDraft = {
        type: 'new' as const,
        single_chat_name: 'Existing Draft',
        agent_name: 'Test-Agent',
      };

      useSingleChatStore.setState({
        activeSingleChatId: null,
        draftChat: existingDraft,
      });

      const { result } = renderHook(() => useAssistantChat());

      act(() => {
        result.current.initAssistantChat();
      });

      const state = useSingleChatStore.getState();
      expect(state.draftChat).toEqual(existingDraft);
    });
  });

  describe('startNewChat', () => {
    it('应该清除当前会话并创建新的 draft', () => {
      useSingleChatStore.setState({
        activeSingleChatId: 'existing-chat',
        draftChat: null,
      });

      const { result } = renderHook(() => useAssistantChat());

      act(() => {
        result.current.startNewChat();
      });

      const state = useSingleChatStore.getState();
      expect(state.activeSingleChatId).toBeNull();
      expect(state.draftChat).toEqual({
        type: 'new',
        single_chat_name: 'Agents Hub 助手',
        agent_name: 'Agents-Hub-Assistant',
      });
    });

    it('应该在已有 draft 时替换为新的 draft', () => {
      useSingleChatStore.setState({
        activeSingleChatId: null,
        draftChat: {
          type: 'new',
          single_chat_name: 'Old Draft',
          agent_name: 'Old-Agent',
        },
      });

      const { result } = renderHook(() => useAssistantChat());

      act(() => {
        result.current.startNewChat();
      });

      const state = useSingleChatStore.getState();
      expect(state.draftChat).toEqual({
        type: 'new',
        single_chat_name: 'Agents Hub 助手',
        agent_name: 'Agents-Hub-Assistant',
      });
    });
  });
});
