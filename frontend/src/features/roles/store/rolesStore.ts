/**
 * 角色状态管理
 */

import { create } from 'zustand';
import type { RoleWithSkills } from '@/shared/adapters/roleAdapter';

interface RolesState {
  roles: RoleWithSkills[];
  loading: boolean;
  error: string | null;

  setRoles: (roles: RoleWithSkills[]) => void;
  addRole: (role: RoleWithSkills) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useRolesStore = create<RolesState>((set) => ({
  roles: [],
  loading: false,
  error: null,

  setRoles: (roles) => set({ roles }),
  addRole: (role) => set((state) => ({ roles: [...state.roles, role] })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({ roles: [], loading: false, error: null }),
}));
