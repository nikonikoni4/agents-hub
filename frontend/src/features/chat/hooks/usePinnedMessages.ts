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
    async (messageId: number) => {
      if (!chatId) return;
      try {
        const newPin = await pinMessage(chatId, { message_id: messageId });
        // 直接将返回的数据添加到 state，无需再次请求
        setPinnedMessages((prev) => [...prev, newPin]);
      } catch (err) {
        console.error('Failed to pin message:', err);
        throw err;
      }
    },
    [chatId]
  );

  // 取消置顶
  const unpin = useCallback(
    async (messageId: number) => {
      if (!chatId) return;
      try {
        await unpinMessage(chatId, { message_id: messageId });
        // 直接从 state 中移除该消息
        setPinnedMessages((prev) => prev.filter((p) => p.message_id !== messageId));
      } catch (err) {
        console.error('Failed to unpin message:', err);
        throw err;
      }
    },
    [chatId]
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
