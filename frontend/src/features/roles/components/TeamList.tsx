/**
 * 团队列表组件
 */

import { useState } from 'react';
import type { TeamWithMembers } from '../types';
import styles from './TeamList.module.css';

export interface TeamListProps {
  teams: TeamWithMembers[];
  selectedTeam: string | null;
  onSelectTeam: (teamName: string) => void;
  onCreateTeam: () => void;
  onDeleteTeam: (teamName: string) => void;
}

export function TeamList({
  teams,
  selectedTeam,
  onSelectTeam,
  onCreateTeam,
  onDeleteTeam,
}: TeamListProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const handleDelete = (e: React.MouseEvent, teamName: string) => {
    e.stopPropagation();
    if (deleteConfirm === teamName) {
      onDeleteTeam(teamName);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(teamName);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3>团队列表</h3>
        <button type="button" className={styles.addBtn} onClick={onCreateTeam}>
          + 新建
        </button>
      </div>
      <div className={styles.list}>
        {teams.map((team) => (
          <button
            key={team.name}
            type="button"
            className={`${styles.item} ${selectedTeam === team.name ? styles.active : ''}`}
            onClick={() => onSelectTeam(team.name)}
          >
            <div className={styles.itemIcon}>👥</div>
            <div className={styles.itemInfo}>
              <div className={styles.itemName}>{team.name}</div>
              <div className={styles.itemCount}>{team.members.length} 成员</div>
            </div>
            {deleteConfirm === team.name ? (
              <div className={styles.deleteConfirm} onClick={(e) => e.stopPropagation()}>
                <span className={styles.confirmText}>确认？</span>
                <button
                  type="button"
                  className={styles.confirmYes}
                  onClick={(e) => handleDelete(e, team.name)}
                >
                  是
                </button>
                <button
                  type="button"
                  className={styles.confirmNo}
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteConfirm(null);
                  }}
                >
                  否
                </button>
              </div>
            ) : (
              <button
                type="button"
                className={styles.deleteBtn}
                onClick={(e) => handleDelete(e, team.name)}
              >
                删除
              </button>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
