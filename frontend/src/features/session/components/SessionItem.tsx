import { useState } from 'react';
import { SessionItem as SessionItemType } from '@/shared/adapters/sessionAdapter';
import { useSessionActions } from '../hooks/useSessionActions';
import { useDeleteGroupChat } from '../hooks/useDeleteGroupChat';
import { useForkGroupChat } from '../hooks/useForkGroupChat';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { formatRelativeTime } from '@/shared/adapters/sessionAdapter';
import './SessionItem.css';

interface SessionItemProps {
  session: SessionItemType;
  isActive?: boolean;
}

export function SessionItem({ session, isActive = false }: SessionItemProps) {
  const { handleSelectSession } = useSessionActions();
  const { deleteChat, deleting } = useDeleteGroupChat();
  const { forkChat, forking } = useForkGroupChat();
  const openSingleChat = useSingleChatStore((s) => s.openSingleChat);
  const [showMenu, setShowMenu] = useState(false);
  const [showForkInput, setShowForkInput] = useState(false);
  const [forkName, setForkName] = useState('');

  const isSingleChat = session.type === 'single_chat';

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`确定要删除群聊「${session.title}」吗？`)) return;
    try {
      await deleteChat(session.id, false);
    } catch {
      alert('删除失败，请重试');
    } finally {
      setShowMenu(false);
    }
  };

  const handleForkClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setForkName(`${session.title} (fork)`);
    setShowForkInput(true);
    setShowMenu(false);
  };

  const handleForkConfirm = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!forkName.trim()) return;
    try {
      const newId = await forkChat(session.id, forkName.trim());
      handleSelectSession(newId);
    } catch {
      alert('Fork 失败，请重试');
    } finally {
      setShowForkInput(false);
    }
  };

  const handleForkCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowForkInput(false);
  };

  const handleItemClick = () => {
    if (showMenu || showForkInput) return;
    if (isSingleChat) {
      openSingleChat(session.id);
    } else {
      handleSelectSession(session.id);
    }
  };

  return (
    <div
      className={`session-item ${session.isUnread ? 'unread' : ''} ${isActive ? 'active' : ''}`}
      onClick={handleItemClick}
    >
      <div className="session-content">
        <div className="session-title">
          <span className="session-type-badge">{isSingleChat ? '单聊' : '群聊'}</span>
          {session.title}
        </div>
        <div className="session-preview">{session.preview}</div>
        <div className="session-meta">
          <span className="session-time">
            {session.lastViewAt
              ? formatRelativeTime(session.lastViewAt)
              : formatRelativeTime(session.lastUpdateAt)}
          </span>
          {session.isUnread && <span className="unread-badge">●</span>}
        </div>
      </div>
      {!isSingleChat && (
        <div className="session-actions">
          <button
            className="menu-button"
            onClick={(e) => {
              e.stopPropagation();
              setShowMenu(!showMenu);
            }}
            title="更多操作"
          >
            ⋮
          </button>
          {showMenu && (
            <div className="context-menu">
              <button className="menu-item" onClick={handleForkClick}>
                Fork 群聊
              </button>
              <button className="menu-item danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? '删除中...' : '删除群聊'}
              </button>
            </div>
          )}
          {showForkInput && (
            <div className="fork-input-container" onClick={(e) => e.stopPropagation()}>
              <input
                className="fork-input"
                value={forkName}
                onChange={(e) => setForkName(e.target.value)}
                placeholder="输入新群聊名称"
                autoFocus
              />
              <div className="fork-actions">
                <button className="fork-confirm" onClick={handleForkConfirm} disabled={forking}>
                  {forking ? 'Fork 中...' : '确认'}
                </button>
                <button className="fork-cancel" onClick={handleForkCancel}>
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
