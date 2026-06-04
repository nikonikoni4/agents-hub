/**
 * 创建角色弹窗组件
 */

import { useState } from 'react';
import { AvatarSelector } from './AvatarSelector';
import { useCreateRole } from '../hooks/useCreateRole';
import type { CreateRoleFormData } from '../types';
import type { AgentPlatform } from '@/shared/types/api-schemas';
import styles from './CreateRoleDialog.module.css';

export interface CreateRoleDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateRoleDialog({ isOpen, onClose, onSuccess }: CreateRoleDialogProps) {
  const [formData, setFormData] = useState<CreateRoleFormData>({
    name: '',
    platform: 'claude',
    avatar: null,
    description: '',
  });

  const { createRole, submitting } = useCreateRole();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      alert('请输入角色名称');
      return;
    }

    const result = await createRole(formData);

    if (result.success) {
      onSuccess?.();
      handleClose();
    } else {
      alert(result.error || '创建失败');
    }
  };

  const handleClose = () => {
    setFormData({ name: '', platform: 'claude', avatar: null, description: '' });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>创建角色</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label htmlFor="role-name">角色名称 *</label>
            <input
              id="role-name"
              type="text"
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="输入角色名称"
              required
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="role-platform">平台 *</label>
            <select
              id="role-platform"
              value={formData.platform}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, platform: e.target.value as AgentPlatform }))
              }
            >
              <option value="claude">Claude</option>
              <option value="codex">Codex</option>
            </select>
          </div>

          <div className={styles.field}>
            <label>头像</label>
            <AvatarSelector
              selectedAvatar={formData.avatar}
              onSelect={(avatar) => setFormData((prev) => ({ ...prev, avatar }))}
            />
          </div>

          <div className={styles.field}>
            <label>角色类型</label>
            <div className={styles.typeBadge}>team_member</div>
            <p className={styles.typeHint}>当前版本角色类型固定为 team_member</p>
          </div>

          <div className={styles.field}>
            <label htmlFor="role-description">角色描述</label>
            <textarea
              id="role-description"
              value={formData.description}
              onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="输入角色描述（可选）"
              rows={3}
            />
          </div>

          <div className={styles.field}>
            <label>技能列表</label>
            <div className={styles.skillPlaceholder}>技能配置功能开发中...</div>
          </div>

          <div className={styles.actions}>
            <button type="button" onClick={handleClose} className={styles.cancelBtn}>
              取消
            </button>
            <button type="submit" className={styles.submitBtn} disabled={submitting}>
              {submitting ? '创建中...' : '创建'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
