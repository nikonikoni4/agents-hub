/**
 * useLoopStatus Hook
 *
 * 职责：
 * - 管理 Loop 状态的加载和刷新
 * - 提供 Loop 切换操作方法
 * - 监听 WebSocket refresh 信号自动刷新（防抖处理，避免高频信号导致冗余请求）
 *
 * 架构约束：
 * - 状态存储在 loopStore 中，所有调用方共享同一份数据
 * - 管理副作用（API 调用、WebSocket 订阅）
 * - 使用 AbortController 防止并发请求导致的状态竞争
 * - WebSocket refresh 信号经过两级防抖：WebSocketManager(300ms) + useLoopStatus(500ms)
 */

import { useEffect, useCallback, useRef } from 'react';
import { getLoops, getActiveLoop, getLoop } from '@/core/api/groupChatApi';
import { wsManager } from '@/core/websocket/WebSocketManager';
import { useLoopStore } from '../store/loopStore';
import type { RefreshSignal } from '@/shared/types';

/** WebSocket refresh 信号防抖间隔（ms） */
const REFRESH_DEBOUNCE_MS = 500;

export function useLoopStatus(chatId: string | null) {
  const loops = useLoopStore((s) => s.loops);
  const selectedLoop = useLoopStore((s) => s.selectedLoop);
  const execution = useLoopStore((s) => s.execution);
  const isLoading = useLoopStore((s) => s.isLoading);
  const error = useLoopStore((s) => s.error);
  const setChatId = useLoopStore((s) => s.setChatId);
  const setLoops = useLoopStore((s) => s.setLoops);
  const setSelectedLoop = useLoopStore((s) => s.setSelectedLoop);
  const setExecution = useLoopStore((s) => s.setExecution);
  const setIsLoading = useLoopStore((s) => s.setIsLoading);
  const setError = useLoopStore((s) => s.setError);

  // 用于取消之前的请求，防止并发竞争
  const abortControllerRef = useRef<AbortController | null>(null);
  // 防抖定时器：合并高频 WebSocket refresh 信号
  const refreshDebounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 取消之前的请求
  const cancelPendingRequests = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // 刷新 Loop 列表
  const refreshLoops = useCallback(async () => {
    if (!chatId) {
      setLoops([]);
      setSelectedLoop(null);
      setExecution(null);
      setError(null);
      return;
    }

    // 取消之前的请求，防止并发竞争
    cancelPendingRequests();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setError(null);
    try {
      const data = await getLoops(chatId, controller.signal);
      // 检查请求是否已被取消
      if (!controller.signal.aborted) {
        setLoops(data.loops);
      }
    } catch (err) {
      // 忽略 AbortError（请求被取消）
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      if (!controller.signal.aborted) {
        const message = err instanceof Error ? err.message : '加载 Loop 列表失败';
        setError(message);
        console.error('Failed to load loops:', err);
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, [
    chatId,
    setLoops,
    setSelectedLoop,
    setExecution,
    setIsLoading,
    setError,
    cancelPendingRequests,
  ]);

  // 加载激活的 Loop（定义 + 执行状态）
  const loadActiveLoop = useCallback(async () => {
    if (!chatId) {
      setSelectedLoop(null);
      setExecution(null);
      return;
    }

    // 取消之前的请求，防止并发竞争
    cancelPendingRequests();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    try {
      const data = await getActiveLoop(chatId, controller.signal);
      // 检查请求是否已被取消
      if (!controller.signal.aborted) {
        setSelectedLoop(data.loop);
        setExecution(data.execution);
      }
    } catch (err) {
      // 忽略 AbortError（请求被取消）
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }
      if (!controller.signal.aborted) {
        const message = err instanceof Error ? err.message : '加载激活 Loop 失败';
        setError(message);
        console.error('Failed to load active loop:', err);
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
      }
    }
  }, [chatId, setSelectedLoop, setExecution, setError, setIsLoading, cancelPendingRequests]);

  // 切换到指定 Loop
  const selectLoop = useCallback(
    async (loopId: string) => {
      if (!chatId) return;

      // 取消之前的请求，防止并发竞争
      cancelPendingRequests();
      const controller = new AbortController();
      abortControllerRef.current = controller;

      setIsLoading(true);
      try {
        const data = await getLoop(chatId, loopId, controller.signal);
        // 检查请求是否已被取消
        if (!controller.signal.aborted) {
          setSelectedLoop(data.loop);
          setExecution(data.execution);
        }
      } catch (err) {
        // 忽略 AbortError（请求被取消）
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        if (!controller.signal.aborted) {
          const message = err instanceof Error ? err.message : '加载 Loop 失败';
          setError(message);
          console.error('Failed to load loop:', err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [chatId, setSelectedLoop, setExecution, setError, setIsLoading, cancelPendingRequests]
  );

  // 防抖版 loadActiveLoop：合并高频 WebSocket refresh 信号，减少冗余 API 请求
  const debouncedLoadActiveLoop = useCallback(() => {
    if (refreshDebounceTimerRef.current !== null) {
      clearTimeout(refreshDebounceTimerRef.current);
    }
    refreshDebounceTimerRef.current = setTimeout(() => {
      refreshDebounceTimerRef.current = null;
      loadActiveLoop();
    }, REFRESH_DEBOUNCE_MS);
  }, [loadActiveLoop]);

  // chatId 变化时自动加载（串行执行，避免并发竞争）
  useEffect(() => {
    setChatId(chatId);
    // 串行执行，避免两个请求同时操作 isLoading
    const loadData = async () => {
      await refreshLoops();
      await loadActiveLoop();
    };
    loadData();
  }, [chatId, setChatId, refreshLoops, loadActiveLoop]);

  // 监听 WebSocket refresh 信号（防抖处理）
  useEffect(() => {
    if (!chatId) return;

    const handleRefresh = (data?: unknown) => {
      const signal = data as RefreshSignal;
      // 只响应当前群聊的刷新信号
      if (signal?.group_chat_id === chatId) {
        debouncedLoadActiveLoop();
      }
    };

    wsManager.on('refresh', handleRefresh);

    return () => {
      wsManager.off('refresh', handleRefresh);
      // 清理防抖定时器
      if (refreshDebounceTimerRef.current !== null) {
        clearTimeout(refreshDebounceTimerRef.current);
        refreshDebounceTimerRef.current = null;
      }
      // 组件卸载时取消所有待处理的请求
      cancelPendingRequests();
    };
  }, [chatId, debouncedLoadActiveLoop, cancelPendingRequests]);

  return {
    loops,
    selectedLoop,
    execution,
    isLoading,
    error,
    refreshLoops,
    loadActiveLoop,
    selectLoop,
  };
}
