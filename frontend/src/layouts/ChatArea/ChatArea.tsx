import {
  MoreVerticalIcon,
  RightPanelIcon,
  PlusIcon,
  CheckCircleIcon,
  SendIcon,
} from '@/shared/components';
import styles from './ChatArea.module.css';

export interface ChatAreaProps {
  onToggleRightSidebar?: () => void;
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
