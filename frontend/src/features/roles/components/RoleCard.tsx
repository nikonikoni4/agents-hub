/**
 * 角色卡片组件
 */

import { AvatarImage } from '@/shared/components';
import type { RoleWithSkills } from '../types';
import styles from './RoleCard.module.css';

export interface RoleCardProps {
  role: RoleWithSkills;
  onClick?: () => void;
  onEdit?: (role: RoleWithSkills) => void;
}

export function RoleCard({ role, onClick, onEdit }: RoleCardProps) {
  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(role);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    alert('当前不支持删除');
  };

  return (
    <div className={styles.card} onClick={onClick}>
      <div className={styles.header}>
        <div className={styles.avatar}>
          <AvatarImage avatar={role.avatar} fallback={role.name} />
        </div>
        <div className={styles.info}>
          <h3 className={styles.name}>{role.name}</h3>
          <div className={styles.badges}>
            <span className={`${styles.badge} ${styles.platform}`}>{role.platform}</span>
            <span className={`${styles.badge} ${styles.type}`}>
              {role.type === 'leader' ? 'leader' : 'team_member'}
            </span>
          </div>
        </div>
        <div className={styles.actions}>
          {onEdit && (
            <button
              type="button"
              className={styles.editBtn}
              onClick={handleEdit}
              aria-label="编辑角色"
            >
              ✏️
            </button>
          )}
          <button
            type="button"
            className={styles.deleteBtn}
            onClick={handleDelete}
            aria-label="删除角色"
          >
            🗑️
          </button>
        </div>
      </div>

      {role.description && <p className={styles.description}>{role.description}</p>}

      <div className={styles.skills}>
        <span className={styles.skillsLabel}>Skills:</span>
        {role.skills.length > 0 ? (
          <div className={styles.skillsList}>
            {role.skills.map((skill) => (
              <span key={skill.id} className={styles.skillBadge}>
                {skill.name}
              </span>
            ))}
          </div>
        ) : (
          <span className={styles.noSkills}>暂无技能</span>
        )}
      </div>
    </div>
  );
}
