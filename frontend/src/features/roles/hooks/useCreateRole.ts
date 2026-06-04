/**
 * 创建角色逻辑 hook
 */

import { useCallback, useState } from 'react';
import { useRolesStore } from '../store/rolesStore';
import { createRole } from '@/core/api/roleApi';
import { aggregateRoleWithSkills } from '@/shared/adapters/roleAdapter';
import type { CreateRoleFormData } from '../types';

export function useCreateRole() {
  const [submitting, setSubmitting] = useState(false);
  const { addRole } = useRolesStore();

  const handleCreateRole = useCallback(
    async (formData: CreateRoleFormData): Promise<boolean> => {
      setSubmitting(true);
      try {
        await createRole({
          name: formData.name,
          platform: formData.platform,
          avatar: formData.avatar,
          description: formData.description,
          type: 'team_member',
          abilities: [],
        });

        const newRole = await aggregateRoleWithSkills(formData.name);
        addRole(newRole);
        return true;
      } catch (err) {
        console.error('创建角色失败:', err);
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [addRole]
  );

  return { createRole: handleCreateRole, submitting };
}
