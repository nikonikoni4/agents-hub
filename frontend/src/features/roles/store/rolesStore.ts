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
  updateRole: (name: string, updates: Partial<RoleWithSkills>) => void;
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
  updateRole: (name, updates) =>
    set((state) => ({
      roles: state.roles.map((r) => (r.name === name ? { ...r, ...updates } : r)),
    })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  reset: () => set({ roles: [], loading: false, error: null }),
}));
