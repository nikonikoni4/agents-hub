import { useState } from 'react';
import { PlusIcon, UsersIcon, ZapIcon, SettingsIcon } from '@/shared/components';
import { SessionList, CreateGroupChatDialog } from '@/features/session';
import styles from './LeftSidebar.module.css';

export interface LeftSidebarProps {
  collapsed: boolean;
  onViewModeChange?: (mode: 'chat' | 'role' | 'skill') => void;
}

export function LeftSidebar({ collapsed, onViewModeChange }: LeftSidebarProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  return (
    <div className={`${styles.leftSidebar} ${collapsed ? styles.collapsed : ''}`}>
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
          className={styles.sidebarBtn}
          onClick={() => onViewModeChange?.('role')}
          aria-label="角色管理"
        >
          <UsersIcon />
          <span>角色管理</span>
        </button>
        <button
          className={styles.sidebarBtn}
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
