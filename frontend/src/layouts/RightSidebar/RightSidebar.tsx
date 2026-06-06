import { useMembers, MemberWithRole } from '@/features/chat/hooks';
import { AvatarImage, ResizeHandle } from '@/shared/components';
import styles from './RightSidebar.module.css';

export interface RightSidebarProps {
  collapsed: boolean;
  width?: number;
  onResize?: (delta: number) => void;
  resizing?: boolean;
  onResizeStart?: () => void;
  onResizeEnd?: () => void;
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

function MemberItem({ member }: { member: MemberWithRole }) {
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
        </div>
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
}: RightSidebarProps) {
  const { members, loading } = useMembers();

  return (
    <div
      className={`${styles.rightSidebar} ${collapsed ? styles.collapsed : ''}`}
      style={{
        ...(width !== undefined ? { width: `${width}px` } : {}),
        ...(resizing ? { transition: 'none' } : {}),
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
            members.map((member) => <MemberItem key={member.name} member={member} />)
          )}
        </div>
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
