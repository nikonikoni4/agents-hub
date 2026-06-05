/**
 * 角色技能管理 hook
 *
 * 职责：
 * - 获取指定角色的技能列表
 * - 添加技能到角色
 * - 从角色移除技能
 */

import { useState, useEffect, useCallback } from 'react';
import { getRoleSkills, addSkillToRole, removeSkillFromRole } from '@/core/api';
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
      const data = await getRoleSkills(roleName);
      setSkills(data);
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
        const newSkill = await addSkillToRole(roleName, skillId);
        setSkills((prev) => [...prev, newSkill]);
        // 同步更新 rolesStore 中的 role 数据
        updateRoleInStore(roleName, { skills: [...skills, newSkill] });
      } catch (err) {
        setError(err instanceof Error ? err.message : '添加技能失败');
        throw err;
      }
    },
    [roleName, skills, updateRoleInStore]
  );

  const removeSkill = useCallback(
    async (skillId: string) => {
      if (!roleName) return;

      try {
        await removeSkillFromRole(roleName, skillId);
        const updatedSkills = skills.filter((s) => s.id !== skillId);
        setSkills(updatedSkills);
        // 同步更新 rolesStore 中的 role 数据
        updateRoleInStore(roleName, { skills: updatedSkills });
      } catch (err) {
        setError(err instanceof Error ? err.message : '移除技能失败');
        throw err;
      }
    },
    [roleName, skills, updateRoleInStore]
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
