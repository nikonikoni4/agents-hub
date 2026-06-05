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
  addTeam: (team: TeamWithMembers) => void;
  removeTeam: (name: string) => void;
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
  addTeam: (team) =>
    set((state) => ({
      teams: [...state.teams, team],
      selectedTeam: state.selectedTeam ?? team.name,
    })),
  removeTeam: (name) =>
    set((state) => {
      const teams = state.teams.filter((t) => t.name !== name);
      const selectedTeam =
        state.selectedTeam === name ? (teams[0]?.name ?? null) : state.selectedTeam;
      return { teams, selectedTeam };
    }),
  updateTeam: (name, updater) =>
    set((state) => ({
      teams: state.teams.map((team) => (team.name === name ? updater(team) : team)),
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({ teams: [], selectedTeam: null, loading: false, error: null }),
}));
