/**
 * 创建对话所需数据 hook
 *
 * 职责：
 * - 获取所有角色（单聊全新模式 / 群聊选成员）
 * - 获取群聊列表（单聊群组模式）
 *
 * 纯数据获取，不依赖任何 feature store。
 */

import { useState, useEffect, useCallback } from 'react';
import { listRoles } from '@/core/api/roleApi';
import { listGroupChatInfos } from '@/core/api/groupChatApi';
import type { RoleApiResponse, GroupChatInfoApiResponse } from '@/shared/types';

export function useCreateChatData(isOpen: boolean) {
  const [roles, setRoles] = useState<RoleApiResponse[]>([]);
  const [groupChats, setGroupChats] = useState<GroupChatInfoApiResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [roleData, chatData] = await Promise.all([listRoles(), listGroupChatInfos()]);
      setRoles(roleData);
      setGroupChats(chatData);
    } catch (err) {
      console.error('Failed to refresh chat data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setLoading(true);
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
  }, [isOpen]);

  return { roles, groupChats, loading, refresh };
}
