/**
 * 创建群组对话 hook
 *
 * 职责：
 * - 获取可选角色列表（区分 Leader / Worker）
 * - 调用创建群聊 API
 */

import { useState, useEffect, useCallback } from 'react';
import { listRoles } from '@/core/api/roleApi';
import { createGroupChat } from '@/core/api/groupChatApi';
import type { RoleApiResponse } from '@/shared/types/api-schemas';
import type { CreateGroupChatRequest } from '@/shared/types/api-requests';

export function useCreateGroupChat() {
  const [roles, setRoles] = useState<RoleApiResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listRoles().then((data) => {
      if (!cancelled) {
        setRoles(data);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const createChat = useCallback(async (data: CreateGroupChatRequest): Promise<string | null> => {
    setSubmitting(true);
    try {
      const result = await createGroupChat(data);
      return result.group_chat_id;
    } catch (err) {
      console.error('Failed to create group chat:', err);
      return null;
    } finally {
      setSubmitting(false);
    }
  }, []);

  const leaders = roles.filter((r) => r.type === 'leader');
  const workers = roles.filter((r) => r.type === 'team_member');

  return { roles, leaders, workers, loading, submitting, createChat };
}
