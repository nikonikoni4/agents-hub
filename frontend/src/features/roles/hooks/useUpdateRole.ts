/**
 * useUpdateRole Hook
 *
 * 职责：
 * - 调用 updateRole API 更新角色信息
 * - 更新本地 store 状态
 *
 * 架构约束：
 * - 管理副作用（API 调用）
 * - 不包含 UI 逻辑
 */

import { useState } from 'react';
import { updateRole } from '@/core/api';
import { useRolesStore } from '../store/rolesStore';
import { wsManager } from '@/core/websocket/WebSocketManager';
import type { UpdateRoleRequest } from '@/shared/types';

export function useUpdateRole() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { updateRole: updateRoleInStore } = useRolesStore();

  const handleUpdateRole = async (
    name: string,
    data: UpdateRoleRequest,
    onSuccess?: () => void
  ) => {
    setLoading(true);
    setError(null);

    try {
      const updatedRole = await updateRole(name, data);
      updateRoleInStore(name, updatedRole);
      wsManager.emit('refresh');
      onSuccess?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : '更新角色失败';
      setError(message);
      console.error('Failed to update role:', err);
    } finally {
      setLoading(false);
    }
  };

  return {
    updateRole: handleUpdateRole,
    loading,
    error,
  };
}
