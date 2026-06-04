import styles from './ChatArea.module.css';

export interface ChatAreaProps {
  onToggleRightSidebar?: () => void;
}

// SVG 图标组件
function MoreVerticalIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <circle cx="12" cy="12" r="1" />
      <circle cx="12" cy="5" r="1" />
      <circle cx="12" cy="19" r="1" />
    </svg>
  );
}

function RightPanelIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      stroke="currentColor"
      fill="none"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="15" y1="3" x2="15" y2="21" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M12 5v14m7-7H5" />
    </svg>
  );
}

function CheckCircleIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M5 12h14m-7-7 7 7-7 7" />
    </svg>
  );
}

export function ChatArea({ onToggleRightSidebar }: ChatAreaProps) {
  return (
    <div className={styles.chatArea}>
      {/* 对话头部 */}
      <div className={styles.chatHeader}>
        <div className={styles.chatTitle}>测试连接</div>
        <div className={styles.chatActions}>
          <button className={styles.iconBtn}>
            <MoreVerticalIcon />
          </button>
          <button className={styles.iconBtn} onClick={onToggleRightSidebar} title="切换右侧栏">
            <RightPanelIcon />
          </button>
        </div>
      </div>

      {/* 消息区域 */}
      <div className={styles.chatMessages}>
        <div className={styles.message}>
          <div className={styles.messageBubble}>
            <p>在的，连接正常。</p>
          </div>
        </div>
      </div>

      {/* 输入区 */}
      <div className={styles.chatInputContainer}>
        <div className={styles.chatInputWrapper}>
          <button className={styles.iconBtn}>
            <PlusIcon />
          </button>
          <input type="text" className={styles.chatInput} placeholder="要求后续变更" />
          <button className={styles.iconBtn}>
            <CheckCircleIcon />
          </button>
          <div className={styles.versionLabel}>5.5</div>
          <button className={styles.iconBtn}>
            <SendIcon />
          </button>
        </div>
      </div>
    </div>
  );
}
