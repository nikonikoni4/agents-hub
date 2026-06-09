/**
 * useTeamManagement Hook
 *
 * 职责：
 * - 获取团队列表
 * - 创建/删除团队
 * - 获取可选角色列表
 */

import { useState, useEffect, useCallback } from 'react';
import { listTeams, createTeam, deleteTeam } from '@/core/api/teamApi';
import { listRoles } from '@/core/api/roleApi';
import type { TeamApiResponse, RoleApiResponse } from '@/shared/types';

export function useTeamManagement() {
  const [teams, setTeams] = useState<TeamApiResponse[]>([]);
  const [roles, setRoles] = useState<RoleApiResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [teamsData, rolesData] = await Promise.all([listTeams(), listRoles()]);
      setTeams(teamsData);
      setRoles(rolesData);
    } catch (err) {
      console.error('Failed to load teams/roles:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleCreateTeam = useCallback(
    async (name: string, members: string[]): Promise<boolean> => {
      setSubmitting(true);
      try {
        await createTeam({ name, members });
        await refresh();
        return true;
      } catch (err) {
        console.error('Failed to create team:', err);
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [refresh]
  );

  const handleDeleteTeam = useCallback(async (name: string): Promise<boolean> => {
    try {
      await deleteTeam(name);
      setTeams((prev) => prev.filter((t) => t.name !== name));
      return true;
    } catch (err) {
      console.error('Failed to delete team:', err);
      return false;
    }
  }, []);

  return { teams, roles, loading, submitting, handleCreateTeam, handleDeleteTeam, refresh };
}
