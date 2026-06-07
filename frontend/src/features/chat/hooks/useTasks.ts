import { useState, useEffect, useCallback } from 'react';
import { getActiveTasks } from '@/core/api/groupChatApi';
import { wsManager } from '@/core/websocket/WebSocketManager';
import type { TaskListInfo, RefreshSignal } from '@/shared/types';

export function useTasks(chatId: string | null) {
  const [taskList, setTaskList] = useState<TaskListInfo | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!chatId) {
      setTaskList(null);
      return;
    }

    setLoading(true);
    try {
      const data = await getActiveTasks(chatId);
      setTaskList(data);
    } catch (err) {
      console.error('Failed to load tasks:', err);
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

  return { taskList, loading, refresh };
}
