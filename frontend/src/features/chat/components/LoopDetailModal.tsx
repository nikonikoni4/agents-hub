/**
 * LoopDetailModal 组件
 *
 * Loop 详情模态框，以垂直节点图形式展示详细的 Loop 状态。
 * 点击节点可在右侧显示节点详情面板。
 */

import { useState } from 'react';
import type { LoopDetailApiResponse, LoopExecutionApiItem, LoopNodeApiItem } from '@/shared/types';
import { getNodeStatus, getExecutionStatusText } from '@/shared/adapters';
import { LoopNodeDetail } from './LoopNodeDetail';
import styles from './LoopDetailModal.module.css';

interface LoopDetailModalProps {
  isOpen: boolean;
  loop: LoopDetailApiResponse | null;
  execution: LoopExecutionApiItem | null;
  onClose: () => void;
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
  isLast,
  isSelected,
  onClick,
}: {
  node: LoopNodeApiItem;
  index: number;
  execution: LoopExecutionApiItem | null;
  isLast: boolean;
  isSelected: boolean;
  onClick: () => void;
}) {
  const status = getNodeStatus(index, execution);
  const statusClassName = `node${status.charAt(0).toUpperCase() + status.slice(1)}`;

  return (
    <div className={styles.nodeConnector}>
      <div
        className={`${styles.node} ${styles[statusClassName as keyof typeof styles] || ''} ${isSelected ? styles.nodeSelected || '' : ''}`}
        onClick={onClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') onClick();
        }}
      >
        <div className={styles.nodeName}>{node.agent_name}</div>
        <div className={styles.nodeRole}>{node.role_description}</div>
      </div>
      {!isLast && <div className={styles.nodeArrow} />}
    </div>
  );
}

export function LoopDetailModal({ isOpen, loop, execution, onClose }: LoopDetailModalProps) {
  const [selectedNodeIndex, setSelectedNodeIndex] = useState<number | null>(0);

  if (!isOpen || !loop) {
    return null;
  }

  const statusInfo = getExecutionStatusText(execution);
  const hasError = execution?.status === 'failed' && execution.error_message;
  const selectedNode = selectedNodeIndex !== null ? loop.nodes[selectedNodeIndex] : null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h3 className={styles.title}>{loop.name || loop.loop_id}</h3>
          <button className={styles.closeBtn} onClick={onClose}>
            ×
          </button>
        </div>
        <div className={styles.content}>
          {/* 状态标识 */}
          <div className={`${styles.statusBadge} ${STATUS_CLASS_MAP[statusInfo.statusId] || ''}`}>
            {statusInfo.text}
          </div>

          {/* 迭代次数 */}
          <div className={styles.iterationInfo}>
            迭代 {execution?.current_iteration || 0} / {loop.max_iterations}
          </div>

          {/* 主内容区域：节点图 + 详情面板 */}
          <div className={styles.mainArea}>
            {/* 垂直节点图 */}
            <div className={styles.nodeList}>
              {loop.nodes.map((node, index) => (
                <NodeItem
                  key={node.node_id}
                  node={node}
                  index={index}
                  execution={execution}
                  isLast={index === loop.nodes.length - 1}
                  isSelected={selectedNodeIndex === index}
                  onClick={() => setSelectedNodeIndex(selectedNodeIndex === index ? null : index)}
                />
              ))}
            </div>

            {/* 节点详情面板 */}
            {selectedNode && (
              <div className={styles.detailPanel}>
                <LoopNodeDetail node={selectedNode} />
              </div>
            )}
          </div>

          {/* 错误信息 */}
          {hasError && <div className={styles.errorMessage}>{execution.error_message}</div>}
        </div>
      </div>
    </div>
  );
}
