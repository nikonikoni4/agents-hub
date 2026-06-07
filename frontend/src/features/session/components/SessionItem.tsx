/**
 * SessionItem 组件
 *
 * 职责：
 * - 显示单个 session 的信息
 * - 处理点击切换
 * - 显示未读标记
 * - 显示成员聚合头像
 * - 提供删除群聊功能
 */

import { useState } from 'react';
import { SessionItem as SessionItemType } from '@/shared/adapters/sessionAdapter';
import { useSessionActions } from '../hooks/useSessionActions';
import { useDeleteGroupChat } from '../hooks/useDeleteGroupChat';
import { formatRelativeTime } from '@/shared/adapters/sessionAdapter';
import { CompositeAvatar } from '@/shared/components';
import './SessionItem.css';

interface SessionItemProps {
  session: SessionItemType;
  isActive?: boolean;
}

export function SessionItem({ session, isActive = false }: SessionItemProps) {
  const { handleSelectSession } = useSessionActions();
  const { deleteChat, deleting } = useDeleteGroupChat();
  const [showMenu, setShowMenu] = useState(false);

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

  const handleItemClick = () => {
    if (!showMenu) {
      handleSelectSession(session.id);
    }
  };

  return (
    <div
      className={`session-item ${session.isUnread ? 'unread' : ''} ${isActive ? 'active' : ''}`}
      onClick={handleItemClick}
    >
      {session.memberAvatars.length > 0 && (
        <CompositeAvatar avatars={session.memberAvatars} size={40} />
      )}
      <div className="session-content">
        <div className="session-title">{session.title}</div>
        <div className="session-preview">{session.preview}</div>
        <div className="session-meta">
          <span className="session-time">{formatRelativeTime(session.lastUpdateAt)}</span>
          {session.isUnread && <span className="unread-badge">●</span>}
        </div>
      </div>
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
    </div>
  );
}
