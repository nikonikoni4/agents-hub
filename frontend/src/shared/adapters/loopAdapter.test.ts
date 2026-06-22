/**
 * loopAdapter 测试
 */

import { describe, it, expect } from 'vitest';
import { getNodeStatus, getExecutionStatusText } from './loopAdapter';
import type { LoopExecutionApiItem } from '@/shared/types';

describe('loopAdapter', () => {
  const mockExecution: LoopExecutionApiItem = {
    execution_id: 'exec-1',
    status: 'running',
    current_iteration: 2,
    current_node_index: 1,
    error_message: null,
  };

  describe('getNodeStatus', () => {
    it('execution 为 null 时返回 pending', () => {
      expect(getNodeStatus(0, null)).toBe('pending');
    });

    it('节点索引小于 current_node_index 返回 completed', () => {
      expect(getNodeStatus(0, mockExecution)).toBe('completed');
    });

    it('节点索引等于 current_node_index 返回 current', () => {
      expect(getNodeStatus(1, mockExecution)).toBe('current');
    });

    it('节点索引大于 current_node_index 返回 pending', () => {
      expect(getNodeStatus(2, mockExecution)).toBe('pending');
    });
  });

  describe('getExecutionStatusText', () => {
    it('execution 为 null 时返回未激活', () => {
      const result = getExecutionStatusText(null);
      expect(result.text).toBe('未激活');
      expect(result.statusId).toBe('inactive');
    });

    it('created 状态返回正确文本', () => {
      const result = getExecutionStatusText({ ...mockExecution, status: 'created' });
      expect(result.text).toBe('已创建');
      expect(result.statusId).toBe('created');
    });

    it('running 状态返回正确文本', () => {
      const result = getExecutionStatusText(mockExecution);
      expect(result.text).toBe('运行中');
      expect(result.statusId).toBe('running');
    });

    it('paused 状态返回正确文本', () => {
      const result = getExecutionStatusText({ ...mockExecution, status: 'paused' });
      expect(result.text).toBe('已暂停');
      expect(result.statusId).toBe('paused');
    });

    it('completed 状态返回正确文本', () => {
      const result = getExecutionStatusText({ ...mockExecution, status: 'completed' });
      expect(result.text).toBe('已完成');
      expect(result.statusId).toBe('completed');
    });

    it('failed 状态返回正确文本', () => {
      const result = getExecutionStatusText({ ...mockExecution, status: 'failed' });
      expect(result.text).toBe('失败');
      expect(result.statusId).toBe('failed');
    });
  });
});
