import { useState, useCallback, useEffect } from 'react';
import { TopBar } from '../TopBar';
import { LeftSidebar } from '../LeftSidebar';
import { ChatArea, type RightSidebarContent } from '../ChatArea';
import { RightSidebar } from '../RightSidebar';
import { RoleManagement } from '../RoleManagement';
import { SkillSquare } from '@/features/skills';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import { SingleChatPanel } from '@/features/single-chat/components/SingleChatPanel';
import { ToastContainer } from '@/shared/components';
import styles from './MainLayout.module.css';

type ViewMode = 'chat' | 'role' | 'skill';

export interface MainLayoutProps {
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

export function MainLayout({ theme, onToggleTheme }: MainLayoutProps) {
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('chat');
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(() =>
    Math.round(window.innerWidth * 0.15)
  );
  const [rightSidebarWidth, setRightSidebarWidth] = useState(() =>
    Math.round(window.innerWidth * 0.25)
  );
  const [isResizing, setIsResizing] = useState(false);
  const [rightSidebarContent, setRightSidebarContent] = useState<RightSidebarContent | null>(null);

  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const lastSelectedAt = useSessionStore((s) => s.lastSelectedAt);

  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const displayLocation = useSingleChatStore((s) => s.displayLocation);

  // 当 session 被选中时，自动切换到 chat 视图
  useEffect(() => {
    if (activeSessionId) {
      setViewMode('chat');
    }
  }, [activeSessionId, lastSelectedAt]);

  // When single chat is activated, auto-switch to chat view
  useEffect(() => {
    if (activeSingleChatId) {
      setViewMode('chat');
    }
  }, [activeSingleChatId]);

  // 当有新的预览/diff 内容时，自动展开右侧栏
  useEffect(() => {
    if (rightSidebarContent) {
      setRightSidebarCollapsed(false);
    }
  }, [rightSidebarContent]);

  const handleToggleLeftSidebar = useCallback(() => {
    setLeftSidebarCollapsed((prev) => !prev);
  }, []);

  const handleToggleRightSidebar = useCallback(() => {
    setRightSidebarCollapsed((prev) => !prev);
  }, []);

  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
  }, []);

  const handleLeftResize = useCallback((delta: number) => {
    setLeftSidebarWidth((prev) => Math.max(120, prev + delta));
  }, []);

  const handleRightResize = useCallback((delta: number) => {
    setRightSidebarWidth((prev) => Math.max(120, prev + delta));
  }, []);

  const handleResizeStart = useCallback(() => setIsResizing(true), []);
  const handleResizeEnd = useCallback(() => setIsResizing(false), []);

  return (
    <div className={styles.mainLayout}>
      <TopBar onToggleSidebar={handleToggleLeftSidebar} />
      <div className={styles.mainContainer}>
        <LeftSidebar
          collapsed={leftSidebarCollapsed}
          width={leftSidebarWidth}
          onResize={handleLeftResize}
          resizing={isResizing}
          onResizeStart={handleResizeStart}
          onResizeEnd={handleResizeEnd}
          viewMode={viewMode}
          onViewModeChange={handleViewModeChange}
          theme={theme}
          onToggleTheme={onToggleTheme}
        />
        {viewMode === 'chat' && (
          <>
            {displayLocation === 'main' && activeSingleChatId ? (
              <div className={styles.chatAreaWrapper}>
                <SingleChatPanel />
              </div>
            ) : (
              <ChatArea
                onToggleRightSidebar={handleToggleRightSidebar}
                onContentChange={setRightSidebarContent}
              />
            )}
          </>
        )}
        {viewMode === 'role' && <RoleManagement />}
        {viewMode === 'skill' && <SkillSquare />}
        {viewMode === 'chat' && (
          <RightSidebar
            collapsed={rightSidebarCollapsed}
            width={rightSidebarWidth}
            onResize={handleRightResize}
            resizing={isResizing}
            onResizeStart={handleResizeStart}
            onResizeEnd={handleResizeEnd}
            content={rightSidebarContent}
          />
        )}
      </div>

      {/* Toast 通知 */}
      <ToastContainer />
    </div>
  );
}
