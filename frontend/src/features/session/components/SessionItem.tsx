import { useState } from 'react';
import { SessionItem as SessionItemType } from '@/shared/adapters/sessionAdapter';
import { useSessionActions } from '../hooks/useSessionActions';
import { useDeleteGroupChat } from '../hooks/useDeleteGroupChat';
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
  const openSingleChat = useSingleChatStore((s) => s.openSingleChat);
  const [showMenu, setShowMenu] = useState(false);

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

  const handleItemClick = () => {
    if (showMenu) return;
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
              <button className="menu-item danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? '删除中...' : '删除群聊'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
