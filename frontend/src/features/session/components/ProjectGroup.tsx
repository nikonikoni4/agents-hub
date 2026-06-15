import { useState, useEffect } from 'react';
import { SessionItem } from './SessionItem';
import { useSessionStore } from '../store/sessionStore';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { useProjectGroupChats } from '../hooks/useProjectGroupChats';
import type { ProjectGroup as ProjectGroupType } from '@/shared/adapters/sessionAdapter';
import './ProjectGroup.css';

interface ProjectGroupProps {
  group: ProjectGroupType;
  type: 'group_chat' | 'single_chat';
}

export function ProjectGroup({ group, type }: ProjectGroupProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);

  const activeId = type === 'group_chat' ? activeSessionId : activeSingleChatId;

  // 只有群聊才使用懒加载
  const { sessions, hasMore, isLoading, totalCount, loadMore } = useProjectGroupChats(
    type === 'group_chat' ? group.projectPath : ''
  );

  // 展开时首次加载
  useEffect(() => {
    if (type === 'group_chat' && isExpanded && sessions.length === 0 && hasMore) {
      loadMore();
    }
  }, [type, isExpanded, sessions.length, hasMore, loadMore]);

  // 群聊：使用懒加载数据；单聊：使用一次性加载数据
  const displaySessions = type === 'group_chat' ? sessions : group.sessions || [];

  // 群聊：显示总数；单聊：显示实际长度
  const displayCount = type === 'group_chat' ? totalCount : group.sessions?.length || 0;

  return (
    <div className="project-group">
      <div className="project-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span className="project-icon">{isExpanded ? '▼' : '▶'}</span>
        <span className="project-name">{group.projectName}</span>
        <span className="session-count">{displayCount}</span>
      </div>
      {isExpanded && (
        <div className="sessions">
          {displaySessions.map((session) => (
            <SessionItem key={session.id} session={session} isActive={session.id === activeId} />
          ))}

          {/* 群聊才显示加载更多按钮 */}
          {type === 'group_chat' && hasMore && (
            <button className="load-more-btn" onClick={loadMore} disabled={isLoading}>
              {isLoading ? '加载中...' : `加载更多 (${displayCount - sessions.length} 个)`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
