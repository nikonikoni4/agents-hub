/**
 * SessionItem 组件
 *
 * 职责：
 * - 显示单个 session 的信息
 * - 处理点击切换
 * - 显示未读标记
 * - 显示成员聚合头像
 */

import { SessionItem as SessionItemType } from '@/shared/adapters/sessionAdapter';
import { useSessionActions } from '../hooks/useSessionActions';
import { formatRelativeTime } from '@/shared/adapters/sessionAdapter';
import { CompositeAvatar } from '@/shared/components';
import './SessionItem.css';

interface SessionItemProps {
  session: SessionItemType;
  isActive?: boolean;
}

export function SessionItem({ session, isActive = false }: SessionItemProps) {
  const { handleSelectSession } = useSessionActions();

  return (
    <div
      className={`session-item ${session.isUnread ? 'unread' : ''} ${isActive ? 'active' : ''}`}
      onClick={() => handleSelectSession(session.id)}
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
    </div>
  );
}
