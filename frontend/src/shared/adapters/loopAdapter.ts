/**
 * Loop 相关 Adapter
 *
 * 提供 Loop 状态计算等纯逻辑函数，供 LoopStatusPanel 和 LoopDetailModal 复用。
 *
 * 设计决策：
 * - getNodeStatus / getExecutionStatusText 是纯逻辑，不依赖 CSS 模块
 * - CSS 样式映射由各组件自行处理（因为不同组件的 CSS 类名不同）
 * - 早期恒等 adapter 函数已移除，待实际需要类型转换时再添加
 */

import type { LoopExecutionApiItem } from '@/shared/types/api-schemas';

// ==================== 状态计算函数 ====================

/** 节点状态类型 */
export type NodeStatus = 'completed' | 'current' | 'pending';

/**
 * 根据执行状态计算节点状态
 *
 * @param nodeIndex - 节点在列表中的索引
 * @param execution - 当前执行状态（可为 null）
 * @returns 节点状态：completed / current / pending
 */
export function getNodeStatus(
  nodeIndex: number,
  execution: LoopExecutionApiItem | null
): NodeStatus {
  if (!execution) return 'pending';
  if (nodeIndex < execution.current_node_index) return 'completed';
  if (nodeIndex === execution.current_node_index) return 'current';
  return 'pending';
}

/** 执行状态显示信息（纯逻辑，不含 CSS 类名） */
export interface ExecutionStatusText {
  /** 显示文本 */
  text: string;
  /** 状态标识，用于组件自行映射 CSS 类 */
  statusId: 'created' | 'running' | 'paused' | 'completed' | 'failed' | 'inactive';
}

/**
 * 获取执行状态的显示文本和状态标识
 *
 * @param execution - 当前执行状态（可为 null）
 * @returns 包含显示文本和状态标识的对象
 */
export function getExecutionStatusText(
  execution: LoopExecutionApiItem | null
): ExecutionStatusText {
  if (!execution) {
    return { text: '未激活', statusId: 'inactive' };
  }

  switch (execution.status) {
    case 'created':
      return { text: '已创建', statusId: 'created' };
    case 'running':
      return { text: '运行中', statusId: 'running' };
    case 'paused':
      return { text: '已暂停', statusId: 'paused' };
    case 'completed':
      return { text: '已完成', statusId: 'completed' };
    case 'failed':
      return { text: '失败', statusId: 'failed' };
    default:
      return { text: '未激活', statusId: 'inactive' };
  }
}
