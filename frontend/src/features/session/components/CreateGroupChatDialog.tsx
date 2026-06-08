/**
 * 创建群组对话弹窗
 */

import { useState } from 'react';
import { FolderIcon, AvatarImage } from '@/shared/components';
import { useCreateGroupChat } from '../hooks/useCreateGroupChat';
import { useSessionStore } from '../store/sessionStore';
import { useCreateChatData, useGroupChatMembers } from '@/shared/hooks';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import styles from './CreateGroupChatDialog.module.css';

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

  const { leaders, workers, teams, loading, submitting, createChat } = useCreateGroupChat();
  const {
    roles: allRoles,
    groupChats,
    loading: singleLoading,
    submitting: singleSubmitting,
    submitSingleChat,
  } = useCreateChatData();
  const { members: groupMembers, loading: membersLoading } = useGroupChatMembers(selectedGroupChat);
  const selectSession = useSessionStore((s) => s.selectSession);
  const addSingleChat = useSingleChatStore((s) => s.addSingleChat);
  const openSingleChat = useSingleChatStore((s) => s.openSingleChat);

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
        selectSession(chatId, 'group_chat');
        onSuccess?.();
        handleClose();
      }
    } else {
      if (!selectedAgent) return;
      const chatName = name.trim() || `与 ${selectedAgent} 的对话`;
      const chatId = await submitSingleChat(
        {
          type: singleMode === 'new' ? 'new' : 'fork',
          single_chat_name: chatName,
          agent_name: selectedAgent,
          group_chat_id: singleMode === 'group' ? selectedGroupChat : undefined,
        },
        (id) => {
          addSingleChat({
            single_chat_id: id,
            single_chat_name: chatName,
            type: singleMode === 'new' ? 'new' : 'fork',
            agent_name: selectedAgent,
            platform: 'claude',
            session_id: null,
            group_chat_id: singleMode === 'group' ? selectedGroupChat : null,
            cwd: '',
            created_at: new Date().toISOString(),
            last_active_at: new Date().toISOString(),
          });
          openSingleChat(id);
        }
      );
      if (chatId) {
        onSuccess?.();
        handleClose();
      }
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
                <div className={styles.field}>
                  <label className={styles.fieldLabel}>选择 Agent</label>
                  {singleLoading ? (
                    <span className={styles.emptyHint}>加载角色中...</span>
                  ) : allRoles.length === 0 ? (
                    <span className={styles.emptyHint}>暂无可用角色</span>
                  ) : (
                    <div className={styles.roleList}>
                      {allRoles.map((role) => (
                        <label
                          key={role.name}
                          className={`${styles.roleChip} ${selectedAgent === role.name ? styles.selected : ''}`}
                        >
                          <input
                            type="radio"
                            name="single-agent"
                            checked={selectedAgent === role.name}
                            onChange={() => setSelectedAgent(role.name)}
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
              ) : (
                /* 群组模式：选群聊 → 选成员 → fork/continue */
                <>
                  <div className={styles.field}>
                    <label className={styles.fieldLabel}>选择群聊</label>
                    {singleLoading ? (
                      <span className={styles.emptyHint}>加载群聊中...</span>
                    ) : groupChats.length === 0 ? (
                      <span className={styles.emptyHint}>暂无可用群聊</span>
                    ) : (
                      <div className={styles.roleList}>
                        {groupChats.map((chat) => (
                          <label
                            key={chat.group_chat_id}
                            className={`${styles.roleChip} ${selectedGroupChat === chat.group_chat_id ? styles.selected : ''}`}
                          >
                            <input
                              type="radio"
                              name="group-chat"
                              checked={selectedGroupChat === chat.group_chat_id}
                              onChange={() => {
                                setSelectedGroupChat(chat.group_chat_id);
                                setSelectedAgent(null);
                              }}
                            />
                            {chat.group_chat_name}
                          </label>
                        ))}
                      </div>
                    )}
                  </div>

                  {selectedGroupChat && (
                    <div className={styles.field}>
                      <label className={styles.fieldLabel}>选择 Agent</label>
                      {membersLoading ? (
                        <span className={styles.emptyHint}>加载成员中...</span>
                      ) : groupMembers.length === 0 ? (
                        <span className={styles.emptyHint}>该群聊暂无成员</span>
                      ) : (
                        <div className={styles.roleList}>
                          {groupMembers.map((member) => (
                            <label
                              key={member.name}
                              className={`${styles.roleChip} ${selectedAgent === member.name ? styles.selected : ''}`}
                            >
                              <input
                                type="radio"
                                name="single-agent"
                                checked={selectedAgent === member.name}
                                onChange={() => setSelectedAgent(member.name)}
                              />
                              <span className={styles.roleAvatar}>
                                <AvatarImage
                                  avatar={member.role?.avatar ?? null}
                                  fallback={member.name}
                                />
                              </span>
                              {member.name}
                            </label>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {selectedGroupChat && selectedAgent && (
                    <div className={styles.field}>
                      <label className={styles.fieldLabel}>模式</label>
                      <div className={styles.roleList}>
                        <label className={`${styles.roleChip} ${styles.selected}`}>
                          <input type="radio" name="fork-mode" checked readOnly />
                          Fork
                        </label>
                        <label
                          className={`${styles.roleChip} ${styles.disabled}`}
                          title="Continue 模式暂未开放"
                        >
                          <input type="radio" name="fork-mode" disabled />
                          Continue
                        </label>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* 单聊名称（可选） */}
              <div className={styles.field}>
                <label className={styles.fieldLabel}>对话名称（可选）</label>
                <input
                  type="text"
                  className={styles.input}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={selectedAgent ? `与 ${selectedAgent} 的对话` : '输入对话名称'}
                />
              </div>
            </>
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
            disabled={!canSubmit || (chatMode === 'group' ? submitting : singleSubmitting)}
          >
            {(chatMode === 'group' ? submitting : singleSubmitting) ? '创建中...' : '创建'}
          </button>
        </div>
      </div>
    </div>
  );
}
