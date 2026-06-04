/**
 * useSessionList Hook
 *
 * 职责：
 * - 获取 session 列表数据
 * - 聚合为项目分组
 * - 监听 WebSocket 实时更新
 *
 * 架构约束：
 * - 管理副作用（API 调用、WebSocket 监听）
 * - 不包含 UI 逻辑
 */

import { useEffect } from 'react';
import { useSessionStore } from '../store/sessionStore';
import { storage } from '@/core/storage';
import { listGroupChatInfos } from '@/core/api';
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';

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

        // 3. 更新 store
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
