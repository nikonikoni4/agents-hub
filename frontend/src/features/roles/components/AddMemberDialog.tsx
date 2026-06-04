/**
 * 添加成员弹窗组件
 */

import { useState } from 'react';
import { CreateRoleDialog } from './CreateRoleDialog';
import { useRoles } from '../hooks/useRoles';
import { useTeamMembers } from '../hooks/useTeamMembers';
import type { AddMemberMode } from '../types';
import styles from './AddMemberDialog.module.css';

export interface AddMemberDialogProps {
  isOpen: boolean;
  teamName: string | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AddMemberDialog({ isOpen, teamName, onClose, onSuccess }: AddMemberDialogProps) {
  const [mode, setMode] = useState<AddMemberMode>('existing');
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const { roles } = useRoles();
  const { addMembersToTeam, submitting } = useTeamMembers();

  const handleSubmit = async () => {
    if (!teamName || selectedRoles.length === 0) {
      return;
    }

    await addMembersToTeam(teamName, selectedRoles);
    onSuccess?.();
    handleClose();
  };

  const handleClose = () => {
    setMode('existing');
    setSelectedRoles([]);
    onClose();
  };

  const handleCreateSuccess = async (newRoleName?: string) => {
    setShowCreateDialog(false);
    // 自动将新创建的角色添加到团队
    if (teamName && newRoleName) {
      await addMembersToTeam(teamName, [newRoleName]);
      onSuccess?.();
    }
  };

  const toggleRole = (roleName: string) => {
    setSelectedRoles((prev) =>
      prev.includes(roleName) ? prev.filter((r) => r !== roleName) : [...prev, roleName]
    );
  };

  if (!isOpen) return null;

  return (
    <>
      <div className={styles.overlay} onClick={handleClose}>
        <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
          <div className={styles.header}>
            <h2>添加成员</h2>
            <button type="button" className={styles.closeBtn} onClick={handleClose}>
              ×
            </button>
          </div>

          <div className={styles.content}>
            <div className={styles.modeSelector}>
              <button
                type="button"
                className={`${styles.modeBtn} ${mode === 'existing' ? styles.active : ''}`}
                onClick={() => setMode('existing')}
              >
                添加现有角色
              </button>
              <button
                type="button"
                className={`${styles.modeBtn} ${mode === 'create' ? styles.active : ''}`}
                onClick={() => setMode('create')}
              >
                创建新角色
              </button>
            </div>

            {mode === 'existing' ? (
              <div className={styles.roleList}>
                {roles.map((role) => (
                  <label key={role.name} className={styles.roleItem}>
                    <input
                      type="checkbox"
                      checked={selectedRoles.includes(role.name)}
                      onChange={() => toggleRole(role.name)}
                    />
                    <div className={styles.roleInfo}>
                      <span className={styles.roleName}>{role.name}</span>
                      <span className={styles.roleDesc}>{role.description || '无描述'}</span>
                    </div>
                  </label>
                ))}
              </div>
            ) : (
              <div className={styles.createPrompt}>
                <p>点击下方按钮创建新角色，创建完成后将自动添加到团队</p>
                <button
                  type="button"
                  className={styles.createBtn}
                  onClick={() => setShowCreateDialog(true)}
                >
                  创建角色
                </button>
              </div>
            )}
          </div>

          <div className={styles.actions}>
            <button type="button" onClick={handleClose} className={styles.cancelBtn}>
              取消
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              className={styles.submitBtn}
              disabled={submitting || selectedRoles.length === 0}
            >
              {submitting ? '添加中...' : '添加'}
            </button>
          </div>
        </div>
      </div>

      <CreateRoleDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={handleCreateSuccess}
      />
    </>
  );
}
