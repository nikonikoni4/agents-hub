import { useEffect, useCallback } from 'react';
import { useSingleChatStore } from '../store/singleChatStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { listSingleChats } from '@/core/api/singleChatApi';
import type { RefreshSignal } from '@/shared/types';

export function useSingleChatList() {
  const { singleChats, setSingleChats } = useSingleChatStore();

  const refreshSingleChats = useCallback(async () => {
    try {
      const chats = await listSingleChats();
      setSingleChats(chats);
    } catch (error) {
      console.error('Failed to fetch single chats:', error);
    }
  }, [setSingleChats]);

  useEffect(() => {
    refreshSingleChats();
  }, [refreshSingleChats]);

  useEffect(() => {
    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      if (!signal?.group_chat_id) {
        refreshSingleChats();
      }
    };
    wsManager.on('refresh', handleRefresh);
    return () => { wsManager.off('refresh', handleRefresh); };
  }, [refreshSingleChats]);

  return { singleChats, refreshSingleChats };
}
