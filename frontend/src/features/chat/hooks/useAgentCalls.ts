import { useState, useEffect, useCallback } from 'react';
import { getAgentCalls } from '@/core/api/groupChatApi';
import { wsManager } from '@/core/websocket/WebSocketManager';
import type { AgentCallInfo, RefreshSignal } from '@/shared/types';

export function useAgentCalls(chatId: string | null) {
  const [agentCalls, setAgentCalls] = useState<AgentCallInfo[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!chatId) {
      setAgentCalls([]);
      return;
    }

    setLoading(true);
    try {
      const data = await getAgentCalls(chatId);
      setAgentCalls(data);
    } catch (err) {
      console.error('Failed to load agent calls:', err);
    } finally {
      setLoading(false);
    }
  }, [chatId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!chatId) return;

    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      if (signal?.group_chat_id === chatId) {
        refresh();
      }
    };

    wsManager.on('refresh', handleRefresh);
    return () => {
      wsManager.off('refresh', handleRefresh);
    };
  }, [chatId, refresh]);

  return { agentCalls, loading, refresh };
}
