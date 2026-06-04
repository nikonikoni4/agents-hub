/**
 * 团队列表管理 hook
 */

import { useEffect, useCallback } from 'react';
import { useTeamsStore } from '../store/teamsStore';
import { fetchAllTeamsWithMembers } from '@/shared/adapters/teamAdapter';

export function useTeams() {
  const { teams, selectedTeam, loading, error, setTeams, selectTeam, setLoading, setError } =
    useTeamsStore();

  const fetchTeams = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAllTeamsWithMembers();
      setTeams(data);
      if (data.length > 0 && !selectedTeam) {
        selectTeam(data[0]!.name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载团队失败');
    } finally {
      setLoading(false);
    }
  }, [setTeams, setLoading, setError, selectTeam, selectedTeam]);

  const refreshTeams = useCallback(() => {
    return fetchTeams();
  }, [fetchTeams]);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  const currentTeam = teams.find((t) => t.name === selectedTeam) || null;

  return { teams, selectedTeam, currentTeam, loading, error, selectTeam, refreshTeams };
}
