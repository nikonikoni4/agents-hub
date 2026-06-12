/**
 * 创建角色逻辑 hook
 */

import { useCallback, useState } from 'react';
import { useRolesStore } from '../store/rolesStore';
import { createRole, addSkillToRole, updateRole } from '@/core/api/roleApi';
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
        // 1. 创建角色
        await createRole({
          name: formData.name,
          platform: formData.platform,
          avatar: formData.avatar,
          description: formData.description,
          type: 'team_member',
          abilities: [],
        });

        // 2. 添加技能（如果有）
        if (formData.skills.length > 0) {
          for (const skillName of formData.skills) {
            await addSkillToRole(formData.name, skillName);
          }
        }

        // 3. 更新工具配置（如果有）
        if (formData.enabled_tools.length > 0) {
          await updateRole(formData.name, {
            enabled_tools: formData.enabled_tools,
          });
        }

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
