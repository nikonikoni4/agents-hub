/**
 * 角色管理主面板组件
 */

import { useState } from 'react';
import { RoleCard } from './RoleCard';
import { TeamList } from './TeamList';
import { TeamMemberPanel } from './TeamMemberPanel';
import { CreateRoleDialog } from './CreateRoleDialog';
import { EditRoleDialog } from './EditRoleDialog';
import { AddMemberDialog } from './AddMemberDialog';
import { CreateTeamDialog } from './CreateTeamDialog';
import { useRoles } from '../hooks/useRoles';
import { useTeams } from '../hooks/useTeams';
import { useTeamActions } from '../hooks/useTeamActions';
import type { RoleManagementTab } from '../types';
import type { RoleWithSkills } from '@/shared/adapters/roleAdapter';
import styles from './RoleManagementPanel.module.css';

export function RoleManagementPanel() {
  const [activeTab, setActiveTab] = useState<RoleManagementTab>('teams');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showAddMemberDialog, setShowAddMemberDialog] = useState(false);
  const [showCreateTeamDialog, setShowCreateTeamDialog] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleWithSkills | null>(null);

  const { roles, loading: rolesLoading, refreshRoles } = useRoles();
  const { teams, selectedTeam, currentTeam, selectTeam, refreshTeams } = useTeams();
  const { handleDeleteTeam } = useTeamActions();

  const handleCreateRoleSuccess = () => {
    refreshRoles();
    if (activeTab === 'teams') {
      refreshTeams();
    }
  };

  const handleEditRole = (role: RoleWithSkills) => {
    setEditingRole(role);
    setShowEditDialog(true);
  };

  const handleEditSuccess = () => {
    refreshRoles();
    if (activeTab === 'teams') {
      refreshTeams();
    }
  };

  const handleAddMemberSuccess = () => {
    refreshTeams();
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>角色管理</h1>

        <div className={styles.tabs}>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'teams' ? styles.active : ''}`}
            onClick={() => setActiveTab('teams')}
          >
            团队管理
          </button>
          <button
            type="button"
            className={`${styles.tab} ${activeTab === 'roles' ? styles.active : ''}`}
            onClick={() => setActiveTab('roles')}
          >
            角色管理
          </button>
        </div>
      </div>

      <div className={styles.content}>
        {activeTab === 'teams' ? (
          <div className={styles.teamsView}>
            <TeamList
              teams={teams}
              selectedTeam={selectedTeam}
              onSelectTeam={selectTeam}
              onCreateTeam={() => setShowCreateTeamDialog(true)}
              onDeleteTeam={handleDeleteTeam}
            />
            <TeamMemberPanel team={currentTeam} onAddMember={() => setShowAddMemberDialog(true)} />
          </div>
        ) : (
          <div className={styles.rolesView}>
            <div className={styles.rolesHeader}>
              <button
                type="button"
                className={styles.addRoleBtn}
                onClick={() => setShowCreateDialog(true)}
              >
                + 添加角色
              </button>
            </div>

            {rolesLoading ? (
              <div className={styles.loading}>加载中...</div>
            ) : roles.length === 0 ? (
              <div className={styles.empty}>暂无角色</div>
            ) : (
              <div className={styles.rolesGrid}>
                {roles.map((role) => (
                  <RoleCard key={role.name} role={role} onEdit={handleEditRole} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <CreateRoleDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={handleCreateRoleSuccess}
      />

      <EditRoleDialog
        isOpen={showEditDialog}
        role={editingRole}
        onClose={() => {
          setShowEditDialog(false);
          setEditingRole(null);
        }}
        onSuccess={handleEditSuccess}
      />

      <AddMemberDialog
        isOpen={showAddMemberDialog}
        teamName={selectedTeam}
        onClose={() => setShowAddMemberDialog(false)}
        onSuccess={handleAddMemberSuccess}
      />

      <CreateTeamDialog
        isOpen={showCreateTeamDialog}
        onClose={() => setShowCreateTeamDialog(false)}
        onSuccess={refreshTeams}
      />
    </div>
  );
}
