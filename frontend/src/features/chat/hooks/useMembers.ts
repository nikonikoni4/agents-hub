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

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { getMembers, listRoles, updateMemberDockerMode, compressAgentContext } from '@/core/api';
import { useCompressStatusStore } from '@/features/chat/store/compressStatusStore';
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
  /** 是否正在压缩上下文（前端本地计算） */
  compressing: boolean;
}

export function useMembers() {
  const activeSessionId = useSessionStore((s) => s.activeSessionId);

  const [members, setMembers] = useState<MemberWithRole[]>([]);
  const [loading, setLoading] = useState(false);
  // 从全局 store 读取压缩状态，不再用本地 useState
  const pendingAgents = useCompressStatusStore((s) => s.pendingAgents);

  const fetchMembers = useCallback(async () => {
    if (!activeSessionId) {
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
        compressing: false,
      }));
      setMembers(membersWithRole);
    } catch (err) {
      console.error('Failed to load members:', err);
    } finally {
      setLoading(false);
    }
  }, [activeSessionId]);

  useEffect(() => {
    fetchMembers();
  }, [fetchMembers]);

  // 监听 WebSocket refresh 信号
  useEffect(() => {
    if (!activeSessionId) return;

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
  }, [activeSessionId, fetchMembers]);

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

  const compressAgent = useCallback(
    async (agentName: string) => {
      if (!activeSessionId) return;

      console.log('[useMembers] compressAgent START:', agentName);
      // 标记开始压缩
      useCompressStatusStore.getState().startCompress(agentName);

      try {
        await compressAgentContext(activeSessionId, agentName);
        console.log('[useMembers] compressAgent API SUCCESS:', agentName);
        // 压缩成功后刷新成员列表（后端会广播 refresh，但主动刷新更可靠）
        await fetchMembers();
      } catch (error) {
        console.error('[useMembers] compressAgent ERROR:', agentName, error);
        throw error;
      } finally {
        // 标记压缩结束
        console.log('[useMembers] compressAgent FINISH:', agentName);
        useCompressStatusStore.getState().finishCompress(agentName);
      }
    },
    [activeSessionId, fetchMembers]
  );

  // 合并 compressing 状态到 members
  const membersWithCompressing = useMemo(() => {
    const result = members.map((m) => ({
      ...m,
      compressing: pendingAgents.has(m.name)
    }));
    console.log('[useMembers] membersWithCompressing:', result.map(m => ({ name: m.name, compressing: m.compressing })));
    console.log('[useMembers] pendingAgents:', Array.from(pendingAgents));
    return result;
  }, [members, pendingAgents]);

  return {
    members: membersWithCompressing,
    loading,
    refresh: fetchMembers,
    toggleDockerMode,
    compressAgent,
  };
}
