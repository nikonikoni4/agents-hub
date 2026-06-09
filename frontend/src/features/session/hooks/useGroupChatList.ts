import { useEffect, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { storage } from '@/core/storage';
import { listGroupChatInfos, getMembers } from '@/core/api';
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';
import type { RefreshSignal } from '@/shared/types';

export function useGroupChatList() {
  const { projectGroups, setProjectGroups } = useSessionStore();
  const activeSessionId = useSessionStore((s) => s.activeSessionId);

  const refreshGroupChats = useCallback(async () => {
    try {
      const [chats, lastViewRecords] = await Promise.all([
        listGroupChatInfos(),
        storage.getLastViewRecords(),
      ]);

      // 只传群聊数据，不传单聊
      const groups = groupSessionsByProject(chats, lastViewRecords, []);

      // 加载成员头像
      const groupChatSessionIds = groups.flatMap((g) =>
        g.sessions.map((s) => s.id)
      );

      const roleAvatarMap = await buildRoleAvatarMap();

      if (groupChatSessionIds.length > 0) {
        const memberResults = await Promise.all(
          groupChatSessionIds.map((id) => getMembers(id).catch(() => []))
        );

        let idx = 0;
        for (const group of groups) {
          for (const session of group.sessions) {
            const members = memberResults[idx++] ?? [];
            session.memberAvatars = members
              .slice(0, 4)
              .map((m) => roleAvatarMap.get(m.name) ?? null);
            session.memberCount = members.length;
          }
        }
      }

      setProjectGroups(groups);
    } catch (error) {
      console.error('Failed to fetch group chats:', error);
    }
  }, [setProjectGroups]);

  useEffect(() => {
    refreshGroupChats();
  }, [refreshGroupChats]);

  useEffect(() => {
    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      if (!signal?.group_chat_id || signal.group_chat_id === activeSessionId) {
        refreshGroupChats();
      }
    };
    wsManager.on('refresh', handleRefresh);
    return () => { wsManager.off('refresh', handleRefresh); };
  }, [refreshGroupChats, activeSessionId]);

  return { projectGroups, refreshGroupChats };
}
