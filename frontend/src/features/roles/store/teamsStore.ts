/**
 * 团队状态管理
 */

import { create } from 'zustand';
import type { TeamWithMembers } from '../types';

interface TeamsState {
  teams: TeamWithMembers[];
  selectedTeam: string | null;
  loading: boolean;
  error: string | null;

  setTeams: (teams: TeamWithMembers[]) => void;
  selectTeam: (name: string | null) => void;
  updateTeam: (name: string, updater: (team: TeamWithMembers) => TeamWithMembers) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useTeamsStore = create<TeamsState>((set) => ({
  teams: [],
  selectedTeam: null,
  loading: false,
  error: null,

  setTeams: (teams) => set({ teams }),
  selectTeam: (name) => set({ selectedTeam: name }),
  updateTeam: (name, updater) =>
    set((state) => ({
      teams: state.teams.map((team) => (team.name === name ? updater(team) : team)),
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({ teams: [], selectedTeam: null, loading: false, error: null }),
}));
