/**
 * 导航处理 hook
 *
 * 职责：
 * - 处理群聊跳转
 * - 处理单聊创建（打开 draft 面板）
 */

import { useCallback } from 'react';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { useSingleChatStore } from '../store/singleChatStore';
import type {
  NavigationMark,
  GroupChatNavigationData,
  CreateSingleChatNavigationData,
} from '@/shared/utils/navigationParser';

export function useNavigationHandler() {
  const selectGroupChat = useSessionStore((s) => s.selectGroupChat);
  const openDraftChat = useSingleChatStore((s) => s.openDraftChat);

  const handleNavigation = useCallback(
    (navigation: NavigationMark) => {
      if (navigation.type === 'group_chat') {
        const { group_chat_id } = navigation.data as GroupChatNavigationData;
        selectGroupChat(group_chat_id);
      } else if (navigation.type === 'create_single_chat') {
        const { agent_name, description } = navigation.data as CreateSingleChatNavigationData;
        openDraftChat({
          agent_name,
          single_chat_name: description || agent_name,
          type: 'new',
        });
      }
    },
    [selectGroupChat, openDraftChat]
  );

  return { handleNavigation };
}
