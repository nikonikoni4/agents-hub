/**
 * Loop Store
 *
 * 职责：
 * - 存储当前活跃会话的 Loop 状态（列表、当前选中、执行状态）
 * - 保证所有组件共享同一份 Loop 状态
 *
 * 架构约束：
 * - 不包含副作用（API 调用在 useLoopStatus hook 中）
 * - 纯状态管理
 */

import { create } from 'zustand';
import type { LoopDetailApiResponse, LoopExecutionApiItem } from '@/shared/adapters';

interface LoopState {
  /** 当前活跃 chatId */
  chatId: string | null;
  /** Loop 定义列表 */
  loops: LoopDetailApiResponse[];
  /** 当前选中的 Loop */
  selectedLoop: LoopDetailApiResponse | null;
  /** 当前选中 Loop 的执行状态 */
  execution: LoopExecutionApiItem | null;
  /** 是否加载中 */
  isLoading: boolean;
  /** 错误信息（API 调用失败时设置） */
  error: string | null;

  // Actions
  /** 设置 chatId（切换会话时调用） */
  setChatId: (chatId: string | null) => void;
  /** 替换整个 Loop 列表 */
  setLoops: (loops: LoopDetailApiResponse[]) => void;
  /** 设置当前选中的 Loop */
  setSelectedLoop: (loop: LoopDetailApiResponse | null) => void;
  /** 设置执行状态 */
  setExecution: (execution: LoopExecutionApiItem | null) => void;
  /** 设置加载状态 */
  setIsLoading: (loading: boolean) => void;
  /** 设置错误信息 */
  setError: (error: string | null) => void;
}

export const useLoopStore = create<LoopState>((set) => ({
  chatId: null,
  loops: [],
  selectedLoop: null,
  execution: null,
  isLoading: false,
  error: null,

  setChatId: (chatId) => set({ chatId }),
  setLoops: (loops) => set({ loops }),
  setSelectedLoop: (loop) => set({ selectedLoop: loop }),
  setExecution: (execution) => set({ execution }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
}));
