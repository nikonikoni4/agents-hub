/**
 * 创建团队弹窗组件
 */

import { useState } from 'react';
import { useRoles } from '../hooks/useRoles';
import { useTeamActions } from '../hooks/useTeamActions';
import styles from './CreateTeamDialog.module.css';

export interface CreateTeamDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateTeamDialog({ isOpen, onClose, onSuccess }: CreateTeamDialogProps) {
  const [name, setName] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);

  const { roles } = useRoles();
  const { handleCreateTeam, submitting } = useTeamActions();

  const handleClose = () => {
    setName('');
    setSelectedMembers([]);
    onClose();
  };

  const toggleMember = (roleName: string) => {
    setSelectedMembers((prev) =>
      prev.includes(roleName) ? prev.filter((r) => r !== roleName) : [...prev, roleName]
    );
  };

  const canSubmit = name.trim() && selectedMembers.length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    const ok = await handleCreateTeam(name.trim(), selectedMembers);
    if (ok) {
      onSuccess?.();
      handleClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>新建团队</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.field}>
            <label className={styles.label}>团队名称</label>
            <input
              type="text"
              className={styles.input}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="输入团队名称"
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label}>选择成员</label>
            {roles.length === 0 ? (
              <span className={styles.emptyHint}>暂无可用角色，请先创建角色</span>
            ) : (
              <div className={styles.roleList}>
                {roles.map((role) => (
                  <label
                    key={role.name}
                    className={`${styles.roleChip} ${selectedMembers.includes(role.name) ? styles.selected : ''}`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedMembers.includes(role.name)}
                      onChange={() => toggleMember(role.name)}
                    />
                    {role.name}
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className={styles.actions}>
          <button type="button" onClick={handleClose} className={styles.cancelBtn}>
            取消
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            className={styles.submitBtn}
            disabled={!canSubmit || submitting}
          >
            {submitting ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}
