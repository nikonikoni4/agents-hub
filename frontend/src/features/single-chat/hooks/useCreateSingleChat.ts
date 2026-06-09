/**
 * 创建单聊 hook
 *
 * 职责：
 * - 包装 shared/useCreateChatData（数据获取）
 * - 连接 singleChatStore（状态更新 + 打开面板）
 */

import { useCallback } from 'react';
import { useCreateChatData } from '@/shared/hooks/useCreateChatData';
import { useSingleChatStore } from '../store/singleChatStore';
import type { CreateSingleChatRequest } from '@/shared/types';

export function useCreateSingleChat() {
  const { roles, groupChats, loading, submitting, submitSingleChat } = useCreateChatData();
  const addSingleChat = useSingleChatStore((s) => s.addSingleChat);
  const openSingleChat = useSingleChatStore((s) => s.openSingleChat);

  const createChat = useCallback(
    async (data: CreateSingleChatRequest): Promise<string | null> => {
      return submitSingleChat(data, (chatId) => {
        addSingleChat({
          single_chat_id: chatId,
          single_chat_name: data.single_chat_name,
          type: data.type,
          agent_name: data.agent_name,
          platform: 'claude',
          session_id: null,
          group_chat_id: data.group_chat_id ?? null,
          cwd: data.cwd ?? '',
          created_at: new Date().toISOString(),
          last_active_at: new Date().toISOString(),
        });
        openSingleChat(chatId);
      });
    },
    [submitSingleChat, addSingleChat, openSingleChat]
  );

  return { roles, groupChats, loading, submitting, createChat };
}
