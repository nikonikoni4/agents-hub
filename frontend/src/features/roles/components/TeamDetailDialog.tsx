/**
 * 团队详情弹窗组件
 */

import { TeamMemberCard } from './TeamMemberCard';
import type { TeamWithMembers } from '../types';
import styles from './TeamDetailDialog.module.css';

export interface TeamDetailDialogProps {
  isOpen: boolean;
  onClose: () => void;
  team: TeamWithMembers;
}

export function TeamDetailDialog({ isOpen, onClose, team }: TeamDetailDialogProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.teamInfo}>
            <h2 className={styles.teamName}>{team.name}</h2>
            <span className={styles.memberCount}>{team.members.length} 成员</span>
          </div>
          <button type="button" className={styles.closeBtn} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          {team.members.length === 0 ? (
            <div className={styles.empty}>暂无成员</div>
          ) : (
            <div className={styles.memberGrid}>
              {team.members.map((member) => (
                <TeamMemberCard key={member.name} role={member} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
