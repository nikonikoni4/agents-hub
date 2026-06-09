import { create } from 'zustand';
import type { SingleChatApiResponse } from '@/shared/types';

export interface DraftChat {
  agent_name: string;
  single_chat_name: string;
  type: 'new' | 'fork' | 'continue_group_chat';
  group_chat_id?: string;
}

interface SingleChatState {
  singleChats: SingleChatApiResponse[];
  activeSingleChatId: string | null;
  draftChat: DraftChat | null;
  displayLocation: 'sidebar' | 'main';

  setSingleChats: (chats: SingleChatApiResponse[]) => void;
  openSingleChat: (id: string) => void;
  openDraftChat: (draft: DraftChat) => void;
  closeSingleChat: () => void;
  addSingleChat: (chat: SingleChatApiResponse) => void;
  promoteDraftToReal: (realId: string, chat: SingleChatApiResponse) => void;
  toggleLocation: () => void;
  clearActive: () => void;
}

export const useSingleChatStore = create<SingleChatState>((set) => ({
  singleChats: [],
  activeSingleChatId: null,
  draftChat: null,
  displayLocation: 'sidebar',

  setSingleChats: (chats) => set({ singleChats: chats }),

  openSingleChat: (id) => set({ activeSingleChatId: id, draftChat: null, displayLocation: 'sidebar' }),

  openDraftChat: (draft) => set({ activeSingleChatId: null, draftChat: draft, displayLocation: 'sidebar' }),

  closeSingleChat: () => set({ activeSingleChatId: null, draftChat: null }),

  addSingleChat: (chat) => set((state) => ({ singleChats: [...state.singleChats, chat] })),

  promoteDraftToReal: (realId, chat) =>
    set((state) => ({
      singleChats: [...state.singleChats, chat],
      activeSingleChatId: realId,
      draftChat: null,
    })),

  toggleLocation: () =>
    set((state) => ({
      displayLocation: state.displayLocation === 'sidebar' ? 'main' : 'sidebar',
    })),

  clearActive: () => set({ activeSingleChatId: null, draftChat: null }),
}));
