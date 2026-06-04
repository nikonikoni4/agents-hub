/**
 * 角色成员行组件
 */

import { AvatarImage } from '@/shared/components';
import type { RoleWithSkills } from '../types';
import styles from './RoleMemberRow.module.css';

export interface RoleMemberRowProps {
  role: RoleWithSkills;
  onRemove: (roleName: string) => void;
}

export function RoleMemberRow({ role, onRemove }: RoleMemberRowProps) {
  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm(`确定将 ${role.name} 从团队中移除？`)) {
      onRemove(role.name);
    }
  };

  return (
    <div className={styles.row}>
      <div className={styles.avatar}>
        <AvatarImage avatar={role.avatar} fallback={role.name} />
      </div>
      <div className={styles.info}>
        <div className={styles.header}>
          <span className={styles.name}>{role.name}</span>
          <span className={`${styles.badge} ${styles.type}`}>
            {role.type === 'leader' ? 'leader' : 'team_member'}
          </span>
        </div>
        {role.description && <p className={styles.description}>{role.description}</p>}
      </div>
      <button
        type="button"
        className={styles.removeBtn}
        onClick={handleRemove}
        aria-label={`移除 ${role.name}`}
      >
        ×
      </button>
    </div>
  );
}
