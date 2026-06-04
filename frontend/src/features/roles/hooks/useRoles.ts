/**
 * 角色列表管理 hook
 */

import { useEffect, useCallback } from 'react';
import { useRolesStore } from '../store/rolesStore';
import { aggregateAllRolesWithSkills } from '@/shared/adapters/roleAdapter';

export function useRoles() {
  const { roles, loading, error, setRoles, setLoading, setError } = useRolesStore();

  const fetchRoles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await aggregateAllRolesWithSkills();
      setRoles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载角色失败');
    } finally {
      setLoading(false);
    }
  }, [setRoles, setLoading, setError]);

  const refreshRoles = useCallback(() => {
    return fetchRoles();
  }, [fetchRoles]);

  useEffect(() => {
    fetchRoles();
  }, [fetchRoles]);

  return { roles, loading, error, refreshRoles };
}
