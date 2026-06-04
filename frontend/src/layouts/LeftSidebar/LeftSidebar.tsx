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
        <button className={styles.sidebarBtn}>
          <PlusIcon />
          <span>新对话</span>
        </button>
        <button className={styles.sidebarBtn}>
          <UsersIcon />
          <span>角色管理</span>
        </button>
        <button className={styles.sidebarBtn}>
          <ZapIcon />
          <span>技能广场</span>
        </button>
      </div>

      {/* 项目区 */}
      <div className={styles.sidebarProjects}>
        <div className={styles.sectionTitle}>项目</div>

        <div className={styles.projectItem}>
          <div className={styles.projectName}>
            <FolderIcon />
            feat_group_chat_service
          </div>
        </div>
        <div className={styles.chatItem}>
          <span>测试连接</span>
          <span className={styles.chatTime}>58 分</span>
        </div>
        <div className={styles.chatItem}>
          <span>我现在在准备开始实现docs...</span>
        </div>

        <div className={styles.projectItem}>
          <div className={styles.projectName}>
            <FolderIcon />
            agents-hub
          </div>
        </div>
        <div className={styles.chatItem}>
          <span>当前存在一个问题，docker...</span>
        </div>
        <div className={styles.chatItem}>
          <span>$superpowers:brainstorming...</span>
        </div>
      </div>

      {/* 对话区域 */}
      <div className={styles.sidebarChats}>
        <div className={styles.sectionTitle}>对话</div>
        <div className={styles.chatListItem}>暂无聊天</div>
      </div>

      {/* 设置按钮 */}
      <div className={styles.sidebarFooter}>
        <button className={styles.sidebarBtn}>
          <SettingsIcon />
          <span>设置</span>
        </button>
      </div>
    </div>
  );
}
