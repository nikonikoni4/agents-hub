/**
 * 团队列表管理 hook
 */

import { useEffect, useCallback, useRef } from 'react';
import { useTeamsStore } from '../store/teamsStore';
import { aggregateAllTeams } from '@/shared/adapters/teamAdapter';
import { aggregateRoleWithSkills } from '@/shared/adapters/roleAdapter';
import type { TeamWithMembers } from '../types';

export function useTeams() {
  const { teams, selectedTeam, loading, error, setTeams, selectTeam, setLoading, setError } =
    useTeamsStore();
  const selectedTeamRef = useRef(selectedTeam);

  // 同步 ref
  useEffect(() => {
    selectedTeamRef.current = selectedTeam;
  }, [selectedTeam]);

  const fetchTeams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const teamDataList = await aggregateAllTeams();
      // 组合 team 和 role 数据
      const teamsWithMembers: TeamWithMembers[] = await Promise.all(
        teamDataList.map(async (team) => {
          const members = await Promise.all(
            team.members.map((name) => aggregateRoleWithSkills(name))
          );
          return { name: team.name, members };
        })
      );
      setTeams(teamsWithMembers);
      if (teamsWithMembers.length > 0 && !selectedTeamRef.current) {
        selectTeam(teamsWithMembers[0]!.name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载团队失败');
    } finally {
      setLoading(false);
    }
  }, [setTeams, setLoading, setError, selectTeam]);

  const refreshTeams = useCallback(() => {
    return fetchTeams();
  }, [fetchTeams]);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  const currentTeam = teams.find((t) => t.name === selectedTeam) || null;

  return { teams, selectedTeam, currentTeam, loading, error, selectTeam, refreshTeams };
}
