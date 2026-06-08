import { ReactNode, useState } from 'react';
import { Icon, LockIcon } from '../Icon';
import styles from './PermissionRequest.module.css';

export type PermissionStatus = 'pending' | 'approved' | 'rejected';

export interface PermissionRequestProps {
  title: string;
  content: ReactNode;
  timestamp: string | Date;
  onApprove: () => void;
  onReject: () => void;
  status?: PermissionStatus;
  icon?: ReactNode;
  className?: string;
  /** 发起请求的 agent 名称（可选） */
  agentName?: string;
}

function formatTimestamp(ts: string | Date): string {
  const date = typeof ts === 'string' ? new Date(ts) : ts;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function PermissionRequest({
  title,
  content,
  timestamp,
  onApprove,
  onReject,
  status = 'pending',
  icon,
  className = '',
  agentName,
}: PermissionRequestProps) {
  const isResolved = status !== 'pending';
  const [acted, setActed] = useState(false);
  const disabled = isResolved || acted;

  return (
    <div
      className={`${styles.card}${isResolved ? ` ${styles.resolved}` : ''}${className ? ` ${className}` : ''}`}
    >
      <div className={styles.header}>
        <div className={styles.iconWrapper}>{icon ?? <LockIcon size={16} />}</div>
        <div className={styles.titleGroup}>
          <div className={styles.title}>
            {title}
            {agentName && <span className={styles.agentName}>{agentName}</span>}
          </div>
          <div className={styles.time}>{formatTimestamp(timestamp)}</div>
        </div>
      </div>

      <div className={styles.body}>{content}</div>

      <div className={styles.actions}>
        <button
          className={styles.btnReject}
          disabled={disabled}
          onClick={() => {
            setActed(true);
            onReject();
          }}
        >
          <Icon size={13}>
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </Icon>
          拒绝
        </button>
        <button
          className={styles.btnApprove}
          disabled={disabled}
          onClick={() => {
            setActed(true);
            onApprove();
          }}
        >
          <Icon size={13}>
            <polyline points="20 6 9 17 4 12" />
          </Icon>
          允许
        </button>
      </div>

      {isResolved && (
        <div className={styles.resolvedLabel}>{status === 'approved' ? '已允许' : '已拒绝'}</div>
      )}
    </div>
  );
}
