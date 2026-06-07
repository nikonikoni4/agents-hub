import type { TaskListInfo, TaskStatus } from '@/shared/types';
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

export function TasksPanel({ taskList, loading }: TasksPanelProps) {
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
              <div key={task.task_id} className={styles.taskItem}>
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
    </div>
  );
}
