/**
 * useSessionList Hook
 *
 * 职责：
 * - 获取 session 列表数据（群聊 + 单聊）
 * - 聚合为项目分组
 * - 聚合成员头像数据
 * - 监听 WebSocket 实时更新
 *
 * 架构约束：
 * - 管理副作用（API 调用、WebSocket 监听）
 * - 不包含 UI 逻辑
 */

import { useEffect, useCallback } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { storage } from '@/core/storage';
import { listGroupChatInfos, getMembers } from '@/core/api';
import { listSingleChats } from '@/core/api/singleChatApi';
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';

export function useSessionList() {
  const { projectGroups, setProjectGroups } = useSessionStore();

  const refreshSessions = useCallback(async () => {
    try {
      const [chats, singleChats, lastViewRecords] = await Promise.all([
        listGroupChatInfos(),
        listSingleChats(),
        storage.getLastViewRecords(),
      ]);

      const groups = groupSessionsByProject(chats, lastViewRecords, singleChats);

      // 为群聊加载成员头像，为单聊加载 agent 头像
      const groupChatSessionIds = groups.flatMap((g) =>
        g.sessions.filter((s) => s.type === 'group_chat').map((s) => s.id)
      );

      const roleAvatarMap = await buildRoleAvatarMap();

      if (groupChatSessionIds.length > 0) {
        const memberResults = await Promise.all(
          groupChatSessionIds.map((id) => getMembers(id).catch(() => []))
        );

        let idx = 0;
        for (const group of groups) {
          for (const session of group.sessions) {
            if (session.type === 'group_chat') {
              const members = memberResults[idx++] ?? [];
              session.memberAvatars = members
                .slice(0, 4)
                .map((m) => roleAvatarMap.get(m.name) ?? null);
              session.memberCount = members.length;
            } else if (session.type === 'single_chat' && session.agentName) {
              // 单聊：用 agent 头像作为第一个头像
              session.memberAvatars = [roleAvatarMap.get(session.agentName) ?? null];
            }
          }
        }
      } else {
        // 没有群聊时，仍需为单聊设置头像
        for (const group of groups) {
          for (const session of group.sessions) {
            if (session.type === 'single_chat' && session.agentName) {
              session.memberAvatars = [roleAvatarMap.get(session.agentName) ?? null];
            }
          }
        }
      }

      setProjectGroups(groups);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    }
  }, [setProjectGroups]);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    const handleRefresh = () => {
      refreshSessions();
    };

    wsManager.on('refresh', handleRefresh);
    return () => {
      wsManager.off('refresh', handleRefresh);
    };
  }, [refreshSessions]);

  return { projectGroups, refreshSessions };
}
