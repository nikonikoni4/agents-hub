/**
 * usePinnedMessages Hook
 *
 * 职责：
 * - 管理置顶消息列表的加载和刷新
 * - 提供 pin/unpin 操作方法
 * - 监听 WebSocket refresh 信号自动刷新
 *
 * 架构约束：
 * - 管理副作用（API 调用、WebSocket 订阅）
 * - 不直接操作 DOM 或组件状态
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { getPinnedMessages, pinMessage, unpinMessage } from '@/core/api/groupChatApi';
import { wsManager } from '@/core/websocket/WebSocketManager';
import type { PinnedMessageInfo, RefreshSignal } from '@/shared/types';

export function usePinnedMessages(chatId: string | null) {
  const [pinnedMessages, setPinnedMessages] = useState<PinnedMessageInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // 刷新置顶消息列表
  const refresh = useCallback(async () => {
    if (!chatId) {
      setPinnedMessages([]);
      return;
    }

    setIsLoading(true);
    try {
      const data = await getPinnedMessages(chatId);
      setPinnedMessages(data);
    } catch (err) {
      console.error('Failed to load pinned messages:', err);
    } finally {
      setIsLoading(false);
    }
  }, [chatId]);

  // chatId 变化时自动加载
  useEffect(() => {
    refresh();
  }, [refresh]);

  // 监听 WebSocket refresh 信号
  useEffect(() => {
    if (!chatId) return;

    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      // 只响应当前群聊的刷新信号
      if (signal?.group_chat_id === chatId) {
        refresh();
      }
    };

    wsManager.on('refresh', handleRefresh);

    return () => {
      wsManager.off('refresh', handleRefresh);
    };
  }, [chatId, refresh]);

  // 置顶消息
  const pin = useCallback(
    async (speaker: string, timestamp: string) => {
      if (!chatId) return;
      try {
        await pinMessage(chatId, { speaker, timestamp });
        await refresh();
      } catch (err) {
        console.error('Failed to pin message:', err);
        throw err;
      }
    },
    [chatId, refresh]
  );

  // 取消置顶
  const unpin = useCallback(
    async (speaker: string, timestamp: string) => {
      if (!chatId) return;
      try {
        await unpinMessage(chatId, { speaker, timestamp });
        await refresh();
      } catch (err) {
        console.error('Failed to unpin message:', err);
        throw err;
      }
    },
    [chatId, refresh]
  );

  // 构建置顶消息查找集合
  const pinnedSet = useMemo(() => {
    return new Set(pinnedMessages.map((p) => `${p.speaker}:${p.timestamp}`));
  }, [pinnedMessages]);

  // 判断消息是否已置顶
  const isPinned = useCallback(
    (speaker: string, timestamp: string) => {
      return pinnedSet.has(`${speaker}:${timestamp}`);
    },
    [pinnedSet]
  );

  return {
    pinnedMessages,
    isLoading,
    pin,
    unpin,
    isPinned,
    refresh,
  };
}
