import { useState, useEffect } from 'react';
import { useMembers, MemberWithRole } from '@/features/chat/hooks';
import { usePinnedMessages } from '@/features/chat/hooks/usePinnedMessages';
import { useAgentCalls } from '@/features/chat/hooks/useAgentCalls';
import { useTasks } from '@/features/chat/hooks/useTasks';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { SingleChatPanel } from '@/features/single-chat/components/SingleChatPanel';
import { AvatarImage, ResizeHandle, DiffViewer, MarkdownRenderer } from '@/shared/components';
import { useToast } from '@/shared/components/Toast/useToast';
import { RightSidebarContent } from '@/shared/types/layout';
import { AgentCallsPanel } from './AgentCallsPanel';
import { TasksPanel } from './TasksPanel';
import styles from './RightSidebar.module.css';

type SidebarTab = 'single-chat' | 'chat' | 'tasks' | 'preview' | 'diff' | 'web';

/** 将 file:/// URL 转换为后端 HTTP 代理 URL */
function toPreviewUrl(url: string): string {
  if (url.startsWith('file:///')) {
    const filePath = decodeURIComponent(url.slice(8));
    return `/api/v1/files/preview?path=${encodeURIComponent(filePath)}`;
  }
  return url;
}

const TAB_LABELS: Record<SidebarTab, string> = {
  'single-chat': '单聊',
  chat: '群聊',
  tasks: '任务',
  preview: '预览',
  diff: 'Diff',
  web: '网页',
};

export interface RightSidebarProps {
  collapsed: boolean;
  width?: number;
  onResize?: (delta: number) => void;
  resizing?: boolean;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
  content?: RightSidebarContent | null;
}

// SVG 图标组件

function UsersIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function MaximizeIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5" />
    </svg>
  );
}

function GlobeIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function MemberItem({
  member,
  onToggleDocker,
}: {
  member: MemberWithRole;
  onToggleDocker: (memberName: string) => void;
}) {
  return (
    <div className={styles.memberItem}>
      <div className={styles.memberAvatar}>
        <AvatarImage avatar={member.role?.avatar ?? null} fallback={member.name} />
      </div>
      <div className={styles.memberInfo}>
        <div className={styles.memberName}>{member.name}</div>
        <div className={styles.memberRole}>
          {member.role?.type === 'leader' ? '负责人' : '成员'}
          <span className={styles.memberPlatform}>{member.role?.platform ?? 'unknown'}</span>
        </div>
        {member.cwd && (
          <div className={styles.memberCwd} title={member.cwd}>
            📁 {member.cwd}
          </div>
        )}
      </div>
      <div className={styles.memberStatus}>
        <span className={member.status === 'busy' ? styles.statusBusy : styles.statusIdle}>
          {member.status === 'busy' ? '忙碌' : '空闲'}
        </span>
      </div>
      <button
        className={styles.dockerToggle}
        onClick={() => onToggleDocker(member.name)}
        title={
          member.use_docker ? 'Docker 模式（点击切换到本地）' : '本地模式（点击切换到 Docker）'
        }
      >
        {member.use_docker ? '🐳' : '💻'}
      </button>
      <div className={member.isOnline ? styles.onlineDot : styles.offlineDot} />
    </div>
  );
}

export function RightSidebar({
  collapsed,
  width,
  onResize,
  resizing,
  onResizeStart,
  onResizeEnd,
  content,
}: RightSidebarProps) {
  const { members, loading, toggleDockerMode } = useMembers();
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const { pinnedMessages, unpin } = usePinnedMessages(activeSessionId);
  const { agentCalls, loading: callsLoading } = useAgentCalls(activeSessionId);
  const { taskList, loading: tasksLoading } = useTasks(activeSessionId);
  const toast = useToast();
  const isSingleChatOpen = useSingleChatStore((s) => s.isPanelOpen);
  const [activeTab, setActiveTab] = useState<SidebarTab>('chat');

  // content 变化时自动切换到对应 tab
  useEffect(() => {
    if (content?.type === 'preview' || content?.type === 'diff' || content?.type === 'web') {
      setActiveTab(content.type);
    }
  }, [content]);

  // 单聊面板打开时自动切换到 single-chat tab
  useEffect(() => {
    if (isSingleChatOpen) {
      setActiveTab('single-chat');
    }
  }, [isSingleChatOpen]);

  const handleToggleDocker = async (memberName: string) => {
    try {
      await toggleDockerMode(memberName);
    } catch (error) {
      const message = error instanceof Error ? error.message : '切换 Docker 模式失败';
      toast.error(message);
    }
  };

  return (
    <div
      className={`${styles.rightSidebar} ${collapsed ? styles.collapsed : ''}`}
      style={{
        ...(collapsed ? { width: 0 } : width !== undefined ? { width: `${width}px` } : {}),
        ...(resizing ? { transition: 'none' } : {}),
        ...(activeTab === 'single-chat' ? { overflow: 'hidden' } : {}),
      }}
    >
      {!collapsed && onResize && (
        <ResizeHandle
          direction="right"
          onResize={onResize}
          onResizeStart={onResizeStart}
          onResizeEnd={onResizeEnd}
        />
      )}

      <div className={styles.tabBar}>
        {(Object.keys(TAB_LABELS) as SidebarTab[]).map((tab) => (
          <button
            key={tab}
            className={`${styles.tabButton} ${activeTab === tab ? styles.tabActive : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {activeTab === 'single-chat' && <SingleChatPanel />}

      {activeTab === 'chat' && (
        <>
          <div className={styles.rightModule}>
            <div className={styles.moduleTitle}>
              <UsersIcon />
              成员列表
            </div>
            <div className={styles.memberList}>
              {loading ? (
                <div className={styles.emptyText}>加载中...</div>
              ) : members.length === 0 ? (
                <div className={styles.emptyText}>暂无成员</div>
              ) : (
                members.map((member) => (
                  <MemberItem
                    key={member.name}
                    member={member}
                    onToggleDocker={handleToggleDocker}
                  />
                ))
              )}
            </div>
          </div>

          <div className={styles.rightModule}>
            <div className={styles.moduleTitle}>
              <span>📌</span>
              <span>Pinned</span>
            </div>
            {pinnedMessages.length === 0 ? (
              <div className={styles.emptyText}>暂无置顶消息</div>
            ) : (
              <div className={styles.pinnedList}>
                {pinnedMessages.map((p) => (
                  <div key={p.message_id} className={styles.pinnedItem}>
                    <div className={styles.pinnedContent}>
                      <span className={styles.pinnedSpeaker}>{p.speaker}</span>
                      <span className={styles.pinnedText}>{p.content}</span>
                    </div>
                    <button
                      className={styles.pinnedRemove}
                      onClick={() => unpin(p.message_id)}
                      title="取消置顶"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {activeTab === 'tasks' && (
        <>
          <AgentCallsPanel agentCalls={agentCalls} loading={callsLoading} />
          <TasksPanel taskList={taskList} loading={tasksLoading} />
        </>
      )}

      {activeTab === 'preview' && (
        <div className={styles.rightModule}>
          <div className={styles.moduleTitle}>
            <EyeIcon />
            预览
          </div>
          {content && content.type === 'preview' ? (
            <div className={styles.moduleContent}>
              <div className={styles.filePathHeader}>{content.filePath}</div>
              <div className={styles.previewContent}>
                <MarkdownRenderer content={content.content} />
              </div>
            </div>
          ) : (
            <div className={styles.emptyText}>无预览内容</div>
          )}
        </div>
      )}

      {activeTab === 'diff' && (
        <div className={styles.rightModule}>
          <div className={styles.moduleTitle}>
            <MaximizeIcon />
            Diff
          </div>
          {content && content.type === 'diff' ? (
            <div className={styles.moduleContent}>
              <div className={styles.filePathHeader}>{content.filePath}</div>
              <DiffViewer diff={content.content} />
            </div>
          ) : (
            <div className={styles.emptyText}>无代码差异</div>
          )}
        </div>
      )}

      {activeTab === 'web' && (
        <div className={styles.webPreviewPanel}>
          <div className={styles.webPreviewHeader}>
            <GlobeIcon />
            <span>网页预览</span>
            {content && content.type === 'web' && (
              <a
                className={styles.webPreviewOpenBtn}
                href={toPreviewUrl(content.url)}
                target="_blank"
                rel="noopener noreferrer"
              >
                在浏览器中打开
              </a>
            )}
          </div>
          {content && content.type === 'web' ? (
            <iframe
              className={styles.webPreviewIframe}
              src={toPreviewUrl(content.url)}
              sandbox="allow-scripts allow-same-origin allow-forms"
              loading="lazy"
              title={content.title || '网页预览'}
            />
          ) : (
            <div className={styles.emptyText}>点击消息中的预览卡片查看网页</div>
          )}
        </div>
      )}
    </div>
  );
}
