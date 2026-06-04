import { useState, useCallback } from 'react';
import { TopBar } from '../TopBar';
import { LeftSidebar } from '../LeftSidebar';
import { ChatArea } from '../ChatArea';
import { RightSidebar } from '../RightSidebar';
import { RoleManagement } from '../RoleManagement';
import { SkillSquare } from '@/features/skills';
import { ToastContainer } from '@/shared/components';
import styles from './MainLayout.module.css';

type ViewMode = 'chat' | 'role' | 'skill';

export interface MainLayoutProps {
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

// 主题图标组件
function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <circle cx="12" cy="12" r="5" />
      <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

export function MainLayout({ theme, onToggleTheme }: MainLayoutProps) {
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('chat');

  const handleToggleLeftSidebar = useCallback(() => {
    setLeftSidebarCollapsed((prev) => !prev);
  }, []);

  const handleToggleRightSidebar = useCallback(() => {
    setRightSidebarCollapsed((prev) => !prev);
  }, []);

  const handleViewModeChange = useCallback((mode: ViewMode) => {
    setViewMode(mode);
  }, []);

  return (
    <div className={styles.mainLayout}>
      <TopBar onToggleSidebar={handleToggleLeftSidebar} />
      <div className={styles.mainContainer}>
        <LeftSidebar collapsed={leftSidebarCollapsed} onViewModeChange={handleViewModeChange} />
        {viewMode === 'chat' && <ChatArea onToggleRightSidebar={handleToggleRightSidebar} />}
        {viewMode === 'role' && <RoleManagement />}
        {viewMode === 'skill' && <SkillSquare />}
        {viewMode === 'chat' && <RightSidebar collapsed={rightSidebarCollapsed} />}
      </div>

      {/* 主题切换按钮 */}
      <button className={styles.themeToggle} onClick={onToggleTheme} aria-label="切换主题">
        {theme === 'light' ? <MoonIcon /> : <SunIcon />}
      </button>

      {/* Toast 通知 */}
      <ToastContainer />
    </div>
  );
}
