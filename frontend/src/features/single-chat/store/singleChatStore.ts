/**
 * 单聊 Store
 *
 * 职责：
 * - 存储单聊列表
 * - 管理当前活跃的单聊
 * - 控制单聊面板的显隐
 *
 * 架构约束：
 * - 不包含副作用（API 调用在 hooks 中）
 * - 纯状态管理
 */

import { create } from 'zustand';
import type { SingleChatApiResponse } from '@/shared/types';

interface SingleChatState {
  /** 所有单聊列表 */
  singleChats: SingleChatApiResponse[];
  /** 当前活跃的单聊 ID（展示在 RightSidebar） */
  activeSingleChatId: string | null;
  /** 单聊面板是否可见 */
  isPanelOpen: boolean;
  /** 单聊显示位置：'sidebar' 为右侧栏，'main' 为主界面 */
  displayLocation: 'sidebar' | 'main';

  // Actions
  /** 设置单聊列表 */
  setSingleChats: (chats: SingleChatApiResponse[]) => void;
  /** 设置活跃单聊 */
  setActiveSingleChat: (id: string | null) => void;
  /** 打开单聊面板并激活指定单聊 */
  openSingleChat: (id: string) => void;
  /** 关闭单聊面板（保留 activeSingleChatId 以便快速重新打开） */
  closeSingleChat: () => void;
  /** 添加一条单聊记录 */
  addSingleChat: (chat: SingleChatApiResponse) => void;
  /** 切换单聊显示位置 */
  toggleLocation: () => void;
  /** 设置单聊显示位置 */
  setLocation: (location: 'sidebar' | 'main') => void;
}

export const useSingleChatStore = create<SingleChatState>((set) => ({
  singleChats: [],
  activeSingleChatId: null,
  isPanelOpen: false,
  displayLocation: 'sidebar',

  setSingleChats: (chats) => set({ singleChats: chats }),

  setActiveSingleChat: (id) => set({ activeSingleChatId: id }),

  openSingleChat: (id) => set({ activeSingleChatId: id, isPanelOpen: true, displayLocation: 'sidebar' }),

  closeSingleChat: () => set({ isPanelOpen: false }),

  addSingleChat: (chat) => set((state) => ({ singleChats: [...state.singleChats, chat] })),

  toggleLocation: () => set((state) => ({
    displayLocation: state.displayLocation === 'sidebar' ? 'main' : 'sidebar',
  })),

  setLocation: (location) => set({ displayLocation: location }),
}));
