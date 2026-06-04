/**
 * 角色成员行组件
 */

import type { RoleWithSkills } from '../types';
import styles from './RoleMemberRow.module.css';

export interface RoleMemberRowProps {
  role: RoleWithSkills;
  onRemove: (roleName: string) => void;
}

function AvatarImage({ avatar, fallback }: { avatar: string | null; fallback: string }) {
  // SVG 内容以 <svg 开头
  if (avatar && avatar.startsWith('<svg')) {
    return <div className={styles.avatarSvg} dangerouslySetInnerHTML={{ __html: avatar }} />;
  }

  // URL 图片
  if (avatar) {
    return <img src={avatar} alt="头像" className={styles.avatarImg} />;
  }

  // 降级：显示首字母
  return <div className={styles.avatarFallback}>{fallback.charAt(0).toUpperCase()}</div>;
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
