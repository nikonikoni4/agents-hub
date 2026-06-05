/**
 * Session Store
 *
 * 职责：
 * - 存储项目分组的 sessions
 * - 管理当前活跃的 session
 * - 提供更新 session 的操作
 *
 * 架构约束：
 * - 不包含副作用（API 调用在 hooks 中）
 * - 纯状态管理
 */

import { create } from 'zustand';
import { ProjectGroup, SessionItem } from '@/shared/adapters/sessionAdapter';

interface SessionState {
  /** 按项目分组的 sessions */
  projectGroups: ProjectGroup[];
  /** 当前活跃的 session ID */
  activeSessionId: string | null;
  /** 最近一次选择 session 的时间戳 */
  lastSelectedAt: number;

  // Actions
  /** 设置项目分组 */
  setProjectGroups: (groups: ProjectGroup[]) => void;
  /** 选择 session */
  selectSession: (sessionId: string) => void;
  /** 更新某个 session 的数据 */
  updateSession: (sessionId: string, updates: Partial<SessionItem>) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  projectGroups: [],
  activeSessionId: null,
  lastSelectedAt: 0,

  setProjectGroups: (groups) => set({ projectGroups: groups }),

  selectSession: (sessionId) => set({ activeSessionId: sessionId, lastSelectedAt: Date.now() }),

  updateSession: (sessionId, updates) =>
    set((state) => ({
      projectGroups: state.projectGroups.map((group) => ({
        ...group,
        sessions: group.sessions.map((s) => (s.id === sessionId ? { ...s, ...updates } : s)),
      })),
    })),
}));
