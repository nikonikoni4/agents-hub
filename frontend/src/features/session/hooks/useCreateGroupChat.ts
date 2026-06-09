/**
 * 创建群组对话 hook
 *
 * 职责：
 * - 获取可选角色列表（区分 Leader / Worker）
 * - 获取团队列表（用于预选团队成员）
 * - 调用创建群聊 API
 */

import { useState, useEffect, useCallback } from 'react';
import { listRoles } from '@/core/api/roleApi';
import { createGroupChat } from '@/core/api/groupChatApi';
import { aggregateAllTeams } from '@/shared/adapters/teamAdapter';
import type { RoleApiResponse } from '@/shared/types/api-schemas';
import type { CreateGroupChatRequest } from '@/shared/types/api-requests';
import { useGroupChatList } from './useGroupChatList';

export interface TeamOption {
  name: string;
  members: string[];
}

export function useCreateGroupChat() {
  const [roles, setRoles] = useState<RoleApiResponse[]>([]);
  const [teams, setTeams] = useState<TeamOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const { refreshGroupChats } = useGroupChatList();

  useEffect(() => {
    let cancelled = false;
    Promise.all([listRoles(), aggregateAllTeams()]).then(([roleData, teamData]) => {
      if (!cancelled) {
        setRoles(roleData);
        setTeams(teamData.map((t) => ({ name: t.name, members: t.members })));
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const createChat = useCallback(
    async (data: CreateGroupChatRequest): Promise<string | null> => {
      setSubmitting(true);
      try {
        const result = await createGroupChat(data);
        // 创建成功后立即刷新群聊列表
        await refreshGroupChats();
        return result.group_chat_id;
      } catch (err) {
        console.error('Failed to create group chat:', err);
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    [refreshGroupChats]
  );

  const leaders = roles.filter((r) => r.type === 'leader');
  const workers = roles.filter((r) => r.type === 'team_member');

  return { roles, leaders, workers, teams, loading, submitting, createChat };
}
