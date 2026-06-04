/**
 * 团队成员面板组件
 */

import { RoleMemberRow } from './RoleMemberRow';
import { useTeamMembers } from '../hooks/useTeamMembers';
import type { TeamWithMembers } from '../types';
import styles from './TeamMemberPanel.module.css';

export interface TeamMemberPanelProps {
  team: TeamWithMembers | null;
  onAddMember: () => void;
}

export function TeamMemberPanel({ team, onAddMember }: TeamMemberPanelProps) {
  const { removeMemberFromTeam, submitting } = useTeamMembers();

  const handleRemoveMember = async (roleName: string) => {
    if (!team) return;
    const result = await removeMemberFromTeam(team.name, roleName);
    if (!result.success) {
      alert(result.error);
    }
  };

  if (!team) {
    return (
      <div className={styles.empty}>
        <p>请选择一个团队</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <div className={styles.teamInfo}>
          <h2 className={styles.teamName}>{team.name}</h2>
          <span className={styles.memberCount}>{team.members.length} 成员</span>
        </div>
        <button type="button" className={styles.addBtn} onClick={onAddMember} disabled={submitting}>
          + 添加成员
        </button>
      </div>

      <div className={styles.memberList}>
        {team.members.length === 0 ? (
          <div className={styles.noMembers}>暂无成员</div>
        ) : (
          team.members.map((member) => (
            <RoleMemberRow key={member.name} role={member} onRemove={handleRemoveMember} />
          ))
        )}
      </div>
    </div>
  );
}
