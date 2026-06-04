import { PlusIcon, UsersIcon, ZapIcon, FolderIcon, SettingsIcon } from '@/shared/components';
import styles from './LeftSidebar.module.css';

export interface LeftSidebarProps {
  collapsed: boolean;
}

export function LeftSidebar({ collapsed }: LeftSidebarProps) {
  return (
    <div className={`${styles.leftSidebar} ${collapsed ? styles.collapsed : ''}`}>
      {/* 按钮区 */}
      <div className={styles.sidebarButtons}>
        <button className={styles.sidebarBtn} aria-label="新建对话">
          <PlusIcon />
          <span>新对话</span>
        </button>
        <button className={styles.sidebarBtn} aria-label="角色管理">
          <UsersIcon />
          <span>角色管理</span>
        </button>
        <button className={styles.sidebarBtn} aria-label="技能广场">
          <ZapIcon />
          <span>技能广场</span>
        </button>
      </div>

      {/* 项目区 */}
      <div className={styles.sidebarProjects}>
        <div className={styles.sectionTitle}>项目</div>

        <button className={styles.projectItem} aria-label="项目 feat_group_chat_service">
          <div className={styles.projectName}>
            <FolderIcon />
            feat_group_chat_service
          </div>
        </button>
        <button className={styles.chatItem} aria-label="测试连接">
          <span>测试连接</span>
          <span className={styles.chatTime}>58 分</span>
        </button>
        <button className={styles.chatItem} aria-label="我现在在准备开始实现docs...">
          <span>我现在在准备开始实现docs...</span>
        </button>

        <button className={styles.projectItem} aria-label="项目 agents-hub">
          <div className={styles.projectName}>
            <FolderIcon />
            agents-hub
          </div>
        </button>
        <button className={styles.chatItem} aria-label="当前存在一个问题，docker...">
          <span>当前存在一个问题，docker...</span>
        </button>
        <button className={styles.chatItem} aria-label="$superpowers:brainstorming...">
          <span>$superpowers:brainstorming...</span>
        </button>
      </div>

      {/* 对话区域 */}
      <div className={styles.sidebarChats}>
        <div className={styles.sectionTitle}>对话</div>
        <div className={styles.chatListItem}>暂无聊天</div>
      </div>

      {/* 设置按钮 */}
      <div className={styles.sidebarFooter}>
        <button className={styles.sidebarBtn} aria-label="设置">
          <SettingsIcon />
          <span>设置</span>
        </button>
      </div>
    </div>
  );
}
