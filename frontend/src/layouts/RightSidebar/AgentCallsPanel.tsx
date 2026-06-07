import { useState } from 'react';
import type { AgentCallInfo } from '@/shared/types';
import styles from './RightSidebar.module.css';

interface AgentCallsPanelProps {
  agentCalls: AgentCallInfo[];
  loading: boolean;
}

function CallIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z" />
    </svg>
  );
}

const STATUS_COLORS: Record<string, string> = {
  running: '#22c55e',
  pending: 'var(--text-tertiary)',
  completed: 'var(--accent-color)',
  failed: '#ef4444',
  timeout: '#ef4444',
};

function formatElapsed(startedAt: string | null, completedAt: string | null): string {
  if (!startedAt) return '';
  const start = new Date(startedAt).getTime();
  const end = completedAt ? new Date(completedAt).getTime() : Date.now();
  const seconds = Math.round((end - start) / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSeconds = seconds % 60;
  return `${minutes}m${remainSeconds}s`;
}

export function AgentCallsPanel({ agentCalls, loading }: AgentCallsPanelProps) {
  const [expanded, setExpanded] = useState(false);

  const activeCalls = agentCalls.filter((c) => c.status === 'running' || c.status === 'pending');
  const inactiveCalls = agentCalls.filter((c) => c.status !== 'running' && c.status !== 'pending');
  const showInactive = expanded && inactiveCalls.length > 0;

  function renderCall(call: AgentCallInfo) {
    return (
      <div key={call.call_id} className={styles.callItem}>
        <div className={styles.callHeader}>
          <span
            className={styles.callStatusDot}
            style={{ background: STATUS_COLORS[call.status] }}
          />
          <span className={styles.callFrom}>{call.send_from}</span>
          <span className={styles.callArrow}>&rarr;</span>
          <span className={styles.callTo}>{call.send_to}</span>
          <span className={styles.callElapsed}>
            {formatElapsed(call.started_at, call.completed_at)}
          </span>
        </div>
        <div className={styles.callBody}>
          <span className={styles.callContent}>{call.content}</span>
          <span
            className={call.message_type === 'task' ? styles.callTagTask : styles.callTagNotify}
          >
            {call.message_type === 'task' ? 'TASK' : 'NOTIFY'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.rightModule}>
      <div className={styles.moduleTitle}>
        <CallIcon />
        Agent Calls
        {activeCalls.length > 0 && (
          <span className={styles.moduleBadge}>{activeCalls.length} active</span>
        )}
        {inactiveCalls.length > 0 && (
          <button
            className={styles.moduleToggle}
            onClick={() => setExpanded(!expanded)}
            title={expanded ? '收起已完成' : '展开已完成'}
          >
            {expanded ? '▲' : '▼'} {inactiveCalls.length}
          </button>
        )}
      </div>
      {loading ? (
        <div className={styles.emptyText}>加载中...</div>
      ) : agentCalls.length === 0 ? (
        <div className={styles.emptyText}>无活跃调用</div>
      ) : (
        <div className={styles.callList}>
          {activeCalls.map(renderCall)}
          {showInactive && (
            <>
              <div className={styles.callDivider} />
              {inactiveCalls.map(renderCall)}
            </>
          )}
        </div>
      )}
    </div>
  );
}
