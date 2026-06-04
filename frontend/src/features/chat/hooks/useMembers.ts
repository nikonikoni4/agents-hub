/**
 * useMembers Hook
 *
 * 职责：
 * - 根据 activeSessionId 加载成员列表
 * - 聚合 GroupChatMember 和 Role 信息
 *
 * 架构约束：
 * - 管理副作用（API 调用）
 * - 通过 store 订阅 activeSessionId（不直接 import session feature）
 */

import { useState, useEffect } from 'react';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { getMembers, getRoleInfo } from '@/core/api';
import type { GroupChatMemberApiItem, RoleApiResponse } from '@/shared/types';

/**
 * 成员完整信息（聚合 Member + Role）
 */
export interface MemberWithRole extends GroupChatMemberApiItem {
  /** 角色详细信息 */
  role: RoleApiResponse | null;
  /** 是否在线（有 main_session） */
  isOnline: boolean;
}

export function useMembers() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);

  const [members, setMembers] = useState<MemberWithRole[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeSessionId) {
      setMembers([]);
      return;
    }

    let cancelled = false;
    setLoading(true);

    async function fetchMembers() {
      try {
        // 1. 获取成员列表
        const memberList = await getMembers(activeSessionId!);

        // 2. 并行获取所有角色信息
        const rolePromises = memberList.map(
          (m) => getRoleInfo(m.name).catch(() => null) // 角色不存在时返回 null
        );
        const roles = await Promise.all(rolePromises);

        // 3. 聚合数据
        if (!cancelled) {
          const membersWithRole: MemberWithRole[] = memberList.map((member, index) => ({
            ...member,
            role: roles[index] ?? null,
            isOnline: member.main_session !== null,
          }));
          setMembers(membersWithRole);
        }
      } catch (err) {
        console.error('Failed to load members:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchMembers();

    return () => {
      cancelled = true;
    };
  }, [activeSessionId]);

  return { members, loading };
}
