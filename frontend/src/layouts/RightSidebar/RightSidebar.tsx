import { useState, useEffect, useCallback, useRef } from 'react';
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

function MemberItem({
  member,
  onToggleDocker,
  onCompress,
}: {
  member: MemberWithRole;
  onToggleDocker: (memberName: string, enableDocker: boolean) => void;
  onCompress: (memberName: string) => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭菜单
  useEffect(() => {
    if (!showMenu) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showMenu]);

  const canCompress = member.isOnline && member.status !== 'busy' && !member.compressing;

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
          {member.context_usage != null && member.context_usage > 0 && (
            <span className={styles.memberContext}>{member.context_usage}K</span>
          )}
        </div>
        {member.cwd && (
          <div className={styles.memberCwd} title={member.cwd}>
            📁 {member.cwd}
          </div>
        )}
      </div>
      <div className={styles.memberStatus}>
        <span className={member.status === 'busy' ? styles.statusBusy : styles.statusIdle}>
          {member.compressing ? '压缩中' : member.status === 'busy' ? '忙碌' : '空闲'}
        </span>
      </div>
      <button
        className={styles.dockerToggle}
        onClick={() => onToggleDocker(member.name, !member.use_docker)}
        title={
          member.use_docker ? 'Docker 模式（点击切换到本地）' : '本地模式（点击切换到 Docker）'
        }
      >
        {member.use_docker ? '🐳' : '💻'}
      </button>
      <div className={styles.memberMenuWrapper} ref={menuRef}>
        <button
          className={styles.memberMenuBtn}
          onClick={() => setShowMenu(!showMenu)}
          title="更多操作"
        >
          ⋮
        </button>
        {showMenu && (
          <div className={styles.memberMenuDropdown}>
            <button
              className={styles.memberMenuItem}
              disabled={!canCompress}
              onClick={() => {
                setShowMenu(false);
                onCompress(member.name);
              }}
              title={
                !member.isOnline
                  ? 'Agent 离线'
                  : member.status === 'busy'
                    ? 'Agent 正在执行任务'
                    : member.compressing
                      ? '压缩中...'
                      : '压缩上下文'
              }
            >
              {member.compressing ? '压缩中...' : '压缩上下文'}
            </button>
          </div>
        )}
      </div>
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
  const { members, loading, toggleDockerMode, compressAgent } = useMembers();
  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const displayLocation = useSingleChatStore((s) => s.displayLocation);
  const toggleLocation = useSingleChatStore((s) => s.toggleLocation);
  // 单聊不支持置顶、Agent 调用、任务列表，传 null 跳过 API 调用
  const groupChatId = activeSessionId && !activeSingleChatId ? activeSessionId : null;
  const { pinnedMessages, unpin } = usePinnedMessages(groupChatId);
  const { agentCalls, loading: callsLoading } = useAgentCalls(groupChatId);
  const { taskList, loading: tasksLoading } = useTasks(groupChatId);
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<SidebarTab>('chat');
  const [dockerConfirm, setDockerConfirm] = useState<{
    memberName: string;
    enableDocker: boolean;
  } | null>(null);

  // content 变化时自动切换到对应 tab
  useEffect(() => {
    if (content?.type === 'preview' || content?.type === 'diff' || content?.type === 'web') {
      setActiveTab(content.type);
    }
  }, [content]);

  // 单聊激活时自动切换到 single-chat tab
  useEffect(() => {
    if (activeSingleChatId) {
      setActiveTab('single-chat');
    }
  }, [activeSingleChatId]);

  const handleToggleDocker = useCallback(
    (memberName: string, enableDocker: boolean) => {
      // 开启沙箱时显示确认对话框
      if (enableDocker) {
        setDockerConfirm({ memberName, enableDocker });
      } else {
        // 关闭沙箱直接执行
        toggleDockerMode(memberName).catch((error) => {
          const message = error instanceof Error ? error.message : '切换 Docker 模式失败';
          toast.error(message);
        });
      }
    },
    [toggleDockerMode, toast]
  );

  const handleConfirmDocker = useCallback(async () => {
    if (!dockerConfirm) return;

    try {
      await toggleDockerMode(dockerConfirm.memberName);
    } catch (error) {
      const message = error instanceof Error ? error.message : '切换 Docker 模式失败';
      toast.error(message);
    } finally {
      setDockerConfirm(null);
    }
  }, [dockerConfirm, toggleDockerMode, toast]);

  const handleCancelDocker = useCallback(() => {
    setDockerConfirm(null);
  }, []);

  const handleCompress = useCallback(
    (memberName: string) => {
      compressAgent(memberName).catch((error) => {
        const message = error instanceof Error ? error.message : '压缩上下文失败';
        toast.error(message);
      });
    },
    [compressAgent, toast]
  );

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

      {activeTab === 'single-chat' && (
        <>
          {displayLocation === 'main' ? (
            <div className={styles.placeholder}>
              <p className={styles.placeholderText}>单聊已移至主界面</p>
              <button className={styles.placeholderBtn} onClick={() => toggleLocation()}>
                返回右侧
              </button>
            </div>
          ) : (
            <SingleChatPanel />
          )}
        </>
      )}

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
                    onCompress={handleCompress}
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
            {/* <GlobeIcon /> */}
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
            <div className={styles.webPreviewEmpty}>
              <div className={styles.emptyText}>点击消息中的预览卡片查看网页</div>
            </div>
          )}
        </div>
      )}

      {/* Docker 确认对话框 */}
      {dockerConfirm && (
        <div className={styles.modalOverlay} onClick={handleCancelDocker}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <span>🐳</span>
              <span>开启 Docker 沙箱</span>
            </div>
            <div className={styles.modalBody}>
              <p>开启沙箱会改变当前仓库或子仓库的索引，建议在子仓库中运行，避免干扰主仓库。</p>
              <p>
                是否继续为 <strong>{dockerConfirm.memberName}</strong> 开启沙箱？
              </p>
            </div>
            <div className={styles.modalFooter}>
              <button className={styles.modalCancelBtn} onClick={handleCancelDocker}>
                取消
              </button>
              <button className={styles.modalConfirmBtn} onClick={handleConfirmDocker}>
                确认开启
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
