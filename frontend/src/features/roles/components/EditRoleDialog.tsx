/**
 * 编辑角色弹窗组件
 *
 * 职责：
 * - 编辑角色描述
 * - 更换角色头像
 * - 管理角色技能
 */

import { useState, useEffect } from 'react';
import { AvatarSelector } from './AvatarSelector';
import { useUpdateRole } from '../hooks/useUpdateRole';
import { useRoleSkills } from '../hooks/useRoleSkills';
import { SkillSelectorModal } from '@/shared/components';
import type { RoleWithSkills } from '@/shared/adapters/roleAdapter';
import styles from './CreateRoleDialog.module.css';

export interface EditRoleDialogProps {
  isOpen: boolean;
  role: RoleWithSkills | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export function EditRoleDialog({ isOpen, role, onClose, onSuccess }: EditRoleDialogProps) {
  const [description, setDescription] = useState('');
  const [avatar, setAvatar] = useState<string | null>(null);
  const [showSkillSelector, setShowSkillSelector] = useState(false);

  const { updateRole, loading } = useUpdateRole();
  const { skills: roleSkills, addSkill, removeSkill } = useRoleSkills(role?.name ?? null);

  // 当 role 变化时重置表单
  useEffect(() => {
    if (role) {
      setDescription(role.description ?? '');
      setAvatar(role.avatar);
    }
  }, [role]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!role) return;

    await updateRole(role.name, { description, avatar }, () => {
      onSuccess?.();
      onClose();
    });
  };

  const handleAddSkill = async (skill: { name: string }) => {
    try {
      await addSkill(skill.name);
    } catch (err) {
      console.error('Failed to add skill:', err);
    }
  };

  const handleRemoveSkill = async (skillId: string) => {
    try {
      await removeSkill(skillId);
    } catch (err) {
      console.error('Failed to remove skill:', err);
    }
  };

  const handleClose = () => {
    setDescription('');
    setAvatar(null);
    setShowSkillSelector(false);
    onClose();
  };

  if (!isOpen || !role) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>编辑角色</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.field}>
            <label>角色名称</label>
            <div className={styles.typeBadge}>{role.name}</div>
          </div>

          <div className={styles.field}>
            <label>头像</label>
            <AvatarSelector selectedAvatar={avatar} onSelect={setAvatar} />
          </div>

          <div className={styles.field}>
            <label htmlFor="edit-description">角色描述</label>
            <textarea
              id="edit-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="输入角色描述（可选）"
              rows={3}
            />
          </div>

          <div className={styles.field}>
            <label>技能列表</label>
            <div className={styles.skillsContainer}>
              {roleSkills.length > 0 ? (
                <div className={styles.skillsList}>
                  {roleSkills.map((skill) => (
                    <div key={skill.id} className={styles.skillItem}>
                      <span className={styles.skillName}>{skill.name}</span>
                      <button
                        type="button"
                        className={styles.removeSkillBtn}
                        onClick={() => handleRemoveSkill(skill.id)}
                        aria-label={`移除 ${skill.name}`}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={styles.noSkills}>暂无技能</div>
              )}
              <button
                type="button"
                className={styles.addSkillBtn}
                onClick={() => setShowSkillSelector(true)}
              >
                + 添加技能
              </button>
            </div>
          </div>

          <div className={styles.actions}>
            <button type="button" onClick={handleClose} className={styles.cancelBtn}>
              取消
            </button>
            <button type="submit" className={styles.submitBtn} disabled={loading}>
              {loading ? '保存中...' : '保存'}
            </button>
          </div>
        </form>
      </div>

      <SkillSelectorModal
        isOpen={showSkillSelector}
        onClose={() => setShowSkillSelector(false)}
        onSelect={handleAddSkill}
        excludeNames={roleSkills.map((s) => s.name)}
      />
    </div>
  );
}
