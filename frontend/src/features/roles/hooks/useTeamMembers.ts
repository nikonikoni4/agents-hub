/**
 * 团队成员管理 hook
 */

import { useCallback, useState } from 'react';
import { useTeamsStore } from '../store/teamsStore';
import { updateTeam } from '@/core/api/teamApi';
import { fetchTeamWithMembers } from '@/shared/adapters/teamAdapter';

export function useTeamMembers() {
  const [submitting, setSubmitting] = useState(false);
  const { updateTeam: updateTeamInStore } = useTeamsStore();

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

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: err instanceof Error ? err.message : '添加成员失败',
        };
      } finally {
        setSubmitting(false);
      }
    },
    [updateTeamInStore]
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

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: err instanceof Error ? err.message : '移除成员失败',
        };
      } finally {
        setSubmitting(false);
      }
    },
    [updateTeamInStore]
  );

  return { addMembersToTeam, removeMemberFromTeam, submitting };
}
