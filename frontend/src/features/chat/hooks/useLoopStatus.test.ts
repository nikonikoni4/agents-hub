/**
 * useLoopStatus Hook 测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useLoopStatus } from './useLoopStatus';
import { useLoopStore } from '../store/loopStore';
import type { LoopDetailApiResponse, LoopExecutionApiItem } from '@/shared/types';

// Mock API 函数
vi.mock('@/core/api/groupChatApi', () => ({
  getLoops: vi.fn(),
  getActiveLoop: vi.fn(),
  getLoop: vi.fn(),
}));

// Mock WebSocket Manager
vi.mock('@/core/websocket/WebSocketManager', () => ({
  wsManager: {
    on: vi.fn(),
    off: vi.fn(),
  },
}));

import { getLoops, getActiveLoop, getLoop } from '@/core/api/groupChatApi';
import { wsManager } from '@/core/websocket/WebSocketManager';

const mockGetLoops = vi.mocked(getLoops);
const mockGetActiveLoop = vi.mocked(getActiveLoop);
const mockGetLoop = vi.mocked(getLoop);
const mockWsManager = vi.mocked(wsManager);

describe('useLoopStatus', () => {
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

  beforeEach(() => {
    vi.clearAllMocks();
    // 重置 store
    useLoopStore.setState({
      chatId: null,
      loops: [],
      selectedLoop: null,
      execution: null,
      isLoading: false,
      error: null,
    });
  });

  describe('chatId 变化时自动加载', () => {
    it('chatId 为 null 时清空状态', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: null });

      // Act
      renderHook(() => useLoopStatus(null));

      // Assert
      await waitFor(() => {
        const state = useLoopStore.getState();
        expect(state.loops).toEqual([]);
        expect(state.selectedLoop).toBeNull();
        expect(state.execution).toBeNull();
      });
    });

    it('chatId 变化时加载 loops 和 activeLoop', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [mockLoop] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: mockExecution });

      // Act
      renderHook(() => useLoopStatus('chat-1'));

      // Assert
      await waitFor(() => {
        const state = useLoopStore.getState();
        expect(state.loops).toHaveLength(1);
        expect(state.selectedLoop).toEqual(mockLoop);
        expect(state.execution).toEqual(mockExecution);
      });
    });
  });

  describe('refreshLoops', () => {
    it('刷新 Loop 列表并更新 store', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [mockLoop] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: null });

      const { result } = renderHook(() => useLoopStatus('chat-1'));

      // 等待初始加载完成
      await waitFor(() => {
        expect(useLoopStore.getState().loops).toHaveLength(1);
      });

      // 修改 mock 返回新数据
      const newLoop = { ...mockLoop, loop_id: 'loop-2', name: '新循环' };
      mockGetLoops.mockResolvedValue({ loops: [mockLoop, newLoop] });

      // Act
      await act(async () => {
        await result.current.refreshLoops();
      });

      // Assert
      expect(useLoopStore.getState().loops).toHaveLength(2);
      expect(useLoopStore.getState().loops[1]!.loop_id).toBe('loop-2');
    });

    it('API 失败时不影响现有状态但暴露 error', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [mockLoop] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: null });

      const { result } = renderHook(() => useLoopStatus('chat-1'));

      await waitFor(() => {
        expect(useLoopStore.getState().loops).toHaveLength(1);
      });

      // 让下次调用失败
      mockGetLoops.mockRejectedValueOnce(new Error('网络错误'));

      // Act
      await act(async () => {
        await result.current.refreshLoops();
      });

      // Assert - 原有数据不变，但 error 被设置
      expect(useLoopStore.getState().loops).toHaveLength(1);
      expect(useLoopStore.getState().error).toBe('网络错误');
      expect(result.current.error).toBe('网络错误');
    });
  });

  describe('loadActiveLoop', () => {
    it('加载激活的 Loop 和执行状态', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: mockExecution });

      const { result } = renderHook(() => useLoopStatus('chat-1'));

      // Act
      await act(async () => {
        await result.current.loadActiveLoop();
      });

      // Assert
      expect(useLoopStore.getState().selectedLoop).toEqual(mockLoop);
      expect(useLoopStore.getState().execution).toEqual(mockExecution);
    });
  });

  describe('selectLoop', () => {
    it('切换到指定 Loop', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: null });
      const targetLoop = { ...mockLoop, loop_id: 'loop-2', name: '目标循环' };
      mockGetLoop.mockResolvedValue({ loop: targetLoop, execution: mockExecution });

      const { result } = renderHook(() => useLoopStatus('chat-1'));

      // 等待初始加载完成
      await waitFor(() => {
        expect(mockGetActiveLoop).toHaveBeenCalled();
      });

      // Act
      await act(async () => {
        await result.current.selectLoop('loop-2');
      });

      // Assert
      expect(useLoopStore.getState().selectedLoop).toEqual(targetLoop);
      expect(useLoopStore.getState().execution).toEqual(mockExecution);
      expect(mockGetLoop).toHaveBeenCalledWith('chat-1', 'loop-2', expect.any(AbortSignal));
    });
  });

  describe('WebSocket refresh 监听', () => {
    it('注册 refresh 事件监听', () => {
      // Act
      renderHook(() => useLoopStatus('chat-1'));

      // Assert
      expect(mockWsManager.on).toHaveBeenCalledWith('refresh', expect.any(Function));
    });

    it('chatId 变化时注销旧监听并注册新监听', () => {
      // Arrange
      const { rerender } = renderHook(({ chatId }) => useLoopStatus(chatId), {
        initialProps: { chatId: 'chat-1' },
      });

      // Act
      rerender({ chatId: 'chat-2' });

      // Assert - 旧的被注销，新的被注册
      expect(mockWsManager.off).toHaveBeenCalledWith('refresh', expect.any(Function));
      expect(mockWsManager.on).toHaveBeenCalledTimes(2);
    });

    it('收到匹配的 refresh 信号时刷新 activeLoop', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: mockExecution });

      renderHook(() => useLoopStatus('chat-1'));

      // 捕获注册的 handler
      const handler = mockWsManager.on.mock.calls.find((call) => call[0] === 'refresh')![1] as (
        data?: unknown
      ) => void;

      // 修改 mock 返回新数据
      const updatedExecution = { ...mockExecution, current_iteration: 3 };
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: updatedExecution });

      // Act - 模拟收到 refresh 信号
      await act(async () => {
        handler({ group_chat_id: 'chat-1' });
      });

      // Assert
      await waitFor(() => {
        expect(useLoopStore.getState().execution?.current_iteration).toBe(3);
      });
    });

    it('收到不匹配的 refresh 信号时不刷新', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: mockExecution });

      renderHook(() => useLoopStatus('chat-1'));

      await waitFor(() => {
        expect(mockGetActiveLoop).toHaveBeenCalledTimes(1);
      });

      const handler = mockWsManager.on.mock.calls.find((call) => call[0] === 'refresh')?.[1] as (
        data?: unknown
      ) => void;

      // Act - 收到不匹配的信号
      await act(async () => {
        handler?.({ group_chat_id: 'chat-其他' });
      });

      // Assert - 没有额外调用
      expect(mockGetActiveLoop).toHaveBeenCalledTimes(1);
    });
  });

  describe('返回值', () => {
    it('返回所有状态和方法', async () => {
      // Arrange
      mockGetLoops.mockResolvedValue({ loops: [mockLoop] });
      mockGetActiveLoop.mockResolvedValue({ loop: mockLoop, execution: mockExecution });

      const { result } = renderHook(() => useLoopStatus('chat-1'));

      // Assert
      await waitFor(() => {
        expect(result.current.loops).toBeDefined();
        expect(result.current.selectedLoop).toBeDefined();
        expect(result.current.execution).toBeDefined();
        expect(result.current.isLoading).toBeDefined();
        expect(result.current.error).toBeDefined();
        expect(typeof result.current.refreshLoops).toBe('function');
        expect(typeof result.current.loadActiveLoop).toBe('function');
        expect(typeof result.current.selectLoop).toBe('function');
      });
    });
  });
});
