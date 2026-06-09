/**
 * 团队管理弹窗
 *
 * 职责：
 * - 显示团队列表
 * - 创建新团队
 * - 删除团队
 */

import { useState } from 'react';
import { useTeamManagement } from '../hooks/useTeamManagement';
import styles from './TeamListDialog.module.css';

export interface TeamListDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function TeamListDialog({ isOpen, onClose }: TeamListDialogProps) {
  const { teams, roles, loading, submitting, handleCreateTeam, handleDeleteTeam } =
    useTeamManagement();
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<string[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  if (!isOpen) return null;

  const resetForm = () => {
    setNewName('');
    setSelectedMembers([]);
    setShowCreate(false);
  };

  const toggleMember = (name: string) => {
    setSelectedMembers((prev) =>
      prev.includes(name) ? prev.filter((m) => m !== name) : [...prev, name]
    );
  };

  const handleCreate = async () => {
    if (!newName.trim() || selectedMembers.length === 0) return;
    const ok = await handleCreateTeam(newName.trim(), selectedMembers);
    if (ok) resetForm();
  };

  const handleDelete = async (name: string) => {
    const ok = await handleDeleteTeam(name);
    if (ok) setDeleteConfirm(null);
  };

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>团队管理</h2>
          <button type="button" className={styles.closeBtn} onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          {/* 团队列表 */}
          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <span className={styles.sectionTitle}>团队列表</span>
              {!showCreate && (
                <button type="button" className={styles.addBtn} onClick={() => setShowCreate(true)}>
                  + 新建团队
                </button>
              )}
            </div>

            {loading ? (
              <div className={styles.empty}>加载中...</div>
            ) : teams.length === 0 && !showCreate ? (
              <div className={styles.empty}>暂无团队，请创建</div>
            ) : (
              <div className={styles.teamList}>
                {teams.map((team) => (
                  <div key={team.name} className={styles.teamCard}>
                    <div className={styles.teamInfo}>
                      <span className={styles.teamName}>{team.name}</span>
                      <span className={styles.teamMembers}>
                        {team.members.length} 位成员: {team.members.join(', ')}
                      </span>
                    </div>
                    {deleteConfirm === team.name ? (
                      <div className={styles.deleteConfirm}>
                        <span>确认删除？</span>
                        <button
                          type="button"
                          className={styles.confirmYes}
                          onClick={() => handleDelete(team.name)}
                        >
                          是
                        </button>
                        <button
                          type="button"
                          className={styles.confirmNo}
                          onClick={() => setDeleteConfirm(null)}
                        >
                          否
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className={styles.deleteBtn}
                        onClick={() => setDeleteConfirm(team.name)}
                      >
                        删除
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 创建表单 */}
          {showCreate && (
            <div className={styles.section}>
              <div className={styles.sectionHeader}>
                <span className={styles.sectionTitle}>新建团队</span>
                <button type="button" className={styles.cancelTextBtn} onClick={resetForm}>
                  取消
                </button>
              </div>
              <div className={styles.form}>
                <div className={styles.field}>
                  <label className={styles.label}>团队名称</label>
                  <input
                    type="text"
                    className={styles.input}
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="输入团队名称"
                  />
                </div>
                <div className={styles.field}>
                  <label className={styles.label}>选择成员</label>
                  {roles.length === 0 ? (
                    <span className={styles.emptyHint}>暂无可用角色，请先创建角色</span>
                  ) : (
                    <div className={styles.roleList}>
                      {roles.map((role) => (
                        <label
                          key={role.name}
                          className={`${styles.roleChip} ${selectedMembers.includes(role.name) ? styles.selected : ''}`}
                        >
                          <input
                            type="checkbox"
                            checked={selectedMembers.includes(role.name)}
                            onChange={() => toggleMember(role.name)}
                          />
                          {role.name}
                        </label>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  className={styles.submitBtn}
                  disabled={!newName.trim() || selectedMembers.length === 0 || submitting}
                  onClick={handleCreate}
                >
                  {submitting ? '创建中...' : '创建团队'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
