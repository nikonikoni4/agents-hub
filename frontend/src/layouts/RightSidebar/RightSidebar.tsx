import styles from './RightSidebar.module.css';

export interface RightSidebarProps {
  collapsed: boolean;
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

export function RightSidebar({ collapsed }: RightSidebarProps) {
  return (
    <div className={`${styles.rightSidebar} ${collapsed ? styles.collapsed : ''}`}>
      <div className={styles.rightModule}>
        <div className={styles.moduleTitle}>
          <UsersIcon />
          成员列表
        </div>
        <div className={styles.moduleItem}>暂无成员</div>
      </div>

      <div className={styles.rightModule}>
        <div className={styles.moduleTitle}>
          <EyeIcon />
          预览
        </div>
        <div className={styles.moduleItem}>无预览内容</div>
      </div>

      <div className={styles.rightModule}>
        <div className={styles.moduleTitle}>
          <MaximizeIcon />
          Diff
        </div>
        <div className={styles.moduleItem}>无代码差异</div>
      </div>
    </div>
  );
}
