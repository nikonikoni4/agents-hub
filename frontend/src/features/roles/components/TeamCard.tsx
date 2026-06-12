/**
 * 团队卡片组件
 */

import { useState } from 'react';
import { TeamMemberCard } from './TeamMemberCard';
import type { TeamWithMembers } from '../types';
import styles from './TeamCard.module.css';

export interface TeamCardProps {
  team: TeamWithMembers;
  onAddMember: () => void;
  onDeleteTeam: (teamName: string) => void;
}

export function TeamCard({ team, onAddMember, onDeleteTeam }: TeamCardProps) {
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const handleDelete = () => {
    if (deleteConfirm) {
      onDeleteTeam(team.name);
      setDeleteConfirm(false);
    } else {
      setDeleteConfirm(true);
    }
  };

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.teamInfo}>
          <h3 className={styles.teamName}>{team.name}</h3>
          <span className={styles.memberCount}>{team.members.length} 成员</span>
        </div>
        <div className={styles.actions}>
          <button type="button" className={styles.addBtn} onClick={onAddMember}>
            + 添加成员
          </button>
          {deleteConfirm ? (
            <div className={styles.deleteConfirm}>
              <span className={styles.confirmText}>确认删除？</span>
              <button type="button" className={styles.confirmYes} onClick={handleDelete}>
                是
              </button>
              <button type="button" className={styles.confirmNo} onClick={() => setDeleteConfirm(false)}>
                否
              </button>
            </div>
          ) : (
            <button type="button" className={styles.deleteBtn} onClick={handleDelete}>
              删除
            </button>
          )}
        </div>
      </div>
      <div className={styles.memberGrid}>
        {team.members.length === 0 ? (
          <div className={styles.empty}>暂无成员</div>
        ) : (
          team.members.map((member) => (
            <TeamMemberCard key={member.name} role={member} />
          ))
        )}
      </div>
    </div>
  );
}
