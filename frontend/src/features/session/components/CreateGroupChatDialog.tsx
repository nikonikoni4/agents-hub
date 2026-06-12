/**
 * 创建群组对话弹窗
 */

import { useState } from 'react';
import { FolderIcon, AvatarImage } from '@/shared/components';
import { useCreateGroupChat } from '../hooks/useCreateGroupChat';
import { useSessionStore } from '../store/sessionStore';
import { useCreateChatData, useGroupChatMembers } from '@/shared/hooks';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import type { DraftChat } from '@/features/single-chat/store/singleChatStore';
import styles from './CreateGroupChatDialog.module.css';

// SVG图标组件
const PlusIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M12 5v14m7-7H5" />
  </svg>
);

const UserIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const UsersIcon = () => (
  <svg viewBox="0 0 24 24">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
    <circle cx="9" cy="7" r="4" />
    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
  </svg>
);

export interface CreateGroupChatDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

type ChatMode = 'single' | 'group';
type SingleMode = 'new' | 'group';

export function CreateGroupChatDialog({ isOpen, onClose, onSuccess }: CreateGroupChatDialogProps) {
  const [chatMode, setChatMode] = useState<ChatMode>('group');
  const [name, setName] = useState('');
  const [selectedLeader, setSelectedLeader] = useState<string | null>(null);
  const [selectedWorkers, setSelectedWorkers] = useState<string[]>([]);
  const [projectPath, setProjectPath] = useState('');
  const [selectedTeam, setSelectedTeam] = useState<string | null>(null);

  // 单聊状态
  const [singleMode, setSingleMode] = useState<SingleMode>('new');
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedGroupChat, setSelectedGroupChat] = useState<string | null>(null);

  const { leaders, workers, teams, loading, submitting, createChat } = useCreateGroupChat(isOpen);
  const { roles: allRoles, groupChats, loading: singleLoading } = useCreateChatData(isOpen);
  const { members: groupMembers, loading: membersLoading } = useGroupChatMembers(selectedGroupChat);
  const selectGroupChat = useSessionStore((s) => s.selectGroupChat);
  const openDraftChat = useSingleChatStore((s) => s.openDraftChat);

  const handleClose = () => {
    setChatMode('group');
    setName('');
    setSelectedLeader(null);
    setSelectedWorkers([]);
    setProjectPath('');
    setSelectedTeam(null);
    setSingleMode('new');
    setSelectedAgent(null);
    setSelectedGroupChat(null);
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

  const canSubmit =
    chatMode === 'group'
      ? !!name.trim() && !!selectedLeader && !!projectPath.trim()
      : singleMode === 'new'
        ? !!selectedAgent
        : !!selectedGroupChat && !!selectedAgent;

  const handleSubmit = async () => {
    if (chatMode === 'group') {
      if (!canSubmit || !selectedLeader) return;
      const chatId = await createChat({
        group_chat_name: name.trim(),
        team_members: [selectedLeader, ...selectedWorkers],
        project_path: projectPath.trim(),
      });
      if (chatId) {
        selectGroupChat(chatId);
        onSuccess?.();
        handleClose();
      }
    } else {
      if (!selectedAgent) return;
      const chatName = name.trim() || `与 ${selectedAgent} 的对话`;
      const draft: DraftChat = {
        type: singleMode === 'new' ? 'new' : 'fork',
        single_chat_name: chatName,
        agent_name: selectedAgent,
        group_chat_id: singleMode === 'group' ? (selectedGroupChat ?? undefined) : undefined,
      };
      openDraftChat(draft);
      onSuccess?.();
      handleClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.dialog} onClick={(e) => e.stopPropagation()}>
        {/* 标题栏 - 增加图标和副标题 */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <div className={styles.headerIcon}>
              <PlusIcon />
            </div>
            <div className={styles.headerText}>
              <h2>新建对话</h2>
              <div className={styles.headerSubtitle}>选择对话模式并配置团队成员</div>
            </div>
          </div>
          <button type="button" className={styles.closeBtn} onClick={handleClose}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          {/* Tab切换 - 增加图标 */}
          <div className={styles.modeSelector}>
            <button
              type="button"
              className={`${styles.modeBtn} ${chatMode === 'single' ? styles.modeBtnActive : ''}`}
              onClick={() => setChatMode('single')}
            >
              <UserIcon />
              单聊
            </button>
            <button
              type="button"
              className={`${styles.modeBtn} ${chatMode === 'group' ? styles.modeBtnActive : ''}`}
              onClick={() => setChatMode('group')}
            >
              <UsersIcon />
              群聊
            </button>
          </div>

          {chatMode === 'single' ? (
            <>
              {/* 单聊子模式切换 */}
              <div className={styles.modeSelector}>
                <button
                  type="button"
                  className={`${styles.modeBtn} ${singleMode === 'new' ? styles.modeBtnActive : ''}`}
                  onClick={() => {
                    setSingleMode('new');
                    setSelectedAgent(null);
                    setSelectedGroupChat(null);
                  }}
                >
                  全新
                </button>
                <button
                  type="button"
                  className={`${styles.modeBtn} ${singleMode === 'group' ? styles.modeBtnActive : ''}`}
                  onClick={() => {
                    setSingleMode('group');
                    setSelectedAgent(null);
                  }}
                >
                  群组
                </button>
              </div>

              {singleMode === 'new' ? (
                /* 全新模式：从所有角色中选择 */
                <div className={styles.formSection}>
                  <div className={styles.formSectionTitle}>选择 Agent</div>
                  <div className={styles.field}>
                    <div className={styles.fieldHeader}>
                      <label className={styles.fieldLabel}>
                        Agent
                        <span className={`${styles.badge} ${styles.badgeRequired}`}>必选</span>
                      </label>
                      <span className={styles.fieldHint}>选择一个 AI 助手开始对话</span>
                    </div>
                    {singleLoading ? (
                      <span className={styles.emptyHint}>加载角色中...</span>
                    ) : allRoles.length === 0 ? (
                      <span className={styles.emptyHint}>暂无可用角色</span>
                    ) : (
                      <div className={styles.roleGrid}>
                        {allRoles.map((role) => (
                          <div
                            key={role.name}
                            className={`${styles.roleCard} ${selectedAgent === role.name ? styles.roleCardSelected : ''}`}
                            onClick={() => setSelectedAgent(role.name)}
                          >
                            <span className={styles.roleAvatarLarge}>
                              <AvatarImage avatar={role.avatar} fallback={role.name} />
                            </span>
                            <span className={styles.roleName}>{role.name}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className={styles.field}>
                    <div className={styles.fieldHeader}>
                      <label className={styles.fieldLabel}>
                        对话名称
                        <span className={`${styles.badge} ${styles.badgeOptional}`}>可选</span>
                      </label>
                    </div>
                    <input
                      type="text"
                      className={styles.input}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={
                        selectedAgent ? `与 ${selectedAgent} 的对话` : '输入对话名称（可选）'
                      }
                    />
                  </div>
                </div>
              ) : (
                /* 群组模式：选群聊 → 选成员 → fork/continue */
                <div className={styles.formSection}>
                  <div className={styles.formSectionTitle}>选择群聊</div>
                  <div className={styles.field}>
                    <div className={styles.fieldHeader}>
                      <label className={styles.fieldLabel}>
                        群聊
                        <span className={`${styles.badge} ${styles.badgeRequired}`}>必选</span>
                      </label>
                    </div>
                    {singleLoading ? (
                      <span className={styles.emptyHint}>加载群聊中...</span>
                    ) : groupChats.length === 0 ? (
                      <span className={styles.emptyHint}>暂无可用群聊</span>
                    ) : (
                      <div className={styles.teamSelector}>
                        {groupChats.map((chat) => (
                          <div
                            key={chat.group_chat_id}
                            className={`${styles.teamChip} ${selectedGroupChat === chat.group_chat_id ? styles.teamChipSelected : ''}`}
                            onClick={() => {
                              setSelectedGroupChat(chat.group_chat_id);
                              setSelectedAgent(null);
                            }}
                          >
                            <span className={styles.teamIcon}>👥</span>
                            {chat.group_chat_name}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {selectedGroupChat && (
                    <>
                      <div className={styles.formSectionTitle}>选择 Agent</div>
                      <div className={styles.field}>
                        <div className={styles.fieldHeader}>
                          <label className={styles.fieldLabel}>
                            Agent
                            <span className={`${styles.badge} ${styles.badgeRequired}`}>必选</span>
                          </label>
                        </div>
                        {membersLoading ? (
                          <span className={styles.emptyHint}>加载成员中...</span>
                        ) : groupMembers.length === 0 ? (
                          <span className={styles.emptyHint}>该群聊暂无成员</span>
                        ) : (
                          <div className={styles.roleGrid}>
                            {groupMembers.map((member) => (
                              <div
                                key={member.name}
                                className={`${styles.roleCard} ${selectedAgent === member.name ? styles.roleCardSelected : ''}`}
                                onClick={() => setSelectedAgent(member.name)}
                              >
                                <span className={styles.roleAvatarLarge}>
                                  <AvatarImage
                                    avatar={member.role?.avatar ?? null}
                                    fallback={member.name}
                                  />
                                </span>
                                <span className={styles.roleName}>{member.name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </>
                  )}

                  {selectedGroupChat && selectedAgent && (
                    <div className={styles.field}>
                      <label className={styles.fieldLabel}>模式</label>
                      <div className={styles.roleList}>
                        <label className={`${styles.roleChip} ${styles.roleChipSelected}`}>
                          <input type="radio" name="fork-mode" checked readOnly />
                          Fork
                        </label>
                        <label
                          className={`${styles.roleChip} ${styles.roleChipDisabled}`}
                          title="Continue 模式暂未开放"
                        >
                          <input type="radio" name="fork-mode" disabled />
                          Continue
                        </label>
                      </div>
                    </div>
                  )}

                  <div className={styles.formSectionTitle}>对话配置</div>
                  <div className={styles.field}>
                    <div className={styles.fieldHeader}>
                      <label className={styles.fieldLabel}>
                        对话名称
                        <span className={`${styles.badge} ${styles.badgeOptional}`}>可选</span>
                      </label>
                    </div>
                    <input
                      type="text"
                      className={styles.input}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder={
                        selectedAgent ? `与 ${selectedAgent} 的对话` : '输入对话名称（可选）'
                      }
                    />
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {/* 基本信息 */}
              <div className={styles.formSection}>
                <div className={styles.formSectionTitle}>基本信息</div>
                <div className={styles.field}>
                  <div className={styles.fieldHeader}>
                    <label className={styles.fieldLabel}>
                      群组名称
                      <span className={`${styles.badge} ${styles.badgeRequired}`}>必选</span>
                    </label>
                  </div>
                  <input
                    type="text"
                    className={styles.input}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="输入群组名称"
                  />
                </div>
              </div>

              {/* 快速选择团队 */}
              {teams.length > 0 && (
                <div className={styles.formSection}>
                  <div className={styles.formSectionTitle}>快速选择团队</div>
                  <div className={styles.field}>
                    <div className={styles.teamSelector}>
                      {teams.map((team) => (
                        <div
                          key={team.name}
                          className={`${styles.teamChip} ${selectedTeam === team.name ? styles.teamChipSelected : ''}`}
                          onClick={() => handleSelectTeam(team.name)}
                        >
                          <span className={styles.teamIcon}>👥</span>
                          {team.name}
                          <span className={styles.teamMemberCount}>{team.members.length}人</span>
                        </div>
                      ))}
                    </div>
                    {selectedTeam && (
                      <span className={styles.emptyHint}>
                        已选择「{selectedTeam}」的成员，可在下方调整
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* 配置成员 */}
              <div className={styles.formSection}>
                <div className={styles.formSectionTitle}>配置成员</div>
                <div className={styles.field}>
                  <div className={styles.fieldHeader}>
                    <label className={styles.fieldLabel}>
                      Leader
                      <span className={`${styles.badge} ${styles.badgeRequired}`}>必选</span>
                    </label>
                    <span className={styles.fieldHint}>选择团队负责人</span>
                  </div>
                  {loading ? (
                    <span className={styles.emptyHint}>加载角色中...</span>
                  ) : leaders.length === 0 ? (
                    <span className={styles.emptyHint}>暂无可用的 Leader 角色</span>
                  ) : (
                    <div className={styles.roleGrid}>
                      {leaders.map((role) => (
                        <div
                          key={role.name}
                          className={`${styles.roleCard} ${selectedLeader === role.name ? styles.roleCardSelected : ''}`}
                          onClick={() => setSelectedLeader(role.name)}
                        >
                          <span className={styles.roleAvatarLarge}>
                            <AvatarImage avatar={role.avatar} fallback={role.name} />
                          </span>
                          <span className={styles.roleName}>{role.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className={styles.field}>
                  <div className={styles.fieldHeader}>
                    <label className={styles.fieldLabel}>
                      Workers
                      <span className={`${styles.badge} ${styles.badgeOptional}`}>可选</span>
                    </label>
                    <span className={styles.fieldHint}>选择团队成员（可多选）</span>
                  </div>
                  {loading ? (
                    <span className={styles.emptyHint}>加载角色中...</span>
                  ) : workers.length === 0 ? (
                    <span className={styles.emptyHint}>暂无可用的 Worker 角色</span>
                  ) : (
                    <div className={styles.roleGrid}>
                      {workers.map((role) => (
                        <div
                          key={role.name}
                          className={`${styles.roleCard} ${selectedWorkers.includes(role.name) ? styles.roleCardSelected : ''}`}
                          onClick={() => toggleWorker(role.name)}
                        >
                          <span className={styles.roleAvatarLarge}>
                            <AvatarImage avatar={role.avatar} fallback={role.name} />
                          </span>
                          <span className={styles.roleName}>{role.name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 项目配置 */}
              <div className={styles.formSection}>
                <div className={styles.formSectionTitle}>项目配置</div>
                <div className={styles.field}>
                  <div className={styles.fieldHeader}>
                    <label className={styles.fieldLabel}>
                      项目路径
                      <span className={`${styles.badge} ${styles.badgeRequired}`}>必选</span>
                    </label>
                  </div>
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
