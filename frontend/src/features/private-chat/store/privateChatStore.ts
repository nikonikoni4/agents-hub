/**
 * 私聊状态管理 Store
 *
 * 管理私聊特有的状态：关联群聊、Agent 名称、最后活动时间。
 * 纯状态管理，不包含 API 调用和计时器逻辑（副作用在 hooks 中）。
 */

import { create } from 'zustand';

interface PrivateChatState {
  /** 关联的群聊 ID */
  activeGroupChatId: string | null;
  /** 私聊中的 Agent 名称 */
  activeAgentName: string | null;
  /** 最后活动时间戳 */
  lastActivityTime: number | null;

  /** 设置活跃私聊状态 */
  startPrivateChat: (groupChatId: string, agentName: string) => void;
  /** 清除所有状态 */
  stopPrivateChat: () => void;
  /** 更新最后活动时间 */
  updateActivity: () => void;
}

export const usePrivateChatStore = create<PrivateChatState>((set) => ({
  activeGroupChatId: null,
  activeAgentName: null,
  lastActivityTime: null,

  startPrivateChat: (groupChatId: string, agentName: string) => {
    set({
      activeGroupChatId: groupChatId,
      activeAgentName: agentName,
      lastActivityTime: Date.now(),
    });
  },

  stopPrivateChat: () => {
    set({
      activeGroupChatId: null,
      activeAgentName: null,
      lastActivityTime: null,
    });
  },

  updateActivity: () => {
    set({ lastActivityTime: Date.now() });
  },
}));
