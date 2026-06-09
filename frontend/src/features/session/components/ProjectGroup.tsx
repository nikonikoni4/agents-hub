import { useState } from 'react';
import { ProjectGroup as ProjectGroupType } from '@/shared/adapters/sessionAdapter';
import { SessionItem } from './SessionItem';
import { useSessionStore } from '../store/sessionStore';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import './ProjectGroup.css';

interface ProjectGroupProps {
  group: ProjectGroupType;
  type: 'group_chat' | 'single_chat';
}

export function ProjectGroup({ group, type }: ProjectGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);

  const activeId = type === 'group_chat' ? activeSessionId : activeSingleChatId;

  return (
    <div className="project-group">
      <div className="project-header" onClick={() => setIsExpanded(!isExpanded)}>
        <span className="project-icon">{isExpanded ? '▼' : '▶'}</span>
        <span className="project-name">{group.projectName}</span>
        <span className="session-count">{group.sessions.length}</span>
      </div>
      {isExpanded && (
        <div className="sessions">
          {group.sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
