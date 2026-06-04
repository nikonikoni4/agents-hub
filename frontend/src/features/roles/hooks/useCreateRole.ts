/**
 * 创建角色逻辑 hook
 */

import { useCallback, useState } from 'react';
import { useRolesStore } from '../store/rolesStore';
import { createRole } from '@/core/api/roleApi';
import { aggregateRoleWithSkills } from '@/shared/adapters/roleAdapter';
import { useToast } from '@/shared/components';
import type { CreateRoleFormData } from '../types';

export function useCreateRole() {
  const [submitting, setSubmitting] = useState(false);
  const { addRole } = useRolesStore();
  const toast = useToast();

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
        toast.success('角色创建成功');
        return true;
      } catch (err) {
        toast.error(err instanceof Error ? err.message : '创建角色失败');
        return false;
      } finally {
        setSubmitting(false);
      }
    },
    [addRole, toast]
  );

  return { createRole: handleCreateRole, submitting };
}
