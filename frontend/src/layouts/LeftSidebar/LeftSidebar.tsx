import { useState } from 'react';
import { PlusIcon, UsersIcon, ZapIcon, SettingsIcon, ResizeHandle } from '@/shared/components';
import { SessionList, CreateGroupChatDialog } from '@/features/session';
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
}: LeftSidebarProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);

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
      </div>

      <CreateGroupChatDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onSuccess={() => onViewModeChange?.('chat')}
      />
    </div>
  );
}
