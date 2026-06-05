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

import { useEffect } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { storage } from '@/core/storage';
import { listGroupChatInfos, getMembers } from '@/core/api';
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';
import { buildRoleAvatarMap } from '@/shared/adapters/roleAvatarAdapter';

export function useSessionList() {
  const { projectGroups, setProjectGroups } = useSessionStore();

  useEffect(() => {
    async function fetchSessions() {
      try {
        // 1. 并行获取数据
        const [chats, lastViewRecords] = await Promise.all([
          listGroupChatInfos(),
          storage.getLastViewRecords(),
        ]);

        // 2. 聚合数据
        const groups = groupSessionsByProject(chats, lastViewRecords);

        // 3. 聚合成员头像
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

        // 4. 更新 store
        setProjectGroups(groups);
      } catch (error) {
        console.error('Failed to fetch sessions:', error);
      }
    }

    fetchSessions();

    // TODO: 监听 WebSocket 更新
    // const unsubscribe = wsManager.on('message', (data) => {
    //   if (data.type === 'chat_updated') {
    //     fetchSessions(); // 简化实现：重新获取全部
    //   }
    // });
    // return unsubscribe;
  }, [setProjectGroups]);

  return { projectGroups };
}
