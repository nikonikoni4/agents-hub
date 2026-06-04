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
import { groupSessionsByProject } from '@/shared/adapters/sessionAdapter';
import type { GroupChatInfoApiResponse } from '@/shared/types/api-schemas';

/**
 * 临时 Mock API（待实现真实 API）
 */
async function mockFetchGroupChats(): Promise<GroupChatInfoApiResponse[]> {
  // 模拟网络延迟
  await new Promise((resolve) => setTimeout(resolve, 100));

  return [
    {
      group_chat_id: 'gc1',
      group_chat_name: '需求分析会话',
      project_path: 'D:\\projects\\agents-hub',
      created_at: '2026-06-05T09:00:00Z',
      group_type: 'sequence_execute',
      is_active: true,
      last_speaker: 'Manager',
      last_message: '请开始分析用户需求',
      last_update_at: '2026-06-05T10:00:00Z',
    },
    {
      group_chat_id: 'gc2',
      group_chat_name: '代码实现会话',
      project_path: 'D:\\projects\\agents-hub',
      created_at: '2026-06-05T08:00:00Z',
      group_type: 'manager_orchestrate',
      is_active: true,
      last_speaker: 'Developer',
      last_message: '前端组件已完成',
      last_update_at: '2026-06-05T11:00:00Z',
    },
    {
      group_chat_id: 'gc3',
      group_chat_name: '测试会话',
      project_path: '/home/user/another-project',
      created_at: '2026-06-05T07:00:00Z',
      group_type: 'sequence_execute',
      is_active: false,
      last_speaker: 'Tester',
      last_message: '单元测试通过',
      last_update_at: '2026-06-05T12:00:00Z',
    },
  ];
}

export function useSessionList() {
  const { projectGroups, setProjectGroups } = useSessionStore();

  useEffect(() => {
    async function fetchSessions() {
      try {
        // 1. 并行获取数据
        const [chats, lastViewRecords] = await Promise.all([
          mockFetchGroupChats(), // TODO: 替换为真实 API
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
