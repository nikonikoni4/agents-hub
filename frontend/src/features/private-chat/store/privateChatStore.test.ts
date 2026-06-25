/**
 * privateChatStore 测试
 *
 * 测试覆盖：
 * 1. 状态管理
 * 2. 方法实现
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { usePrivateChatStore } from './privateChatStore';

describe('privateChatStore', () => {
  beforeEach(() => {
    // 重置 store 状态
    usePrivateChatStore.setState({
      activeGroupChatId: null,
      activeAgentName: null,
      lastActivityTime: null,
    });
  });

  describe('状态管理', () => {
    it('应该有正确的初始状态', () => {
      const state = usePrivateChatStore.getState();
      expect(state.activeGroupChatId).toBeNull();
      expect(state.activeAgentName).toBeNull();
      expect(state.lastActivityTime).toBeNull();
    });

    it('应该在 startPrivateChat 时设置活跃私聊状态', () => {
      const { startPrivateChat } = usePrivateChatStore.getState();
      startPrivateChat('group-1', 'agent-1');

      const state = usePrivateChatStore.getState();
      expect(state.activeGroupChatId).toBe('group-1');
      expect(state.activeAgentName).toBe('agent-1');
      expect(state.lastActivityTime).toBeTypeOf('number');
    });

    it('应该在 stopPrivateChat 时清除所有状态', () => {
      // 先设置状态
      usePrivateChatStore.setState({
        activeGroupChatId: 'group-1',
        activeAgentName: 'agent-1',
        lastActivityTime: Date.now(),
      });

      const { stopPrivateChat } = usePrivateChatStore.getState();
      stopPrivateChat();

      const state = usePrivateChatStore.getState();
      expect(state.activeGroupChatId).toBeNull();
      expect(state.activeAgentName).toBeNull();
      expect(state.lastActivityTime).toBeNull();
    });

    it('应该在 updateActivity 时更新最后活动时间', () => {
      const before = Date.now();
      const { updateActivity } = usePrivateChatStore.getState();
      updateActivity();

      const state = usePrivateChatStore.getState();
      expect(state.lastActivityTime).toBeGreaterThanOrEqual(before);
    });

    it('应该在 startPrivateChat 时更新最后活动时间', () => {
      const before = Date.now();
      const { startPrivateChat } = usePrivateChatStore.getState();
      startPrivateChat('group-1', 'agent-1');

      const state = usePrivateChatStore.getState();
      expect(state.lastActivityTime).toBeGreaterThanOrEqual(before);
    });
  });
});
