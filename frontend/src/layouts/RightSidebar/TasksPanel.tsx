import { useState } from 'react';
import type { TaskListInfo, TaskInfo, TaskStatus } from '@/shared/types';
import styles from './RightSidebar.module.css';

interface TasksPanelProps {
  taskList: TaskListInfo | null;
  loading: boolean;
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" stroke="currentColor" fill="none" strokeWidth="2">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

const STATUS_ICONS: Record<TaskStatus, string> = {
  completed: '✓',
  running: '●',
  pending: '○',
  failed: '✗',
};

const STATUS_ICON_COLORS: Record<TaskStatus, string> = {
  completed: '#22c55e',
  running: 'var(--accent-color)',
  pending: 'var(--text-tertiary)',
  failed: '#ef4444',
};

const TASK_SORT_ORDER: Record<TaskStatus, number> = {
  running: 0,
  pending: 1,
  completed: 2,
  failed: 3,
};

const STATUS_LABELS: Record<TaskStatus, string> = {
  running: '运行中',
  pending: '等待中',
  completed: '已完成',
  failed: '失败',
};

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

interface TaskDetailDialogProps {
  task: TaskInfo | null;
  onClose: () => void;
}

function TaskDetailDialog({ task, onClose }: TaskDetailDialogProps) {
  if (!task) return null;

  return (
    <div className={styles.callDetailOverlay} onClick={onClose}>
      <div className={styles.callDetailDialog} onClick={(e) => e.stopPropagation()}>
        <div className={styles.callDetailHeader}>
          <h3>任务详情</h3>
          <button type="button" className={styles.callDetailClose} onClick={onClose}>
            ×
          </button>
        </div>
        <div className={styles.callDetailContent}>
          <div className={styles.callDetailRow}>
            <span className={styles.callDetailLabel}>任务 ID</span>
            <span className={styles.callDetailValue}>{task.task_id}</span>
          </div>
          <div className={styles.callDetailRow}>
            <span className={styles.callDetailLabel}>状态</span>
            <span className={styles.callDetailValue}>
              <span
                className={styles.taskStatusIcon}
                style={{ color: STATUS_ICON_COLORS[task.status], marginRight: 6 }}
              >
                {STATUS_ICONS[task.status]}
              </span>
              {STATUS_LABELS[task.status]}
            </span>
          </div>
          <div className={styles.callDetailRow}>
            <span className={styles.callDetailLabel}>负责人</span>
            <span className={styles.callDetailValue}>@{task.owner}</span>
          </div>
          <div className={styles.callDetailRow}>
            <span className={styles.callDetailLabel}>创建者</span>
            <span className={styles.callDetailValue}>{task.created_by}</span>
          </div>
          <div className={styles.callDetailRow}>
            <span className={styles.callDetailLabel}>创建时间</span>
            <span className={styles.callDetailValue}>{formatTime(task.created_at)}</span>
          </div>
          <div className={styles.callDetailRow}>
            <span className={styles.callDetailLabel}>更新时间</span>
            <span className={styles.callDetailValue}>{formatTime(task.updated_at)}</span>
          </div>
          <div className={styles.callDetailSection}>
            <span className={styles.callDetailLabel}>任务内容</span>
            <div className={styles.callDetailMessage}>{task.content}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function TasksPanel({ taskList, loading }: TasksPanelProps) {
  const [selectedTask, setSelectedTask] = useState<TaskInfo | null>(null);
  const tasks = taskList?.tasks ?? [];
  const sortedTasks = [...tasks].sort(
    (a, b) => TASK_SORT_ORDER[a.status] - TASK_SORT_ORDER[b.status]
  );
  const doneCount = tasks.filter((t) => t.status === 'completed').length;
  const totalCount = tasks.length;
  const progress = totalCount > 0 ? (doneCount / totalCount) * 100 : 0;

  return (
    <div className={styles.rightModule}>
      <div className={styles.moduleTitle}>
        <CheckIcon />
        Tasks
        {totalCount > 0 && (
          <span className={styles.moduleBadge}>
            {doneCount}/{totalCount}
          </span>
        )}
      </div>
      {loading ? (
        <div className={styles.emptyText}>加载中...</div>
      ) : tasks.length === 0 ? (
        <div className={styles.emptyText}>暂无任务</div>
      ) : (
        <>
          <div className={styles.taskProgress}>
            <div className={styles.taskProgressBar} style={{ width: `${progress}%` }} />
          </div>
          <div className={styles.taskList}>
            {sortedTasks.map((task) => (
              <div
                key={task.task_id}
                className={styles.taskItem}
                onClick={() => setSelectedTask(task)}
              >
                <span
                  className={styles.taskStatusIcon}
                  style={{ color: STATUS_ICON_COLORS[task.status] }}
                >
                  {STATUS_ICONS[task.status]}
                </span>
                <span className={styles.taskContent}>{task.content}</span>
                <span className={styles.taskOwner}>@{task.owner}</span>
              </div>
            ))}
          </div>
        </>
      )}
      <TaskDetailDialog task={selectedTask} onClose={() => setSelectedTask(null)} />
    </div>
  );
}
