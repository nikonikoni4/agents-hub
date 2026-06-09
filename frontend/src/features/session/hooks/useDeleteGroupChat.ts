/**
 * 删除群聊 hook
 *
 * 职责：
 * - 提供删除群聊功能
 * - 乐观更新本地状态
 * - 失败时回滚或重新加载
 */

import { useCallback, useState } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { deleteGroupChat } from '@/core/api/groupChatApi';
import { useGroupChatList } from './useGroupChatList';

export function useDeleteGroupChat() {
  const { projectGroups, setProjectGroups } = useSessionStore();
  const { refreshGroupChats } = useGroupChatList();
  const [deleting, setDeleting] = useState(false);

  const deleteChat = useCallback(
    async (chatId: string, keepData: boolean = false): Promise<void> => {
      setDeleting(true);

      // 1. 乐观更新：立即从列表移除
      const updatedGroups = projectGroups
        .map((group) => ({
          ...group,
          sessions: group.sessions.filter((s) => s.id !== chatId),
        }))
        .filter((group) => group.sessions.length > 0);

      setProjectGroups(updatedGroups);

      // 2. 调用 API
      try {
        await deleteGroupChat(chatId, keepData);
      } catch (error) {
        // 3. 失败时重新加载列表（回滚）
        await refreshGroupChats();
        throw error;
      } finally {
        setDeleting(false);
      }
    },
    [projectGroups, setProjectGroups, refreshGroupChats]
  );

  return { deleteChat, deleting };
}
