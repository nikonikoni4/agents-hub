/**
 * 角色技能管理 hook
 *
 * 职责：
 * - 获取指定角色的技能列表
 * - 添加技能到角色
 * - 从角色移除技能
 *
 * 增删操作后通过 getRoleInfo 刷新角色数据。
 */

import { useState, useEffect, useCallback } from 'react';
import { getRoleInfo, addSkillToRole, removeSkillFromRole } from '@/core/api';
import { useRolesStore } from '../store/rolesStore';
import type { RoleSkillApiItem } from '@/shared/types';

export function useRoleSkills(roleName: string | null) {
  const [skills, setSkills] = useState<RoleSkillApiItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { updateRole: updateRoleInStore } = useRolesStore();

  const fetchSkills = useCallback(async () => {
    if (!roleName) {
      setSkills([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const role = await getRoleInfo(roleName);
      setSkills(role.skills);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载技能失败');
    } finally {
      setLoading(false);
    }
  }, [roleName]);

  const addSkill = useCallback(
    async (skillId: string) => {
      if (!roleName) return;

      try {
        await addSkillToRole(roleName, skillId);
        const role = await getRoleInfo(roleName);
        setSkills(role.skills);
        updateRoleInStore(roleName, role);
      } catch (err) {
        setError(err instanceof Error ? err.message : '添加技能失败');
        throw err;
      }
    },
    [roleName, updateRoleInStore]
  );

  const removeSkill = useCallback(
    async (skillId: string) => {
      if (!roleName) return;

      try {
        await removeSkillFromRole(roleName, skillId);
        const role = await getRoleInfo(roleName);
        setSkills(role.skills);
        updateRoleInStore(roleName, role);
      } catch (err) {
        setError(err instanceof Error ? err.message : '移除技能失败');
        throw err;
      }
    },
    [roleName, updateRoleInStore]
  );

  useEffect(() => {
    fetchSkills();
  }, [fetchSkills]);

  return {
    skills,
    loading,
    error,
    addSkill,
    removeSkill,
    refreshSkills: fetchSkills,
  };
}
