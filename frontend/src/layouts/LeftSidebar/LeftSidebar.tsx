import { useState, useEffect } from 'react';
import {
  PlusIcon,
  UsersIcon,
  ZapIcon,
  SettingsIcon,
  BotIcon,
  ResizeHandle,
} from '@/shared/components';
import { SessionList, CreateGroupChatDialog } from '@/features/session';
import { useSessionStore } from '@/features/session/store/sessionStore';
import { useSingleChatStore } from '@/features/single-chat/store/singleChatStore';
import styles from './LeftSidebar.module.css';

export interface LeftSidebarProps {
  collapsed: boolean;
  width?: number;
  onResize?: (delta: number) => void;
  resizing?: boolean;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
  viewMode?: 'chat' | 'role' | 'skill';
  onViewModeChange?: (mode: 'chat' | 'role' | 'skill') => void;
  theme?: 'light' | 'dark';
  onToggleTheme?: () => void;
}

export function LeftSidebar({
  collapsed,
  width,
  onResize,
  resizing,
  onResizeStart,
  onResizeEnd,
  viewMode,
  onViewModeChange,
  theme,
  onToggleTheme,
}: LeftSidebarProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const openDraftChat = useSingleChatStore((s) => s.openDraftChat);

  const activeSessionId = useSessionStore((s) => s.activeSessionId);
  const activeSingleChatId = useSingleChatStore((s) => s.activeSingleChatId);
  const lastSelectedAt = useSessionStore((s) => s.lastSelectedAt);

  // Auto-switch to chat view when a session is selected
  useEffect(() => {
    if (activeSessionId || activeSingleChatId) {
      onViewModeChange?.('chat');
    }
  }, [activeSessionId, activeSingleChatId, lastSelectedAt, onViewModeChange]);

  const handleCreateAssistantChat = () => {
    openDraftChat({
      type: 'new',
      single_chat_name: 'Agents Hub 助手',
      agent_name: 'Agents-Hub-Assistant',
    });
    onViewModeChange?.('chat');
  };

  return (
    <div
      className={`${styles.leftSidebar} ${collapsed ? styles.collapsed : ''}`}
      style={{
        ...(collapsed ? { width: 0 } : width !== undefined ? { width: `${width}px` } : {}),
        ...(resizing ? { transition: 'none' } : {}),
      }}
    >
      {!collapsed && onResize && (
        <ResizeHandle
          direction="left"
          onResize={onResize}
          onResizeStart={onResizeStart}
          onResizeEnd={onResizeEnd}
        />
      )}
      {/* 按钮区 */}
      <div className={styles.sidebarButtons}>
        <button
          className={styles.sidebarBtn}
          onClick={() => setShowCreateDialog(true)}
          aria-label="新建对话"
        >
          <PlusIcon />
          <span>新对话</span>
        </button>
        <button
          className={`${styles.sidebarBtn} ${viewMode === 'role' ? styles.active : ''}`}
          onClick={() => onViewModeChange?.('role')}
          aria-label="角色管理"
        >
          <UsersIcon />
          <span>角色管理</span>
        </button>
        <button
          className={`${styles.sidebarBtn} ${viewMode === 'skill' ? styles.active : ''}`}
          onClick={() => onViewModeChange?.('skill')}
          aria-label="技能广场"
        >
          <ZapIcon />
          <span>技能广场</span>
        </button>
        <button
          className={styles.sidebarBtn}
          onClick={handleCreateAssistantChat}
          aria-label="Agents Hub 助手"
        >
          <BotIcon />
          <span>Agents Hub 助手</span>
        </button>
      </div>

      {/* Session 列表区（按项目分组） */}
      <div className={styles.sidebarSessions}>
        <SessionList />
      </div>

      {/* 设置按钮 */}
      <div className={styles.sidebarFooter}>
        <button className={styles.sidebarBtn} aria-label="设置">
          <SettingsIcon />
          <span>设置</span>
        </button>
        {onToggleTheme && (
          <button className={styles.sidebarBtn} onClick={onToggleTheme} aria-label="切换主题">
            {theme === 'light' ? (
              <svg
                viewBox="0 0 24 24"
                stroke="currentColor"
                fill="none"
                strokeWidth="2"
                width="18"
                height="18"
              >
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            ) : (
              <svg
                viewBox="0 0 24 24"
                stroke="currentColor"
                fill="none"
                strokeWidth="2"
                width="18"
                height="18"
              >
                <circle cx="12" cy="12" r="5" />
                <path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
              </svg>
            )}
            <span>{theme === 'light' ? '深色模式' : '浅色模式'}</span>
          </button>
        )}
      </div>

      <CreateGroupChatDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={() => onViewModeChange?.('chat')}
      />
    </div>
  );
}
