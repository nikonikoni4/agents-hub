/**
 * LoopStatusPanel 组件
 *
 * 侧边栏 Loop 状态面板，显示 Loop 节点列表和执行状态。
 *
 * 功能：
 * - 下拉菜单：切换显示不同的 Loop 定义
 * - 节点列表：垂直排列，显示节点名称和状态样式
 * - 状态标识：显示 Loop 执行状态
 * - 进度显示：显示当前迭代次数
 * - 空状态：显示"暂无Loop定义"
 * - 点击节点列表打开详情模态框
 */

import { useCallback, useState } from 'react';
import { useLoopStatus } from '../hooks/useLoopStatus';
import type { LoopNodeApiItem, LoopExecutionApiItem } from '@/shared/types';
import { getNodeStatus, getExecutionStatusText } from '@/shared/adapters';
import { LoopDetailModal } from './LoopDetailModal';
import styles from './LoopStatusPanel.module.css';

interface LoopStatusPanelProps {
  chatId: string | null;
}

/** 执行状态 ID 到 CSS 类名的映射 */
const STATUS_CLASS_MAP: Record<string, string> = {
  created: styles.statusInactive || '',
  running: styles.statusRunning || '',
  paused: styles.statusPaused || '',
  completed: styles.statusCompleted || '',
  failed: styles.statusFailed || '',
  inactive: styles.statusInactive || '',
};

/**
 * 节点项组件
 */
function NodeItem({
  node,
  index,
  execution,
}: {
  node: LoopNodeApiItem;
  index: number;
  execution: LoopExecutionApiItem | null;
}) {
  const status = getNodeStatus(index, execution);
  const statusClassName = `loopNode${status.charAt(0).toUpperCase() + status.slice(1)}`;

  return (
    <div className={`${styles.loopNode} ${styles[statusClassName as keyof typeof styles] || ''}`}>
      <div className={styles.loopNodeIndicator} />
      <div className={styles.loopNodeInfo}>
        <div className={styles.loopNodeName}>{node.agent_name}</div>
        <div className={styles.loopNodeRole}>{node.role_description}</div>
      </div>
      <div className={styles.loopNodeType}>{node.node_type === 'terminator' ? '判断' : '执行'}</div>
    </div>
  );
}

export function LoopStatusPanel({ chatId }: LoopStatusPanelProps) {
  const { loops, selectedLoop, execution, isLoading, selectLoop } = useLoopStatus(chatId);

  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleSelectLoop = useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const loopId = e.target.value;
      if (loopId) {
        selectLoop(loopId);
      }
    },
    [selectLoop]
  );

  const handleOpenModal = useCallback(() => {
    setIsModalOpen(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setIsModalOpen(false);
  }, []);

  // 空状态
  if (!isLoading && loops.length === 0) {
    return (
      <div className={styles.loopPanel}>
        <div className={styles.loopPanelHeader}>
          <span className={styles.loopPanelIcon}>🔄</span>
          <span className={styles.loopPanelTitle}>Loop</span>
        </div>
        <div className={styles.loopEmptyState}>暂无Loop定义</div>
      </div>
    );
  }

  const statusInfo = getExecutionStatusText(execution);

  return (
    <div className={styles.loopPanel}>
      <div className={styles.loopPanelHeader}>
        <span className={styles.loopPanelIcon}>🔄</span>
        <span className={styles.loopPanelTitle}>Loop</span>
        {execution && (
          <span
            className={`${styles.loopStatusBadge} ${STATUS_CLASS_MAP[statusInfo.statusId] || ''}`}
          >
            {statusInfo.text}
          </span>
        )}
      </div>

      {/* 下拉菜单 */}
      {loops.length > 1 && (
        <div className={styles.loopSelectWrapper}>
          <select
            className={styles.loopSelect}
            value={selectedLoop?.loop_id || ''}
            onChange={handleSelectLoop}
          >
            {loops.map((loop) => (
              <option key={loop.loop_id} value={loop.loop_id}>
                {loop.name || loop.loop_id}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* 进度显示 */}
      {execution && (
        <div className={styles.loopProgress}>
          迭代 {execution.current_iteration} / {selectedLoop?.max_iterations || '?'}
        </div>
      )}

      {/* 节点列表 - 点击打开详情模态框 */}
      {selectedLoop && (
        <div
          className={styles.loopNodeList}
          onClick={handleOpenModal}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              handleOpenModal();
            }
          }}
        >
          {selectedLoop.nodes.map((node, index) => (
            <NodeItem key={node.node_id} node={node} index={index} execution={execution} />
          ))}
        </div>
      )}

      {/* 加载状态 */}
      {isLoading && <div className={styles.loopLoading}>加载中...</div>}

      {/* 详情模态框 */}
      <LoopDetailModal
        isOpen={isModalOpen}
        loop={selectedLoop}
        execution={execution}
        onClose={handleCloseModal}
      />
    </div>
  );
}
