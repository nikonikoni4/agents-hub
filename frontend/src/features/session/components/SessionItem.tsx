/**
 * SessionItem 组件
 *
 * 职责：
 * - 显示单个 session 的信息（群聊或单聊）
 * - 处理点击切换
 * - 显示未读标记
 * - 显示成员聚合头像（群聊）或单人头像（单聊）
 * - 提供删除功能
 */

import { useState } from 'react';
import { SessionItem as SessionItemType } from '@/shared/adapters/sessionAdapter';
import { useSessionActions } from '../hooks/useSessionActions';
import { useSessionStore } from '../store/sessionStore';
import { useDeleteGroupChat } from '../hooks/useDeleteGroupChat';
import { formatRelativeTime } from '@/shared/adapters/sessionAdapter';
import { CompositeAvatar, AvatarImage } from '@/shared/components';
import { storage } from '@/core/storage';
import './SessionItem.css';

interface SessionItemProps {
  session: SessionItemType;
  isActive?: boolean;
  onSelectSingleChat?: (id: string) => void;
}

export function SessionItem({ session, isActive = false, onSelectSingleChat }: SessionItemProps) {
  const { handleSelectSession } = useSessionActions();
  const updateSession = useSessionStore((s) => s.updateSession);
  const { deleteChat, deleting } = useDeleteGroupChat();
  const [showMenu, setShowMenu] = useState(false);

  const isSingleChat = session.type === 'single_chat';

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`确定要删除群聊「${session.title}」吗？`)) {
      return;
    }

    try {
      await deleteChat(session.id, false);
    } catch (error) {
      console.error('删除群聊失败:', error);
      alert('删除失败，请重试');
    } finally {
      setShowMenu(false);
    }
  };

  const handleMenuClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowMenu(!showMenu);
  };

  const handleItemClick = async () => {
    if (showMenu) return;

    if (isSingleChat && onSelectSingleChat) {
      onSelectSingleChat(session.id);
      // 标记单聊为已读
      const now = new Date().toISOString();
      await storage.setLastView(session.id, now);
      updateSession(session.id, { isUnread: false });
    } else {
      handleSelectSession(session.id, 'group_chat');
    }
  };

  return (
    <div
      className={`session-item ${session.isUnread ? 'unread' : ''} ${isActive ? 'active' : ''} ${isSingleChat ? 'single-chat' : ''}`}
      onClick={handleItemClick}
    >
      {isSingleChat ? (
        <div className="session-avatar-single">
          <AvatarImage
            avatar={session.memberAvatars[0] ?? null}
            fallback={session.agentName ?? '?'}
          />
        </div>
      ) : (
        session.memberAvatars.length > 0 && (
          <CompositeAvatar avatars={session.memberAvatars} size={40} />
        )
      )}
      <div className="session-content">
        <div className="session-title">
          {session.title}
          {isSingleChat && <span className="session-type-badge">单聊</span>}
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
          <button className="menu-button" onClick={handleMenuClick} title="更多操作">
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
