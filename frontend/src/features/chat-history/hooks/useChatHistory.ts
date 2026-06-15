import { useState, useEffect, useCallback } from 'react';
import { getMemberHistory } from '@/core/api';
import type { MemberHistoryMessage } from '@/shared/types';

export function useChatHistory(chatId: string | null, agentName: string | null) {
  const [messages, setMessages] = useState<MemberHistoryMessage[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchHistory = useCallback(async () => {
    if (!chatId || !agentName) {
      setMessages([]);
      return;
    }
    setLoading(true);
    try {
      const data = await getMemberHistory(chatId, agentName);
      setMessages(data.messages);
    } catch (err) {
      console.error('Failed to load member history:', err);
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, [chatId, agentName]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return { messages, loading, refresh: fetchHistory };
}
