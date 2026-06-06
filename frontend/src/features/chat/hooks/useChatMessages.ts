/**
 * useChatMessages Hook
 *
 * 职责：
 * - 根据 activeSessionId 加载消息列表
 * - 提供会话标题、角色头像映射
 * - 管理增量加载（loadMore）的完整生命周期，包括滚动位置恢复
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
// loadMore 完成后的冷却期（ms），防止滚动位置恢复后再次触发
const LOAD_MORE_COOLDOWN_MS = 100;

export function useChatMessages() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const projectGroups = useSessionStore((s) => s.projectGroups);

  const [messages, setMessages] = useState<MessageApiItem[]>([]);
  const [roleAvatarMap, setRoleAvatarMap] = useState<Map<string, string | null>>(new Map());
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  // 标记正在恢复滚动位置（阻止自动滚动，但不阻止新消息触发滚动）
  const [isRestoringScroll, setIsRestoringScroll] = useState(false);

  // 同步锁：防止 React 批处理期间重复调用 loadMore
  const loadingMoreRef = useRef(false);
  // 用 ref 存储 messages，避免 loadMore 因 messages 依赖频繁重建
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  // 冷却期标记，防止 loadMore 完成后立即再次触发（只阻止 loadMore，不阻止自动滚动）
  const loadMoreCooldownRef = useRef(false);
  // 待清理的异步操作
  const pendingCleanupRef = useRef<(() => void) | null>(null);

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

  // WebSocket refresh: 当前 session 收到新消息时，追加新消息（不覆盖已加载的历史）
  useEffect(() => {
    if (!activeSessionId) return;

    const handleRefresh = (signal?: { group_chat_id: string }) => {
      if (signal?.group_chat_id === activeSessionId) {
        getMessages(activeSessionId, PAGE_SIZE, undefined)
          .then((newestMessages) => {
            setMessages((prev) => {
              if (prev.length === 0) return newestMessages;
              const existingKeys = new Set(prev.map((m) => `${m.speaker}:${m.timestamp}`));
              const appended = newestMessages.filter(
                (m) => !existingKeys.has(`${m.speaker}:${m.timestamp}`)
              );
              return appended.length > 0 ? [...prev, ...appended] : prev;
            });
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

  // 内部加载方法：只负责 API 调用和状态更新，不处理滚动
  const loadMoreInternal = useCallback(async () => {
    const currentMessages = messagesRef.current;
    if (!activeSessionId || !hasMore || loadingMoreRef.current || currentMessages.length === 0) {
      return false; // 未实际加载
    }
    loadingMoreRef.current = true;
    setLoadingMore(true);
    try {
      const cursor = currentMessages[0]?.timestamp;
      const olderMessages = await getMessages(activeSessionId, PAGE_SIZE, cursor);
      if (olderMessages.length < PAGE_SIZE) {
        setHasMore(false);
      }
      if (olderMessages.length > 0) {
        setMessages((prev) => [...olderMessages, ...prev]);
      }
      return olderMessages.length > 0; // 有新消息才视为实际加载
    } finally {
      loadingMoreRef.current = false;
      setLoadingMore(false);
    }
  }, [activeSessionId, hasMore]);

  // 公开方法：加载更多并恢复滚动位置
  // 调用方只需传入容器元素，hook 内部处理防抖、状态管理、滚动恢复的完整生命周期
  const loadMoreWithRestore = useCallback(
    async (container: HTMLElement) => {
      if (loadMoreCooldownRef.current) return;
      loadMoreCooldownRef.current = true;
      setIsRestoringScroll(true);

      // 清理之前可能残留的定时器
      if (pendingCleanupRef.current) {
        pendingCleanupRef.current();
        pendingCleanupRef.current = null;
      }

      const prevHeight = container.scrollHeight;
      let rafId: number | null = null;
      let timerId: number | null = null;

      // 组合 cleanup 函数：清理 rAF 和 setTimeout
      const cleanup = () => {
        if (rafId !== null) {
          cancelAnimationFrame(rafId);
          rafId = null;
        }
        if (timerId !== null) {
          clearTimeout(timerId);
          timerId = null;
        }
        setIsRestoringScroll(false);
        loadMoreCooldownRef.current = false;
      };
      pendingCleanupRef.current = cleanup;

      try {
        const didLoad = await loadMoreInternal();
        if (didLoad) {
          // 等 DOM 更新后恢复滚动位置
          rafId = requestAnimationFrame(() => {
            rafId = null; // rAF 已执行，标记为 null
            container.scrollTop = container.scrollHeight - prevHeight;
            // 滚动恢复完成（~16ms），立即允许自动滚动
            setIsRestoringScroll(false);

            // 冷却期继续生效（防止 loadMore 重复触发）
            timerId = window.setTimeout(() => {
              timerId = null; // setTimeout 已执行，标记为 null
              loadMoreCooldownRef.current = false;
              pendingCleanupRef.current = null; // 全部完成，清空 cleanup
            }, LOAD_MORE_COOLDOWN_MS);
          });
        } else {
          cleanup();
          pendingCleanupRef.current = null;
        }
      } catch (err) {
        console.error('Failed to load more messages:', err);
        cleanup();
        pendingCleanupRef.current = null;
      }
    },
    [loadMoreInternal]
  );

  // 卸载时清理异步操作
  useEffect(() => {
    return () => {
      if (pendingCleanupRef.current) {
        pendingCleanupRef.current();
      }
    };
  }, []);

  return {
    messages,
    loading,
    activeTitle,
    activeSessionId,
    roleAvatarMap,
    hasMore,
    loadingMore,
    isRestoringScroll,
    loadMoreWithRestore,
  };
}
