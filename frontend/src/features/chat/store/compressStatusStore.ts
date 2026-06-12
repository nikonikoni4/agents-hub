/**
 * Compress Status Store
 *
 * 职责：
 * - 追踪哪些 agent 正在压缩上下文
 * - 追踪是否正在全量压缩所有 agent
 * - 供 ChatArea 显示"正在压缩"临时系统消息
 * - 供 RightSidebar 等其他组件读取压缩状态
 *
 * 架构约束：
 * - 纯状态管理，不含副作用
 * - Set 引用每次更新时新建，确保 Zustand 触发 re-render
 */

import { create } from 'zustand';

interface CompressStatusState {
  /** 当前正在压缩的 agent 名称集合 */
  pendingAgents: Set<string>;
  /** 是否正在全量压缩所有 agent */
  isCompressingAll: boolean;
  /** 标记某 agent 开始压缩 */
  startCompress: (agentName: string) => void;
  /** 标记某 agent 压缩结束 */
  finishCompress: (agentName: string) => void;
  /** 标记开始全量压缩 */
  startCompressAll: () => void;
  /** 标记全量压缩结束 */
  finishCompressAll: () => void;
}

export const useCompressStatusStore = create<CompressStatusState>((set) => ({
  pendingAgents: new Set(),
  isCompressingAll: false,
  startCompress: (agentName) =>
    set((state) => {
      const next = new Set(state.pendingAgents);
      next.add(agentName);
      console.log('[CompressStore] startCompress:', agentName, 'pendingAgents:', Array.from(next));
      return { pendingAgents: next };
    }),
  finishCompress: (agentName) =>
    set((state) => {
      const next = new Set(state.pendingAgents);
      next.delete(agentName);
      console.log('[CompressStore] finishCompress:', agentName, 'pendingAgents:', Array.from(next));
      return { pendingAgents: next };
    }),
  startCompressAll: () => {
    console.log('[CompressStore] startCompressAll');
    return set({ isCompressingAll: true });
  },
  finishCompressAll: () => {
    console.log('[CompressStore] finishCompressAll');
    return set({ isCompressingAll: false });
  },
}));
