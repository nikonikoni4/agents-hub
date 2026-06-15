/**
 * 角色管理主面板组件
 */

import { useState } from 'react';
import { RoleCard } from './RoleCard';
import { TeamCard } from './TeamCard';
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
  const { teams, selectedTeam, selectTeam, refreshTeams } = useTeams();
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
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>角色管理</h1>
          {activeTab === 'teams' ? (
            <button
              type="button"
              className={styles.addRoleBtn}
              onClick={() => setShowCreateTeamDialog(true)}
            >
              + 新建团队
            </button>
          ) : (
            <button
              type="button"
              className={styles.addRoleBtn}
              onClick={() => setShowCreateDialog(true)}
            >
              + 添加角色
            </button>
          )}
        </div>

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
            <div className={styles.teamsGrid}>
              {teams.map((team) => (
                <TeamCard
                  key={team.name}
                  team={team}
                  onAddMember={() => {
                    selectTeam(team.name);
                    setShowAddMemberDialog(true);
                  }}
                  onDeleteTeam={handleDeleteTeam}
                />
              ))}
              <button
                type="button"
                className={styles.createCard}
                onClick={() => setShowCreateTeamDialog(true)}
              >
                <div className={styles.createCardIcon}>
                  <svg viewBox="0 0 24 24">
                    <path d="M12 5v14m7-7H5" />
                  </svg>
                </div>
                <span className={styles.createCardText}>创建团队</span>
              </button>
            </div>
          </div>
        ) : (
          <div className={styles.rolesView}>
            {rolesLoading ? (
              <div className={styles.loading}>加载中...</div>
            ) : (
              <div className={styles.rolesGrid}>
                {roles.map((role) => (
                  <RoleCard key={role.name} role={role} onEdit={handleEditRole} />
                ))}
                <button
                  type="button"
                  className={styles.createCard}
                  onClick={() => setShowCreateDialog(true)}
                >
                  <div className={styles.createCardIcon}>
                    <svg viewBox="0 0 24 24">
                      <path d="M12 5v14m7-7H5" />
                    </svg>
                  </div>
                  <span className={styles.createCardText}>创建角色</span>
                </button>
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
