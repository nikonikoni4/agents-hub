/**
 * 获取群聊成员（含角色信息）hook
 *
 * 职责：
 * - 根据 groupChatId 获取该群聊的成员列表
 * - 关联角色信息（头像、类型等）
 *
 * 复用场景：单聊创建弹窗的"群组"模式、成员管理等
 */

import { useState, useEffect } from 'react';
import { getMembers } from '@/core/api/groupChatApi';
import { listRoles } from '@/core/api/roleApi';
import type { GroupChatMemberApiItem, RoleApiResponse } from '@/shared/types';

export interface MemberWithRole extends GroupChatMemberApiItem {
  role: RoleApiResponse | null;
}

export function useGroupChatMembers(groupChatId: string | null) {
  const [members, setMembers] = useState<MemberWithRole[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!groupChatId) {
      setMembers([]);
      return;
    }

    let cancelled = false;
    setLoading(true);

    Promise.all([getMembers(groupChatId), listRoles()]).then(([memberData, roleData]) => {
      if (cancelled) return;
      const roleMap = new Map(roleData.map((r) => [r.name, r]));
      const enriched: MemberWithRole[] = memberData.map((m) => ({
        ...m,
        role: roleMap.get(m.name) ?? null,
      }));
      setMembers(enriched);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [groupChatId]);

  return { members, loading };
}
