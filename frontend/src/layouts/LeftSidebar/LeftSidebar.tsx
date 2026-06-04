import styles from './LeftSidebar.module.css';

export interface LeftSidebarProps {
  collapsed: boolean;
}

// SVG 图标组件
function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M12 5v14m7-7H5" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function ZapIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v6m0 6v6" />
    </svg>
  );
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
