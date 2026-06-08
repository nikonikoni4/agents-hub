/**
 * 导航处理 hook
 *
 * 职责：
 * - 处理群聊跳转
 * - 处理单聊创建
 */

import { useCallback } from 'react';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { useCreateSingleChat } from './useCreateSingleChat';
import type { NavigationMark, GroupChatNavigationData, CreateSingleChatNavigationData } from '@/shared/utils/navigationParser';

export function useNavigationHandler() {
  const selectSession = useSessionStore((s) => s.selectSession);
  const { createChat } = useCreateSingleChat();

  const handleNavigation = useCallback(
    async (navigation: NavigationMark) => {
      if (navigation.type === 'group_chat') {
        const { group_chat_id } = navigation.data as GroupChatNavigationData;
        selectSession(group_chat_id);
      } else if (navigation.type === 'create_single_chat') {
        const { agent_name, description } = navigation.data as CreateSingleChatNavigationData;
        await createChat({
          type: 'new',
          agent_name,
          single_chat_name: description || agent_name,
        });
      }
    },
    [selectSession, createChat]
  );

  return { handleNavigation };
}
