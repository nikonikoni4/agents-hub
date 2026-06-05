/**
 * 团队创建/删除 hook
 */

import { useCallback, useState } from 'react';
import { createTeam, deleteTeam } from '@/core/api/teamApi';
import { aggregateRoleWithSkills } from '@/shared/adapters/roleAdapter';
import { useTeamsStore } from '../store/teamsStore';
import { useToast } from '@/shared/components';
import type { TeamWithMembers } from '../types';

export function useTeamActions() {
  const [submitting, setSubmitting] = useState(false);
  const { addTeam, removeTeam } = useTeamsStore();
  const toast = useToast();

  const handleCreateTeam = useCallback(
    async (name: string, members: string[]): Promise<boolean> => {
      setSubmitting(true);
      try {
        await createTeam({ name, members });
        const roles = await Promise.all(members.map((m) => aggregateRoleWithSkills(m)));
        const newTeam: TeamWithMembers = { name, members: roles };
        addTeam(newTeam);
        toast.success('团队创建成功');
        return true;
      } catch (err) {
        toast.error(err instanceof Error ? err.message : '创建团队失败');
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [addTeam, toast]
  );

  const handleDeleteTeam = useCallback(
    async (name: string): Promise<boolean> => {
      try {
        await deleteTeam(name);
        removeTeam(name);
        toast.success('团队已删除');
        return true;
      } catch (err) {
        toast.error(err instanceof Error ? err.message : '删除团队失败');
        return false;
      }
    },
    [removeTeam, toast]
  );

  return { handleCreateTeam, handleDeleteTeam, submitting };
}
