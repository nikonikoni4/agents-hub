/**
 * ProjectGroup 组件
 *
 * 职责：
 * - 显示项目分组
 * - 管理折叠/展开状态
 * - 渲染该项目下的所有 sessions
 */

import { useState } from 'react';
import { ProjectGroup as ProjectGroupType } from '@/shared/adapters/sessionAdapter';
import { SessionItem } from './SessionItem';
import { useSessionStore } from '../store/sessionStore';
import './ProjectGroup.css';

interface ProjectGroupProps {
  group: ProjectGroupType;
  onSelectSingleChat?: (id: string) => void;
}

export function ProjectGroup({ group, onSelectSingleChat }: ProjectGroupProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const activeSessionId = useSessionStore((state) => state.activeSessionId);

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
              isActive={session.id === activeSessionId}
              onSelectSingleChat={onSelectSingleChat}
            />
          ))}
        </div>
      )}
    </div>
  );
}
