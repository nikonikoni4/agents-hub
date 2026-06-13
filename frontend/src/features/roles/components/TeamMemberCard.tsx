/**
 * 团队成员卡片组件
 * 支持 compact（缩略）和 default（完整）两种模式
 */

import { AvatarImage } from '@/shared/components';
import type { RoleWithSkills } from '../types';
import styles from './TeamMemberCard.module.css';

export interface TeamMemberCardProps {
  role: RoleWithSkills;
  /** 缩略模式：只显示头像、名称和简短描述 */
  compact?: boolean;
}

/** 截取描述的前 N 个字符 */
function truncateDescription(desc: string, maxLen: number = 20): string {
  if (desc.length <= maxLen) return desc;
  return desc.slice(0, maxLen) + '...';
}

export function TeamMemberCard({ role, compact = false }: TeamMemberCardProps) {
  // 缩略模式
  if (compact) {
    const tooltipText = role.description || role.name;

    return (
      <div className={styles.compactCard} data-tooltip={tooltipText}>
        <div className={styles.compactAvatar}>
          <AvatarImage avatar={role.avatar} fallback={role.name} />
        </div>
        <div className={styles.compactInfo}>
          <span className={styles.compactName}>{role.name}</span>
          {role.description && (
            <span className={styles.compactDesc}>
              {truncateDescription(role.description)}
            </span>
          )}
        </div>
      </div>
    );
  }

  // 完整模式
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
          {role.description && (
            <p className={styles.description} title={role.description}>
              {role.description}
            </p>
          )}
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
