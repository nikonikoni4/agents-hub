/**
 * Pinned Messages Store
 *
 * 职责：
 * - 存储当前活跃会话的置顶消息列表
 * - 保证所有组件共享同一份 pinned 状态
 *
 * 架构约束：
 * - 不包含副作用（API 调用在 usePinnedMessages hook 中）
 * - 纯状态管理
 */

import { create } from 'zustand';
import type { PinnedMessageInfo } from '@/shared/types';

interface PinnedMessagesState {
  /** 当前活跃 chatId */
  chatId: string | null;
  /** 置顶消息列表 */
  pinnedMessages: PinnedMessageInfo[];
  /** 是否加载中 */
  isLoading: boolean;

  // Actions
  /** 设置 chatId（切换会话时调用） */
  setChatId: (chatId: string | null) => void;
  /** 替换整个置顶消息列表 */
  setPinnedMessages: (messages: PinnedMessageInfo[]) => void;
  /** 设置加载状态 */
  setIsLoading: (loading: boolean) => void;
}

export const usePinnedMessagesStore = create<PinnedMessagesState>((set) => ({
  chatId: null,
  pinnedMessages: [],
  isLoading: false,

  setChatId: (chatId) => set({ chatId }),
  setPinnedMessages: (messages) => set({ pinnedMessages: messages }),
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
