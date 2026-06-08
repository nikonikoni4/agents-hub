/**
 * 团队成员管理 hook
 */

import { useCallback, useState } from 'react';
import { useTeamsStore } from '../store/teamsStore';
import { updateTeam, getTeam } from '@/core/api/teamApi';
import { aggregateRoleWithSkills } from '@/shared/adapters/roleAdapter';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { useToast } from '@/shared/components';
import type { TeamWithMembers } from '../types';

export function useTeamMembers() {
  const [submitting, setSubmitting] = useState(false);
  const { updateTeam: updateTeamInStore } = useTeamsStore();
  const toast = useToast();

  const fetchTeamWithMembers = useCallback(async (teamName: string): Promise<TeamWithMembers> => {
    const team = await getTeam(teamName);
    const members = await Promise.all(team.members.map((name) => aggregateRoleWithSkills(name)));
    return { name: team.name, members };
  }, []);

  const addMembersToTeam = useCallback(
    async (teamName: string, roleNames: string[]) => {
      setSubmitting(true);
      try {
        const team = await fetchTeamWithMembers(teamName);
        const existingMembers = team.members.map((m) => m.name);
        const newMembers = [...new Set([...existingMembers, ...roleNames])];

        await updateTeam(teamName, { members: newMembers });

        const updatedTeam = await fetchTeamWithMembers(teamName);
        updateTeamInStore(teamName, () => updatedTeam);
        wsManager.emit('refresh');
        toast.success('成员添加成功');
      } catch (err) {
        toast.error(err instanceof Error ? err.message : '添加成员失败');
      } finally {
        setSubmitting(false);
      }
    },
    [updateTeamInStore, fetchTeamWithMembers, toast]
  );

  const removeMemberFromTeam = useCallback(
    async (teamName: string, roleName: string) => {
      setSubmitting(true);
      try {
        const team = await fetchTeamWithMembers(teamName);
        const newMembers = team.members.filter((m) => m.name !== roleName).map((m) => m.name);

        await updateTeam(teamName, { members: newMembers });

        const updatedTeam = await fetchTeamWithMembers(teamName);
        updateTeamInStore(teamName, () => updatedTeam);
        wsManager.emit('refresh');
        toast.success('成员已移除');
      } catch (err) {
        toast.error(err instanceof Error ? err.message : '移除成员失败');
      } finally {
        setSubmitting(false);
      }
    },
    [updateTeamInStore, fetchTeamWithMembers, toast]
  );

  return { addMembersToTeam, removeMemberFromTeam, submitting };
}
