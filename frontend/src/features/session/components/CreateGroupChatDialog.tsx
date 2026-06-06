/**
 * 创建群组对话弹窗
 */

import { useState } from 'react';
import { FolderIcon, AvatarImage } from '@/shared/components';
import { useCreateGroupChat } from '../hooks/useCreateGroupChat';
import { useSessionStore } from '../store/sessionStore';
import styles from './CreateGroupChatDialog.module.css';

export interface CreateGroupChatDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type ChatMode = 'single' | 'group';

export function CreateGroupChatDialog({ isOpen, onClose, onSuccess }: CreateGroupChatDialogProps) {
  const [chatMode, setChatMode] = useState<ChatMode>('group');
  const [name, setName] = useState('');
  const [selectedLeader, setSelectedLeader] = useState<string | null>(null);
  const [selectedWorkers, setSelectedWorkers] = useState<string[]>([]);
  const [projectPath, setProjectPath] = useState('');
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);

  const { leaders, workers, teams, loading, submitting, createChat } = useCreateGroupChat();
  const selectSession = useSessionStore((s) => s.selectSession);

  const handleClose = () => {
    setChatMode('group');
    setName('');
    setSelectedLeader(null);
    setSelectedWorkers([]);
    setProjectPath('');
    setSelectedTeam(null);
    onClose();
  };

  const toggleWorker = (roleName: string) => {
    setSelectedWorkers((prev) =>
      prev.includes(roleName) ? prev.filter((r) => r !== roleName) : [...prev, roleName]
    );
  };

  // 选择团队时自动选中该团队的成员
  const handleSelectTeam = (teamName: string) => {
    if (selectedTeam === teamName) {
      // 取消选择团队
      setSelectedTeam(null);
      return;
    }
    setSelectedTeam(teamName);
    const team = teams.find((t) => t.name === teamName);
    if (!team) return;

    // 从团队成员中找到匹配的 leader 和 workers
    const teamMemberNames = new Set(team.members);
    const matchedLeader = leaders.find((l) => teamMemberNames.has(l.name));
    const matchedWorkers = workers.filter((w) => teamMemberNames.has(w.name)).map((w) => w.name);

    if (matchedLeader) {
      setSelectedLeader(matchedLeader.name);
    }
    setSelectedWorkers(matchedWorkers);
  };

  const handleBrowse = async () => {
    if ('showDirectoryPicker' in window) {
      try {
        const handle = await (
          window as { showDirectoryPicker: () => Promise<{ name: string }> }
        ).showDirectoryPicker();
        setProjectPath(handle.name);
      } catch {
        // 用户取消选择
      }
    }
  };

  const canSubmit = chatMode === 'group' && name.trim() && selectedLeader && projectPath.trim();

  const handleSubmit = async () => {
    if (!canSubmit || !selectedLeader) return;

    const chatId = await createChat({
      group_chat_name: name.trim(),
      team_members: [selectedLeader, ...selectedWorkers],
      project_path: projectPath.trim(),
    });

    if (chatId) {
      selectSession(chatId);
      onSuccess?.();
      handleClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2>新建对话</h2>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          {/* 模式切换 */}
          <div className={styles.modeSelector}>
            <button
              type="button"
              className={`${styles.modeBtn} ${chatMode === 'single' ? styles.modeBtnActive : ''}`}
              onClick={() => setChatMode('single')}
            >
              单聊
            </button>
            <button
              type="button"
              className={`${styles.modeBtn} ${chatMode === 'group' ? styles.modeBtnActive : ''}`}
              onClick={() => setChatMode('group')}
            >
              群聊
            </button>
          </div>

          {chatMode === 'single' ? (
            <div className={styles.placeholder}>
              <p>单聊功能开发中，敬请期待...</p>
            </div>
          ) : (
            <>
              {/* 群组名称 */}
              <div className={styles.field}>
                <label className={styles.fieldLabel}>群组名称</label>
                <input
                  type="text"
                  className={styles.input}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="输入群组名称"
                />
              </div>

              {/* 团队预选 */}
              {teams.length > 0 && (
                <div className={styles.field}>
                  <label className={styles.fieldLabel}>快速选择团队（可选）</label>
                  <div className={styles.roleList}>
                    {teams.map((team) => (
                      <button
                        key={team.name}
                        type="button"
                        className={`${styles.roleChip} ${selectedTeam === team.name ? styles.selected : ''}`}
                        onClick={() => handleSelectTeam(team.name)}
                      >
                        <span>👥</span>
                        {team.name}
                        <span className={styles.teamMemberCount}>{team.members.length}人</span>
                      </button>
                    ))}
                  </div>
                  {selectedTeam && (
                    <span className={styles.emptyHint}>
                      已选择「{selectedTeam}」的成员，可在下方调整
                    </span>
                  )}
                </div>
              )}

              {/* Leader 选择 */}
              <div className={styles.field}>
                <label className={styles.fieldLabel}>Leader（必选）</label>
                {loading ? (
                  <span className={styles.emptyHint}>加载角色中...</span>
                ) : leaders.length === 0 ? (
                  <span className={styles.emptyHint}>暂无可用的 Leader 角色</span>
                ) : (
                  <div className={styles.roleList}>
                    {leaders.map((role) => (
                      <label
                        key={role.name}
                        className={`${styles.roleChip} ${selectedLeader === role.name ? styles.selected : ''}`}
                      >
                        <input
                          type="radio"
                          name="leader"
                          checked={selectedLeader === role.name}
                          onChange={() => setSelectedLeader(role.name)}
                        />
                        <span className={styles.roleAvatar}>
                          <AvatarImage avatar={role.avatar} fallback={role.name} />
                        </span>
                        {role.name}
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* Worker 选择 */}
              <div className={styles.field}>
                <label className={styles.fieldLabel}>Workers（可选）</label>
                {loading ? (
                  <span className={styles.emptyHint}>加载角色中...</span>
                ) : workers.length === 0 ? (
                  <span className={styles.emptyHint}>暂无可用的 Worker 角色</span>
                ) : (
                  <div className={styles.roleList}>
                    {workers.map((role) => (
                      <label
                        key={role.name}
                        className={`${styles.roleChip} ${selectedWorkers.includes(role.name) ? styles.selected : ''}`}
                      >
                        <input
                          type="checkbox"
                          checked={selectedWorkers.includes(role.name)}
                          onChange={() => toggleWorker(role.name)}
                        />
                        <span className={styles.roleAvatar}>
                          <AvatarImage avatar={role.avatar} fallback={role.name} />
                        </span>
                        {role.name}
                      </label>
                    ))}
                  </div>
                )}
              </div>

              {/* 项目路径 */}
              <div className={styles.field}>
                <label className={styles.fieldLabel}>项目路径</label>
                <div className={styles.pathRow}>
                  <input
                    type="text"
                    className={`${styles.input} ${styles.pathInput}`}
                    value={projectPath}
                    onChange={(e) => setProjectPath(e.target.value)}
                    placeholder="/home/user/projects/your-project"
                  />
                  {import.meta.env.PROD && (
                    <button type="button" className={styles.browseBtn} onClick={handleBrowse}>
                      <FolderIcon />
                      浏览
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <div className={styles.actions}>
          <button type="button" onClick={handleClose} className={styles.cancelBtn}>
            取消
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            className={styles.submitBtn}
            disabled={!canSubmit || submitting}
          >
            {submitting ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}
