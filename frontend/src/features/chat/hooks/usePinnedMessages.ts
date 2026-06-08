/**
 * usePinnedMessages Hook
 *
 * 职责：
 * - 管理置顶消息列表的加载和刷新
 * - 提供 pin/unpin 操作方法
 * - 监听 WebSocket refresh 信号自动刷新
 *
 * 架构约束：
 * - 状态存储在 pinnedMessagesStore 中，所有调用方共享同一份数据
 * - 管理副作用（API 调用、WebSocket 订阅）
 */

import { useEffect, useCallback, useMemo } from 'react';
import { getPinnedMessages, pinMessage, unpinMessage } from '@/core/api/groupChatApi';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { usePinnedMessagesStore } from '../store/pinnedMessagesStore';
import type { RefreshSignal } from '@/shared/types';

export function usePinnedMessages(chatId: string | null) {
  const pinnedMessages = usePinnedMessagesStore((s) => s.pinnedMessages);
  const isLoading = usePinnedMessagesStore((s) => s.isLoading);
  const setChatId = usePinnedMessagesStore((s) => s.setChatId);
  const setPinnedMessages = usePinnedMessagesStore((s) => s.setPinnedMessages);
  const setIsLoading = usePinnedMessagesStore((s) => s.setIsLoading);

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
  }, [chatId, setPinnedMessages, setIsLoading]);

  // chatId 变化时自动加载
  useEffect(() => {
    setChatId(chatId);
    refresh();
  }, [chatId, setChatId, refresh]);

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
    async (messageId: number) => {
      if (!chatId) return;
      try {
        await pinMessage(chatId, { message_id: messageId });
        // 刷新列表：写入 store，所有使用此 hook 的组件都会更新
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
    async (messageId: number) => {
      if (!chatId) return;
      try {
        await unpinMessage(chatId, { message_id: messageId });
        // 刷新列表：写入 store，所有使用此 hook 的组件都会更新
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
    return new Set(pinnedMessages.map((p) => p.message_id));
  }, [pinnedMessages]);

  // 判断消息是否已置顶
  const isPinned = useCallback(
    (messageId: number) => {
      return pinnedSet.has(messageId);
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
