/**
 * 私聊状态管理 Store
 *
 * 管理私聊特有的状态：关联群聊、Agent 名称、超时计时器。
 * 纯状态管理，不包含 API 调用（副作用在 hooks 中）。
 */

import { create } from 'zustand';

interface PrivateChatState {
  /** 关联的群聊 ID */
  activeGroupChatId: string | null;
  /** 私聊中的 Agent 名称 */
  activeAgentName: string | null;
  /** 最后活动时间戳 */
  lastActivityTime: number | null;
  /** 超时计时器 ID */
  timerId: ReturnType<typeof setTimeout> | null;

  /** 设置活跃私聊状态 */
  startPrivateChat: (groupChatId: string, agentName: string) => void;
  /** 清除所有状态并清除计时器 */
  stopPrivateChat: () => void;
  /** 重置 3 分钟计时器 */
  resetTimer: () => void;
  /** 清除计时器（不清除状态） */
  clearTimer: () => void;
}

export const usePrivateChatStore = create<PrivateChatState>((set, get) => ({
  activeGroupChatId: null,
  activeAgentName: null,
  lastActivityTime: null,
  timerId: null,

  startPrivateChat: (groupChatId: string, agentName: string) => {
    // 清除旧计时器
    const { timerId } = get();
    if (timerId) {
      clearTimeout(timerId);
    }

    set({
      activeGroupChatId: groupChatId,
      activeAgentName: agentName,
      lastActivityTime: Date.now(),
      timerId: null,
    });
  },

  stopPrivateChat: () => {
    const { timerId } = get();
    if (timerId) {
      clearTimeout(timerId);
    }

    set({
      activeGroupChatId: null,
      activeAgentName: null,
      lastActivityTime: null,
      timerId: null,
    });
  },

  resetTimer: () => {
    const { timerId, activeGroupChatId, activeAgentName } = get();
    if (!activeGroupChatId || !activeAgentName) return;

    // 清除旧计时器
    if (timerId) {
      clearTimeout(timerId);
    }

    // 设置新计时器（计时器回调在 hooks 中处理，这里只管理 ID）
    set({
      lastActivityTime: Date.now(),
      timerId: null, // 计时器由 hooks 设置和管理
    });
  },

  clearTimer: () => {
    const { timerId } = get();
    if (timerId) {
      clearTimeout(timerId);
    }
    set({ timerId: null });
  },
}));
