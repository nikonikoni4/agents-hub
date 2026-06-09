import { create } from 'zustand';
import type { SingleChatApiResponse } from '@/shared/types';

interface SingleChatState {
  singleChats: SingleChatApiResponse[];
  activeSingleChatId: string | null;
  displayLocation: 'sidebar' | 'main';

  setSingleChats: (chats: SingleChatApiResponse[]) => void;
  openSingleChat: (id: string) => void;
  closeSingleChat: () => void;
  addSingleChat: (chat: SingleChatApiResponse) => void;
  toggleLocation: () => void;
  clearActive: () => void;
}

export const useSingleChatStore = create<SingleChatState>((set) => ({
  singleChats: [],
  activeSingleChatId: null,
  displayLocation: 'sidebar',

  setSingleChats: (chats) => set({ singleChats: chats }),

  openSingleChat: (id) =>
    set({ activeSingleChatId: id, displayLocation: 'sidebar' }),

  closeSingleChat: () => set({ activeSingleChatId: null }),

  addSingleChat: (chat) =>
    set((state) => ({ singleChats: [...state.singleChats, chat] })),

  toggleLocation: () =>
    set((state) => ({
      displayLocation: state.displayLocation === 'sidebar' ? 'main' : 'sidebar',
    })),

  clearActive: () => set({ activeSingleChatId: null }),
}));
