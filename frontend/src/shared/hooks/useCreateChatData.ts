/**
 * 创建对话所需数据 hook
 *
 * 职责：
 * - 获取所有角色（单聊全新模式 / 群聊选成员）
 * - 获取群聊列表（单聊群组模式）
 * - 提供 createSingleChat API 调用
 *
 * 纯数据获取 + API 调用，不依赖任何 feature store。
 * 调用方负责在 onSuccess 回调中更新自己的 store。
 */

import { useState, useEffect, useCallback } from 'react';
import { listRoles } from '@/core/api/roleApi';
import { listGroupChatInfos } from '@/core/api/groupChatApi';
import { createSingleChat } from '@/core/api/singleChatApi';
import type {
  RoleApiResponse,
  GroupChatInfoApiResponse,
  CreateSingleChatRequest,
} from '@/shared/types';

export function useCreateChatData() {
  const [roles, setRoles] = useState<RoleApiResponse[]>([]);
  const [groupChats, setGroupChats] = useState<GroupChatInfoApiResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listRoles(), listGroupChatInfos()]).then(([roleData, chatData]) => {
      if (!cancelled) {
        setRoles(roleData);
        setGroupChats(chatData);
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const submitSingleChat = useCallback(
    async (
      data: CreateSingleChatRequest,
      onSuccess?: (chatId: string) => void
    ): Promise<string | null> => {
      setSubmitting(true);
      try {
        const result = await createSingleChat(data);
        onSuccess?.(result.single_chat_id);
        return result.single_chat_id;
      } catch (err) {
        console.error('Failed to create single chat:', err);
        return null;
      } finally {
        setSubmitting(false);
      }
    },
    []
  );

  return { roles, groupChats, loading, submitting, submitSingleChat };
}
