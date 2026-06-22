/**
 * loopStore 测试
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useLoopStore } from './loopStore';
import type { LoopDetailApiResponse, LoopExecutionApiItem } from '@/shared/types';

describe('loopStore', () => {
  beforeEach(() => {
    // 每个测试前重置 store
    useLoopStore.setState({
      chatId: null,
      loops: [],
      selectedLoop: null,
      execution: null,
      isLoading: false,
      error: null,
    });
  });

  const mockLoop: LoopDetailApiResponse = {
    loop_id: 'loop-1',
    name: '测试循环',
    nodes: [],
    max_iterations: 5,
  };

  const mockExecution: LoopExecutionApiItem = {
    execution_id: 'exec-1',
    status: 'running',
    current_iteration: 2,
    current_node_index: 0,
    error_message: null,
  };

  describe('初始状态', () => {
    it('默认状态正确', () => {
      const state = useLoopStore.getState();
      expect(state.chatId).toBeNull();
      expect(state.loops).toEqual([]);
      expect(state.selectedLoop).toBeNull();
      expect(state.execution).toBeNull();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBeNull();
    });
  });

  describe('setChatId', () => {
    it('设置 chatId', () => {
      useLoopStore.getState().setChatId('chat-1');
      expect(useLoopStore.getState().chatId).toBe('chat-1');
    });

    it('设置 chatId 为 null', () => {
      useLoopStore.getState().setChatId('chat-1');
      useLoopStore.getState().setChatId(null);
      expect(useLoopStore.getState().chatId).toBeNull();
    });
  });

  describe('setLoops', () => {
    it('替换 Loop 列表', () => {
      const loops = [mockLoop, { ...mockLoop, loop_id: 'loop-2' }];
      useLoopStore.getState().setLoops(loops);
      expect(useLoopStore.getState().loops).toHaveLength(2);
      expect(useLoopStore.getState().loops[0]!.loop_id).toBe('loop-1');
    });

    it('设置空列表', () => {
      useLoopStore.getState().setLoops([mockLoop]);
      useLoopStore.getState().setLoops([]);
      expect(useLoopStore.getState().loops).toEqual([]);
    });
  });

  describe('setSelectedLoop', () => {
    it('设置当前选中的 Loop', () => {
      useLoopStore.getState().setSelectedLoop(mockLoop);
      expect(useLoopStore.getState().selectedLoop).toEqual(mockLoop);
    });

    it('清除选中的 Loop', () => {
      useLoopStore.getState().setSelectedLoop(mockLoop);
      useLoopStore.getState().setSelectedLoop(null);
      expect(useLoopStore.getState().selectedLoop).toBeNull();
    });
  });

  describe('setExecution', () => {
    it('设置执行状态', () => {
      useLoopStore.getState().setExecution(mockExecution);
      expect(useLoopStore.getState().execution).toEqual(mockExecution);
      expect(useLoopStore.getState().execution!.status).toBe('running');
    });

    it('清除执行状态', () => {
      useLoopStore.getState().setExecution(mockExecution);
      useLoopStore.getState().setExecution(null);
      expect(useLoopStore.getState().execution).toBeNull();
    });
  });

  describe('setIsLoading', () => {
    it('设置加载状态', () => {
      useLoopStore.getState().setIsLoading(true);
      expect(useLoopStore.getState().isLoading).toBe(true);
    });

    it('清除加载状态', () => {
      useLoopStore.getState().setIsLoading(true);
      useLoopStore.getState().setIsLoading(false);
      expect(useLoopStore.getState().isLoading).toBe(false);
    });
  });

  describe('setError', () => {
    it('设置错误信息', () => {
      useLoopStore.getState().setError('网络错误');
      expect(useLoopStore.getState().error).toBe('网络错误');
    });

    it('清除错误信息', () => {
      useLoopStore.getState().setError('网络错误');
      useLoopStore.getState().setError(null);
      expect(useLoopStore.getState().error).toBeNull();
    });
  });
});
