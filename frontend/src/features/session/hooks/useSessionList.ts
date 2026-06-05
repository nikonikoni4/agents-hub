/**
 * useSessionList Hook
 *
 * 职责：
 * - 获取 session 列表数据
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
import { storage } from '@/core/storage';
import { listGroupChatInfos, getMembers } from '@/core/api';
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';

export function useSessionList() {
  const { projectGroups, setProjectGroups } = useSessionStore();

  const refreshSessions = useCallback(async () => {
    try {
      const [chats, lastViewRecords] = await Promise.all([
        listGroupChatInfos(),
        storage.getLastViewRecords(),
      ]);

      const groups = groupSessionsByProject(chats, lastViewRecords);

      const allSessionIds = groups.flatMap((g) => g.sessions.map((s) => s.id));

      if (allSessionIds.length > 0) {
        const [roleAvatarMap, ...memberResults] = await Promise.all([
          buildRoleAvatarMap(),
          ...allSessionIds.map((id) => getMembers(id).catch(() => [])),
        ]);

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
      console.error('Failed to fetch sessions:', error);
    }
  }, [setProjectGroups]);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  return { projectGroups, refreshSessions };
}
