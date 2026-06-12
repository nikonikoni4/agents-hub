/**
 * 团队成员卡片组件
 */

import { AvatarImage } from '@/shared/components';
import type { RoleWithSkills } from '../types';
import styles from './TeamMemberCard.module.css';

export interface TeamMemberCardProps {
  role: RoleWithSkills;
}

export function TeamMemberCard({ role }: TeamMemberCardProps) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.avatarWrapper}>
          <div className={styles.avatar}>
            <AvatarImage avatar={role.avatar} fallback={role.name} />
          </div>
          <div className={styles.statusDot} />
        </div>
        <div className={styles.info}>
          <span className={styles.name}>{role.name}</span>
          {role.description && <p className={styles.description}>{role.description}</p>}
        </div>
      </div>
      {role.skills.length > 0 ? (
        <div className={styles.skillsContainer}>
          <div className={styles.skills}>
            {role.skills.map((skill) => (
              <span key={skill.name} className={styles.skillTag}>
                {skill.name}
              </span>
            ))}
          </div>
        </div>
      ) : (
        <div className={styles.noSkills}>暂无技能</div>
      )}
    </div>
  );
}
