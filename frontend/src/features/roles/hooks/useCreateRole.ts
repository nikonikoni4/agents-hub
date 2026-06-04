/**
 * 创建角色逻辑 hook
 */

import { useCallback, useState } from 'react';
import { useRolesStore } from '../store/rolesStore';
import { createRole } from '@/core/api/roleApi';
import { fetchRoleWithSkills } from '@/shared/adapters/roleAdapter';
import type { CreateRoleFormData } from '../types';

export function useCreateRole() {
  const [submitting, setSubmitting] = useState(false);
  const { addRole } = useRolesStore();

  const handleCreateRole = useCallback(
    async (formData: CreateRoleFormData) => {
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

        const newRole = await fetchRoleWithSkills(formData.name);
        addRole(newRole);

        return { success: true };
      } catch (err) {
        return {
          success: false,
          error: err instanceof Error ? err.message : '创建角色失败',
        };
      } finally {
        setSubmitting(false);
      }
    },
    [addRole]
  );

  return { createRole: handleCreateRole, submitting };
}
