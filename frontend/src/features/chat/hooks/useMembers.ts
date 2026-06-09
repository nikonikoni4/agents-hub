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

import { useState, useEffect, useCallback } from 'react';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { getMembers, listRoles, updateMemberDockerMode } from '@/core/api';
import { wsManager } from '@/core/websocket/WebSocketManager';
import type { GroupChatMemberApiItem, RoleApiResponse, RefreshSignal } from '@/shared/types';

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
  const activeSessionType = useSessionStore((s) => s.activeSessionType);

  const [members, setMembers] = useState<MemberWithRole[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchMembers = useCallback(async () => {
    // 单聊不支持成员列表，跳过 API 调用
    if (!activeSessionId || activeSessionType === 'single_chat') {
      setMembers([]);
      return;
    }

    setLoading(true);
    try {
      // 并行获取成员列表和所有角色信息（避免 N+1 查询）
      const [memberList, allRoles] = await Promise.all([getMembers(activeSessionId), listRoles()]);

      const roleMap = new Map(allRoles.map((r) => [r.name, r]));

      // 聚合数据
      const membersWithRole: MemberWithRole[] = memberList.map((member) => ({
        ...member,
        role: roleMap.get(member.name) ?? null,
        isOnline: member.main_session !== null,
      }));
      setMembers(membersWithRole);
    } catch (err) {
      console.error('Failed to load members:', err);
    } finally {
      setLoading(false);
    }
  }, [activeSessionId, activeSessionType]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  // 监听 WebSocket refresh 信号（单聊跳过）
  useEffect(() => {
    if (!activeSessionId || activeSessionType === 'single_chat') return;

    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      if (!signal?.group_chat_id || signal.group_chat_id === activeSessionId) {
        fetchMembers();
      }
    };

    wsManager.on('refresh', handleRefresh);

    return () => {
      wsManager.off('refresh', handleRefresh);
    };
  }, [activeSessionId, activeSessionType, fetchMembers]);

  const toggleDockerMode = useCallback(
    async (memberName: string) => {
      if (!activeSessionId) return;

      const currentMember = members.find((m) => m.name === memberName);
      if (!currentMember) return;

      const newValue = !currentMember.use_docker;

      // 乐观更新
      setMembers((prev) =>
        prev.map((m) => (m.name === memberName ? { ...m, use_docker: newValue } : m))
      );

      try {
        await updateMemberDockerMode(activeSessionId, memberName, newValue);
      } catch (error) {
        console.error('Failed to toggle docker mode:', error);
        // 失败时回滚
        await fetchMembers();
        throw error;
      }
    },
    [activeSessionId, members, fetchMembers]
  );

  return { members, loading, refresh: fetchMembers, toggleDockerMode };
}
