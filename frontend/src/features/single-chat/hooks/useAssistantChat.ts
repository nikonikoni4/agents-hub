/**
 * Agents Hub 助手会话管理 hook
 *
 * 封装会话查找和 store 操作，供 AgentsHubAssistantModal 组件使用。
 * 遵循架构规则：组件只关注 UI，业务逻辑在 hooks 中。
 */

import { useCallback } from 'react';
import { useSingleChatStore } from '../store/singleChatStore';
import { findLatestAssistantChat } from '../utils/findLatestAssistantChat';

export function useAssistantChat() {
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const singleChats = useSingleChatStore((s) => s.singleChats);
  const draftChat = useSingleChatStore((s) => s.draftChat);
  const openSingleChat = useSingleChatStore((s) => s.openSingleChat);
  const openDraftChat = useSingleChatStore((s) => s.openDraftChat);
  const clearActive = useSingleChatStore((s) => s.clearActive);

  // 打开弹窗时查找最近的助手会话
  const initAssistantChat = useCallback(() => {
    // 如果已有活跃的助手会话，不需要查找
    if (activeSingleChatId) return;

    // 如果已有助手相关的 draft，不需要重新创建
    if (draftChat && draftChat.agent_name === 'Agents-Hub-Assistant') return;

    // 有非助手的 draft（如私聊），需要替换为助手会话
    const latestChat = findLatestAssistantChat(singleChats);
    if (latestChat) {
      openSingleChat(latestChat.single_chat_id);
    } else {
      openDraftChat({
        type: 'new',
        single_chat_name: 'Agents Hub 助手',
        agent_name: 'Agents-Hub-Assistant',
      });
    }
  }, [activeSingleChatId, draftChat, singleChats, openSingleChat, openDraftChat]);

  // 开始新对话
  const startNewChat = useCallback(() => {
    clearActive();
    openDraftChat({
      type: 'new',
      single_chat_name: 'Agents Hub 助手',
      agent_name: 'Agents-Hub-Assistant',
    });
  }, [clearActive, openDraftChat]);

  return {
    initAssistantChat,
    startNewChat,
  };
}
