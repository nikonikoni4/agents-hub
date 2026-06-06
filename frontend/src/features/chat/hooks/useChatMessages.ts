/**
 * useChatMessages Hook
 *
 * 职责：
 * - 根据 activeSessionId 加载消息列表
 * - 提供会话标题
 * - 提供角色头像映射
 *
 * 架构约束：
 * - 管理副作用（API 调用）
 * - 通过 store 订阅 activeSessionId（不直接 import session feature）
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { getMessages } from '@/core/api/groupChatApi';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';
import type { MessageApiItem } from '@/shared/types';

// 与后端 API 默认 limit 保持一致 (routes/group_chat.py)
const PAGE_SIZE = 30;

export function useChatMessages() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const projectGroups = useSessionStore((s) => s.projectGroups);

  const [messages, setMessages] = useState<MessageApiItem[]>([]);
  const [roleAvatarMap, setRoleAvatarMap] = useState<Map<string, string | null>>(new Map());
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const loadingMoreRef = useRef(false);

  // 从 store 中查找当前 session 的标题
  const activeTitle =
    projectGroups.flatMap((g) => g.sessions).find((s) => s.id === activeSessionId)?.title ?? null;

  // 初始加载最新消息
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      setRoleAvatarMap(new Map());
      setHasMore(true);
      return;
    }

    let cancelled = false;
    setLoading(true);

    Promise.all([getMessages(activeSessionId, PAGE_SIZE, undefined), buildRoleAvatarMap()])
      .then(([msgData, avatarMap]) => {
        if (!cancelled) {
          setMessages(msgData);
          setRoleAvatarMap(avatarMap);
          setHasMore(msgData.length >= PAGE_SIZE);
        }
      })
      .catch((err) => {
        console.error('Failed to load messages:', err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeSessionId]);

  // WebSocket refresh: 当前 session 收到新消息时重新拉取
  useEffect(() => {
    if (!activeSessionId) return;

    const handleRefresh = (signal?: { group_chat_id: string }) => {
      if (signal?.group_chat_id === activeSessionId) {
        getMessages(activeSessionId, PAGE_SIZE, undefined)
          .then((msgData) => {
            setMessages(msgData);
            setHasMore(msgData.length >= PAGE_SIZE);
          })
          .catch((err) => {
            console.error('Failed to refresh messages:', err);
          });
      }
    };

    wsManager.on('refresh', handleRefresh);
    return () => {
      wsManager.off('refresh', handleRefresh);
    };
  }, [activeSessionId]);

  // 加载更多（向上滚动时调用）
  const loadMore = useCallback(async () => {
    if (!activeSessionId || !hasMore || loadingMoreRef.current || messages.length === 0) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    try {
      const cursor = messages[0]?.timestamp;
      const olderMessages = await getMessages(activeSessionId, PAGE_SIZE, cursor);
      if (olderMessages.length < PAGE_SIZE) {
        setHasMore(false);
      }
      if (olderMessages.length > 0) {
        setMessages((prev) => [...olderMessages, ...prev]);
      }
    } catch (err) {
      console.error('Failed to load more messages:', err);
    } finally {
      loadingMoreRef.current = false;
      // 注意：不在这里 setLoadingMore(false)
      // 由调用方（ChatArea handleScroll）在滚动位置恢复后再重置，
      // 避免 setMessages 和 setLoadingMore(false) 同批处理导致自动滚动到底部
    }
  }, [activeSessionId, hasMore, messages]);

  return {
    messages,
    loading,
    activeTitle,
    activeSessionId,
    roleAvatarMap,
    hasMore,
    loadingMore,
    setLoadingMore,
    loadMore,
  };
}
