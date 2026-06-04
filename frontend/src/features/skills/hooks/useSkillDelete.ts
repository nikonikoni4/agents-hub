/**
 * 删除技能 Hook
 */

import { useState } from 'react';
import { deleteSkill } from '@/core/api/skillApi';

/**
 * 删除技能
 */
export function useSkillDelete() {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async (skillName: string, onSuccess?: () => void) => {
    const confirmed = window.confirm(`确定要删除技能 "${skillName}" 吗？`);
    if (!confirmed) return;

    setDeleting(true);
    try {
      await deleteSkill(skillName);
      onSuccess?.();
    } catch (error) {
      console.error('删除技能失败:', error);
      alert('删除失败，请稍后重试');
    } finally {
      setDeleting(false);
    }
  };

  return { handleDelete, deleting };
}
