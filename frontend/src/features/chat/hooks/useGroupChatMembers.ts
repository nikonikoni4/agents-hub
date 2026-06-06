/**
 * 群成员管理 hook
 *
 * 职责：
 * - 加载群成员列表
 * - 添加/删除群成员
 * - 监听 WebSocket refresh 信号自动刷新
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getMembers,
  addGroupChatMembers,
  removeGroupChatMember,
} from '@/core/api/groupChatApi';
import { wsManager } from '@/core/websocket/WebSocketManager';
import type { GroupChatMemberApiItem, RefreshSignal } from '@/shared/types';

export function useGroupChatMembers(chatId: string | null) {
  const [members, setMembers] = useState<GroupChatMemberApiItem[]>([]);
  const [loading, setLoading] = useState(false);

  // 刷新成员列表
  const refresh = useCallback(async () => {
    if (!chatId) {
      setMembers([]);
      return;
    }

    setLoading(true);
    try {
      const data = await getMembers(chatId);
      setMembers(data);
    } catch (err) {
      console.error('Failed to load group chat members:', err);
    } finally {
      setLoading(false);
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
      if (signal?.group_chat_id === chatId) {
        refresh();
      }
    };

    wsManager.on('refresh', handleRefresh);

    return () => {
      wsManager.off('refresh', handleRefresh);
    };
  }, [chatId, refresh]);

  // 添加成员
  const addMembers = useCallback(
    async (memberNames: string[]) => {
      if (!chatId) return;
      try {
        await addGroupChatMembers(chatId, { member_names: memberNames });
        await refresh();
      } catch (err) {
        console.error('Failed to add group chat members:', err);
        throw err;
      }
    },
    [chatId, refresh]
  );

  // 删除成员
  const removeMember = useCallback(
    async (memberName: string) => {
      if (!chatId) return;
      try {
        await removeGroupChatMember(chatId, memberName);
        await refresh();
      } catch (err) {
        console.error('Failed to remove group chat member:', err);
        throw err;
      }
    },
    [chatId, refresh]
  );

  return {
    members,
    loading,
    addMembers,
    removeMember,
    refresh,
  };
}
