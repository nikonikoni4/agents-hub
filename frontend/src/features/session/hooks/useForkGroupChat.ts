/**
 * Fork 群聊 hook
 *
 * 职责：
 * - 提供 fork 群聊功能
 * - 处理 loading、error 状态
 * - 成功后触发会话列表刷新
 */

import { useCallback, useState } from 'react';
import { forkGroupChat } from '@/core/api/groupChatApi';
import { useGroupChatList } from './useGroupChatList';

export function useForkGroupChat() {
  const { refreshGroupChats } = useGroupChatList();
  const [forking, setForking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const forkChat = useCallback(
    async (chatId: string, name: string): Promise<string> => {
      setForking(true);
      setError(null);

      try {
        const result = await forkGroupChat(chatId, name);
        // 刷新会话列表
        refreshGroupChats();
        return result.group_chat_id;
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Fork 失败';
        setError(message);
        throw err;
      } finally {
        setForking(false);
      }
    },
    [refreshGroupChats]
  );

  return { forkChat, forking, error };
}
