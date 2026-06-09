import { useState, useMemo } from 'react';
import { useGroupChatList } from '../hooks/useGroupChatList';
import { useSingleChatList } from '@/features/single-chat/hooks/useSingleChatList';
import { groupSingleChatsByProject } from '@/shared/adapters/sessionAdapter';
import { ProjectGroup } from './ProjectGroup';
import './SessionList.css';

type SessionTab = 'group' | 'single';

export function SessionList() {
  const [activeTab, setActiveTab] = useState<SessionTab>('group');
  const { projectGroups: groupChatGroups } = useGroupChatList();
  const { singleChats } = useSingleChatList();

  const singleChatGroups = useMemo(() => groupSingleChatsByProject(singleChats), [singleChats]);

  const groups = activeTab === 'group' ? groupChatGroups : singleChatGroups;

  return (
    <div className="session-list">
      <div className="session-tabs">
        <button
          className={`session-tab ${activeTab === 'group' ? 'active' : ''}`}
          onClick={() => setActiveTab('group')}
        >
          群聊
        </button>
        <button
          className={`session-tab ${activeTab === 'single' ? 'active' : ''}`}
          onClick={() => setActiveTab('single')}
        >
          单聊
        </button>
      </div>
      {groups.length === 0 ? (
        <div className="session-list-empty">
          <p>{activeTab === 'group' ? '暂无群聊' : '暂无单聊'}</p>
        </div>
      ) : (
        groups.map((group) => (
          <ProjectGroup
            key={group.projectPath}
            group={group}
            type={activeTab === 'group' ? 'group_chat' : 'single_chat'}
          />
        ))
      )}
    </div>
  );
}
