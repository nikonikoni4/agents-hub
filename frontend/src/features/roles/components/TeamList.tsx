/**
 * 团队列表组件
 */

import type { TeamWithMembers } from '../types';
import styles from './TeamList.module.css';

export interface TeamListProps {
  teams: TeamWithMembers[];
  selectedTeam: string | null;
  onSelectTeam: (teamName: string) => void;
}

export function TeamList({ teams, selectedTeam, onSelectTeam }: TeamListProps) {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h3>团队列表</h3>
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
          </button>
        ))}
      </div>
    </div>
  );
}
