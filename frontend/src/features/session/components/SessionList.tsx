/**
 * SessionList 组件
 *
 * 职责：
 * - 获取并显示 session 列表（群聊 + 单聊）
 * - 按项目分组展示
 * - 处理加载和错误状态
 */

import { useSessionList } from '../hooks/useSessionList';
import { ProjectGroup } from './ProjectGroup';
import './SessionList.css';

interface SessionListProps {
  onSelectSingleChat?: (id: string) => void;
}

export function SessionList({ onSelectSingleChat }: SessionListProps) {
  const { projectGroups } = useSessionList();

  if (projectGroups.length === 0) {
    return (
      <div className="session-list-empty">
        <p>暂无会话</p>
      </div>
    );
  }

  return (
    <div className="session-list">
      {projectGroups.map((group) => (
        <ProjectGroup
          key={group.projectPath}
          group={group}
          onSelectSingleChat={onSelectSingleChat}
        />
      ))}
    </div>
  );
}
