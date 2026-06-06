/**
 * 管理群成员弹窗组件
 *
 * 功能：
 * - 显示所有可用角色列表
 * - 已选择的成员显示「已选择」
 * - 未选择的成员显示「未选择」
 * - 支持添加/删除成员
 */

import { useState } from 'react';
import { useRoles } from '@/features/roles/hooks/useRoles';
import { useGroupChatMembers } from '../hooks/useGroupChatMembers';
import styles from './ManageMembersDialog.module.css';

export interface ManageMembersDialogProps {
  isOpen: boolean;
  chatId: string | null;
  onClose: () => void;
}

export function ManageMembersDialog({ isOpen, chatId, onClose }: ManageMembersDialogProps) {
  const { roles } = useRoles();
  const { members, loading, addMembers, removeMember } = useGroupChatMembers(chatId);
  const [submitting, setSubmitting] = useState(false);

  // 已选择的成员名称集合
  const selectedMemberNames = new Set(members.map((m) => m.name));

  const handleToggleMember = async (roleName: string) => {
    if (!chatId || submitting) return;

    setSubmitting(true);
    try {
      if (selectedMemberNames.has(roleName)) {
        await removeMember(roleName);
      } else {
        await addMembers([roleName]);
      }
    } catch (err) {
      console.error('Failed to toggle member:', err);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>管理群成员</h2>
          <button type="button" className={styles.closeBtn} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          {loading ? (
            <div className={styles.loading}>加载中...</div>
          ) : (
            <div className={styles.roleList}>
              {roles.map((role) => {
                const isSelected = selectedMemberNames.has(role.name);
                return (
                  <div key={role.name} className={styles.roleItem}>
                    <div className={styles.roleInfo}>
                      <span className={styles.roleName}>{role.name}</span>
                      <span className={styles.roleDesc}>{role.description || '无描述'}</span>
                    </div>
                    <button
                      type="button"
                      className={`${styles.toggleBtn} ${isSelected ? styles.selected : ''}`}
                      onClick={() => handleToggleMember(role.name)}
                      disabled={submitting}
                    >
                      {isSelected ? '已选择' : '未选择'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className={styles.actions}>
          <button type="button" onClick={onClose} className={styles.closeActionBtn}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
